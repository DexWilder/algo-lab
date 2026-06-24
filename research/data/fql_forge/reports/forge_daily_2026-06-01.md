# FQL Forge Daily — 2026-06-01

**Run mode:** dry-run
**Total runtime:** 68.6s
**Candidates tested:** 5
**Verdict counts:** {'PASS': 2, 'WATCH': 2, 'KILL': 1, 'RETEST': 0}
**Evidence tier:** Cheap Screen Tier — verdicts are cheap-screen surfacing, NOT validated edge. See `feedback_durable_artifacts_both_surfaces.md` and the post-Phase-1 doctrine: Forge currently produces cheap-screen evidence, not validated edge evidence.

## Per-candidate results

| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Runtime | Verdict (tier) |
|---|---|---|---:|---:|---:|---:|---:|---|
| XB-PB-EMA-Ladder-MCL | MCL | Workhorse cross-asset / energy | 1078 | 1.073 | 1992 | -2077 | 15.0s | WATCH — Cheap Screen Tier |
| XB-PB-EMA-Ladder-MYM | MYM | Workhorse cross-asset | 479 | 1.222 | 2764 | -885 | 7.0s | PASS — Cheap Screen Tier |
| XB-BB-EMA-Ladder-MES | MES | Workhorse cross-asset (BB + proven trio) | 690 | 1.130 | 2689 | -1831 | 21.0s | WATCH — Cheap Screen Tier |
| XB-BB-EMA-Ladder-MGC | MGC | Workhorse cross-asset | 298 | 1.502 | 4460 | -650 | 11.0s | PASS — Cheap Screen Tier |
| XB-BB-EMA-Ladder-MCL | MCL | Workhorse cross-asset / energy | 466 | 1.007 | 80 | -1210 | 14.7s | KILL — Cheap Screen Tier |

## Architecture trends

- PASS assets in this batch: ['MYM', 'MGC']
- Per the donor catalog, ema_slope + profit_ladder remain co-validated load-bearing pair.

## Next-batch recommendation

- Next safe candidates to screen (14 untested in this run): ['XB-PB-EMA-Ladder-MES', 'XB-PB-EMA-Ladder-MGC', 'XB-BB-EMA-Ladder-MYM']...

## Safety affirmation

- No registry mutation
- No Lane A surfaces touched
- No runtime/scheduler/portfolio/checkpoint changes
- Operator approves all promotions / appends
