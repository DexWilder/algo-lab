# FQL Forge Daily — 2026-05-08

**Run mode:** dry-run
**Total runtime:** 94.3s
**Candidates tested:** 5
**Verdict counts:** {'PASS': 3, 'WATCH': 2, 'KILL': 0, 'RETEST': 0}

## Per-candidate results

| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Runtime | Verdict |
|---|---|---|---:|---:|---:|---:|---:|---|
| XB-BB-EMA-AfternoonOnly-MGC | MGC | Sparse-session tail-engine — BB entry MGC, afternoon-restricted | 379 | 1.191 | 1693 | -2272 | 11.2s | PASS |
| XB-ORB-EMA-Chandelier-MNQ | MNQ | Asymmetric exit alt — chandelier trailing exit instead of profit_ladder | 1202 | 1.565 | 32310 | -1651 | 20.9s | PASS |
| XB-ORB-EMA-TimeStop-MNQ | MNQ | Asymmetric exit alt — fixed time-stop exit (tail-engine due to forced cutoff) | 1202 | 1.488 | 26972 | -1862 | 20.6s | PASS |
| XB-ORB-EMA-MidlineTarget-MNQ | MNQ | Asymmetric exit alt — midline target (different exit philosophy) | 1202 | 1.085 | 2416 | -2659 | 20.6s | WATCH |
| XB-PB-EMA-Ladder-MES | MES | Workhorse cross-asset (PB + proven trio) | 1476 | 1.155 | 6799 | -1876 | 20.9s | WATCH |

## Architecture trends

- PASS assets in this batch: ['MGC', 'MNQ', 'MNQ']
- Per the donor catalog, ema_slope + profit_ladder remain co-validated load-bearing pair.

## Next-batch recommendation

- Next safe candidates to screen (14 untested in this run): ['XB-PB-EMA-Ladder-MGC', 'XB-PB-EMA-Ladder-MCL', 'XB-PB-EMA-Ladder-MYM']...

## Safety affirmation

- No registry mutation
- No Lane A surfaces touched
- No runtime/scheduler/portfolio/checkpoint changes
- Operator approves all promotions / appends
