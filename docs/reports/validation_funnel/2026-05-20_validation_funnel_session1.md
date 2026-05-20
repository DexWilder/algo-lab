# Validation Funnel v0 — Session 1 (2026-05-20)

**Filed by:** `research/validation_funnel.py`
**Authority:** T1 intelligence; no registry mutation, no status changes.
**Sprint:** Phase 2 / Paper-Readiness Sprint Item #7.

## Session 1 scope — Gates 1+2+3

- **Gate 1 (1 pt):** cheap-screen PASS documented at intake
- **Gate 2 (1 pt):** correlation cleared — not a retained-variant duplicate
- **Gate 3 (2 pt):** cost-adjusted net PF ≥ 1.15

Sessions 2-4 will add 9 more points across walk-forward, trade count,
concentration, forward-runner, and promotion-humility gates (13 pt max total).

## Cost assumptions used

Per FQL evidence law: net PFs below come from the post-Piece-I cost-aware
engine. `engine/asset_config.py` is the single source of truth. Conservative
estimates; replace with broker rate sheets before paper/prop.

| Asset | Cost assumption |
|---|---|
| MCL | comm=$0.62, slip=2t |
| MGC | comm=$0.62, slip=1t |
| MNQ | comm=$0.62, slip=1t |
| MYM | comm=$0.62, slip=2t |

## Per-candidate scorecard

| Candidate | Asset | Bucket | G1 | G2 | G3 | S1 score | Net PF | Notes |
|---|---|---|---:|---:|---:|---:|---:|---|
| XB-ORB-EMA-Ladder-MYM | MYM | probation | 1 | 1 | 2 | 4/4 | 1.625 |  |
| XB-ORB-EMA-Ladder-MNQ | MNQ | probation | 1 | 1 | 2 | 4/4 | 1.620 |  |
| XB-BB-EMA-Ladder-MGC | MGC | correlation | 1 | 1 | 2 | 4/4 | 1.592 |  |
| XB-ORB-EMA-Chandelier-MNQ | MNQ | correlation | 1 | 1 | 2 | 4/4 | 1.574 |  |
| XB-BB-EMA-Ladder-MYM | MYM | correlation | 1 | 1 | 2 | 4/4 | 1.551 |  |
| XB-PB-EMA-Ladder-MNQ | MNQ | correlation | 1 | 1 | 2 | 4/4 | 1.406 |  |
| XB-VWAP-EMA-Ladder-MYM | MYM | correlation | 1 | 1 | 2 | 4/4 | 1.325 |  |
| XB-ORB-EMA-Ladder-MCL | MCL | probation | 1 | 1 | 2 | 4/4 | 1.298 |  |
| XB-VWAP-EMA-Ladder-MGC | MGC | correlation | 1 | 1 | 2 | 4/4 | 1.297 |  |
| XB-BB-EMA-Ladder-MNQ | MNQ | correlation | 1 | 1 | 2 | 4/4 | 1.237 |  |
| XB-PB-EMA-Ladder-MYM | MYM | correlation | 1 | 1 | 2 | 4/4 | 1.202 |  |
| XB-ORB-EMA-TimeStop-MNQ | MNQ | correlation | 1 | 0 | 2 | 3/4 | 1.507 | retained variant of XB-ORB-EMA-Chandelier-MNQ cluster — duplicate exposure |

## Session 1 summary

- **11/12 candidates score full marks** (4/4) and advance to Session 2 gates.
- **1 candidate(s) partial** (failed at least one Session 1 gate but not all).
- **0 candidate(s) blocked** (failed all Session 1 gates).
- **Exposure cluster count after Session 1: 11** (retained variants do not count as separate slots).

## Top risks before Session 2 (Gate 4: walk-forward H1/H2)

- Walk-forward is the heaviest gate (3 pts) and most likely to cull candidates.
- MCL probation (net PF 1.298) is the closest to the 1.15 gate; small WF instability could compound the fragility flag.
- The 9 correlation candidates have not been walk-forward tested under the cost-aware engine. WF was originally computed pre-Piece-I (mostly zero-cost via correlation_matrix.py path); a fresh run is required.
- Walk-forward + cost-aware backtests = ~12 candidates × ≥4 WF runs each = significant compute. Session 2 may need to chunk or background.

## Cluster / top-3 selection note

- **XB-ORB-EMA-TimeStop-MNQ** is the retained variant of the **XB-ORB-EMA-Chandelier-MNQ** cluster. Both remain registered but count as one exposure slot for top-3 selection.

---

*Session 1 of 4. Read-only intelligence; no decisions taken. Next session: Gate 4 walk-forward on the candidates that score full marks here.*
