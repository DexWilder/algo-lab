# FQL Forge Daily — 2026-05-05

**Run mode:** dry-run
**Total runtime:** 77.3s
**Candidates tested:** 5
**Verdict counts:** {'PASS': 2, 'WATCH': 3, 'KILL': 0, 'RETEST': 0}

## Per-candidate results

| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Runtime | Verdict |
|---|---|---|---:|---:|---:|---:|---:|---|
| XB-PB-EMA-Ladder-MES | MES | Workhorse cross-asset (PB + proven trio) | 1473 | 1.151 | 6627 | -1876 | 21.3s | WATCH |
| XB-PB-EMA-Ladder-MGC | MGC | Workhorse cross-asset | 854 | 1.194 | 5338 | -2219 | 11.7s | WATCH |
| XB-PB-EMA-Ladder-MCL | MCL | Workhorse cross-asset / energy | 1061 | 1.311 | 7386 | -1093 | 15.6s | PASS |
| XB-PB-EMA-Ladder-MYM | MYM | Workhorse cross-asset | 462 | 1.351 | 4044 | -772 | 7.0s | PASS |
| XB-BB-EMA-Ladder-MES | MES | Workhorse cross-asset (BB + proven trio) | 682 | 1.123 | 2501 | -1831 | 21.8s | WATCH |

## Architecture trends

- PASS assets in this batch: ['MCL', 'MYM']
- Per the donor catalog, ema_slope + profit_ladder remain co-validated load-bearing pair.

## Next-batch recommendation

- Next safe candidates to screen (7 untested in this run): ['XB-BB-EMA-Ladder-MGC', 'XB-BB-EMA-Ladder-MCL', 'XB-BB-EMA-Ladder-MYM']...

## Safety affirmation

- No registry mutation
- No Lane A surfaces touched
- No runtime/scheduler/portfolio/checkpoint changes
- Operator approves all promotions / appends
