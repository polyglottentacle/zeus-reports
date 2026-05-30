#!/usr/bin/env python3
"""
Hermes Briefing Agent — Zeus Trading System
Legge daily_report.json da GitHub e manda il briefing mattutino su Telegram.

Setup su Hermes:
  pip install requests
  export TELEGRAM_BOT_TOKEN="..."
  export TELEGRAM_CHAT_ID="..."
  export ZEUS_REPORT_URL="https://raw.githubusercontent.com/polyglottentacle/zeus-reports/main/output/daily_report.json"

Cron (08:05 UTC ogni giorno):
  5 8 * * * /usr/bin/python3 /opt/zeus/hermes/briefing.py >> /var/log/zeus_briefing.log 2>&1
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("ERROR: 'requests' non installato. Esegui: pip install requests")
    sys.exit(1)


def _load_dotenv(path: Path) -> None:
    """Carica .env in os.environ (robusto: ignora commenti/righe vuote,
    valori con '='). Non sovrascrive variabili già impostate."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip(), val.strip()
        if key and key not in os.environ:
            os.environ[key] = val


# Cerca .env nella root di Zeus (parent di hermes/)
_load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ── Configurazione ─────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
ZEUS_REPORT_URL = os.environ.get(
    "ZEUS_REPORT_URL",
    "https://raw.githubusercontent.com/polyglottentacle/zeus-reports/main/output/daily_report.json",
)
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


