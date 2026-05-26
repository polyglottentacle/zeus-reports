import json


def compute_kelly_fraction(backtest_summary: dict) -> dict:
    """Simple Kelly fraction estimator based on win rate and average win/loss."""
    result = {
        "kelly_fraction": None,
        "note": "No sufficient metrics for Kelly calculation.",
    }

    win_rate = backtest_summary.get("win_rate")
    avg_profit = backtest_summary.get("avg_profit_pct")
    avg_loss = backtest_summary.get("avg_loss_pct")

    if win_rate is not None and avg_profit is not None and avg_loss is not None and avg_loss != 0:
        try:
            b = avg_profit / abs(avg_loss)
            f = (win_rate - (1 - win_rate) / b) if b != 0 else None
            if f is not None:
                result["kelly_fraction"] = round(max(min(f, 1.0), 0.0), 4)
                result["note"] = "Estimated Kelly fraction."
        except Exception:
            result["note"] = "Error computing Kelly fraction."

    return result
