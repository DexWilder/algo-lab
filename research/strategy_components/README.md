# Strategy Component Library

Reusable building blocks extracted from harvested strategies.
Components can be recombined into new strategies for automated testing.

## Categories

### entries/
Entry logic patterns — trigger conditions for trade initiation.
Examples: VWAP deviation, EMA crossover, ORB breakout, FVG fill, liquidity sweep.

### filters/
Quality and regime filters — conditions that gate entry signals.
Examples: ADX trending, volume above MA, session time, RSI range, volatility regime.

### exits/
Exit models — how trades are closed.
Examples: ATR multiple bracket, trailing stop, time-based, target level, session close.

### risk_models/
Position sizing and risk controls.
Examples: fixed fractional, ATR-based stops, max daily loss, consecutive loss limit.

### session_models/
Time-based trading constraints.
Examples: NY open window, London/NY overlap, kill zones, power hours, session flatten.

## Component Format

Each component is a JSON file:
```json
{
  "id": "ENTRY-VWAP-DEV-001",
  "name": "VWAP Deviation Entry",
  "category": "entry",
  "description": "Enter when price extends N ATRs from VWAP",
  "parameters": {"dist_atr": 1.2, "direction": "mean_reversion"},
  "source_strategies": ["VWAP-003", "VWAP-007"],
  "automation_fitness": 5,
  "notes": ""
}
```

## Usage

Components feed the strategy generator pipeline:
```
Entry + Filter + Exit + Risk + Session → Candidate Strategy → Backtest
```
