# FQL Forge Daily — 2026-05-29

**Run mode:** dry-run
**Total runtime:** 68.2s
**Candidates tested:** 5
**Verdict counts:** {'PASS': 2, 'WATCH': 2, 'KILL': 1, 'RETEST': 0}
**Evidence tier:** Cheap Screen Tier — verdicts are cheap-screen surfacing, NOT validated edge. See `feedback_durable_artifacts_both_surfaces.md` and the post-Phase-1 doctrine: Forge currently produces cheap-screen evidence, not validated edge evidence.

## Per-candidate results

| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Runtime | Verdict (tier) |
|---|---|---|---:|---:|---:|---:|---:|---|
| XB-BB-EMA-Ladder-MCL | MCL | Workhorse cross-asset / energy | 465 | 1.003 | 39 | -1210 | 14.7s | KILL — Cheap Screen Tier |
| XB-BB-EMA-Ladder-MYM | MYM | Workhorse cross-asset | 240 | 1.536 | 2963 | -646 | 6.9s | PASS — Cheap Screen Tier |
| XB-VWAP-EMA-Ladder-MES | MES | Workhorse cross-asset / VWAP closeout test | 887 | 1.085 | 2290 | -3544 | 20.8s | WATCH — Cheap Screen Tier |
| XB-VWAP-EMA-Ladder-MGC | MGC | Workhorse cross-asset / VWAP closeout test | 381 | 1.285 | 3614 | -1870 | 11.1s | PASS — Cheap Screen Tier |
| XB-VWAP-EMA-Ladder-MCL | MCL | Workhorse cross-asset / VWAP closeout test | 509 | 1.084 | 1076 | -1852 | 14.8s | WATCH — Cheap Screen Tier |

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
