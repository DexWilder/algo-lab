# FQL Forge Daily — 2026-06-02

**Run mode:** dry-run
**Total runtime:** 59.7s
**Candidates tested:** 5
**Verdict counts:** {'PASS': 3, 'WATCH': 2, 'KILL': 0, 'RETEST': 0}
**Evidence tier:** Cheap Screen Tier — verdicts are cheap-screen surfacing, NOT validated edge. See `feedback_durable_artifacts_both_surfaces.md` and the post-Phase-1 doctrine: Forge currently produces cheap-screen evidence, not validated edge evidence.

## Per-candidate results

| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Runtime | Verdict (tier) |
|---|---|---|---:|---:|---:|---:|---:|---|
| XB-BB-EMA-Ladder-MYM | MYM | Workhorse cross-asset | 241 | 1.545 | 3012 | -646 | 7.0s | PASS — Cheap Screen Tier |
| XB-VWAP-EMA-Ladder-MES | MES | Workhorse cross-asset / VWAP closeout test | 888 | 1.082 | 2213 | -3544 | 20.6s | WATCH — Cheap Screen Tier |
| XB-VWAP-EMA-Ladder-MGC | MGC | Workhorse cross-asset / VWAP closeout test | 381 | 1.285 | 3614 | -1870 | 10.8s | PASS — Cheap Screen Tier |
| XB-VWAP-EMA-Ladder-MCL | MCL | Workhorse cross-asset / VWAP closeout test | 511 | 1.087 | 1106 | -1852 | 14.5s | WATCH — Cheap Screen Tier |
| XB-VWAP-EMA-Ladder-MYM | MYM | Workhorse cross-asset / VWAP closeout test | 282 | 1.375 | 2605 | -660 | 6.8s | PASS — Cheap Screen Tier |

## Architecture trends

- PASS assets in this batch: ['MYM', 'MGC', 'MYM']
- Per the donor catalog, ema_slope + profit_ladder remain co-validated load-bearing pair.

## Next-batch recommendation

- Next safe candidates to screen (14 untested in this run): ['XB-PB-EMA-Ladder-MES', 'XB-PB-EMA-Ladder-MGC', 'XB-PB-EMA-Ladder-MCL']...

## Safety affirmation

- No registry mutation
- No Lane A surfaces touched
- No runtime/scheduler/portfolio/checkpoint changes
- Operator approves all promotions / appends
