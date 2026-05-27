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
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("ERROR: 'requests' non installato. Esegui: pip install requests")
    sys.exit(1)

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

    # Icona stato MiroFish
    mf_icon = "✅" if mf_status == "ok" else ("⚠️" if mf_status == "disabled" else "❌")

    # Valutazione complessiva
    try:
        sharpe_val = float(bs.get("sharpe", -99))
        kelly_val = float(kelly_data.get("kelly_fraction", 0))
        if sharpe_val > 0.5 and kelly_val > 0:
            verdict = "🟢 STRATEGIA ATTIVA — posizione consentita"
        elif sharpe_val > 0:
            verdict = "🟡 STRATEGIA DEBOLE — size ridotto"
        else:
            verdict = "🔴 STRATEGIA PERDENTE — size zero, aspetta miglioramento"
    except (TypeError, ValueError):
        verdict = "⚪ Dati insufficienti"

    msg = (
        f"🤖 *Zeus Morning Briefing* — {ts} UTC\n"
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
        f"━━━━━━━━━━━━━━━━\n"
        f"{verdict}"
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
