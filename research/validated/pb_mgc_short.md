# ALGO-CORE-PB-MGC-001 — Validated Candidate

## Identity

| Field | Value |
|-------|-------|
| Strategy | PB Trend (Pullback Trend-Following) |
| Asset | MGC (Micro Gold) |
| Mode | Short-only |
| Timeframe | 5m |
| Data Source | Databento GLBX.MDP3 |
| Data Range | 2024-02-29 → 2026-03-06 (596 trading days) |
| Status | **Validated** |

## Performance

| Metric | Value |
|--------|------:|
| Profit Factor | 2.02 |
| Sharpe Ratio | 4.176 |
| Win Rate | 57.1% |
| Total PnL | $767.00 |
| Max Drawdown | $283.00 |
| Expectancy | $27.39/trade |
| Avg R | 0.437 |
| Avg Win | $94.94 |
| Avg Loss | -$62.67 |
| Best Trade | $290.00 |
| Worst Trade | -$118.00 |
| Trade Count | 28 |
| Trading Days | 26 |
| Avg Trades/Day | 1.08 |
| Max Consec Wins | 3 |
| Max Consec Losses | 2 |
| Gross Profit | $1,519.00 |
| Gross Loss | -$752.00 |

## Monthly Consistency

| Month | Trades | PnL | WR% |
|------:|-------:|----:|----:|
| 2024-03 | 2 | $102 | 100% |
| 2024-05 | 5 | $56 | 60% |
| 2024-07 | 3 | $37 | 33% |
| 2024-09 | 1 | -$36 | 0% |
| 2024-12 | 1 | $35 | 100% |
| 2025-01 | 3 | -$58 | 33% |
| 2025-03 | 3 | $14 | 67% |
| 2025-05 | 3 | $143 | 67% |
| 2025-07 | 4 | $8 | 50% |
| 2025-11 | 1 | -$94 | 0% |
| 2026-03 | 2 | $560 | 100% |

**8/11 months positive (73%)**

## Trade Duration

| Stat | Value |
|------|------:|
| Mean | 41.8 min |
| Median | 15.0 min |
| Max | 265 min |
| Under 30m | 78.6% |
| Under 60m | 89.3% |
| Over 2h | 10.7% |

## Session Distribution

| Hour | Trades | PnL | WR% |
|-----:|-------:|----:|----:|
| 08:xx | 2 | $3 | 50% |
| 09:xx | 11 | $415 | 54.5% |
| 10:xx | 12 | $336 | 58.3% |
| 13:xx | 1 | -$36 | 0% |
| 14:xx | 1 | $48 | 100% |
| 15:xx | 1 | $1 | 100% |

Morning window (08:45–11:00) produces 89% of trades and 98% of PnL.

## Drawdown Clusters

| Cluster | Trades | Max DD |
|--------:|-------:|-------:|
| #3–7 | 4 | $227 |
| #11–19 | 8 | $160 |
| #20–21 | 1 | $77 |
| #26–27 | 1 | $125 |

Largest drawdown ($227) lasted 4 trades. No catastrophic drawdown events.

## Equity Curve

See: `research/experiments/pb_mgc_short_analysis/equity_curve.csv`

Steady upward slope with shallow drawdowns. Two large winners in March 2026 ($290 + $270) create a hockey-stick tail — need to evaluate whether edge exists without those.

## Parameters (Frozen)

```
FAST_EMA=9, SLOW_EMA=21, TREND_EMA=200, MTF_EMA=600
ADX_MIN=14.0, VOL_MA_LEN=20, VOL_MULT=1.0
SL_ATR=1.5, TP_ATR=2.1, MIN_STOP_TICKS=20
Session: 08:30-15:15, Warmup: 15m
Power windows: 08:45-11:00, 13:30-15:10
```

## Risk Flags

1. **Small sample** — 28 trades is below the 50-trade threshold for statistical confidence
2. **Hockey-stick tail** — March 2026 ($560) accounts for 73% of total PnL
3. **Low frequency** — ~1 trade per active month, long periods with zero activity
4. **No April, June, Aug, Oct 2024; Feb, Apr, Jun, Aug, Sep, Oct, Dec 2025** — many months with no trades

## Next Steps

- Run on extended data (4+ years) to increase sample size
- Test sensitivity to parameter changes (especially SL/TP ATR multiples)
- Backtest on full-size GC to validate edge scales
- Monitor for regime dependency (gold bull market bias?)
