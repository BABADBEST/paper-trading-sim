import json
import unittest

from trading_sim.server import app, engine


class ServerRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        engine.start(seed_price=100.0)
        # Let a few ticks generate
        import time
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        engine.stop()

    def setUp(self):
        self.client = app.test_client()

    def test_index_returns_html(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Paper Trading Simulator", resp.data)

    def test_snapshot_endpoint(self):
        resp = self.client.get("/snapshot")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn("last_price", data)
        self.assertIn("total_pnl", data)

    def test_order_buy_and_sell(self):
        resp = self.client.post("/order", json={"side": "buy", "qty": 1})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["side"], "buy")

        resp = self.client.post("/order", json={"side": "sell", "qty": 1})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["side"], "sell")

    def test_order_invalid_side(self):
        resp = self.client.post("/order", json={"side": "hold", "qty": 1})
        self.assertEqual(resp.status_code, 400)

    def test_reset_endpoint(self):
        resp = self.client.post("/reset")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["status"], "reset")


if __name__ == "__main__":
    unittest.main()
