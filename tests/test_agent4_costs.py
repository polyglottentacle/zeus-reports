import unittest

from agents.agent4_costs import estimate_costs


class TestAgent4Costs(unittest.TestCase):
    def test_costs_from_trades(self):
        trades = [
            {
                "stake_amount": 100.0,
                "open_rate": 100.0,
                "amount": 1.0,
                "leverage": 1.0,
                "trade_duration": 480,
                "profit_abs": 1.0,
            }
        ]
        summary = {"starting_balance": 1000.0}
        result = estimate_costs(summary, trades)
        self.assertEqual(result["commissioni_stimate"], 0.2)
        self.assertEqual(result["slippage_stimato"], 0.1)
        self.assertEqual(result["funding_stimato"], 0.01)
        self.assertEqual(result["tassa_box3_stimata"], 21.6)
        self.assertEqual(result["profit_netto_stimato"], round(1.0 - 0.2 - 0.1 - 0.01 - 21.6, 2))


if __name__ == "__main__":
    unittest.main()
