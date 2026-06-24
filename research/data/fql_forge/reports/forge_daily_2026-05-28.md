# FQL Forge Daily — 2026-05-28

**Run mode:** dry-run
**Total runtime:** 63.8s
**Candidates tested:** 5
**Verdict counts:** {'PASS': 2, 'WATCH': 3, 'KILL': 0, 'RETEST': 0}
**Evidence tier:** Cheap Screen Tier — verdicts are cheap-screen surfacing, NOT validated edge. See `feedback_durable_artifacts_both_surfaces.md` and the post-Phase-1 doctrine: Forge currently produces cheap-screen evidence, not validated edge evidence.

## Per-candidate results

| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Runtime | Verdict (tier) |
|---|---|---|---:|---:|---:|---:|---:|---|
| XB-PB-EMA-Ladder-MGC | MGC | Workhorse cross-asset | 870 | 1.136 | 3989 | -2219 | 10.9s | WATCH — Cheap Screen Tier |
| XB-PB-EMA-Ladder-MCL | MCL | Workhorse cross-asset / energy | 1076 | 1.068 | 1826 | -2077 | 14.4s | WATCH — Cheap Screen Tier |
| XB-PB-EMA-Ladder-MYM | MYM | Workhorse cross-asset | 477 | 1.214 | 2668 | -885 | 6.8s | PASS — Cheap Screen Tier |
| XB-BB-EMA-Ladder-MES | MES | Workhorse cross-asset (BB + proven trio) | 690 | 1.130 | 2689 | -1831 | 20.6s | WATCH — Cheap Screen Tier |
| XB-BB-EMA-Ladder-MGC | MGC | Workhorse cross-asset | 296 | 1.532 | 4532 | -637 | 11.1s | PASS — Cheap Screen Tier |

## Architecture trends

- PASS assets in this batch: ['MYM', 'MGC']
- Per the donor catalog, ema_slope + profit_ladder remain co-validated load-bearing pair.

## Next-batch recommendation

- Next safe candidates to screen (14 untested in this run): ['XB-PB-EMA-Ladder-MES', 'XB-BB-EMA-Ladder-MCL', 'XB-BB-EMA-Ladder-MYM']...

## Safety affirmation

- No registry mutation
- No Lane A surfaces touched
- No runtime/scheduler/portfolio/checkpoint changes
- Operator approves all promotions / appends
