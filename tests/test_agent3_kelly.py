import unittest

from agents.agent3_kelly import compute_kelly_fraction


class TestAgent3Kelly(unittest.TestCase):
    def test_kelly_fraction_from_trades(self):
        trades = [
            {"profit_ratio": 0.02},
            {"profit_ratio": -0.01},
            {"profit_ratio": 0.015},
            {"profit_ratio": -0.02},
            {"profit_ratio": 0.025},
            {"profit_ratio": -0.01},
        ]
        result = compute_kelly_fraction({}, trades)
        self.assertIsInstance(result["kelly_fraction"], float)
        self.assertGreaterEqual(result["kelly_fraction"], 0.0)
        self.assertLessEqual(result["kelly_fraction"], 1.0)
        self.assertIsNotNone(result["win_rate"])
        self.assertGreater(result["win_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
