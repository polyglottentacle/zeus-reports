#!/usr/bin/env python3
"""
Hermes Bot — Zeus Trading System
Bot Telegram bidirezionale: riceve messaggi, risponde con contesto Zeus via LLM.

Variabili d'ambiente richieste (in hermes/.env):
  TELEGRAM_BOT_TOKEN   — token del bot da @BotFather
  TELEGRAM_CHAT_ID     — chat ID autorizzato (solo tu puoi scrivere)
  OPENROUTER_API_KEY   — API key OpenRouter (per DeepSeek V4 Pro)
  ZEUS_REPORT_URL      — URL raw del daily_report.json su GitHub

Avvio:
  python3 /opt/zeus/hermes/bot.py

Come servizio systemd (raccomandato):
  vedi hermes/hermes-bot.service
"""

import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("ERROR: pip install requests")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = str(os.environ.get("TELEGRAM_CHAT_ID", ""))
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
ZEUS_REPORT_URL    = os.environ.get(
    "ZEUS_REPORT_URL",
    "https://raw.githubusercontent.com/polyglottentacle/zeus-reports/main/output/daily_report.json",
)
LLM_MODEL          = os.environ.get("HERMES_LLM_MODEL", "deepseek/deepseek-chat")
OPENROUTER_URL     = "https://openrouter.ai/api/v1/chat/completions"
TELEGRAM_API       = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

SYSTEM_PROMPT = """Sei Hermes, l'agente AI del sistema Zeus di Olimpus.
Zeus è un sistema di trading quantitativo che include:
- Freqtrade con strategie BTC/USDT 1h (EMA/RSI/ADX)
- Agenti DSR (Deflated Sharpe Ratio), Kelly fraction, stima costi/tasse
- MiroFish: simulatore di sentiment sociale con 100 agenti AI
- Pipeline automatica: daily_report.json → GitHub → Telegram

Il tuo ruolo: rispondere a domande sul sistema Zeus, interpretare i dati del report,
suggerire miglioramenti alle strategie, spiegare i numeri.
Rispondi sempre in italiano, in modo conciso e tecnico.
Se hai il report disponibile, usa i dati reali per rispondere."""


# ── Telegram helpers ──────────────────────────────────────────────────────────

def tg_get(method: str, params: dict = None) -> dict:
    r = requests.get(f"{TELEGRAM_API}/{method}", params=params, timeout=30)
    return r.json()

def tg_post(method: str, payload: dict) -> dict:
    r = requests.post(f"{TELEGRAM_API}/{method}", json=payload, timeout=30)
    return r.json()

def send_message(chat_id: str, text: str) -> dict:
    # Telegram ha limite 4096 char per messaggio
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    result = {}
    for chunk in chunks:
        result = tg_post("sendMessage", {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        })
    return result

def send_typing(chat_id: str) -> None:
    tg_post("sendChatAction", {"chat_id": chat_id, "action": "typing"})


# ── Report Zeus ───────────────────────────────────────────────────────────────

def fetch_report() -> dict:
    try:
        r = requests.get(ZEUS_REPORT_URL, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def summarize_report(report: dict) -> str:
    if "error" in report:
        return f"[Report non disponibile: {report['error']}]"

    ts  = report.get("timestamp", "")[:16].replace("T", " ")
    bs  = report.get("backtest_summary", {})
    dsr = report.get("dsr", {})
    kel = report.get("kelly", {})
    mf  = report.get("mirofish", {})

    try:    sharpe   = f"{float(bs.get('sharpe', 0)):.3f}"
    except: sharpe   = "n/d"
    try:    kelly_f  = f"{float(kel.get('kelly_fraction', 0)):.4f}"
    except: kelly_f  = "n/d"

    return (
        f"[Zeus Report — {ts} UTC]\n"
        f"Strategia: {bs.get('strategy_name','n/d')} | Sharpe: {sharpe} | "
        f"Trade: {bs.get('trade_count','n/d')}\n"
        f"DSR: {dsr.get('dsr','n/d')} | Kelly: {kelly_f}\n"
        f"MiroFish: {mf.get('status','n/d')} | "
        f"Azioni: {mf.get('mirofish_run',{}).get('total_actions','n/d')}"
    )


# ── LLM (OpenRouter) ──────────────────────────────────────────────────────────

# Storico messaggi per sessione (in memoria, si azzera al riavvio)
_history: list = []

def ask_llm(user_message: str, report_summary: str) -> str:
    global _history

    # Inietta il report come contesto nel primo messaggio o ogni 10 turni
    if not _history or len(_history) % 20 == 0:
        context_msg = {
            "role": "system",
            "content": SYSTEM_PROMPT + "\n\nDati correnti:\n" + report_summary,
        }
    else:
        context_msg = {"role": "system", "content": SYSTEM_PROMPT}

    _history.append({"role": "user", "content": user_message})

    # Mantieni storico ultimi 20 messaggi per non sforare il contesto
    recent = _history[-20:]

    messages = [context_msg] + recent

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/polyglottentacle/zeus-reports",
        "X-Title": "Hermes Zeus Bot",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.7,
    }

    r = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=60)
    r.raise_for_status()
    data = r.json()

    reply = data["choices"][0]["message"]["content"]
    _history.append({"role": "assistant", "content": reply})
    return reply


