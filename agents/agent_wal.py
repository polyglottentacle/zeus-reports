"""
agent_wal.py — Zeus Sense #7: WAL Reader (Apollo Memory)

Legge il Write-Ahead Log (blockchain di trade) di Black/White Apollo e
restituisce le metriche di performance REALE: win rate, PnL, drawdown vivo.

Fonti (in ordine di priorità):
  1. APOLLO_WAL_PATH  — file locale/montato (path completo al WAL JSON-L)
  2. APOLLO_API_URL   — REST API di Apollo (porta 23112 Black / 5600 White)
  3. APOLLO_WAL_JSON  — stringa JSON grezza (per test/debug)

Se nessuna fonte è disponibile → status="unavailable", mai crash.

Contratto di output:
  {
    "sense": "wal",
    "status": "ok" | "unavailable" | "error",
    "source": "file" | "api" | "demo",
    "timestamp": "...",
    "apollo": {
      "black": { "win_rate_7d": 0.0, "win_rate_30d": 0.0, "pnl_today": 0.0, "pnl_30d": 0.0,
                 "trades_7d": 0, "trades_30d": 0, "open_positions": 0,
                 "mode": "SHADOW", "last_trade": null, "drawdown_live": 0.0 },
      "white": { ... same ... }
    },
    "combined": {
      "win_rate_7d": 0.0, "pnl_today": 0.0, "total_trades": 0, "verdict": "SHADOW"
    },
    "verdict": "SHADOW" | "WINNING" | "LOSING" | "CAUTION",
    "message": "..."
  }
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError


# ─── CONFIG ─────────────────────────────────────────────────────────────────

APOLLO_WAL_PATH = os.environ.get("APOLLO_WAL_PATH", "")           # path file WAL locale
APOLLO_API_URL_BLACK = os.environ.get("APOLLO_API_URL_BLACK", "")  # es. http://1.2.3.4:23112
APOLLO_API_URL_WHITE = os.environ.get("APOLLO_API_URL_WHITE", "")  # es. http://1.2.3.4:5600
APOLLO_WAL_JSON = os.environ.get("APOLLO_WAL_JSON", "")            # JSON grezzo override

_API_TIMEOUT = 8  # secondi


# ─── PARSE HELPERS ──────────────────────────────────────────────────────────

def _parse_wal_lines(lines: List[str]) -> List[dict]:
    """Parsea JSON-Lines WAL. Ogni riga = una entry. Ignora righe malformate."""
    entries = []
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                entries.append(obj)
        except Exception:
            pass
    return entries


def _parse_wal_array(data: Any) -> List[dict]:
    """Accetta JSON array o singolo oggetto WAL."""
    if isinstance(data, list):
        return [e for e in data if isinstance(e, dict)]
    if isinstance(data, dict):
        # Potrebbe essere {"trades": [...]} o {"wal": [...]}
        for key in ("trades", "wal", "entries", "log", "history"):
            if isinstance(data.get(key), list):
                return [e for e in data[key] if isinstance(e, dict)]
        return [data]
    return []


def _is_trade_entry(e: dict) -> bool:
    """True se l'entry rappresenta un trade chiuso."""
    has_result = any(k in e for k in ("profit", "pnl", "result", "win", "loss", "close_price"))
    has_action = e.get("action") in ("CLOSE", "SELL", "BUY_CLOSE", "TRADE_CLOSE", "closed") if "action" in e else True
    return has_result or has_action


def _entry_timestamp(e: dict) -> Optional[datetime]:
    """Estrae il timestamp dall'entry WAL."""
    for key in ("timestamp", "close_time", "time", "date", "ts", "created_at"):
        val = e.get(key)
        if val is None:
            continue
        try:
            if isinstance(val, (int, float)):
                # unix ms o seconds
                ts = val / 1000 if val > 1e10 else val
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            if isinstance(val, str):
                # prova ISO format
                val_clean = val.replace("Z", "+00:00")
                return datetime.fromisoformat(val_clean)
        except Exception:
            pass
    return None


def _entry_profit(e: dict) -> float:
    """Estrae il profitto (in USDT o %) dall'entry WAL."""
    for key in ("profit_usdt", "pnl", "profit", "pnl_usdt", "realized_pnl", "net_pnl"):
        v = e.get(key)
        if v is not None:
            try:
                return float(v)
            except Exception:
                pass
    # fallback: calcolo da entry/exit price
    for entry_k, exit_k in (("entry_price", "exit_price"), ("open_price", "close_price")):
        ep = e.get(entry_k)
        xp = e.get(exit_k)
        side = str(e.get("side", "long")).lower()
        size = e.get("size") or e.get("qty") or e.get("quantity") or 1
        if ep and xp:
            try:
                ep, xp, size = float(ep), float(xp), float(size)
                pnl = (xp - ep) * size if side == "long" else (ep - xp) * size
                return pnl
            except Exception:
                pass
    return 0.0


