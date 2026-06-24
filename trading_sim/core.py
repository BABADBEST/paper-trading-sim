from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Literal, Optional, Sequence

Signal = Literal["buy", "sell", "hold"]


def sma(values: Sequence[float], period: int) -> List[Optional[float]]:
    if period <= 0:
        raise ValueError("period must be > 0")
    out: List[Optional[float]] = []
    window_sum = 0.0
    for i, value in enumerate(values):
        window_sum += value
        if i >= period:
            window_sum -= values[i - period]
        if i + 1 < period:
            out.append(None)
        else:
            out.append(window_sum / period)
    return out


def ema(values: Sequence[float], period: int) -> List[Optional[float]]:
    if period <= 0:
        raise ValueError("period must be > 0")
    out: List[Optional[float]] = [None] * len(values)
    if len(values) < period:
        return out
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    alpha = 2 / (period + 1)
    current = seed
    for i in range(period, len(values)):
        current = (values[i] - current) * alpha + current
        out[i] = current
    return out


def build_chart_series(
    prices: Sequence[float], sma_period: int = 5, ema_period: int = 5
) -> Dict[str, List[Optional[float]]]:
    return {"price": list(prices), "sma": sma(prices, sma_period), "ema": ema(prices, ema_period)}


@dataclass
class RiskControls:
    max_position: int = 10
    daily_loss_limit: float = 500.0

    def can_buy(self, current_position: int) -> bool:
        return current_position < self.max_position

    def can_trade(self, total_pnl: float) -> bool:
        return total_pnl > -self.daily_loss_limit


@dataclass
class Trade:
    side: Literal["buy", "sell"]
    qty: int
    price: float
    pnl: float = 0.0


@dataclass
class BacktestResult:
    trades: List[Trade]
    equity_curve: List[float]
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float


class Backtester:
    def __init__(self, starting_cash: float = 10_000.0, fee_bps: float = 1.0):
        self.starting_cash = starting_cash
        self.fee_bps = fee_bps

    def run(
        self,
        prices: Sequence[float],
        strategy: Callable[[int, float, Dict[str, List[Optional[float]]]], Signal],
        risk: Optional[RiskControls] = None,
        qty_per_trade: int = 1,
    ) -> BacktestResult:
        if not prices:
            return BacktestResult([], [], 0.0, 0.0, 0.0)
        risk = risk or RiskControls()
        chart = build_chart_series(prices)

        cash = self.starting_cash
        position = 0
        avg_entry = 0.0
        realized = 0.0
        equity_curve: List[float] = []
        trades: List[Trade] = []

        for i, price in enumerate(prices):
            unrealized = (price - avg_entry) * position if position else 0.0
            total_pnl = realized + unrealized
            signal = strategy(i, price, chart)

            if signal == "buy" and risk.can_trade(total_pnl) and risk.can_buy(position):
                qty = min(qty_per_trade, risk.max_position - position)
                if qty > 0:
                    fee = price * qty * (self.fee_bps / 10_000)
                    cash -= price * qty + fee
                    avg_entry = ((avg_entry * position) + (price * qty)) / (position + qty)
                    position += qty
                    trades.append(Trade("buy", qty, price))

            elif signal == "sell" and position > 0 and risk.can_trade(total_pnl):
                qty = min(qty_per_trade, position)
                fee = price * qty * (self.fee_bps / 10_000)
                trade_pnl = (price - avg_entry) * qty
                cash += price * qty - fee
                position -= qty
                realized += trade_pnl
                if position == 0:
                    avg_entry = 0.0
                trades.append(Trade("sell", qty, price, pnl=trade_pnl))

            unrealized = (price - avg_entry) * position if position else 0.0
            equity_curve.append(cash + position * price)

        final_price = prices[-1]
        unrealized = (final_price - avg_entry) * position if position else 0.0
        total_pnl = realized + unrealized
        return BacktestResult(
            trades=trades,
            equity_curve=equity_curve,
            realized_pnl=realized,
            unrealized_pnl=unrealized,
            total_pnl=total_pnl,
        )


class PnLDashboard:
    @staticmethod
    def summarize(result: BacktestResult) -> Dict[str, float]:
        closed = [t for t in result.trades if t.side == "sell"]
        wins = [t for t in closed if t.pnl > 0]
        return {
            "realized_pnl": round(result.realized_pnl, 2),
            "unrealized_pnl": round(result.unrealized_pnl, 2),
            "total_pnl": round(result.total_pnl, 2),
            "trades": float(len(result.trades)),
            "win_rate": (len(wins) / len(closed) * 100.0) if closed else 0.0,
        }
