def compute_kelly_fraction(backtest_summary: dict) -> dict:
    """Estimate Kelly fraction, half-Kelly and position sizing from backtest metrics."""
    result = {
        "kelly_fraction": None,
        "half_kelly": None,
        "max_position_usdt": None,
        "note": "Insufficient metrics for Kelly calculation.",
    }

    win_rate = backtest_summary.get("win_rate") or backtest_summary.get("winrate")
    avg_profit = backtest_summary.get("avg_profit_pct") or backtest_summary.get("avg_profit")
    avg_loss = backtest_summary.get("avg_loss_pct") or backtest_summary.get("avg_loss")

    profit_pct = backtest_summary.get("profit_pct") or backtest_summary.get("profit_total")
    profit_factor = backtest_summary.get("profit_factor")

    if win_rate is not None and avg_profit is not None and avg_loss is not None:
        source = "avg_profit"  # explicit average values
    elif win_rate is not None and profit_pct is not None and profit_factor is not None:
        source = "inferred"
    else:
        source = None

    if source is not None:
        try:
            win_rate = float(win_rate)
            if source == "avg_profit":
                avg_profit = float(avg_profit)
                avg_loss = float(avg_loss)
            else:
                profit_pct = float(profit_pct)
                profit_factor = float(profit_factor)
                if win_rate <= 0 or win_rate >= 1 or profit_factor == 1:
                    raise ValueError("Cannot infer average profit/loss")
                avg_loss = profit_pct / ((1 - win_rate) * (profit_factor - 1))
                avg_profit = profit_factor * ((1 - win_rate) / win_rate) * avg_loss

            if avg_loss == 0:
                raise ValueError("avg_loss is zero")

            b = avg_profit / abs(avg_loss)
            if b > 0:
                f = win_rate - (1 - win_rate) / b
                f = max(min(f, 1.0), 0.0)
                half_f = round(f / 2, 4)

                stake = backtest_summary.get("stake_amount") or backtest_summary.get("stake") or backtest_summary.get("equity") or backtest_summary.get("wallet_balance") or 1000
                try:
                    stake = float(stake)
                except Exception:
                    stake = 1000.0

                result["kelly_fraction"] = round(f, 4)
                result["half_kelly"] = half_f
                result["max_position_usdt"] = round(stake * f, 2)
                result["note"] = "Estimated Kelly fraction from backtest metrics."
        except Exception:
            result["note"] = "Error computing Kelly fraction."

    return result