# ── Comandi speciali ──────────────────────────────────────────────────────────

def handle_command(cmd: str, chat_id: str) -> bool:
    """Gestisce comandi /start /report /reset /status. Ritorna True se gestito."""
    cmd = cmd.strip().lower().split()[0]

    if cmd == "/start":
        send_message(chat_id,
            "🤖 *Hermes attivo.*\n\n"
            "Sono il tuo agente Zeus. Puoi chiedermi:\n"
            "• Come sta andando la strategia?\n"
            "• Cosa dice il DSR / Kelly di oggi?\n"
            "• Cosa ha prodotto MiroFish?\n"
            "• Suggerimenti per migliorare lo Sharpe\n\n"
            "Comandi disponibili:\n"
            "`/report` — mostra il summary del report corrente\n"
            "`/reset` — azzera la memoria della conversazione\n"
            "`/status` — stato del sistema Zeus"
        )
        return True

    if cmd == "/report":
        report = fetch_report()
        send_message(chat_id, f"```\n{summarize_report(report)}\n```")
        return True

    if cmd == "/reset":
        global _history
        _history = []
        send_message(chat_id, "✅ Memoria conversazione azzerata.")
        return True

    if cmd == "/status":
        report = fetch_report()
        ts = report.get("timestamp", "n/d")[:16]
        mf = report.get("mirofish", {})
        send_message(chat_id,
            f"🟢 *Hermes online*\n"
            f"Ultimo report: `{ts} UTC`\n"
            f"MiroFish: `{mf.get('status','n/d')}`\n"
            f"Bot attivo da: `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC`"
        )
        return True

    return False


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN non impostato.")
        sys.exit(1)
    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY non impostato.")
        sys.exit(1)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Hermes Bot avviato.")
    print(f"  Modello LLM: {LLM_MODEL}")
    print(f"  Chat autorizzata: {TELEGRAM_CHAT_ID}")

    # Carica report all'avvio
    report = fetch_report()
    report_summary = summarize_report(report)
    print(f"  Report caricato: {report.get('timestamp','n/d')[:16]}")

    offset = 0  # Long polling offset

    while True:
        try:
            # Long polling: aspetta fino a 30s per nuovi messaggi
            result = tg_get("getUpdates", {"offset": offset, "timeout": 30})

            if not result.get("ok"):
                print(f"  Telegram error: {result}")
                time.sleep(5)
                continue

            updates = result.get("result", [])

            for update in updates:
                offset = update["update_id"] + 1

                msg = update.get("message") or update.get("edited_message")
                if not msg:
                    continue

                chat_id = str(msg["chat"]["id"])
                text    = msg.get("text", "").strip()

                if not text:
                    continue

                # Sicurezza: risponde solo alla chat autorizzata
                if TELEGRAM_CHAT_ID and chat_id != TELEGRAM_CHAT_ID:
                    send_message(chat_id, "⛔ Non autorizzato.")
                    continue

                print(f"  [{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Messaggio: {text[:60]}")

                # Comandi speciali
                if text.startswith("/"):
                    if not handle_command(text, chat_id):
                        send_message(chat_id, "Comando non riconosciuto. Usa /start per l'elenco.")
                    continue

                # Messaggio libero → LLM
                send_typing(chat_id)

                # Ricarica report ogni 10 messaggi
                if len(_history) % 10 == 0:
                    report = fetch_report()
                    report_summary = summarize_report(report)

                try:
                    reply = ask_llm(text, report_summary)
                    send_message(chat_id, reply)
                except Exception as e:
                    err = str(e)[:200]
                    send_message(chat_id, f"⚠️ Errore LLM: `{err}`")
                    print(f"  LLM error: {e}")

        except KeyboardInterrupt:
            print("\nHermes Bot fermato.")
            break
        except Exception as e:
            print(f"  Loop error: {e}")
            traceback.print_exc()
            time.sleep(10)


if __name__ == "__main__":
    main()