def _is_win(e: dict) -> bool:
    """True se il trade è stato vincente."""
    # campo diretto
    win = e.get("win") or e.get("is_win") or e.get("won")
    if win is not None:
        return bool(win)
    result = str(e.get("result", "")).lower()
    if result in ("win", "profit", "positive", "true", "1"):
        return True
    if result in ("loss", "loss", "negative", "false", "0"):
        return False
    # fallback: profitto positivo
    return _entry_profit(e) > 0


# ─── METRICS CALCULATOR ─────────────────────────────────────────────────────

def _compute_metrics(entries: List[dict]) -> dict:
    """Calcola metriche da una lista di entry WAL parsed."""
    now = datetime.now(tz=timezone.utc)
    cutoff_7d  = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    trades_7d, trades_30d = [], []
    pnl_today = 0.0
    open_positions = 0
    last_trade = None

    for e in entries:
        # Conta posizioni aperte
        if e.get("status") in ("open", "OPEN", "active", "ACTIVE"):
            open_positions += 1
            continue

        if not _is_trade_entry(e):
            continue

        ts = _entry_timestamp(e)
        profit = _entry_profit(e)
        is_win = _is_win(e)

        trade_rec = {
            "ts": ts.isoformat() if ts else None,
            "profit": profit,
            "win": is_win,
        }

        if ts:
            if ts >= cutoff_30d:
                trades_30d.append(trade_rec)
            if ts >= cutoff_7d:
                trades_7d.append(trade_rec)
            if ts >= today_start:
                pnl_today += profit

        if last_trade is None or (ts and (last_trade["ts"] or "") < ts.isoformat()):
            last_trade = trade_rec

    win_rate_7d  = (sum(1 for t in trades_7d  if t["win"]) / len(trades_7d))  if trades_7d  else 0.0
    win_rate_30d = (sum(1 for t in trades_30d if t["win"]) / len(trades_30d)) if trades_30d else 0.0
    pnl_30d = sum(t["profit"] for t in trades_30d)

    # Drawdown live: massima perdita cumulativa dal picco (ultime 30gg)
    peak = 0.0
    cum  = 0.0
    max_dd = 0.0
    for t in sorted(trades_30d, key=lambda x: x["ts"] or ""):
        cum += t["profit"]
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd

    return {
        "win_rate_7d":    round(win_rate_7d, 4),
        "win_rate_30d":   round(win_rate_30d, 4),
        "pnl_today":      round(pnl_today, 4),
        "pnl_30d":        round(pnl_30d, 4),
        "trades_7d":      len(trades_7d),
        "trades_30d":     len(trades_30d),
        "open_positions": open_positions,
        "drawdown_live":  round(max_dd, 4),
        "last_trade":     last_trade,
    }


def _blank_metrics(mode: str = "SHADOW") -> dict:
    return {
        "win_rate_7d": 0.0, "win_rate_30d": 0.0,
        "pnl_today": 0.0, "pnl_30d": 0.0,
        "trades_7d": 0, "trades_30d": 0,
        "open_positions": 0, "drawdown_live": 0.0,
        "mode": mode, "last_trade": None,
    }


# ─── DATA FETCH ─────────────────────────────────────────────────────────────

def _fetch_from_file() -> Optional[List[dict]]:
    """Legge il WAL da file locale (JSON-Lines o JSON array)."""
    if not APOLLO_WAL_PATH:
        return None
    p = Path(APOLLO_WAL_PATH)
    if not p.exists():
        return None
    try:
        text = p.read_text(encoding="utf-8")
        # Prova JSON array prima
        try:
            data = json.loads(text)
            return _parse_wal_array(data)
        except json.JSONDecodeError:
            pass
        # Prova JSON-Lines
        return _parse_wal_lines(text.splitlines())
    except Exception:
        return None


def _fetch_from_api(base_url: str) -> Optional[dict]:
    """Chiama API Apollo (read-only endpoints) e ritorna dict grezzo."""
    if not base_url:
        return None
    base_url = base_url.rstrip("/")
    # Endpoint candidati Apollo / Freqtrade-compatible
    endpoints = [
        "/api/v1/trades?limit=500",   # Freqtrade standard
        "/api/v1/status",
        "/api/trades",
        "/api/wal",
        "/api/report",
        "/trades",
        "/status",
    ]
    for ep in endpoints:
        url = base_url + ep
        try:
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=_API_TIMEOUT) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data
        except (URLError, Exception):
            continue
    return None


def _fetch_from_json_env() -> Optional[List[dict]]:
    """Legge WAL da variabile d'ambiente APOLLO_WAL_JSON (debug/test)."""
    if not APOLLO_WAL_JSON:
        return None
    try:
        data = json.loads(APOLLO_WAL_JSON)
        return _parse_wal_array(data)
    except Exception:
        return None


# ─── VERDICT ────────────────────────────────────────────────────────────────

