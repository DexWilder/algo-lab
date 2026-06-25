# FQL Forge Daily — 2026-05-22

**Run mode:** dry-run
**Total runtime:** 100.6s
**Candidates tested:** 5
**Verdict counts:** {'PASS': 2, 'WATCH': 3, 'KILL': 0, 'RETEST': 0}
**Evidence tier:** Cheap Screen Tier — verdicts are cheap-screen surfacing, NOT validated edge. See `feedback_durable_artifacts_both_surfaces.md` and the post-Phase-1 doctrine: Forge currently produces cheap-screen evidence, not validated edge evidence.

## Per-candidate results

| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Runtime | Verdict (tier) |
|---|---|---|---:|---:|---:|---:|---:|---|
| XB-VWAP-EMA-Ladder-MGC | MGC | Workhorse cross-asset / VWAP closeout test | 378 | 1.277 | 3478 | -1870 | 17.7s | PASS — Cheap Screen Tier |
| XB-VWAP-EMA-Ladder-MCL | MCL | Workhorse cross-asset / VWAP closeout test | 507 | 1.056 | 716 | -1852 | 19.0s | WATCH — Cheap Screen Tier |
| XB-VWAP-EMA-Ladder-MYM | MYM | Workhorse cross-asset / VWAP closeout test | 278 | 1.346 | 2403 | -660 | 8.1s | PASS — Cheap Screen Tier |
| XB-ORB-EMA-MorningOnly-MNQ | MNQ | Sparse-session tail-engine — morning-only XB | 1648 | 1.029 | 4375 | -11802 | 24.7s | WATCH — Cheap Screen Tier |
| XB-ORB-EMA-AfternoonOnly-MNQ | MNQ | Sparse-session tail-engine — afternoon-only XB | 1651 | 1.066 | 6974 | -4307 | 31.1s | WATCH — Cheap Screen Tier |

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
