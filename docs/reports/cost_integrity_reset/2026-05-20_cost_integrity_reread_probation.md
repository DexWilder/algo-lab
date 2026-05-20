# Cost Integrity Re-Read — probation candidates (2026-05-20)

Per Item #3 Piece C (`docs/_DRAFT_2026-05-19_item3_cost_slippage_preflight.md`).

**Source of truth:** `engine/asset_config.py` (post-Piece-I consolidation).

**Cost assumptions are estimated** — broker/firm rate sheets should replace these before paper/prop, especially for ZN/ZF/ZB, FX, MCL, MYM.

**Deltas:**
- Δ-A = PRIOR net (pre-Piece-I asset_config) → NEW net (post-Piece-I)
- Δ-B = GROSS (silent zero-cost; what fql_forge_batch_runner / correlation_matrix / run_forward_paper produced for unconfigured assets) → NEW net

**Concern levels** (on NEW net PF, backtest workhorse gate 1.20):
- GREEN: net PF ≥ 1.20
- YELLOW: net PF in [1.05, 1.20)
- RED: net PF < 1.05

## Per-candidate table

| Strategy | Asset | Gross PF | Prior net PF | New net PF | Δ-A | Δ-B | Gross PnL | New net PnL | Gross avg | New avg | Cost/RT $ | Cost % | Cost assumption | Verdict Δ-A | Verdict Δ-B | Concern |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| XB-ORB-EMA-Ladder-MNQ | MNQ | 1.661 | 1.62 | 1.62 | 0.0 | -0.041 | 54713.0 | 52009.0 | 45.33 | 43.09 | 2.24 | 4.9 | comm=$0.62, slip=1t | no | no | GREEN |
| XB-ORB-EMA-Ladder-MCL | MCL | 1.489 | 1.368 | 1.298 | -0.07 | -0.191 | 13913.0 | 9092.0 | 15.12 | 9.88 | 5.24 | 34.7 | comm=$0.62, slip=2t | no | no | GREEN |
| XB-ORB-EMA-Ladder-MYM | MYM | 1.753 | 1.663 | 1.625 | -0.038 | -0.128 | 8963.0 | 7761.0 | 24.16 | 20.92 | 3.24 | 13.4 | comm=$0.62, slip=2t | no | no | GREEN |
