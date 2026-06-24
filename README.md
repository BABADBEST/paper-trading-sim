# paper-trading-sim

A live paper-trading simulator with a web dashboard.

## Features

- **Live market data** – simulated price stream with geometric random walk
- **Charting + SMA/EMA indicators** – real-time canvas chart with overlays
- **Strategy backtesting** – run historical strategy tests with `Backtester`
- **Risk controls** – configurable max position and daily loss limit
- **Fake order matching** – immediate simulated fills on buy/sell
- **P&L dashboard** – live equity, realized/unrealized P&L, win rate

## Quick start

```bash
pip install -r requirements.txt   # install dependencies (Flask)
python -m trading_sim              # opens live dashboard at http://localhost:5000
```

Or install as a package:

```bash
pip install .
trading-sim                        # same thing, launches the server
```

## Run tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## Core API

```python
from trading_sim import Backtester, PnLDashboard, LiveTradingEngine, build_chart_series

# Backtesting
result = Backtester().run(prices, strategy, risk, qty_per_trade)
PnLDashboard.summarize(result)

# Live trading
engine = LiveTradingEngine()
engine.start(seed_price=100.0)
engine.place_order("buy", qty=1)
engine.snapshot()
```
