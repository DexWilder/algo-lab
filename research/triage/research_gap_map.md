# Research Gap Map — Algo Lab

## Current Family Coverage

| Family | Harvested | Converted | Convert Queue | Status |
|--------|-----------|-----------|---------------|--------|
| orb | 18 | 1 | 2 | IN PROGRESS |
| vwap | 23 | 1 | 4 | IN PROGRESS |
| ict | 13 | 1 | 2 | IN PROGRESS |
| pb | 0 | 0 | 0 | VALIDATED |
| rev | 0 | 0 | 0 | GAP |
| trend | 0 | 0 | 0 | GAP |
| session | 0 | 0 | 0 | GAP |
| opening_drive | 0 | 0 | 0 | GAP |

## Entry Model Coverage

| Entry Model | Count | Families |
|-------------|-------|----------|
| breakout | 18 | ict, orb, vwap |
| mean_reversion | 12 | vwap |
| crossover | 11 | ict, orb, vwap |
| sweep_reversal | 8 | ict, orb, vwap |
| pullback | 7 | ict, vwap |
| fvg | 4 | ict |
| gap | 3 | ict, orb, vwap |
| order_block | 3 | ict |

## Identified Gaps

- **Pullback family**: Validated internally (pb_trend) but no external harvest for comparison/diversification
- **Pure Mean Reversion**: No non-VWAP reversion strategies (Bollinger band, RSI extremes, etc.)
- **Pure Trend Following**: No MA crossover / momentum strategies in harvest (only SMA-crossover in lab)
- **Session-specific**: No London/Asia session strategies — all US-focused
- **Opening Drive**: Market profile open drive (only ORB-002 partially covers this)

## Overrepresented Areas

- **VWAP Mean Reversion**: 12 strategies — heavily duplicated, cluster aggressively

## Recommended Next Harvest Targets

1. **Pure Mean Reversion** (non-VWAP) — Bollinger band squeeze, RSI extremes, Keltner channels
2. **London/Asia Session** strategies — diversify away from US-only trading hours
3. **Momentum/Trend** — pure breakout-continuation or momentum factor strategies
4. **Gap strategies** — overnight gap fade/continuation for index futures
5. **Market profile** — opening drive, value area, POC-based strategies
