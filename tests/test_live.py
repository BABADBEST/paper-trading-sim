import time
import unittest

from trading_sim.live import LiveTradingEngine
from trading_sim.core import RiskControls


class LiveEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = LiveTradingEngine(
            starting_cash=10_000.0,
            tick_interval=0.05,
            risk=RiskControls(max_position=5, daily_loss_limit=500),
        )

    def tearDown(self):
        self.engine.stop()

    def test_start_generates_prices(self):
        self.engine.start(seed_price=100.0)
        time.sleep(0.3)
        snap = self.engine.snapshot()
        self.assertGreater(len(self.engine.prices), 0)
        self.assertGreater(snap["last_price"], 0)

    def test_buy_and_sell_orders(self):
        self.engine.start(seed_price=50.0)
        time.sleep(0.2)
        trade = self.engine.place_order("buy", qty=2)
        self.assertIsNotNone(trade)
        self.assertEqual(trade.side, "buy")
        self.assertEqual(trade.qty, 2)
        self.assertEqual(self.engine.position, 2)

        trade = self.engine.place_order("sell", qty=1)
        self.assertIsNotNone(trade)
        self.assertEqual(trade.side, "sell")
        self.assertEqual(self.engine.position, 1)

    def test_risk_limits_enforced(self):
        self.engine.start(seed_price=100.0)
        time.sleep(0.15)
        # Buy up to max_position
        for _ in range(5):
            self.engine.place_order("buy", qty=1)
        self.assertEqual(self.engine.position, 5)
        # Next buy should be rejected
        rejected = self.engine.place_order("buy", qty=1)
        self.assertIsNone(rejected)

    def test_sell_without_position_rejected(self):
        self.engine.start(seed_price=100.0)
        time.sleep(0.15)
        rejected = self.engine.place_order("sell", qty=1)
        self.assertIsNone(rejected)

    def test_snapshot_has_chart_data(self):
        self.engine.start(seed_price=100.0)
        time.sleep(0.5)
        snap = self.engine.snapshot()
        self.assertIn("chart", snap)
        self.assertIn("last_price", snap)
        self.assertIn("total_pnl", snap)

    def test_reset_clears_state(self):
        self.engine.start(seed_price=100.0)
        time.sleep(0.2)
        self.engine.place_order("buy", qty=1)
        self.engine.reset()
        self.assertEqual(self.engine.position, 0)
        self.assertEqual(self.engine.realized_pnl, 0.0)
        self.assertEqual(len(self.engine.trades), 0)

    def test_subscribe_callback(self):
        received = []
        self.engine.subscribe(lambda p: received.append(p))
        self.engine.start(seed_price=100.0)
        time.sleep(0.3)
        self.assertGreater(len(received), 0)


if __name__ == "__main__":
    unittest.main()
