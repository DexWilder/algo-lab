# Test: v6.3.1 Baseline

- **Test ID**: T001
- **Version**: v6.3.1
- **Market**: MES1! 5m
- **Changed**: Nothing (all defaults)
- **Date range**: Nov 2, 2025 — Feb 20, 2026 (~110 calendar days)

## Files
- [x] overview_screenshot.png
- [x] equity_curve.png
- [x] returns_breakdown.png
- [x] trades_analysis.png
- [x] detailed_stats.png
- [x] capital_efficiency.png
- [x] runups_drawdowns.png
- [x] trades.csv (TV export, 10 trades)

## Results
- **Net P&L**: +$331.35 (+0.66%)
- **Max DD (intrabar)**: $284.34 (0.56%)
- **Profit Factor**: 1.896
- **Win %**: 60.00% (6/10)
- **Total Trades**: 10 (8 short, 2 long)
- **Days to Lock**: NOT LOCKED ($331 of $3,100 needed)
- **Green Lock Days**: 0
- **P2 Banked Days**: 0
- **P2 Cooldown Days**: 0
- **Halt Days**: 1 (streak halt)
  - Loss halts: 0, Streak halts: 1, Weekly halts: 0, DD halts: 0
- **Lucid Busted**: false
- **Lucid Locked**: false
- **Avg Daily P&L**: ~$3.01
- **Commission**: $12.40 total

## Detailed Breakdown

### By Side
| Metric | All | Long | Short |
|--------|-----|------|-------|
| Net P&L | +$331.35 | -$167.48 | +$498.83 |
| Trades | 10 | 2 | 8 |
| Win % | 60% | 0% | 75% |
| Profit Factor | 1.896 | 0 | 3.464 |
| Avg P&L/trade | $33.14 | -$83.74 | $62.35 |
| Avg win | $116.89 | — | $116.89 |
| Avg loss | $92.49 | $83.74 | $101.24 |
| Win/Loss ratio | 1.264 | 0 | 1.155 |

### Trade Log
| # | Side | Entry | Exit | P&L | Bars | Result |
|---|------|-------|------|-----|------|--------|
| 1 | Short | Nov 7 7:25 | Nov 7 8:00 | +$112.51 | 7 | WIN |
| 2 | Short | Nov 17 7:40 | Nov 17 8:15 | +$118.76 | 7 | WIN |
| 3 | Short | Nov 20 12:05 | Nov 20 12:45 | +$180.01 | 8 | WIN |
| 4 | Short | Nov 21 7:05 | Nov 21 7:35 | +$142.51 | 6 | WIN |
| — | GAP | Nov 21 → Jan 30 | (~70 days, no trades) | — | — | — |
| 5 | Long | Jan 30 7:10 | Jan 30 7:25 | -$81.24 | 3 | LOSS |
| 6 | Long | Jan 30 7:40 | Jan 30 8:15 | -$86.24 | 7 | LOSS |
| 7 | Short | Feb 4 7:35 | Feb 4 7:40 | -$97.49 | 1 | LOSS |
| 8 | Short | Feb 5 6:55 | Feb 5 7:00 | +$133.76 | 1 | WIN |
| 9 | Short | Feb 5 13:05 | Feb 5 13:20 | +$13.76 | 3 | WIN |
| 10 | Short | Feb 13 7:00 | Feb 13 7:05 | -$104.99 | 1 | LOSS |

### Run-ups & Drawdowns
- Max equity run-up (intrabar): $587.54 (1.16%)
- Max equity drawdown (intrabar): $284.34 (0.56%)
- Avg equity run-up duration: 11 days
- Avg equity drawdown duration: 75 days

## Analysis

### What's Working
1. **Risk management is airtight** — max DD $284 is only 7.1% of the $4,000 Lucid trailing DD
2. **Short side is strong** — 75% win rate, 3.46 PF, +$498.83 net
3. **No busts, no locks** — account survived the full period safely
4. **Average win > average loss** — 1.264 ratio overall, positive expectancy

### What's NOT Working
1. **Way too few trades** — 10 trades in 110 days = 1 trade every 11 days
2. **70-day dead zone** (Nov 21 → Jan 30) — zero market participation
3. **Longs are pure losers** — 0/2 win rate, -$167.48 net
4. **Pace to lock is unreachable** — $3.01/day avg = ~1,000 days to reach $3,100
5. **Never triggered green lock** — best single day was ~$322 (trades 3+4 were same period) vs $600 target

### Lucid 100K Projection
At current pace: **$331 in 110 days → $3,100 would take ~1,030 days (~2.8 years)**
This is NOT viable for a prop firm evaluation.

### Key Questions for Next Tests
1. Is the 70-day gap caused by ADX filters being too strict during range-bound Dec/Jan?
2. Should longs be disabled entirely (short-only mode)?
3. Can green lock threshold ($600) be lowered to bank smaller green days?
4. Would relaxing trade limits (maxTradesP1 from 2→3) help?
5. Is the power window filtering killing too many opportunities?
