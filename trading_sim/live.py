from __future__ import annotations

import math
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Literal, Optional

from .core import PnLDashboard, RiskControls, Trade, build_chart_series


@dataclass
class LiveTradingEngine:
    """Runs a simulated live market feed and accepts manual orders."""

    starting_cash: float = 10_000.0
    fee_bps: float = 1.0
    risk: RiskControls = field(default_factory=RiskControls)
    tick_interval: float = 1.0  # seconds between ticks

    # ---- internal state (set on start) ----
    cash: float = field(init=False, default=0.0)
    position: int = field(init=False, default=0)
    avg_entry: float = field(init=False, default=0.0)
    realized_pnl: float = field(init=False, default=0.0)
    prices: List[float] = field(init=False, default_factory=list)
    trades: List[Trade] = field(init=False, default_factory=list)
    _running: bool = field(init=False, default=False)
    _thread: Optional[threading.Thread] = field(init=False, default=None)
    _lock: threading.Lock = field(init=False, default_factory=threading.Lock)
    _listeners: List[Callable[[float], None]] = field(init=False, default_factory=list)

    def reset(self) -> None:
        with self._lock:
            self.cash = self.starting_cash
            self.position = 0
            self.avg_entry = 0.0
            self.realized_pnl = 0.0
            self.prices = []
            self.trades = []

    # ------ price generation (geometric Brownian-ish random walk) ------
    @staticmethod
    def _next_price(last: float, mu: float = 0.0, sigma: float = 0.002) -> float:
        drift = mu - 0.5 * sigma * sigma
        shock = sigma * random.gauss(0, 1)
        return last * math.exp(drift + shock)

    # ------ streaming control ------
    def start(self, seed_price: float = 100.0) -> None:
        self.reset()
        self._running = True
        self._thread = threading.Thread(target=self._run, args=(seed_price,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def subscribe(self, callback: Callable[[float], None]) -> None:
        self._listeners.append(callback)

    def _run(self, seed_price: float) -> None:
        price = seed_price
        while self._running:
            price = self._next_price(price)
            with self._lock:
                self.prices.append(round(price, 4))
            for cb in self._listeners:
                cb(price)
            time.sleep(self.tick_interval)

    # ------ order entry ------
    def place_order(self, side: Literal["buy", "sell"], qty: int = 1) -> Optional[Trade]:
        with self._lock:
            if not self.prices:
                return None
            price = self.prices[-1]
            unrealized = (price - self.avg_entry) * self.position if self.position else 0.0
            total_pnl = self.realized_pnl + unrealized

            if side == "buy":
                if not self.risk.can_trade(total_pnl) or not self.risk.can_buy(self.position):
                    return None
                qty = min(qty, self.risk.max_position - self.position)
                if qty <= 0:
                    return None
                fee = price * qty * (self.fee_bps / 10_000)
                self.cash -= price * qty + fee
                self.avg_entry = (
                    (self.avg_entry * self.position + price * qty) / (self.position + qty)
                )
                self.position += qty
                trade = Trade("buy", qty, price)
                self.trades.append(trade)
                return trade

            elif side == "sell":
                if self.position <= 0 or not self.risk.can_trade(total_pnl):
                    return None
                qty = min(qty, self.position)
                fee = price * qty * (self.fee_bps / 10_000)
                trade_pnl = (price - self.avg_entry) * qty
                self.cash += price * qty - fee
                self.position -= qty
                self.realized_pnl += trade_pnl
                if self.position == 0:
                    self.avg_entry = 0.0
                trade = Trade("sell", qty, price, pnl=trade_pnl)
                self.trades.append(trade)
                return trade

        return None

    # ------ snapshots ------
    def snapshot(self) -> Dict:
        with self._lock:
            last_price = self.prices[-1] if self.prices else 0.0
            unrealized = (
                (last_price - self.avg_entry) * self.position if self.position else 0.0
            )
            chart = {}
            if len(self.prices) >= 2:
                chart = build_chart_series(self.prices, sma_period=5, ema_period=5)

            return {
                "last_price": round(last_price, 4),
                "cash": round(self.cash, 2),
                "position": self.position,
                "avg_entry": round(self.avg_entry, 4),
                "realized_pnl": round(self.realized_pnl, 2),
                "unrealized_pnl": round(unrealized, 2),
                "total_pnl": round(self.realized_pnl + unrealized, 2),
                "equity": round(self.cash + self.position * last_price, 2),
                "num_trades": len(self.trades),
                "chart": chart,
                "trades": [
                    {
                        "side": t.side,
                        "qty": t.qty,
                        "price": round(t.price, 4),
                        "pnl": round(t.pnl, 4),
                    }
                    for t in self.trades[-50:]  # last 50
                ],
            }
