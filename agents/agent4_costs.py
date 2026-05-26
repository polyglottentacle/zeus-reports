def estimate_costs(backtest_summary: dict) -> dict:
    """Estimate trading costs, slippage and simple tax liabilities."""
    result = {
        "commissioni_stimate": None,
        "slippage_stimato": None,
        "funding_rate": 0.0,
        "tassa_box3_stimata": None,
        "tassa_box1_rischio": None,
        "profit_netto_stimato": None,
        "note": "No metrics available to estimate costs.",
    }

    profit_pct = backtest_summary.get("profit_pct") or backtest_summary.get("profit_total")
    trade_count = backtest_summary.get("trade_count") or backtest_summary.get("total_trades")
    stake = backtest_summary.get("stake_amount") or backtest_summary.get("stake") or backtest_summary.get("equity") or 1000
    patrimonio = backtest_summary.get("patrimonio") or stake

    try:
        trade_count = int(trade_count) if trade_count is not None else 0
    except Exception:
        trade_count = 0

    try:
        stake = float(stake)
    except Exception:
        stake = 1000.0

    try:
        patrimonio = float(patrimonio)
    except Exception:
        patrimonio = stake

    if profit_pct is not None and trade_count >= 0:
        try:
            profit_pct = float(profit_pct)
            profit_amount = profit_pct * stake
            commission_rate = 0.001
            slippage_rate = 0.0005

            commissioni = trade_count * commission_rate * stake
            slippage = trade_count * slippage_rate * stake
            tassa_box3 = patrimonio * 0.06 * 0.36
            tassa_box1 = max(0.0, profit_amount) * 0.495
            profit_netto = profit_amount - commissioni - tassa_box3

            result.update({
                "commissioni_stimate": round(commissioni, 2),
                "slippage_stimato": round(slippage, 2),
                "funding_rate": 0.0,
                "tassa_box3_stimata": round(tassa_box3, 2),
                "tassa_box1_rischio": round(tassa_box1, 2),
                "profit_netto_stimato": round(profit_netto, 2),
                "note": "Estimated trading costs and tax liabilities from backtest metrics.",
            })
        except Exception:
            result["note"] = "Error computing estimated costs."

    return result
