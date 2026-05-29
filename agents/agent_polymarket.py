"""
Zeus - Senso POLYMARKET (Prediction Markets)
----------------------------------------------
Legge i mercati predittivi su BTC/crypto da Polymarket (gamma-api) e
produce un segnale aggregato BULLISH / BEARISH / NEUTRAL.

ZERO chiavi API. ZERO rischio. Solo lettura dell'endpoint pubblico.
Nessun ordine, nessun accesso a wallet, nessuna autenticazione.

Schema output:
  {
    "sense": "polymarket",
    "status": "ok" | "unavailable" | "error",
    "timestamp": "...",
    "verdict": "BULLISH" | "BEARISH" | "NEUTRAL",
    "message": "...",
    "markets": [...]
  }

Regola di aggregazione:
  media_p_yes (mercati BTC bullish) > 0.55 → BULLISH
  media_p_yes (mercati BTC bullish) < 0.45 → BEARISH
  altrimenti                               → NEUTRAL
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, List, Optional

GAMMA_URL = "https://gamma-api.polymarket.com/markets"
TIMEOUT_SECONDS = 12

# Keyword usate per filtrare mercati BTC/crypto rilevanti
_BTC_KEYWORDS = ("btc", "bitcoin", "crypto", "cryptocurrency")
# Keyword che indicano un mercato "rialzista" (p_yes > soglia → BULLISH)
_BULLISH_KEYWORDS = (
    "above", "over", "exceed", "reach", "hit",
    "higher", "rally", "bull", "surge", "rise",
)
# Soglie verdetto
_BULL_THR = 0.55
_BEAR_THR = 0.45


def _is_btc_market(question: str) -> bool:
    q = question.lower()
    return any(kw in q for kw in _BTC_KEYWORDS)


def _is_bullish_framing(question: str) -> bool:
    q = question.lower()
    return any(kw in q for kw in _BULLISH_KEYWORDS)


def _fetch_markets(limit: int = 50) -> List[dict]:
    """Scarica i mercati aperti da Polymarket gamma-api."""
    url = f"{GAMMA_URL}?active=true&limit={limit}&order=volume&ascending=false"
    req = urllib.request.Request(url, headers={"User-Agent": "Zeus-Polymarket/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _parse_price(market: dict) -> Optional[float]:
    """Estrae la probabilità YES [0,1] da un mercato Polymarket."""
    # I mercati binari espongono outcomePrices come '["0.73","0.27"]'
    raw = market.get("outcomePrices") or market.get("lastTradePrice")
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list) and parsed:
                return float(parsed[0])
        except (ValueError, TypeError):
            try:
                return float(raw)
            except (ValueError, TypeError):
                pass
    if isinstance(raw, (int, float)):
        return float(raw)
    return None


def sense() -> Dict:
    """Ascolta i mercati predittivi Polymarket su BTC/crypto."""
    now = datetime.now(timezone.utc).isoformat()
    result: Dict = {
        "sense": "polymarket",
        "source": "gamma-api.polymarket.com",
        "timestamp": now,
        "status": "error",
        "verdict": None,
        "message": "Polymarket non raggiungibile.",
        "markets": [],
    }

    try:
        raw_markets = _fetch_markets()
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        result["status"] = "unavailable"
        result["message"] = f"Polymarket API non raggiungibile: {exc}"
        return result
    except Exception as exc:
        result["error"] = str(exc)
        return result

    if not isinstance(raw_markets, list):
        result["message"] = "Risposta inattesa da Polymarket."
        return result

    # Filtra mercati BTC/crypto
    btc_markets = [m for m in raw_markets if _is_btc_market(m.get("question", ""))]

    if not btc_markets:
        result["status"] = "unavailable"
        result["message"] = "Nessun mercato BTC/crypto trovato su Polymarket."
        return result

    bullish_probs: List[float] = []
    parsed: List[dict] = []

    for m in btc_markets:
        question = m.get("question", "")
        p_yes = _parse_price(m)
        if p_yes is None:
            continue

        # Se il framing è "BTC scenderà sotto X" il segnale va invertito
        framing = "bullish" if _is_bullish_framing(question) else "bearish_framing"
        effective_prob = p_yes if framing == "bullish" else (1.0 - p_yes)
        bullish_probs.append(effective_prob)

        parsed.append({
            "question": question,
            "p_yes": round(p_yes, 4),
            "effective_bullish_prob": round(effective_prob, 4),
            "framing": framing,
            "volume": m.get("volume"),
        })

    if not bullish_probs:
        result["status"] = "unavailable"
        result["message"] = "Dati di prezzo non disponibili nei mercati BTC."
        return result

    avg_bull = sum(bullish_probs) / len(bullish_probs)

    if avg_bull > _BULL_THR:
        verdict = "BULLISH"
    elif avg_bull < _BEAR_THR:
        verdict = "BEARISH"
    else:
        verdict = "NEUTRAL"

    result.update({
        "status": "ok",
        "verdict": verdict,
        "avg_bullish_prob": round(avg_bull, 4),
        "market_count": len(parsed),
        "message": (
            f"Polymarket: {len(parsed)} mercati BTC "
            f"| p_bull media = {avg_bull:.1%} → {verdict}"
        ),
        "markets": parsed,
    })
    return result


if __name__ == "__main__":
    print(json.dumps(sense(), indent=2, ensure_ascii=False))
