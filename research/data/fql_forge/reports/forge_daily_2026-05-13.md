# FQL Forge Daily — 2026-05-13

**Run mode:** dry-run
**Total runtime:** 67.8s
**Candidates tested:** 5
**Verdict counts:** {'PASS': 4, 'WATCH': 1, 'KILL': 0, 'RETEST': 0}

## Per-candidate results

| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Runtime | Verdict |
|---|---|---|---:|---:|---:|---:|---:|---|
| XB-PB-EMA-Ladder-MCL | MCL | Workhorse cross-asset / energy | 1066 | 1.307 | 7346 | -1093 | 14.7s | PASS |
| XB-PB-EMA-Ladder-MYM | MYM | Workhorse cross-asset | 467 | 1.355 | 4101 | -772 | 6.7s | PASS |
| XB-BB-EMA-Ladder-MES | MES | Workhorse cross-asset (BB + proven trio) | 685 | 1.126 | 2583 | -1831 | 20.7s | WATCH |
| XB-BB-EMA-Ladder-MGC | MGC | Workhorse cross-asset | 292 | 1.566 | 4603 | -637 | 10.9s | PASS |
| XB-BB-EMA-Ladder-MCL | MCL | Workhorse cross-asset / energy | 461 | 1.211 | 2290 | -874 | 14.7s | PASS |

## Architecture trends

- PASS assets in this batch: ['MCL', 'MYM', 'MGC', 'MCL']
- Per the donor catalog, ema_slope + profit_ladder remain co-validated load-bearing pair.

## Next-batch recommendation

- Next safe candidates to screen (14 untested in this run): ['XB-PB-EMA-Ladder-MES', 'XB-PB-EMA-Ladder-MGC', 'XB-BB-EMA-Ladder-MYM']...

## Safety affirmation

- No registry mutation
- No Lane A surfaces touched
- No runtime/scheduler/portfolio/checkpoint changes
- Operator approves all promotions / appends
