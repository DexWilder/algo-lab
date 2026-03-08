# Test: v6.3.1 — ADX 14 + Extended Range

- **Test ID**: T003
- **Version**: v6.3.1
- **Market**: MES1! 5m
- **Changed from T002**: `adxMin = 14.0` (was 16.0) + extended date range
- **Carried from T002**: `mtfP1 = "15m Only"`
- **Date range**: Nov 2024 → Feb 2026 (~15 months)

## Purpose
T001/T002 showed 66-day dead zone (Nov 24 → Jan 30) with zero trades.
Two hypotheses being tested simultaneously:
1. Is the dead zone seasonal (holiday markets)? → extended range answers this
2. Is ADX filtering too aggressive? → adxMin 14 vs 16 answers this

## Expected Outcome
- Trades increase significantly (target: 50+ over 15 months)
- PF stays above 1.4
- DD remains contained
- Dec-Jan trade gaps either persist (seasonal) or fill (ADX was the bottleneck)

## Failure Condition
- If PF collapses below 1.2 → ADX 16 was protecting quality
- If trades still cluster with 2-month gaps → problem is deeper than ADX

## Files
- [ ] trades.csv (TV export)
- [ ] status_label.png

## Results
- Net P&L:
- Max DD:
- Profit Factor:
- Win %:
- Total Trades:
- Trades/month:
- Dec-Jan trade count:
- Green Lock Days:
- Halt Days:
- Lucid Busted:
- Lucid Locked:

## Notes
