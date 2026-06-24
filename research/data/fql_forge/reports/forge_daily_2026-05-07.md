# FQL Forge Daily — 2026-05-07

**Run mode:** dry-run
**Total runtime:** 83.1s
**Candidates tested:** 5
**Verdict counts:** {'PASS': 2, 'WATCH': 3, 'KILL': 0, 'RETEST': 0}

## Per-candidate results

| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Runtime | Verdict |
|---|---|---|---:|---:|---:|---:|---:|---|
| XB-VWAP-EMA-Ladder-MCL | MCL | Workhorse cross-asset / VWAP closeout test | 503 | 1.277 | 3153 | -1407 | 14.5s | PASS |
| XB-VWAP-EMA-Ladder-MYM | MYM | Workhorse cross-asset / VWAP closeout test | 272 | 1.489 | 3172 | -637 | 6.7s | PASS |
| XB-ORB-EMA-MorningOnly-MNQ | MNQ | Sparse-session tail-engine — morning-only XB | 1637 | 1.024 | 3629 | -11802 | 20.4s | WATCH |
| XB-ORB-EMA-AfternoonOnly-MNQ | MNQ | Sparse-session tail-engine — afternoon-only XB | 1640 | 1.069 | 7211 | -4307 | 20.8s | WATCH |
| XB-PB-EMA-MorningOnly-MNQ | MNQ | Sparse-session tail-engine — morning-only PB entry | 2063 | 1.074 | 8848 | -4399 | 20.7s | WATCH |

## Architecture trends

- PASS assets in this batch: ['MCL', 'MYM']
- Per the donor catalog, ema_slope + profit_ladder remain co-validated load-bearing pair.

## Next-batch recommendation

- Next safe candidates to screen (14 untested in this run): ['XB-PB-EMA-Ladder-MES', 'XB-PB-EMA-Ladder-MGC', 'XB-PB-EMA-Ladder-MCL']...

## Safety affirmation

- No registry mutation
- No Lane A surfaces touched
- No runtime/scheduler/portfolio/checkpoint changes
- Operator approves all promotions / appends
