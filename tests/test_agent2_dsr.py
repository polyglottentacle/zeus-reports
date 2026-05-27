import unittest

from agents.agent2_dsr import compute_dsr


class TestAgent2DSR(unittest.TestCase):
    def test_dsr_returns_probability(self):
        summary = {"sharpe": 1.2, "trade_count": 10}
        trades = [
            {"profit_ratio": 0.02},
            {"profit_ratio": -0.01},
            {"profit_ratio": 0.015},
            {"profit_ratio": -0.02},
            {"profit_ratio": 0.03},
            {"profit_ratio": -0.01},
            {"profit_ratio": 0.01},
            {"profit_ratio": -0.015},
            {"profit_ratio": 0.02},
            {"profit_ratio": -0.005},
        ]
        result = compute_dsr(summary, trades)
        self.assertIsInstance(result["dsr"], float)
        self.assertGreaterEqual(result["dsr"], 0.0)
        self.assertLessEqual(result["dsr"], 1.0)
        self.assertEqual(result["trades_used"], 10)


if __name__ == "__main__":
    unittest.main()