def fetch_report() -> dict:
    """Scarica daily_report.json da GitHub."""
    resp = requests.get(ZEUS_REPORT_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _fmt_float(val, decimals: int = 4) -> str:
    try:
        return f"{float(val):.{decimals}f}"
    except (TypeError, ValueError):
        return str(val) if val is not None else "n/d"


def _fmt_eur(val) -> str:
    try:
        return f"{float(val):.2f}€"
    except (TypeError, ValueError):
        return "n/d"


def format_message(report: dict) -> str:
    """Costruisce il messaggio Telegram con i dati del report."""
    ts = report.get("timestamp", "")[:16].replace("T", " ")

    # ── Backtest
    bs = report.get("backtest_summary", {})
    strategy = bs.get("strategy_name") or "n/d"
    sharpe = _fmt_float(bs.get("sharpe"), 3)
    trade_count = bs.get("trade_count") or bs.get("total_trades") or "n/d"
    profit_pct = _fmt_float(bs.get("profit_pct"), 2)
    drawdown = _fmt_float(bs.get("drawdown_pct") or bs.get("max_relative_drawdown"), 2)

    # ── Agenti
    dsr_data = report.get("dsr", {})
    dsr = _fmt_float(dsr_data.get("dsr"), 4)
    kelly_data = report.get("kelly", {})
    kelly = _fmt_float(kelly_data.get("kelly_fraction"), 4)
    max_pos = _fmt_eur(kelly_data.get("max_position_usdt"))
    win_rate = _fmt_float(kelly_data.get("win_rate"), 1) if kelly_data.get("win_rate") else "n/d"
    try:
        win_rate_pct = f"{float(kelly_data.get('win_rate', 0)) * 100:.1f}%"
    except (TypeError, ValueError):
        win_rate_pct = "n/d"

    costs_data = report.get("costs", {})
    comm = _fmt_eur(costs_data.get("commissioni_stimate"))
    slippage = _fmt_eur(costs_data.get("slippage_stimato"))
    tasse = _fmt_eur(costs_data.get("tassa_box3_stimata"))
    profit_netto = _fmt_eur(costs_data.get("profit_netto_stimato"))

    # ── MiroFish
    mf = report.get("mirofish", {})
    mf_status = mf.get("status", "n/d")
    mf_actions = mf.get("mirofish_run", {}).get("total_actions") or mf.get("total_actions") or "n/d"
    mf_scenarios = mf.get("scenario_count", "n/d")

    # ── 5 Sensi di Zeus
    senses = report.get("senses", {})
    def _sense_icon(verdict):
        if not verdict:
            return "⚪"
        v = str(verdict).upper()
        if "BULL" in v or "UP" in v or "EQUIL" in v:
            return "🟢"
        if "BEAR" in v or "DOWN" in v or "STRESS" in v or "EXTREME_FEAR" in v or "FEAR" in v:
            return "🔴"
        if "NEUTRAL" in v or "SIDEWAYS" in v:
            return "🟡"
        return "🔵"

    def _v(key):
        """Estrae verdict da senses[key] sia dict che stringa."""
        s = senses.get(key)
        if isinstance(s, dict):  return s.get("verdict") or s.get("classification") or "n/d"
        if isinstance(s, str):   return s
        return "n/d"

    udito_v = _v("udito")
    vista_v = _v("vista")
    prev_v  = _v("preveggenza")
    mem_v   = _v("memoria")
    eq_v    = _v("equilibrio")
    oc_v    = _v("occhi")
    oc_dec  = (senses.get("occhi") or {}).get("decision") if isinstance(senses.get("occhi"), dict) else None
    poly_v  = _v("polymarket")
    wal_data  = senses.get("wal") or {}
    wal_status = wal_data.get("status", "n/d")
    wal_verdict= wal_data.get("verdict", "n/d")
    wal_comb  = wal_data.get("combined", {})
    wal_wr    = wal_comb.get("win_rate_7d", 0)
    wal_pnl   = wal_comb.get("pnl_today", 0)
    btc_price = (senses.get("vista") or {}).get("last_price") if isinstance(senses.get("vista"), dict) else None
    fng_val   = (senses.get("udito") or {}).get("value") if isinstance(senses.get("udito"), dict) else None

    # ── Zeus Verdict (sintesi) ──
    zv_data    = report.get("zeus_verdict") or (report.get("strategy_status") or {}).get("zeus_verdict") or {}
    zv_verdict = zv_data.get("zeus_verdict", "—")
    zv_score   = zv_data.get("zeus_score", 0.0)
    zv_conf    = zv_data.get("zeus_confidence", 0.0)
    zv_msg     = zv_data.get("message", "")
    try:
        zv_conf_str = f"{float(zv_conf)*100:.0f}%"
    except Exception:
        zv_conf_str = "n/d"

    ZV_EMOJI = {"LONG": "🟢", "SHORT": "🔴", "FLAT": "🟡", "CAUTION": "🟠"}
    zv_icon = ZV_EMOJI.get(str(zv_verdict).upper(), "⚪")

    # Icona stato MiroFish
    mf_icon = "✅" if mf_status == "ok" else ("⚠️" if mf_status == "disabled" else "❌")

    # Icona WAL
    wal_icon = "✅" if wal_status == "ok" else ("⚠️" if wal_status == "unavailable" else "❌")

    btc_line = f"₿ `{btc_price:,.0f}` USDT" if btc_price else ""
    fng_line = f"F&G: `{fng_val}`" if fng_val else ""

    # WAL line
    if wal_status == "ok":
        wal_line = f"  Win 7d: `{wal_wr*100:.1f}%` | PnL oggi: `{wal_pnl:+.2f}` USDT | Apollo: `{wal_verdict}`"
    else:
        wal_line = f"  ⚠️ `APOLLO_WAL_PATH` non configurato — connetti Zeus al VPS"

    msg = (
        f"🔱 *Zeus Morning Briefing* — {ts} UTC\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{zv_icon} *ZEUS VERDICT: {zv_verdict}*\n"
        f"  Score: `{zv_score:+.3f}` | Conf: `{zv_conf_str}`\n"
        f"  {zv_msg}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"👁 *8 Sensi — Mercato adesso*\n"
        f"  {_sense_icon(udito_v)} 👂 Udito: `{udito_v}` {fng_line}\n"
        f"  {_sense_icon(vista_v)} 👁 Vista: `{vista_v}` {btc_line}\n"
        f"  {_sense_icon(prev_v)} 🔮 Preveggenza: `{prev_v}`\n"
        f"  {_sense_icon(mem_v)} 🧠 Memoria: `{mem_v}`\n"
        f"  {_sense_icon(eq_v)} ⚖️ Equilibrio: `{eq_v}` ({(senses.get('equilibrio') or {}).get('risk_regime','?')})\n"
        f"  {_sense_icon(oc_v)} 🤖 Occhi: `{oc_dec or oc_v or 'n/d'}`\n"
        f"  {_sense_icon(poly_v)} 🎯 Polymarket: `{poly_v}` ({(senses.get('polymarket') or {}).get('market_count',0)} mercati)\n"
        f"  {wal_icon} 🔗 WAL Apollo: `{wal_verdict}`\n"
        f"{wal_line}\n"
        f"\n"
        f"📊 *Backtest: {strategy}*\n"
        f"  Sharpe: `{sharpe}` | Profit: `{profit_pct}%`\n"
        f"  Drawdown: `{drawdown}` | Trade: `{trade_count}`\n"
        f"\n"
        f"🧮 *Agenti quant*\n"
        f"  DSR: `{dsr}` | Kelly: `{kelly}`\n"
        f"  Win rate: `{win_rate_pct}` | Max pos: `{max_pos}`\n"
        f"\n"
        f"💸 *Costi stimati*\n"
        f"  Commissioni: `{comm}` | Slippage: `{slippage}`\n"
        f"  Tasse: `{tasse}` | Netto stimato: `{profit_netto}`\n"
        f"\n"
        f"{mf_icon} *MiroFish sentiment*\n"
        f"  Status: `{mf_status}` | Azioni: `{mf_actions}` | Scenari: `{mf_scenarios}`\n"
        f"\n"
        f"🖥 MODE=PAPER · CONFIRM\\_LIVE\\_TRADING=NO"
    )
    return msg


def send_telegram(text: str) -> dict:
    """Invia il messaggio via Telegram Bot API."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise EnvironmentError(
            "TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID devono essere impostati come variabili d'ambiente."
        )
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    resp = requests.post(TELEGRAM_API, json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Zeus Briefing Agent avviato.")

    try:
        report = fetch_report()
        print(f"  Report scaricato da GitHub. timestamp: {report.get('timestamp', 'n/d')}")
    except Exception as exc:
        print(f"  ERRORE nel download del report: {exc}")
        sys.exit(1)

    message = format_message(report)
    print(f"  Messaggio formattato ({len(message)} caratteri).")

    try:
        result = send_telegram(message)
        if result.get("ok"):
            print(f"  ✅ Messaggio inviato su Telegram. message_id={result['result']['message_id']}")
        else:
            print(f"  ⚠️ Risposta Telegram: {result}")
    except Exception as exc:
        print(f"  ERRORE invio Telegram: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
