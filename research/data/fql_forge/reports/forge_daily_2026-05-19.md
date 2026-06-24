# FQL Forge Daily — 2026-05-19

**Run mode:** dry-run
**Total runtime:** 93.5s
**Candidates tested:** 5
**Verdict counts:** {'PASS': 3, 'WATCH': 2, 'KILL': 0, 'RETEST': 0}
**Evidence tier:** Cheap Screen Tier — verdicts are cheap-screen surfacing, NOT validated edge. See `feedback_durable_artifacts_both_surfaces.md` and the post-Phase-1 doctrine: Forge currently produces cheap-screen evidence, not validated edge evidence.

## Per-candidate results

| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Runtime | Verdict (tier) |
|---|---|---|---:|---:|---:|---:|---:|---|
| XB-ORB-EMA-AfternoonOnly-MNQ | MNQ | Sparse-session tail-engine — afternoon-only XB | 1648 | 1.067 | 7124 | -4307 | 20.8s | WATCH — Cheap Screen Tier |
| XB-PB-EMA-MorningOnly-MNQ | MNQ | Sparse-session tail-engine — morning-only PB entry | 2073 | 1.074 | 8904 | -4399 | 20.7s | WATCH — Cheap Screen Tier |
| XB-BB-EMA-AfternoonOnly-MGC | MGC | Sparse-session tail-engine — BB entry MGC, afternoon-restricted | 382 | 1.214 | 1895 | -2272 | 10.9s | PASS — Cheap Screen Tier |
| XB-ORB-EMA-Chandelier-MNQ | MNQ | Asymmetric exit alt — chandelier trailing exit instead of profit_ladder | 1207 | 1.574 | 32869 | -1651 | 20.8s | PASS — Cheap Screen Tier |
| XB-ORB-EMA-TimeStop-MNQ | MNQ | Asymmetric exit alt — fixed time-stop exit (tail-engine due to forced cutoff) | 1207 | 1.507 | 28076 | -1862 | 20.4s | PASS — Cheap Screen Tier |

## Architecture trends

- PASS assets in this batch: ['MGC', 'MNQ', 'MNQ']
- Per the donor catalog, ema_slope + profit_ladder remain co-validated load-bearing pair.

## Next-batch recommendation

- Next safe candidates to screen (14 untested in this run): ['XB-PB-EMA-Ladder-MES', 'XB-PB-EMA-Ladder-MGC', 'XB-PB-EMA-Ladder-MCL']...

## Safety affirmation

- No registry mutation
- No Lane A surfaces touched
- No runtime/scheduler/portfolio/checkpoint changes
- Operator approves all promotions / appends
