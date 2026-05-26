import json


def compute_dsr(backtest_summary: dict) -> dict:
    """Compute a simple Deflated Sharpe Ratio estimate from available metrics."""
    dsr_result = {
        "dsr": None,
        "note": "Insufficient metrics for DSF computation.",
    }

    # Use available fields if present
    profit_pct = backtest_summary.get("profit_pct")
    drawdown_pct = backtest_summary.get("drawdown_pct")
    trades = backtest_summary.get("trade_count")

    if profit_pct is not None and drawdown_pct is not None and trades is not None:
        try:
            if drawdown_pct != 0 and trades > 0:
                dsr = (profit_pct / abs(drawdown_pct)) * (trades ** 0.5)
                dsr_result["dsr"] = round(dsr, 4)
                dsr_result["note"] = "Estimated DSR from profit, drawdown and trades."
        except Exception:
            dsr_result["note"] = "Error computing DSR."

    return dsr_result
