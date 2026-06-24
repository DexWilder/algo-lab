# FQL Forge Daily — 2026-05-12

**Run mode:** dry-run
**Total runtime:** 160.4s
**Candidates tested:** 5
**Verdict counts:** {'PASS': 2, 'WATCH': 3, 'KILL': 0, 'RETEST': 0}

## Per-candidate results

| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Runtime | Verdict |
|---|---|---|---:|---:|---:|---:|---:|---|
| XB-ORB-EMA-Chandelier-MNQ | MNQ | Asymmetric exit alt — chandelier trailing exit instead of profit_ladder | 1204 | 1.569 | 32551 | -1651 | 23.6s | PASS |
| XB-ORB-EMA-TimeStop-MNQ | MNQ | Asymmetric exit alt — fixed time-stop exit (tail-engine due to forced cutoff) | 1204 | 1.493 | 27295 | -1862 | 41.8s | PASS |
| XB-ORB-EMA-MidlineTarget-MNQ | MNQ | Asymmetric exit alt — midline target (different exit philosophy) | 1204 | 1.087 | 2475 | -2659 | 40.1s | WATCH |
| XB-PB-EMA-Ladder-MES | MES | Workhorse cross-asset (PB + proven trio) | 1478 | 1.155 | 6797 | -1876 | 36.0s | WATCH |
| XB-PB-EMA-Ladder-MGC | MGC | Workhorse cross-asset | 860 | 1.164 | 4636 | -2219 | 18.9s | WATCH |

## Architecture trends

- PASS assets in this batch: ['MNQ', 'MNQ']
- Per the donor catalog, ema_slope + profit_ladder remain co-validated load-bearing pair.

## Next-batch recommendation

- Next safe candidates to screen (14 untested in this run): ['XB-PB-EMA-Ladder-MCL', 'XB-PB-EMA-Ladder-MYM', 'XB-BB-EMA-Ladder-MES']...

## Safety affirmation

- No registry mutation
- No Lane A surfaces touched
- No runtime/scheduler/portfolio/checkpoint changes
- Operator approves all promotions / appends
