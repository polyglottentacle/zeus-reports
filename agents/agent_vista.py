"""
Zeus - Senso VISTA (Sight)
---------------------------
Vede il mercato: prezzo, struttura recente, volatilita e trend di BTC/USDT
tramite endpoint PUBBLICI di un exchange via CCXT.

ZERO chiavi API. ZERO rischio. Solo dati OHLCV pubblici (non autenticati).
Nessun ordine, nessun wallet, nessuna chiave privata caricata MAI.

Se ccxt non e disponibile o l'exchange non risponde, ritorna status di errore
senza far cadere il report.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

DEFAULT_SYMBOL = "BTC/USDT"
DEFAULT_TIMEFRAME = "1d"
DEFAULT_LIMIT = 30
# Exchange pubblici provati in ordine: solo dati pubblici, nessuna autenticazione.
EXCHANGE_CANDIDATES = ("kraken", "coinbase", "kucoin", "bitstamp")


def _pct_change(new: float, old: float) -> Optional[float]:
    if old in (None, 0):
        return None
    return round((new - old) / old * 100.0, 2)


def _volatility(closes: List[float]) -> Optional[float]:
    """Deviazione standard dei rendimenti giornalieri in percentuale."""
    if len(closes) < 3:
        return None
    rets = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes)) if closes[i - 1]]
    if not rets:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / len(rets)
    return round((var ** 0.5) * 100.0, 2)


def _trend(closes: List[float]) -> str:
    """Verdetto di trend basato su SMA breve vs lunga."""
    if len(closes) < 10:
        return "UNKNOWN"
    short = sum(closes[-5:]) / 5
    long = sum(closes[-20:]) / min(20, len(closes)) if len(closes) >= 20 else sum(closes) / len(closes)
    if short > long * 1.01:
        return "UPTREND"
    if short < long * 0.99:
        return "DOWNTREND"
    return "SIDEWAYS"


def see(symbol: str = DEFAULT_SYMBOL,
        timeframe: str = DEFAULT_TIMEFRAME,
        limit: int = DEFAULT_LIMIT) -> Dict:
    """Osserva il mercato tramite dati pubblici. Nessuna chiave, sola lettura."""
    now = datetime.now(timezone.utc).isoformat()
    result = {
        "sense": "vista",
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": now,
        "status": "error",
        "exchange": None,
        "last_price": None,
        "change_24h_pct": None,
        "change_period_pct": None,
        "volatility_pct": None,
        "trend": None,
        "verdict": None,
        "message": "Vista non disponibile.",
    }

    try:
        import ccxt  # noqa: WPS433 (import locale: la vista non deve rompere il report)
    except ImportError:
        result["message"] = "ccxt non installato; Vista in pausa."
        return result

    last_error = None
    for name in EXCHANGE_CANDIDATES:
        try:
            ex_class = getattr(ccxt, name, None)
            if ex_class is None:
                continue
            # enableRateLimit: gentile con gli endpoint pubblici. Nessuna API key.
            exchange = ex_class({"enableRateLimit": True})
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            if not ohlcv or len(ohlcv) < 2:
                last_error = f"{name}: dati OHLCV insufficienti"
                continue

            closes = [float(c[4]) for c in ohlcv]
            last_price = closes[-1]
            prev_price = closes[-2]
            first_price = closes[0]

            result.update({
                "status": "ok",
                "exchange": name,
                "candles": len(closes),
                "last_price": round(last_price, 2),
                "change_24h_pct": _pct_change(last_price, prev_price),
                "change_period_pct": _pct_change(last_price, first_price),
                "volatility_pct": _volatility(closes),
                "trend": _trend(closes),
                "high_period": round(max(c[2] for c in ohlcv), 2),
                "low_period": round(min(c[3] for c in ohlcv), 2),
                "message": f"BTC visto su {name}: {round(last_price, 2)} USDT.",
            })
            result["verdict"] = result["trend"]
            return result
        except Exception as exc:  # prova il prossimo exchange pubblico
            last_error = f"{name}: {exc}"
            continue

    result["message"] = "Nessun exchange pubblico raggiungibile."
    if last_error:
        result["error"] = last_error
    return result


if __name__ == "__main__":
    print(json.dumps(see(), indent=2, ensure_ascii=False))
