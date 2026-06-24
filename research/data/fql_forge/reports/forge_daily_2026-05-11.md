# FQL Forge Daily — 2026-05-11

**Run mode:** dry-run
**Total runtime:** 81.1s
**Candidates tested:** 5
**Verdict counts:** {'PASS': 2, 'WATCH': 3, 'KILL': 0, 'RETEST': 0}

## Per-candidate results

| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Runtime | Verdict |
|---|---|---|---:|---:|---:|---:|---:|---|
| XB-VWAP-EMA-Ladder-MYM | MYM | Workhorse cross-asset / VWAP closeout test | 272 | 1.489 | 3172 | -637 | 7.0s | PASS |
| XB-ORB-EMA-MorningOnly-MNQ | MNQ | Sparse-session tail-engine — morning-only XB | 1639 | 1.024 | 3647 | -11802 | 20.8s | WATCH |
| XB-ORB-EMA-AfternoonOnly-MNQ | MNQ | Sparse-session tail-engine — afternoon-only XB | 1642 | 1.071 | 7478 | -4307 | 21.0s | WATCH |
| XB-PB-EMA-MorningOnly-MNQ | MNQ | Sparse-session tail-engine — morning-only PB entry | 2065 | 1.076 | 8991 | -4399 | 21.1s | WATCH |
| XB-BB-EMA-AfternoonOnly-MGC | MGC | Sparse-session tail-engine — BB entry MGC, afternoon-restricted | 380 | 1.194 | 1715 | -2272 | 11.2s | PASS |

## Architecture trends

- PASS assets in this batch: ['MYM', 'MGC']
- Per the donor catalog, ema_slope + profit_ladder remain co-validated load-bearing pair.

## Next-batch recommendation

- Next safe candidates to screen (14 untested in this run): ['XB-PB-EMA-Ladder-MES', 'XB-PB-EMA-Ladder-MGC', 'XB-PB-EMA-Ladder-MCL']...

## Safety affirmation

- No registry mutation
- No Lane A surfaces touched
- No runtime/scheduler/portfolio/checkpoint changes
- Operator approves all promotions / appends
