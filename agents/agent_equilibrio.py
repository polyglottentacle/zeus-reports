"""
Zeus - Senso EQUILIBRIO (Balance / Risk Perception)
-----------------------------------------------------
Ispirato a mlfinlab (Hudson & Thames) e a López de Prado,
autore del DSR gia' integrato in Zeus (agent2_dsr.py).

Calcola metriche di rischio sul mercato live:
  - Sharpe annualizzato (rolling 30g)
  - Calmar ratio (return / max drawdown)
  - Max drawdown assoluto e relativo (finestra mobile)
  - Pain Index (area sotto il drawdown)
  - Regime di rischio: LOW / MEDIUM / HIGH / EXTREME

ZERO chiavi API. ZERO rischio. Solo OHLCV pubblici.

L'obiettivo: Zeus capisce se il mercato e' in equilibrio o al limite.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Funzioni di rischio core (mlfinlab-inspired)
# ---------------------------------------------------------------------------

def _log_returns(closes: List[float]) -> List[float]:
    returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] > 0 and closes[i] > 0:
            returns.append(math.log(closes[i] / closes[i - 1]))
    return returns


def _annualized_sharpe(returns: List[float], risk_free: float = 0.0) -> Optional[float]:
    """Sharpe annualizzato su rendimenti giornalieri."""
    if len(returns) < 5:
        return None
    n = len(returns)
    mean = sum(returns) / n
    excess = mean - risk_free / 252
    std = math.sqrt(sum((r - mean) ** 2 for r in returns) / n)
    if std == 0:
        return None
    return round((excess / std) * math.sqrt(252), 4)


def _max_drawdown(closes: List[float]) -> Tuple[float, float]:
    """Ritorna (max_drawdown_pct, max_drawdown_abs)."""
    if len(closes) < 2:
        return 0.0, 0.0
    peak = closes[0]
    max_dd_pct = 0.0
    max_dd_abs = 0.0
    for c in closes[1:]:
        if c > peak:
            peak = c
        dd_abs = peak - c
        dd_pct = dd_abs / peak if peak > 0 else 0.0
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct
            max_dd_abs = dd_abs
    return round(max_dd_pct, 6), round(max_dd_abs, 2)


def _calmar_ratio(closes: List[float], period_days: int = 30) -> Optional[float]:
    """Calmar = rendimento annualizzato / max drawdown (mlfinlab core metric)."""
    if len(closes) < 2:
        return None
    total_return = (closes[-1] - closes[0]) / closes[0]
    annualized_return = (1 + total_return) ** (365 / period_days) - 1
    max_dd, _ = _max_drawdown(closes)
    if max_dd == 0:
        return None
    return round(annualized_return / max_dd, 4)


def _pain_index(closes: List[float]) -> float:
    """Pain Index: area media sotto il drawdown (López de Prado, AFML cap. 14)."""
    if len(closes) < 2:
        return 0.0
    peak = closes[0]
    drawdowns = []
    for c in closes:
        if c > peak:
            peak = c
        drawdowns.append((peak - c) / peak if peak > 0 else 0.0)
    return round(sum(drawdowns) / len(drawdowns), 6)


def _volatility_annualized(returns: List[float]) -> Optional[float]:
    """Volatilita' annualizzata (std dei log-returns * sqrt(252))."""
    if len(returns) < 3:
        return None
    mean = sum(returns) / len(returns)
    std = math.sqrt(sum((r - mean) ** 2 for r in returns) / len(returns))
    return round(std * math.sqrt(252) * 100, 2)  # in %


def _risk_regime(sharpe: Optional[float],
                 max_dd: float,
                 vol_ann: Optional[float],
                 pain: float) -> str:
    """Classifica il regime di rischio corrente."""
    danger = 0
    if sharpe is not None and sharpe < -1.0:
        danger += 2
    elif sharpe is not None and sharpe < 0:
        danger += 1

    if max_dd > 0.25:
        danger += 2
    elif max_dd > 0.12:
        danger += 1

    if vol_ann is not None and vol_ann > 80:
        danger += 2
    elif vol_ann is not None and vol_ann > 50:
        danger += 1

    if pain > 0.10:
        danger += 1

    if danger >= 5:
        return "EXTREME"
    if danger >= 3:
        return "HIGH"
    if danger >= 1:
        return "MEDIUM"
    return "LOW"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def balance(ohlcv: Optional[List[List]] = None,
            symbol: str = "BTC/USDT") -> Dict:
    """Valuta l'equilibrio / il rischio del mercato corrente.
    Se ohlcv e' None, fetcha da CCXT pubblico.
    """
    now = datetime.now(timezone.utc).isoformat()
    result = {
        "sense": "equilibrio",
        "symbol": symbol,
        "timestamp": now,
        "status": "error",
        "verdict": None,
        "risk_regime": None,
        "sharpe_30d": None,
        "calmar_30d": None,
        "max_drawdown_pct": None,
        "max_drawdown_abs": None,
        "pain_index": None,
        "volatility_ann_pct": None,
        "message": "Equilibrio non disponibile.",
    }

    if ohlcv is None:
        try:
            import ccxt
            exchange = ccxt.kraken({"enableRateLimit": True})
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe="1d", limit=60)
        except Exception as exc:
            result["error"] = str(exc)
            return result

    if not ohlcv or len(ohlcv) < 5:
        result["message"] = "Dati OHLCV insufficienti per l'equilibrio."
        return result

    closes = [float(c[4]) for c in ohlcv]
    # Finestra rolling 30g per metriche recenti
    window = closes[-30:]
    returns_all = _log_returns(closes)
    returns_30 = _log_returns(window)

    sharpe = _annualized_sharpe(returns_30)
    calmar = _calmar_ratio(window, period_days=30)
    max_dd_pct, max_dd_abs = _max_drawdown(window)
    pain = _pain_index(window)
    vol_ann = _volatility_annualized(returns_all)
    regime = _risk_regime(sharpe, max_dd_pct, vol_ann, pain)

    # Verdict: se regime ok e sharpe ok → EQUILIBRIUM, altrimenti STRESS
    if regime in ("LOW", "MEDIUM") and (sharpe is None or sharpe > -0.5):
        verdict = "EQUILIBRIUM"
    else:
        verdict = "STRESS"

    result.update({
        "status": "ok",
        "verdict": verdict,
        "risk_regime": regime,
        "sharpe_30d": sharpe,
        "calmar_30d": calmar,
        "max_drawdown_pct": round(max_dd_pct * 100, 2),
        "max_drawdown_abs": max_dd_abs,
        "pain_index": pain,
        "volatility_ann_pct": vol_ann,
        "candles_used": len(ohlcv),
        "message": (
            f"Equilibrio {symbol}: regime {regime}, "
            f"Sharpe30g={sharpe}, maxDD={round(max_dd_pct * 100, 1)}%, "
            f"vol={vol_ann}% ann. → {verdict}."
        ),
    })
    return result


if __name__ == "__main__":
    print(json.dumps(balance(), indent=2, ensure_ascii=False))
