# FQL Forge Daily — 2026-05-18

**Run mode:** dry-run
**Total runtime:** 73.7s
**Candidates tested:** 5
**Verdict counts:** {'PASS': 3, 'WATCH': 2, 'KILL': 0, 'RETEST': 0}
**Evidence tier:** Cheap Screen Tier — verdicts are cheap-screen surfacing, NOT validated edge. See `feedback_durable_artifacts_both_surfaces.md` and the post-Phase-1 doctrine: Forge currently produces cheap-screen evidence, not validated edge evidence.

## Per-candidate results

| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Runtime | Verdict (tier) |
|---|---|---|---:|---:|---:|---:|---:|---|
| XB-VWAP-EMA-Ladder-MES | MES | Workhorse cross-asset / VWAP closeout test | 882 | 1.095 | 2538 | -3544 | 20.8s | WATCH — Cheap Screen Tier |
| XB-VWAP-EMA-Ladder-MGC | MGC | Workhorse cross-asset / VWAP closeout test | 375 | 1.289 | 3571 | -1870 | 10.9s | PASS — Cheap Screen Tier |
| XB-VWAP-EMA-Ladder-MCL | MCL | Workhorse cross-asset / VWAP closeout test | 505 | 1.276 | 3159 | -1407 | 14.5s | PASS — Cheap Screen Tier |
| XB-VWAP-EMA-Ladder-MYM | MYM | Workhorse cross-asset / VWAP closeout test | 275 | 1.497 | 3222 | -637 | 6.8s | PASS — Cheap Screen Tier |
| XB-ORB-EMA-MorningOnly-MNQ | MNQ | Sparse-session tail-engine — morning-only XB | 1644 | 1.028 | 4158 | -11802 | 20.7s | WATCH — Cheap Screen Tier |

## Architecture trends

- PASS assets in this batch: ['MGC', 'MCL', 'MYM']
- Per the donor catalog, ema_slope + profit_ladder remain co-validated load-bearing pair.

## Next-batch recommendation

- Next safe candidates to screen (14 untested in this run): ['XB-PB-EMA-Ladder-MES', 'XB-PB-EMA-Ladder-MGC', 'XB-PB-EMA-Ladder-MCL']...

## Safety affirmation

- No registry mutation
- No Lane A surfaces touched
- No runtime/scheduler/portfolio/checkpoint changes
- Operator approves all promotions / appends
