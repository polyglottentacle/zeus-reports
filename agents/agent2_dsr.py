import math
from statistics import NormalDist
from typing import Iterable, List

_NORMAL_DIST = NormalDist()


def _profit_ratios_from_trades(trades: list) -> List[float]:
    ratios = []
    for trade in trades or []:
        ratio = trade.get("profit_ratio")
        if ratio is None:
            profit_abs = trade.get("profit_abs")
            stake = trade.get("stake_amount")
            if stake is None:
                amount = trade.get("amount")
                open_rate = trade.get("open_rate")
                if amount is not None and open_rate is not None:
                    stake = abs(amount) * float(open_rate)
            if profit_abs is not None and stake:
                ratio = float(profit_abs) / float(stake)
        if ratio is not None:
            try:
                ratios.append(float(ratio))
            except (TypeError, ValueError):
                continue
    return ratios


def _skew_kurtosis(values: List[float]) -> tuple[float, float]:
    n = len(values)
    if n < 3:
        return 0.0, 0.0

    mean_value = sum(values) / n
    deviations = [x - mean_value for x in values]
    m2 = sum(x * x for x in deviations) / n
    if m2 <= 0:
        return 0.0, 0.0

    m3 = sum(x * x * x for x in deviations) / n
    m4 = sum(x * x * x * x for x in deviations) / n
    skew = m3 / math.sqrt(m2**3)
    kurt = m4 / (m2**2)
    return skew, kurt


def deflated_sharpe_ratio(sr_hat, sr_benchmark, T, skew, kurt, n_trials):
    """Deflated Sharpe Ratio formula from López de Prado.
    Source: https://github.com/hudson-and-thames/mlfinlab"""
    T = max(int(T), 2)
    n_trials = max(int(n_trials), 2)
    z = _NORMAL_DIST.inv_cdf(1.0 - 1.0 / n_trials)
    V_sr = (1 - skew * sr_hat + ((kurt - 1) / 4) * sr_hat**2) / max(T - 1, 1)
    E_maxSR = sr_benchmark * (((1 - 0.5772) / z) + z)
    return _NORMAL_DIST.cdf((sr_hat - E_maxSR) / math.sqrt(max(V_sr, 1e-12)))


def compute_dsr(backtest_summary: dict, trades: list = None) -> dict:
    """Compute a realistic Deflated Sharpe Ratio from backtest metrics."""
    result = {
        "dsr": None,
        "skew": None,
        "kurtosis": None,
        "benchmark_sharpe": None,
        "trades_used": 0,
        "note": "Deflated Sharpe Ratio not calculated.",
    }

    sr_hat = backtest_summary.get("sharpe") or backtest_summary.get("sharpe_ratio")
    if sr_hat is None:
        return result

    try:
        sr_hat = float(sr_hat)
    except (TypeError, ValueError):
        return result

    trade_returns = _profit_ratios_from_trades(trades) if trades else []
    skew, kurt = _skew_kurtosis(trade_returns)
    if not trade_returns:
        skew, kurt = 0.0, 0.0

    T = backtest_summary.get("trade_count") or backtest_summary.get("total_trades") or len(trade_returns) or 1
    n_trials = backtest_summary.get("trade_count") or len(trade_returns) or 1
    sr_benchmark = float(backtest_summary.get("benchmark_sharpe") or 0.0)

    dsr_value = deflated_sharpe_ratio(sr_hat, sr_benchmark, T, skew, kurt, n_trials)
    result.update({
        "dsr": round(dsr_value, 6),
        "skew": round(skew, 6),
        "kurtosis": round(kurt, 6),
        "benchmark_sharpe": sr_benchmark,
        "trades_used": len(trade_returns),
        "note": "Deflated Sharpe Ratio calcolato con formula di López de Prado.",
    })
    return result