def _compute_verdict(black: dict, white: dict) -> str:
    """Sintesi delle performance Apollo → verdict Zeus."""
    total_trades = black.get("trades_7d", 0) + white.get("trades_7d", 0)
    if total_trades == 0:
        return "SHADOW"     # nessun trade reale → modalità shadow

    # Media pesata per numero di trade
    b_wr = black.get("win_rate_7d", 0.0)
    w_wr = white.get("win_rate_7d", 0.0)
    b_t  = black.get("trades_7d", 0)
    w_t  = white.get("trades_7d", 0)
    total = b_t + w_t
    combined_wr = (b_wr * b_t + w_wr * w_t) / total if total > 0 else 0.0

    pnl_today = black.get("pnl_today", 0.0) + white.get("pnl_today", 0.0)

    if combined_wr >= 0.55 and pnl_today >= 0:
        return "WINNING"
    if combined_wr < 0.40 or pnl_today < -50:
        return "LOSING"
    return "CAUTION"


# ─── MAIN ────────────────────────────────────────────────────────────────────

def read() -> Dict[str, Any]:
    """Legge lo stato di Apollo dalla fonte disponibile. Non crasha mai."""
    ts = datetime.now(tz=timezone.utc).isoformat()
    base = {
        "sense": "wal",
        "timestamp": ts,
        "source": "unavailable",
    }

    # ── ENV JSON override ──
    entries_env = _fetch_from_json_env()
    if entries_env is not None:
        m = _compute_metrics(entries_env)
        m["mode"] = "PAPER"
        verdict = _compute_verdict(m, _blank_metrics())
        return {**base,
                "status": "ok",
                "source": "env_json",
                "apollo": {"black": {**m, "mode": "PAPER"}, "white": _blank_metrics()},
                "combined": {
                    "win_rate_7d": m["win_rate_7d"],
                    "pnl_today": m["pnl_today"],
                    "total_trades": m["trades_7d"] + m["trades_30d"],
                    "verdict": verdict,
                },
                "verdict": verdict,
                "message": f"Apollo WAL caricato da APOLLO_WAL_JSON ({len(entries_env)} entries)."}

    # ── File locale ──
    entries_file = _fetch_from_file()
    if entries_file is not None:
        m = _compute_metrics(entries_file)
        m["mode"] = os.environ.get("APOLLO_MODE", "SHADOW")
        verdict = _compute_verdict(m, _blank_metrics())
        return {**base,
                "status": "ok",
                "source": "file",
                "apollo": {"black": {**m, "mode": m["mode"]}, "white": _blank_metrics()},
                "combined": {
                    "win_rate_7d": m["win_rate_7d"],
                    "pnl_today": m["pnl_today"],
                    "total_trades": m["trades_7d"] + m["trades_30d"],
                    "verdict": verdict,
                },
                "verdict": verdict,
                "message": f"WAL letto da file: {APOLLO_WAL_PATH} ({len(entries_file)} entries)."}

    # ── REST API Apollo Black ──
    black_metrics = _blank_metrics("SHADOW")
    white_metrics = _blank_metrics("SHADOW")
    source_used = "unavailable"

    api_black = _fetch_from_api(APOLLO_API_URL_BLACK)
    if api_black is not None:
        entries = _parse_wal_array(api_black)
        if entries:
            black_metrics = _compute_metrics(entries)
            black_metrics["mode"] = str(api_black.get("mode", "SHADOW"))
            source_used = "api_black"

    api_white = _fetch_from_api(APOLLO_API_URL_WHITE)
    if api_white is not None:
        entries = _parse_wal_array(api_white)
        if entries:
            white_metrics = _compute_metrics(entries)
            white_metrics["mode"] = str(api_white.get("mode", "SHADOW"))
            source_used = "api" if source_used == "api_black" else "api_white"

    if source_used != "unavailable":
        verdict = _compute_verdict(black_metrics, white_metrics)
        b_wr = black_metrics["win_rate_7d"]
        w_wr = white_metrics["win_rate_7d"]
        pnl_today = black_metrics["pnl_today"] + white_metrics["pnl_today"]
        return {**base,
                "status": "ok",
                "source": source_used,
                "apollo": {"black": black_metrics, "white": white_metrics},
                "combined": {
                    "win_rate_7d": round((b_wr + w_wr) / 2, 4),
                    "pnl_today": round(pnl_today, 4),
                    "total_trades": (black_metrics["trades_7d"] + white_metrics["trades_7d"]),
                    "verdict": verdict,
                },
                "verdict": verdict,
                "message": f"Apollo letto via API ({source_used})."}

    # ── Nessuna fonte disponibile ──
    return {**base,
            "status": "unavailable",
            "source": "none",
            "apollo": {"black": _blank_metrics(), "white": _blank_metrics()},
            "combined": {
                "win_rate_7d": 0.0, "pnl_today": 0.0,
                "total_trades": 0, "verdict": "SHADOW",
            },
            "verdict": "SHADOW",
            "message": (
                "WAL non disponibile. Imposta APOLLO_WAL_PATH (path al file WAL) "
                "o APOLLO_API_URL_BLACK / APOLLO_API_URL_WHITE (REST API Apollo)."
            )}


if __name__ == "__main__":
    import sys
    result = read()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["status"] in ("ok", "unavailable") else 1)
