# FQL Forge Daily — 2026-05-27

**Run mode:** dry-run
**Total runtime:** 93.9s
**Candidates tested:** 5
**Verdict counts:** {'PASS': 3, 'WATCH': 2, 'KILL': 0, 'RETEST': 0}
**Evidence tier:** Cheap Screen Tier — verdicts are cheap-screen surfacing, NOT validated edge. See `feedback_durable_artifacts_both_surfaces.md` and the post-Phase-1 doctrine: Forge currently produces cheap-screen evidence, not validated edge evidence.

## Per-candidate results

| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Runtime | Verdict (tier) |
|---|---|---|---:|---:|---:|---:|---:|---|
| XB-BB-EMA-AfternoonOnly-MGC | MGC | Sparse-session tail-engine — BB entry MGC, afternoon-restricted | 383 | 1.194 | 1747 | -2272 | 10.9s | PASS — Cheap Screen Tier |
| XB-ORB-EMA-Chandelier-MNQ | MNQ | Asymmetric exit alt — chandelier trailing exit instead of profit_ladder | 1211 | 1.561 | 32430 | -1651 | 20.6s | PASS — Cheap Screen Tier |
| XB-ORB-EMA-TimeStop-MNQ | MNQ | Asymmetric exit alt — fixed time-stop exit (tail-engine due to forced cutoff) | 1211 | 1.494 | 27596 | -1862 | 20.7s | PASS — Cheap Screen Tier |
| XB-ORB-EMA-MidlineTarget-MNQ | MNQ | Asymmetric exit alt — midline target (different exit philosophy) | 1211 | 1.076 | 2186 | -2659 | 21.1s | WATCH — Cheap Screen Tier |
| XB-PB-EMA-Ladder-MES | MES | Workhorse cross-asset (PB + proven trio) | 1487 | 1.152 | 6731 | -1876 | 20.7s | WATCH — Cheap Screen Tier |

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
