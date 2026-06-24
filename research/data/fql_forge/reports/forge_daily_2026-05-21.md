# FQL Forge Daily — 2026-05-21

**Run mode:** dry-run
**Total runtime:** 73.7s
**Candidates tested:** 5
**Verdict counts:** {'PASS': 2, 'WATCH': 2, 'KILL': 1, 'RETEST': 0}
**Evidence tier:** Cheap Screen Tier — verdicts are cheap-screen surfacing, NOT validated edge. See `feedback_durable_artifacts_both_surfaces.md` and the post-Phase-1 doctrine: Forge currently produces cheap-screen evidence, not validated edge evidence.

## Per-candidate results

| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Runtime | Verdict (tier) |
|---|---|---|---:|---:|---:|---:|---:|---|
| XB-BB-EMA-Ladder-MES | MES | Workhorse cross-asset (BB + proven trio) | 686 | 1.131 | 2701 | -1831 | 20.8s | WATCH — Cheap Screen Tier |
| XB-BB-EMA-Ladder-MGC | MGC | Workhorse cross-asset | 294 | 1.548 | 4588 | -637 | 11.0s | PASS — Cheap Screen Tier |
| XB-BB-EMA-Ladder-MCL | MCL | Workhorse cross-asset / energy | 462 | 0.983 | -204 | -1210 | 14.6s | KILL — Cheap Screen Tier |
| XB-BB-EMA-Ladder-MYM | MYM | Workhorse cross-asset | 239 | 1.551 | 3018 | -646 | 6.8s | PASS — Cheap Screen Tier |
| XB-VWAP-EMA-Ladder-MES | MES | Workhorse cross-asset / VWAP closeout test | 884 | 1.087 | 2338 | -3544 | 20.5s | WATCH — Cheap Screen Tier |

## Architecture trends

- PASS assets in this batch: ['MGC', 'MYM']
- Per the donor catalog, ema_slope + profit_ladder remain co-validated load-bearing pair.

## Next-batch recommendation

- Next safe candidates to screen (14 untested in this run): ['XB-PB-EMA-Ladder-MES', 'XB-PB-EMA-Ladder-MGC', 'XB-PB-EMA-Ladder-MCL']...

## Safety affirmation

- No registry mutation
- No Lane A surfaces touched
- No runtime/scheduler/portfolio/checkpoint changes
- Operator approves all promotions / appends
