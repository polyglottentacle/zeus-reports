import json


def estimate_costs(backtest_summary: dict) -> dict:
    """Estimate Dutch-style trading costs and taxes in a simple way."""
    result = {
        "estimated_costs_pct": None,
        "net_profit_pct": None,
        "note": "No metrics available to estimate costs.",
    }

    gross_profit = backtest_summary.get("profit_pct")
    if gross_profit is not None:
        # Assume a conservative 0.3% trading cost + 0.2% tax impact
        cost_pct = 0.5
        result["estimated_costs_pct"] = cost_pct
        result["net_profit_pct"] = round(gross_profit - cost_pct, 4)
        result["note"] = "Estimated costs using a simple fixed percentage."

    return result
