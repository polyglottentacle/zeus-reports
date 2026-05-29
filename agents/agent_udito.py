"""
Zeus - Senso UDITO (Hearing)
-----------------------------
Ascolta l'umore collettivo del mercato cripto attraverso il Fear & Greed Index
pubblico di alternative.me.

ZERO chiavi API. ZERO rischio. Solo lettura di un endpoint pubblico.
Nessun ordine, nessun accesso a wallet, nessuna autenticazione.

Restituisce un dizionario additivo da inserire nel daily_report.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict

FNG_URL = "https://api.alternative.me/fng/?limit=1&format=json"
TIMEOUT_SECONDS = 10


def _classify(value: int) -> str:
    """Traduce il valore 0-100 in un verdetto operativo per Zeus."""
    if value <= 24:
        return "EXTREME_FEAR"
    if value <= 44:
        return "FEAR"
    if value <= 55:
        return "NEUTRAL"
    if value <= 74:
        return "GREED"
    return "EXTREME_GREED"


def listen() -> Dict:
    """Ascolta il Fear & Greed Index. Solo lettura pubblica, nessuna chiave."""
    now = datetime.now(timezone.utc).isoformat()
    result = {
        "sense": "udito",
        "source": "alternative.me/fng",
        "timestamp": now,
        "status": "error",
        "value": None,
        "classification": None,
        "verdict": None,
        "message": "Fear & Greed Index non raggiungibile.",
    }
    try:
        req = urllib.request.Request(FNG_URL, headers={"User-Agent": "Zeus-Udito/1.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        data = (payload.get("data") or [None])[0]
        if not data:
            result["message"] = "Risposta vuota dal Fear & Greed Index."
            return result

        value = int(data.get("value"))
        classification = _classify(value)
        result.update({
            "status": "ok",
            "value": value,
            "classification": classification,
            "label_remote": data.get("value_classification"),
            "verdict": classification,
            "message": f"Fear & Greed Index = {value} ({classification}).",
        })
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, TypeError) as exc:
        result["error"] = str(exc)
    except Exception as exc:  # difensivo: l'udito non deve mai uccidere il report
        result["error"] = str(exc)
    return result


if __name__ == "__main__":
    print(json.dumps(listen(), indent=2, ensure_ascii=False))
