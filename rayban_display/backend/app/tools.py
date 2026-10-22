"""Tool registry per l'agente vocale. Ogni tool e' una funzione sincrona
che riceve argomenti gia' validati (dict) e ritorna una stringa breve,
pensata per finire su un display di pochi caratteri.

Aggiungere un tool nuovo:
1. Scrivere la funzione `def _tool_xxx(args: dict) -> str`.
2. Aggiungere la sua JSON-schema in TOOL_SPECS (formato OpenAI function-calling,
   compatibile con l'endpoint Groq/OpenAI usato da agent.py).
3. Registrarla in TOOL_REGISTRY.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[3]
DAILY_REPORT_PATH = REPO_ROOT / "output" / "daily_report.json"


def _tool_get_time(args: dict) -> str:
    return datetime.now(timezone.utc).strftime("%H:%M UTC, %d %b %Y")


def _tool_zeus_status(args: dict) -> str:
    """Legge l'ultimo output/daily_report.json di Zeus, se presente.

    ⚠️ IPOTESI: percorso valido solo quando questo backend gira sulla stessa
    macchina/checkout del repo zeus-reports con una pipeline già eseguita.
    Non assume nulla sul contenuto: se il file manca o è malformato lo dice.
    """
    if not DAILY_REPORT_PATH.exists():
        return "Nessun daily_report.json trovato: la pipeline Zeus non è ancora stata eseguita qui."
    try:
        data = json.loads(DAILY_REPORT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return f"daily_report.json presente ma illeggibile: {exc}"

    dsr = (data.get("dsr") or {}).get("dsr")
    kelly_fraction = (data.get("kelly") or {}).get("kelly_fraction")
    timestamp = data.get("timestamp", "?")

    parts = []
    if dsr is not None:
        parts.append(f"DSR {dsr:.4f}")
    if kelly_fraction is not None:
        parts.append(f"Kelly {kelly_fraction:.4f}")
    summary = ", ".join(parts) if parts else "report trovato ma senza campi dsr/kelly"
    return f"Zeus ({timestamp}): {summary}"


TOOL_SPECS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Ritorna l'ora e la data correnti in UTC.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "zeus_status",
            "description": (
                "Ritorna un riassunto sintetico dell'ultimo daily_report.json "
                "generato dalla pipeline di trading Zeus, se disponibile su "
                "questa macchina."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

TOOL_REGISTRY: dict[str, Callable[[dict], str]] = {
    "get_time": _tool_get_time,
    "zeus_status": _tool_zeus_status,
}
