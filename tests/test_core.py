import unittest

from trading_sim import Backtester, PnLDashboard, RiskControls, build_chart_series, ema, sma


class IndicatorsTests(unittest.TestCase):
    def test_sma_and_ema(self):
        prices = [1, 2, 3, 4, 5]
        self.assertEqual(sma(prices, 3), [None, None, 2.0, 3.0, 4.0])
        ema_values = ema(prices, 3)
        self.assertEqual(ema_values[:2], [None, None])
        self.assertAlmostEqual(ema_values[2], 2.0)

    def test_chart_series_contains_indicators(self):
        chart = build_chart_series([10, 11, 12, 13, 14], sma_period=2, ema_period=2)
        self.assertEqual(chart["price"], [10, 11, 12, 13, 14])
        self.assertEqual(len(chart["sma"]), 5)
        self.assertEqual(len(chart["ema"]), 5)


class BacktestTests(unittest.TestCase):
    def test_backtest_risk_and_matching_and_dashboard(self):
        prices = [100, 101, 102, 103, 102, 101]
        has_position = False

        def strategy(i, _price, chart):
            nonlocal has_position
            if chart["sma"][i] is None:
                return "hold"
            if (
                not has_position
                and chart["ema"][i] is not None
                and chart["sma"][i] is not None
                and chart["ema"][i] >= chart["sma"][i]
            ):
                has_position = True
                return "buy"
            if (
                has_position
                and chart["ema"][i] is not None
                and chart["sma"][i] is not None
                and chart["ema"][i] < chart["sma"][i]
            ):
                has_position = False
                return "sell"
            return "hold"

        result = Backtester().run(
            prices=prices,
            strategy=strategy,
            risk=RiskControls(max_position=1, daily_loss_limit=1_000),
            qty_per_trade=1,
        )
        summary = PnLDashboard.summarize(result)
        self.assertGreaterEqual(summary["trades"], 1)
        self.assertIn("total_pnl", summary)
        self.assertLessEqual(
            len([t for t in result.trades if t.side == "buy"]),
            1,
            "max_position should prevent multiple simultaneous long fills",
        )


if __name__ == "__main__":
    unittest.main()
