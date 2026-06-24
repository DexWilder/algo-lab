# FQL Forge Daily — 2026-05-26

**Run mode:** dry-run
**Total runtime:** 82.9s
**Candidates tested:** 5
**Verdict counts:** {'PASS': 1, 'WATCH': 4, 'KILL': 0, 'RETEST': 0}
**Evidence tier:** Cheap Screen Tier — verdicts are cheap-screen surfacing, NOT validated edge. See `feedback_durable_artifacts_both_surfaces.md` and the post-Phase-1 doctrine: Forge currently produces cheap-screen evidence, not validated edge evidence.

## Per-candidate results

| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Runtime | Verdict (tier) |
|---|---|---|---:|---:|---:|---:|---:|---|
| XB-VWAP-EMA-Ladder-MCL | MCL | Workhorse cross-asset / VWAP closeout test | 508 | 1.076 | 967 | -1852 | 14.7s | WATCH — Cheap Screen Tier |
| XB-VWAP-EMA-Ladder-MYM | MYM | Workhorse cross-asset / VWAP closeout test | 279 | 1.364 | 2533 | -660 | 6.7s | PASS — Cheap Screen Tier |
| XB-ORB-EMA-MorningOnly-MNQ | MNQ | Sparse-session tail-engine — morning-only XB | 1649 | 1.028 | 4269 | -11802 | 20.4s | WATCH — Cheap Screen Tier |
| XB-ORB-EMA-AfternoonOnly-MNQ | MNQ | Sparse-session tail-engine — afternoon-only XB | 1652 | 1.063 | 6642 | -4307 | 20.4s | WATCH — Cheap Screen Tier |
| XB-PB-EMA-MorningOnly-MNQ | MNQ | Sparse-session tail-engine — morning-only PB entry | 2077 | 1.073 | 8764 | -4399 | 20.7s | WATCH — Cheap Screen Tier |

## Architecture trends

- PASS assets in this batch: ['MYM']
- Per the donor catalog, ema_slope + profit_ladder remain co-validated load-bearing pair.

## Next-batch recommendation

- Next safe candidates to screen (14 untested in this run): ['XB-PB-EMA-Ladder-MES', 'XB-PB-EMA-Ladder-MGC', 'XB-PB-EMA-Ladder-MCL']...

## Safety affirmation

- No registry mutation
- No Lane A surfaces touched
- No runtime/scheduler/portfolio/checkpoint changes
- Operator approves all promotions / appends
