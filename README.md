# paper-trading-sim

Minimal Python paper-trading simulator that includes:

- live market-data series handling (price stream input)
- chart data generation with SMA/EMA indicators
- strategy backtesting
- risk controls (position cap + daily loss limit)
- fake order matching (immediate simulated fills)
- P&L dashboard summary

## Quick start

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## Core API

- `trading_sim.build_chart_series(prices, sma_period, ema_period)`
- `trading_sim.Backtester().run(prices, strategy, risk, qty_per_trade)`
- `trading_sim.PnLDashboard.summarize(result)`
