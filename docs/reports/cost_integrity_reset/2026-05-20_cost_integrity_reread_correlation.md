# Cost Integrity Re-Read — correlation candidates (2026-05-20)

Per Item #3 Piece D (`docs/_DRAFT_2026-05-19_item3_cost_slippage_preflight.md`).

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
| XB-PB-EMA-Ladder-MNQ | MNQ | 1.461 | 1.406 | 1.406 | 0.0 | -0.055 | 33056.0 | 29754.0 | 22.43 | 20.19 | 2.24 | 10.0 | comm=$0.62, slip=1t | no | no | GREEN |
| XB-PB-EMA-Ladder-MCL | MCL | 1.297 | 1.143 | 1.058 | -0.085 | -0.239 | 7158.0 | 1551.0 | 6.69 | 1.45 | 5.24 | 78.3 | comm=$0.62, slip=2t | no | yes | YELLOW |
| XB-PB-EMA-Ladder-MYM | MYM | 1.346 | 1.244 | 1.202 | -0.042 | -0.144 | 4033.0 | 2507.0 | 8.56 | 5.32 | 3.24 | 37.9 | comm=$0.62, slip=2t | no | no | GREEN |
| XB-BB-EMA-Ladder-MNQ | MNQ | 1.283 | 1.237 | 1.237 | 0.0 | -0.046 | 10293.0 | 8788.0 | 15.32 | 13.08 | 2.24 | 14.6 | comm=$0.62, slip=1t | no | no | GREEN |
| XB-BB-EMA-Ladder-MGC | MGC | 1.749 | 1.592 | 1.592 | 0.0 | -0.157 | 5767.0 | 4818.0 | 19.68 | 16.44 | 3.24 | 16.5 | comm=$0.62, slip=1t | no | no | GREEN |
| XB-BB-EMA-Ladder-MCL | MCL | 1.203 | 1.062 | 0.983 | -0.079 | -0.22 | 2217.0 | -204.0 | 4.8 | -0.44 | 5.24 | 109.2 | comm=$0.62, slip=2t | no | yes | RED |
| XB-BB-EMA-Ladder-MYM | MYM | 1.745 | 1.608 | 1.551 | -0.057 | -0.194 | 3792.0 | 3018.0 | 15.87 | 12.63 | 3.24 | 20.4 | comm=$0.62, slip=2t | no | no | GREEN |
| XB-VWAP-EMA-Ladder-MGC | MGC | 1.416 | 1.297 | 1.297 | 0.0 | -0.119 | 4888.0 | 3670.0 | 13.0 | 9.76 | 3.24 | 24.9 | comm=$0.62, slip=1t | no | no | GREEN |
| XB-VWAP-EMA-Ladder-MCL | MCL | 1.276 | 1.124 | 1.04 | -0.084 | -0.236 | 3159.0 | 513.0 | 6.26 | 1.02 | 5.24 | 83.7 | comm=$0.62, slip=2t | no | yes | RED |
| XB-VWAP-EMA-Ladder-MYM | MYM | 1.482 | 1.372 | 1.325 | -0.047 | -0.157 | 3156.0 | 2262.0 | 11.43 | 8.19 | 3.24 | 28.3 | comm=$0.62, slip=2t | no | no | GREEN |
| XB-ORB-EMA-Chandelier-MNQ | MNQ | 1.637 | 1.574 | 1.574 | 0.0 | -0.063 | 35573.0 | 32869.0 | 29.47 | 27.23 | 2.24 | 7.6 | comm=$0.62, slip=1t | no | no | GREEN |
| XB-ORB-EMA-TimeStop-MNQ | MNQ | 1.57 | 1.507 | 1.507 | 0.0 | -0.063 | 30780.0 | 28076.0 | 25.5 | 23.26 | 2.24 | 8.8 | comm=$0.62, slip=1t | no | no | GREEN |
