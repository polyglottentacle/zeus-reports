import math
from typing import List


def _trade_notional(trade: dict) -> float:
    stake = trade.get("stake_amount")
    if stake is not None:
        return abs(float(stake))
    amount = trade.get("amount")
    open_rate = trade.get("open_rate")
    if amount is not None and open_rate is not None:
        return abs(float(amount) * float(open_rate))
    return 0.0


def _commission_rate(trade: dict) -> float:
    leverage = float(trade.get("leverage") or 1.0)
    if leverage > 1.0:
        return 0.00045
    return 0.001


def _total_trade_costs(trades: List[dict]) -> tuple[float, float, float]:
    total_commission = 0.0
    total_slippage = 0.0
    total_funding = 0.0
    for trade in trades or []:
        notional = _trade_notional(trade)
        if notional <= 0:
            continue

        rate = _commission_rate(trade)
        total_commission += notional * rate * 2
        total_slippage += notional * 0.0005 * 2

        duration_minutes = trade.get("trade_duration") or 0
        duration_hours = float(duration_minutes) / 60.0
        funding_periods = duration_hours / 8.0
        total_funding += notional * 0.0001 * max(funding_periods, 0)

    return total_commission, total_slippage, total_funding


def _total_profit(trades: List[dict]) -> float:
    total = 0.0
    for trade in trades or []:
        profit_abs = trade.get("profit_abs")
        if profit_abs is not None:
            total += float(profit_abs)
    return total


def estimate_costs(backtest_summary: dict, trades: List[dict] = None) -> dict:
    """Estimate commissions, slippage, funding and Dutch tax liabilities."""
    result = {
        "commissioni_stimate": None,
        "slippage_stimato": None,
        "funding_rate": 0.0001,
        "funding_stimato": None,
        "tassa_box3_stimata": None,
        "tassa_box1_rischio": None,
        "profit_netto_stimato": None,
        "note": "No metrics available to estimate costs.",
    }

    trades = trades or []
    total_commission, total_slippage, total_funding = _total_trade_costs(trades)

    # Se non ci sono trade reali E non c'è un backtest, non inventare costi
    starting_balance_raw = backtest_summary.get("starting_balance") or backtest_summary.get("stake_amount") or backtest_summary.get("equity")
    if not trades and starting_balance_raw is None:
        result.update({
            "commissioni_stimate": 0.0,
            "slippage_stimato": 0.0,
            "funding_stimato": 0.0,
            "tassa_box3_stimata": None,
            "tassa_box1_rischio": None,
            "profit_netto_stimato": None,
            "note": "Nessun dato backtest o trade disponibile — costi non stimabili.",
        })
        return result

    patrimonio = float(starting_balance_raw or 1000.0)
    gross_profit = float(backtest_summary.get("profit_total_abs") or _total_profit(trades) or 0.0)

    tassa_box3 = patrimonio * 0.06 * 0.36
    tassa_box1 = max(0.0, gross_profit) * 0.495
    profit_netto = gross_profit - total_commission - total_slippage - total_funding - tassa_box3

    result.update({
        "commissioni_stimate": round(total_commission, 2),
        "slippage_stimato": round(total_slippage, 2),
        "funding_stimato": round(total_funding, 2),
        "tassa_box3_stimata": round(tassa_box3, 2),
        "tassa_box1_rischio": round(tassa_box1, 2),
        "profit_netto_stimato": round(profit_netto, 2),
        "note": (
            "Costi calcolati su commissioni Binance spot 0.1% o Hyperliquid futures 0.045%, "
            "slippage 0.05% per lato, funding 0.01% ogni 8h, tasse Box3 e Box1."
        ),
    })
    return result
