# FQL Forge Daily — 2026-06-29

**Run mode:** dry-run
**Total runtime:** 134.2s
**Candidates tested:** 5
**Verdict counts:** {'PASS': 1, 'WATCH': 4, 'KILL': 0, 'RETEST': 0}
**Evidence tier:** Cheap Screen Tier — verdicts are cheap-screen surfacing, NOT validated edge. See `feedback_durable_artifacts_both_surfaces.md` and the post-Phase-1 doctrine: Forge currently produces cheap-screen evidence, not validated edge evidence.

## Per-candidate results

| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Runtime | Verdict (tier) |
|---|---|---|---:|---:|---:|---:|---:|---|
| XB-ORB-EMA-MorningOnly-MNQ | MNQ | Sparse-session tail-engine — morning-only XB | 1671 | 1.031 | 4798 | -11802 | 86.9s | WATCH — Cheap Screen Tier |
| XB-ORB-EMA-AfternoonOnly-MNQ | MNQ | Sparse-session tail-engine — afternoon-only XB | 1673 | 1.081 | 8751 | -4307 | 0.9s | WATCH — Cheap Screen Tier |
| XB-PB-EMA-MorningOnly-MNQ | MNQ | Sparse-session tail-engine — morning-only PB entry | 2107 | 1.056 | 7100 | -4399 | 0.8s | WATCH — Cheap Screen Tier |
| XB-BB-EMA-MorningOnly-MGC-v2 | MGC | Concentration mutation B2 — morning-only restriction on XB-BB-MGC to test if max-year normalizes | 501 | 1.027 | 562 | -4952 | 45.2s | WATCH — Cheap Screen Tier |
| XB-BB-EMA-AfternoonOnly-MGC | MGC | Sparse-session tail-engine — BB entry MGC, afternoon-restricted | 388 | 1.221 | 2037 | -2272 | 0.5s | PASS — Cheap Screen Tier |

## Architecture trends

- PASS assets in this batch: ['MGC']
- Per the donor catalog, ema_slope + profit_ladder remain co-validated load-bearing pair.

## Next-batch recommendation

- Next safe candidates to screen (18 untested in this run): ['XB-PB-EMA-Ladder-MES', 'XB-PB-EMA-Ladder-MGC', 'XB-PB-EMA-Ladder-MCL']...

## Safety affirmation

- No registry mutation
- No Lane A surfaces touched
- No runtime/scheduler/portfolio/checkpoint changes
- Operator approves all promotions / appends
