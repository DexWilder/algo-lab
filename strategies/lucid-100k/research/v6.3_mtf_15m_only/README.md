# Test: v6.3.1 — P1 MTF 15m Only

- **Test ID**: T002
- **Version**: v6.3.1
- **Market**: MES1! 5m
- **Changed**: `mtfP1 = "15m Only"` (was "15m + 60m")
- **Date range**: Nov 2, 2025 — Feb 20, 2026

## Purpose
Baseline showed only 10 trades in 110 days — too few to evaluate.
Hypothesis: 60m EMA alignment is killing valid intraday pullbacks.
15m bias alone should be sufficient for MES 5m trend detection.

## Files
- [x] trades.csv (TV export, 13 trades)
- [x] status_label (screenshot captured)

## Results
- **Net P&L**: +$470.13 (+0.94%)
- **Max DD (trade-to-trade)**: ~$264.97
- **Profit Factor**: 2.034
- **Win %**: 61.5% (8/13)
- **Total Trades**: 13 (8 short, 5 long)
- **Days to Lock**: NOT LOCKED ($470 of $3,100)
- **Green Lock Days**: 0
- **Halt Days**: 1 (streak halt)
- **Lucid Busted**: false
- **Lucid Locked**: false
- **Floor**: $46,660
- **Recent PF**: 2.03

## Trade Log
| # | Side | Date | P&L | Result | Notes |
|---|------|------|-----|--------|-------|
| 1 | Short | Nov 7 | +$112.51 | WIN | same as T001 |
| 2 | Short | Nov 17 | +$118.76 | WIN | same as T001 |
| 3 | Short | Nov 20 | +$180.01 | WIN | same as T001 |
| 4 | Short | Nov 21 | +$142.51 | WIN | same as T001 |
| **5** | **Long** | **Nov 24** | **+$106.26** | **WIN** | **NEW — blocked by 60m in T001** |
| 6 | Long | Jan 30 | -$81.24 | LOSS | same as T001 (#5) |
| 7 | Long | Jan 30 | -$86.24 | LOSS | same as T001 (#6) |
| 8 | Short | Feb 4 | -$97.49 | LOSS | same as T001 (#7) |
| 9 | Short | Feb 5 | +$133.76 | WIN | same as T001 (#8) |
| 10 | Short | Feb 5 | +$13.76 | WIN | same as T001 (#9) |
| **11** | **Long** | **Feb 6** | **+$117.51** | **WIN** | **NEW — blocked by 60m in T001** |
| 12 | Short | Feb 13 | -$104.99 | LOSS | same as T001 (#10) |
| **13** | **Long** | **Feb 19** | **-$84.99** | **LOSS** | **NEW — blocked by 60m in T001** |

## Comparison vs T001 (Baseline)
| Metric | T001 (15m+60m) | T002 (15m Only) | Delta |
|--------|----------------|-----------------|-------|
| Total Trades | 10 | 13 | **+3 (+30%)** |
| Net P&L | +$331.35 | +$470.13 | **+$138.78 (+42%)** |
| PF | 1.896 | 2.034 | **+0.138** |
| Win % | 60% (6/10) | 61.5% (8/13) | +1.5% |
| Max DD | ~$265 | ~$265 | Same |
| Avg Trade | $33.14 | $36.16 | +$3.02 |
| Green Lock Days | 0 | 0 | Same |
| Streak Halts | 1 | 1 | Same |
| Avg Daily P&L | $3.01 | $4.27 | +$1.26 |
| Short Trades | 8 (6W/2L) | 8 (6W/2L) | **Identical** |
| Long Trades | 2 (0W/2L) | 5 (2W/3L) | +3, 40% WR |

## Key Findings

1. **All 8 short trades are IDENTICAL** between T001 and T002. The 60m filter had zero impact on shorts.
2. **The 3 new trades are ALL longs** — 60m was specifically blocking long entries.
3. **2 of 3 new longs were winners** (+$106 on Nov 24, +$118 on Feb 6). Net from new trades: +$138.78.
4. **PF improved** (1.896 → 2.034) — new trades are net positive.
5. **DD unchanged** — same max drawdown sequence.
6. **Still only 13 trades** — better but well short of 50+ needed.
7. **66-day dead zone** (Nov 24 → Jan 30) persists — this is NOT an MTF problem.

## Verdict
Relaxing P1 MTF helped marginally (+42% profit, +30% trades) but did NOT solve the core problem: the strategy sits out for 2 months during Dec-Jan. The bottleneck is elsewhere (ADX? power windows? regime detection?).
