"""
Zeus - Senso PREVEGGENZA (Foresight)
--------------------------------------
Ispirato a Kronos (shiyu-coder/Kronos, AAAI 2026): modello fondazionale
per candlestick zero-shot. Qui estratto il nucleo algoritmico — pattern
recognition su OHLCV + regressione di momento — senza dipendenze heavy.

ZERO chiavi API. ZERO rischio. Usa i dati OHLCV gia' fetchati da Vista
(o li ri-fetch se Vista non e' disponibile).

Restituisce un verdetto direzionale per i prossimi N giorni:
  BULLISH / BEARISH / NEUTRAL con confidence 0-1.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Pattern candlestick elementari (Kronos-inspired feature set)
# ---------------------------------------------------------------------------

def _body_ratio(o: float, h: float, l: float, c: float) -> float:
    """Rapporto corpo/range totale della candela."""
    rng = h - l
    if rng <= 0:
        return 0.0
    return abs(c - o) / rng


def _upper_shadow(o: float, h: float, l: float, c: float) -> float:
    top = max(o, c)
    rng = h - l
    if rng <= 0:
        return 0.0
    return (h - top) / rng


def _lower_shadow(o: float, h: float, l: float, c: float) -> float:
    bottom = min(o, c)
    rng = h - l
    if rng <= 0:
        return 0.0
    return (bottom - l) / rng


def _candle_signal(o: float, h: float, l: float, c: float) -> float:
    """Segnale singola candela: +1 bullish, -1 bearish, 0 neutro."""
    body = _body_ratio(o, h, l, c)
    direction = 1.0 if c >= o else -1.0

    # Doji: corpo piccolo = incertezza
    if body < 0.1:
        return 0.0

    # Hammer / Shooting Star
    lower = _lower_shadow(o, h, l, c)
    upper = _upper_shadow(o, h, l, c)
    if lower > 0.6 and body < 0.3:
        return 0.6  # hammer → bullish
    if upper > 0.6 and body < 0.3:
        return -0.6  # shooting star → bearish

    return direction * body


def _rsi(closes: List[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = closes[-(period + 1 - i + 1)] - closes[-(period + 1 - i + 2)] if False else 0
    # calcolo pulito
    recent = closes[-(period + 1):]
    gains = [max(recent[i] - recent[i - 1], 0) for i in range(1, len(recent))]
    losses = [max(recent[i - 1] - recent[i], 0) for i in range(1, len(recent))]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def _momentum_score(closes: List[float]) -> float:
    """Punteggio di momentum multi-periodo: -1 a +1."""
    if len(closes) < 21:
        return 0.0
    scores = []
    for period in (5, 10, 20):
        if len(closes) >= period + 1:
            pct = (closes[-1] - closes[-(period + 1)]) / closes[-(period + 1)]
            scores.append(pct)
    if not scores:
        return 0.0
    raw = sum(scores) / len(scores)
    # Normalizza a [-1, +1] con tanh
    return math.tanh(raw * 10)


def _pattern_sequence_score(ohlcv: List[List]) -> float:
    """Legge le ultime candele e produce un segnale composito."""
    if len(ohlcv) < 3:
        return 0.0
    signals = []
    for candle in ohlcv[-5:]:
        ts, o, h, l, c, v = candle[0], candle[1], candle[2], candle[3], candle[4], candle[5] if len(candle) > 5 else 0
        signals.append(_candle_signal(o, h, l, c))

    # Media ponderata: candele recenti pesano di più
    weights = [0.1, 0.15, 0.2, 0.25, 0.3]
    total = sum(s * w for s, w in zip(signals, weights[-len(signals):]))
    return total


def _trend_strength(closes: List[float]) -> Tuple[str, float]:
    """SMA 5 vs SMA 20 — direzione e forza relativa."""
    if len(closes) < 20:
        return "UNKNOWN", 0.0
    sma5 = sum(closes[-5:]) / 5
    sma20 = sum(closes[-20:]) / 20
    divergence = (sma5 - sma20) / sma20
    trend = "UP" if divergence > 0 else "DOWN"
    strength = min(abs(divergence) * 100, 1.0)  # normalizzato
    return trend, round(strength, 4)


# ---------------------------------------------------------------------------
# Entry point principale
# ---------------------------------------------------------------------------

def foresee(ohlcv: Optional[List[List]] = None,
            symbol: str = "BTC/USDT",
            horizon_days: int = 3) -> Dict:
    """Prevede la direzione dei prossimi horizon_days giorni.
    Se ohlcv e' None, lo fetcha da Vista (CCXT pubblico).
    """
    now = datetime.now(timezone.utc).isoformat()
    result = {
        "sense": "preveggenza",
        "symbol": symbol,
        "horizon_days": horizon_days,
        "timestamp": now,
        "status": "error",
        "verdict": None,
        "confidence": None,
        "rsi": None,
        "trend": None,
        "momentum": None,
        "pattern_score": None,
        "message": "Preveggenza non disponibile.",
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
        result["message"] = "Dati OHLCV insufficienti per la preveggenza."
        return result

    closes = [float(c[4]) for c in ohlcv]
    rsi = _rsi(closes)
    momentum = round(_momentum_score(closes), 4)
    pattern = round(_pattern_sequence_score(ohlcv), 4)
    trend, strength = _trend_strength(closes)

    # Segnale composito pesato
    composite = (
        momentum * 0.35
        + pattern * 0.30
        + strength * (1 if trend == "UP" else -1) * 0.20
        + (((rsi or 50) - 50) / 50) * 0.15
    )

    confidence = round(min(abs(composite), 1.0), 4)

    if composite > 0.08:
        verdict = "BULLISH"
    elif composite < -0.08:
        verdict = "BEARISH"
    else:
        verdict = "NEUTRAL"

    result.update({
        "status": "ok",
        "verdict": verdict,
        "confidence": confidence,
        "composite_score": round(composite, 4),
        "rsi": rsi,
        "trend": trend,
        "trend_strength": strength,
        "momentum": momentum,
        "pattern_score": pattern,
        "last_price": round(closes[-1], 2),
        "message": (
            f"Preveggenza {horizon_days}g su {symbol}: {verdict} "
            f"(confidence {confidence:.0%}, RSI {rsi}, trend {trend})."
        ),
    })
    return result


if __name__ == "__main__":
    print(json.dumps(foresee(), indent=2, ensure_ascii=False))
