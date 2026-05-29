"""
Zeus - Senso MEMORIA (Memory)
-------------------------------
Ispirato a Microsoft Qlib (Alpha158 / Alpha360 feature set).
Estrae fattori alpha quantitativi dalla serie storica OHLCV:
momentum multi-periodo, mean-reversion, volume-price divergence,
volatility regime, e un alpha score composito.

ZERO chiavi API. ZERO rischio. Solo dati pubblici OHLCV.

L'obiettivo di Zeus: ricordare strutture ricorrenti del mercato,
non solo reagire al presente.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Alpha factors estratti da Qlib Alpha158
# ---------------------------------------------------------------------------

def _alpha_momentum(closes: List[float], period: int) -> Optional[float]:
    """Rendimento logaritmico su N giorni (Qlib: RESI, ROC)."""
    if len(closes) <= period:
        return None
    return round(math.log(closes[-1] / closes[-(period + 1)]), 6)


def _alpha_mean_reversion(closes: List[float], period: int = 20) -> Optional[float]:
    """Zscore prezzo vs SMA: quanto si e' allontanato dalla media (Qlib: WVMA)."""
    if len(closes) < period:
        return None
    sma = sum(closes[-period:]) / period
    std = math.sqrt(sum((c - sma) ** 2 for c in closes[-period:]) / period)
    if std == 0:
        return 0.0
    return round((closes[-1] - sma) / std, 4)


def _alpha_vol_momentum(volumes: List[float], closes: List[float], period: int = 10) -> Optional[float]:
    """Correlazione volume-prezzo: volume aumenta quando il prezzo sale? (Qlib: VWAP-like)."""
    if len(volumes) < period or len(closes) < period + 1:
        return None
    score = 0.0
    for i in range(1, period + 1):
        price_dir = 1.0 if closes[-i] > closes[-(i + 1)] else -1.0
        vol_rel = volumes[-i] / (sum(volumes[-period:]) / period) if sum(volumes[-period:]) > 0 else 1.0
        score += price_dir * (vol_rel - 1.0)
    return round(score / period, 4)


def _alpha_volatility_regime(closes: List[float], short: int = 5, long: int = 20) -> Optional[float]:
    """Regime di volatilita': volatilita' breve / lunga (Qlib: STD ratio)."""
    if len(closes) < long:
        return None

    def _std(xs):
        m = sum(xs) / len(xs)
        return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))

    returns = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes)) if closes[i - 1] > 0]
    if len(returns) < long:
        return None
    std_short = _std(returns[-short:])
    std_long = _std(returns[-long:])
    if std_long == 0:
        return 1.0
    return round(std_short / std_long, 4)


def _alpha_hl_efficiency(ohlcv: List[List], period: int = 10) -> Optional[float]:
    """Efficienza H-L: quanto del range H-L viene catturato dal movimento direzionale (Qlib: KLEN)."""
    if len(ohlcv) < period:
        return None
    scores = []
    for candle in ohlcv[-period:]:
        o, h, l, c = candle[1], candle[2], candle[3], candle[4]
        rng = h - l
        if rng > 0:
            directional = abs(c - o)
            scores.append(directional / rng)
    return round(sum(scores) / len(scores), 4) if scores else None


# ---------------------------------------------------------------------------
# Aggregazione alpha composito (Qlib-style: equal-weight IC-weighted)
# ---------------------------------------------------------------------------

def _composite_alpha(factors: Dict[str, Optional[float]]) -> float:
    """Combina i fattori in un alpha score normalizzato tra -1 e +1."""
    weights = {
        "mom_5d": 0.25,
        "mom_20d": 0.20,
        "mean_rev": -0.20,   # contrarian: se sopra media, abbassa il bullish
        "vol_momentum": 0.20,
        "vol_regime": -0.10, # alta vol breve = incertezza
        "hl_efficiency": 0.05,
    }
    total_w = 0.0
    score = 0.0
    for k, w in weights.items():
        v = factors.get(k)
        if v is not None and not math.isnan(v) and not math.isinf(v):
            # Normalizza ogni fattore con tanh per restare in [-1,+1]
            score += math.tanh(v) * w
            total_w += abs(w)
    if total_w == 0:
        return 0.0
    return round(score / total_w, 4)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def remember(ohlcv: Optional[List[List]] = None,
             symbol: str = "BTC/USDT") -> Dict:
    """Estrae i fattori alpha dalla memoria storica di BTC.
    Se ohlcv e' None, fetcha da CCXT pubblico.
    """
    now = datetime.now(timezone.utc).isoformat()
    result = {
        "sense": "memoria",
        "symbol": symbol,
        "timestamp": now,
        "status": "error",
        "verdict": None,
        "alpha_score": None,
        "factors": {},
        "message": "Memoria non disponibile.",
    }

    if ohlcv is None:
        try:
            import ccxt
            exchange = ccxt.kraken({"enableRateLimit": True})
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe="1d", limit=60)
        except Exception as exc:
            result["error"] = str(exc)
            return result

    if not ohlcv or len(ohlcv) < 10:
        result["message"] = "Dati OHLCV insufficienti per la memoria."
        return result

    closes = [float(c[4]) for c in ohlcv]
    volumes = [float(c[5]) for c in ohlcv if len(c) > 5]

    factors = {
        "mom_5d": _alpha_momentum(closes, 5),
        "mom_20d": _alpha_momentum(closes, 20),
        "mean_rev": _alpha_mean_reversion(closes, 20),
        "vol_momentum": _alpha_vol_momentum(volumes, closes, 10) if volumes else None,
        "vol_regime": _alpha_volatility_regime(closes, 5, 20),
        "hl_efficiency": _alpha_hl_efficiency(ohlcv, 10),
    }

    alpha = _composite_alpha(factors)

    if alpha > 0.10:
        verdict = "BULLISH"
    elif alpha < -0.10:
        verdict = "BEARISH"
    else:
        verdict = "NEUTRAL"

    result.update({
        "status": "ok",
        "verdict": verdict,
        "alpha_score": alpha,
        "factors": {k: v for k, v in factors.items() if v is not None},
        "candles_used": len(ohlcv),
        "message": (
            f"Memoria storica {symbol}: alpha={alpha:+.4f} → {verdict}. "
            f"Momentum 5g={factors.get('mom_5d')}, "
            f"mean_rev={factors.get('mean_rev')}."
        ),
    })
    return result


if __name__ == "__main__":
    print(json.dumps(remember(), indent=2, ensure_ascii=False))
