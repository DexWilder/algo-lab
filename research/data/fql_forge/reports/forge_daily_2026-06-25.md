# FQL Forge Daily — 2026-06-25

**Run mode:** dry-run
**Total runtime:** 1000.1s
**Candidates tested:** 5
**Verdict counts:** {'PASS': 3, 'WATCH': 2, 'KILL': 0, 'RETEST': 0}
**Evidence tier:** Cheap Screen Tier — verdicts are cheap-screen surfacing, NOT validated edge. See `feedback_durable_artifacts_both_surfaces.md` and the post-Phase-1 doctrine: Forge currently produces cheap-screen evidence, not validated edge evidence.

## Per-candidate results

| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Runtime | Verdict (tier) |
|---|---|---|---:|---:|---:|---:|---:|---|
| XB-PB-EMA-MorningOnly-MNQ | MNQ | Sparse-session tail-engine — morning-only PB entry | 2103 | 1.065 | 8127 | -4399 | 748.9s | WATCH — Cheap Screen Tier |
| XB-BB-EMA-MorningOnly-MGC-v2 | MGC | Concentration mutation B2 — morning-only restriction on XB-BB-MGC to test if max-year normalizes | 500 | 1.027 | 555 | -4952 | 244.1s | WATCH — Cheap Screen Tier |
| XB-BB-EMA-AfternoonOnly-MGC | MGC | Sparse-session tail-engine — BB entry MGC, afternoon-restricted | 388 | 1.221 | 2037 | -2272 | 1.6s | PASS — Cheap Screen Tier |
| XB-ORB-EMA-Chandelier-MNQ | MNQ | Asymmetric exit alt — chandelier trailing exit instead of profit_ladder | 1224 | 1.586 | 34813 | -1651 | 2.9s | PASS — Cheap Screen Tier |
| XB-ORB-EMA-TimeStop-MNQ | MNQ | Asymmetric exit alt — fixed time-stop exit (tail-engine due to forced cutoff) | 1224 | 1.519 | 29859 | -1862 | 2.5s | PASS — Cheap Screen Tier |

## Architecture trends

- PASS assets in this batch: ['MGC', 'MNQ', 'MNQ']
- Per the donor catalog, ema_slope + profit_ladder remain co-validated load-bearing pair.

## Next-batch recommendation

- Next safe candidates to screen (18 untested in this run): ['XB-PB-EMA-Ladder-MES', 'XB-PB-EMA-Ladder-MGC', 'XB-PB-EMA-Ladder-MCL']...

## Safety affirmation

- No registry mutation
- No Lane A surfaces touched
- No runtime/scheduler/portfolio/checkpoint changes
- Operator approves all promotions / appends
