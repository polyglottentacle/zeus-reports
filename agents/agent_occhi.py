"""
Zeus - Senso OCCHI (Multi-agent LLM Vision)
--------------------------------------------
Adattatore per TradingAgents (TauricResearch/TradingAgents).
Esegue il framework in un venv ISOLATO (ochi/venv/) via subprocess,
per evitare conflitti di dipendenze con il runtime principale di Zeus.

ZERO rischio di rompere MiroFish, Camel-AI o openai 1.x.

Pipeline usata:
  - Analisti: market + social + news (no fundamentals: non supportato per crypto)
  - Provider LLM: DeepSeek (dalle variabili Zeus: LLM_API_KEY, LLM_BASE_URL)
  - Asset: BTC-USD, asset_type="crypto"
  - Output: decisione 5-tier → Buy / Overweight / Hold / Underweight / Sell

Setup necessario (UNA VOLTA):
  cd C:\\Users\\docum\\Desktop\\zeus\\ochi
  bash setup_venv.sh

Restituisce un dict JSON-safe compatibile con gli altri sensi di Zeus.
Se TradingAgents fallisce o il venv non esiste → status="error" o "setup_required".
Non fa MAI crashare orchestrator.py.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

BASE_DIR  = Path(__file__).resolve().parent.parent
OCHI_DIR  = BASE_DIR / "ochi"
RUNNER    = OCHI_DIR / "runner.py"

# Cerca il Python del venv ochi (Windows e Linux)
_VENV_CANDIDATES = [
    OCHI_DIR / "venv" / "Scripts" / "python.exe",   # Windows
    OCHI_DIR / "venv" / "bin" / "python",            # Linux/Mac
    OCHI_DIR / "venv" / "bin" / "python3",
]

TIMEOUT_SECONDS = int(os.environ.get("OCCHI_TIMEOUT", "180"))


def _find_venv_python() -> Path | None:
    for candidate in _VENV_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def _env_for_runner() -> dict:
    """Costruisce le variabili d'ambiente per il runner isolato."""
    env = dict(os.environ)
    # Carica il .env di Zeus se presente
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env.setdefault(k.strip(), v.strip())
        except Exception:
            pass
    return env


def look(symbol: str = "BTC-USD",
         trade_date: str | None = None) -> Dict:
    """Esegue TradingAgents nel venv isolato e restituisce il risultato come dict."""
    now = datetime.now(timezone.utc).isoformat()
    if trade_date is None:
        trade_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    base_result = {
        "sense": "occhi",
        "symbol": symbol,
        "trade_date": trade_date,
        "timestamp": now,
        "status": "error",
        "decision": None,
        "verdict": None,
        "message": "Occhi non disponibile.",
    }

    # Controlla che il runner esista
    if not RUNNER.exists():
        base_result["message"] = f"Runner non trovato: {RUNNER}"
        return base_result

    # Cerca il Python del venv ochi
    venv_py = _find_venv_python()
    if venv_py is None:
        base_result["status"] = "setup_required"
        base_result["message"] = (
            "Venv ochi non configurato. Esegui:\n"
            "  cd ochi && bash setup_venv.sh"
        )
        return base_result

    env = _env_for_runner()
    env["OCCHI_SYMBOL"]  = symbol
    env["OCCHI_DATE"]    = trade_date
    env["OCCHI_TIMEOUT"] = str(TIMEOUT_SECONDS)

    try:
        proc = subprocess.run(
            [str(venv_py), str(RUNNER)],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS + 30,  # subprocess timeout > runner timeout
            env=env,
            cwd=str(OCHI_DIR),
        )

        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()

        if not stdout:
            base_result["error"] = stderr[:500] if stderr else "nessun output"
            base_result["message"] = "Runner non ha prodotto output."
            return base_result

        # Prende solo l'ultima riga JSON (il runner potrebbe stampare log prima)
        json_line = None
        for line in reversed(stdout.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                json_line = line
                break

        if json_line is None:
            base_result["error"] = stdout[:500]
            base_result["message"] = "Output non JSON dal runner."
            return base_result

        result = json.loads(json_line)
        return result

    except subprocess.TimeoutExpired:
        base_result["error"] = f"Timeout dopo {TIMEOUT_SECONDS}s"
        base_result["message"] = f"TradingAgents non ha risposto entro {TIMEOUT_SECONDS}s."
        return base_result
    except json.JSONDecodeError as exc:
        base_result["error"] = str(exc)
        base_result["message"] = "Risposta non JSON dal runner."
        return base_result
    except Exception as exc:
        base_result["error"] = str(exc)
        base_result["message"] = f"Errore subprocess: {exc}"
        return base_result


if __name__ == "__main__":
    print(json.dumps(look(), indent=2, ensure_ascii=False))
