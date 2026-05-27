from typing import List


def _safe_mean(values: List[float]) -> float:
    values = [float(v) for v in values if v is not None]
    return sum(values) / len(values) if values else 0.0


def _extract_profit_ratios(trades: List[dict]) -> List[float]:
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


def compute_kelly_fraction(backtest_summary: dict, trades: List[dict] = None) -> dict:
    """Compute Kelly fraction using win rate and average win/loss ratios."""
    result = {
        "kelly_fraction": None,
        "half_kelly": None,
        "max_position_usdt": None,
        "win_rate": None,
        "avg_win_ratio": None,
        "avg_loss_ratio": None,
        "note": "Insufficient metrics for Kelly calculation.",
    }

    trade_returns = _extract_profit_ratios(trades) if trades else []
    if trade_returns:
        winners = [r for r in trade_returns if r > 0]
        losers = [abs(r) for r in trade_returns if r < 0]
        p = len(winners) / len(trade_returns)
        avg_win = _safe_mean(winners)
        avg_loss = _safe_mean(losers)
    else:
        p = float(backtest_summary.get("win_rate") or backtest_summary.get("winrate") or 0.0)
        avg_win = float(backtest_summary.get("avg_profit_pct") or backtest_summary.get("avg_profit") or 0.0)
        avg_loss = abs(float(backtest_summary.get("avg_loss_pct") or backtest_summary.get("avg_loss") or 0.0))

    q = 1.0 - p
    if avg_loss <= 0 or avg_win <= 0:
        result["note"] = "Non ci sono vittorie o perdite sufficienti per calcolare Kelly."
        return result

    b = avg_win / avg_loss
    if b <= 0:
        result["note"] = "Rapporto tra vincite e perdite non valido per Kelly."
        return result

    f = (p * b - q) / b
    f = max(min(f, 1.0), 0.0)
    stake = backtest_summary.get("stake_amount") or backtest_summary.get("starting_balance") or backtest_summary.get("equity") or 1000.0
    try:
        stake = float(stake)
    except (TypeError, ValueError):
        stake = 1000.0

    result.update({
        "kelly_fraction": round(f, 6),
        "half_kelly": round(f / 2, 6),
        "max_position_usdt": round(stake * f, 2),
        "win_rate": round(p, 6),
        "avg_win_ratio": round(avg_win, 6),
        "avg_loss_ratio": round(avg_loss, 6),
        "note": (
            "Kelly fraction calcolata con la formula f=(p*b-q)/b,"
            " dove p è la probabilità di successo e b è avg_win/avg_loss."
        ),
    })
    return result
