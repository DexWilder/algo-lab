# Phase 1C Activation Record — WH-MNQ-stop_run_reversal — 2026-06-15

> **Status:** WIRED to paper. **VERDICT: PHASE1C_WIRED_OK.** Operator-approved 2026-06-15 with $1,500 max-DD kill ceiling.
> First execution mutation of the Lane A campaign. 1 MNQ, intraday-flat daily workhorse.

## 1. Exact files changed
- `research/data/strategy_registry.json` — **added** entry `WH-MNQ-stop_run_reversal-ema_slope-PL` (166→167 strategies). No other entry modified.
- `research/live_drift_monitor.py` — added to `STRATEGY_PROMOTED_DATES` (2026-06-14) and `BASELINE["strategies"]` (tier `full`).
- `research/phase1c_wire_stop_run_reversal_2026-06-15.py` — wiring + verification script.

Registry entry key fields: `status=probation`, `controller_action=PROBATION`, `executable_state=EXECUTABLE`, `execution_config.exit_variant=null`, `promotion_date=2026-06-14`, `paper_ready=true`, `promotion_eligible=true`, `portfolio_role=workhorse`, `strategy_name=xb_stop_run_reversal_ema_ladder`, `direction=both`.

**Kill switches:** max-DD **$1,500** realized (closed-trade equity from paper-start) · rolling-12 Era-3 PF<1.0 · Mon PF<0.9 first 6 Mondays · 13h-bucket PF<0.85. **SLA:** 30 trades or 30 sessions, whichever later.

## 2. Final active MNQ workhorse count
**2 of ≤2 (within cap):** `WH-MNQ-stop_run_reversal-ema_slope-PL` + `XB-ORB-EMA-Ladder-MNQ`. (`TV-NFP-High-Low-Levels` remains separate sparse-event MNQ exposure.)

## 3. Execution-approval gate result
`approved=True, reason=APPROVED_PROMOTION_DATE` — passes the fail-closed gate via clean positive approval evidence (no contradiction; not experimental; not paper_ready=false).

## 4. Runner-load verification
In `build_portfolio_config(include_probation=True)`: present, `mode=both`, `asset=MNQ`, **`exit_variant=None`** (donchian trap avoided → runner uses the verified `mod.generate_signals`). In `get_eval_strategies` (controller/scorecard visibility): yes.

## 5. Drift-monitor / scorecard recognition
`live_drift_monitor.BASELINE["strategies"]` contains it (tier `full`, ALARM-permitted); `STRATEGY_PROMOTED_DATES` = 2026-06-14 (replay filter). Scorecards/digest read the registry (status=probation, in eval set) → recognized.

## 6. Confirmation excluded books remain excluded
All confirmed NOT in runner: `XB-ORB-EMA-Chandelier-MNQ`, `XB-PB-EMA-Chandelier-MNQ`, `XB-ORB-EMA-ATRTrail-MES` (Track 2 shadow), `XB-ORB-EMA-Ladder-MGC` (gated `BLOCKED_PAPER_READY_FALSE`, under review).

## Untouched (per instruction)
Phase 1D/FOMC, Wave 2/3, Lane B, live/prop, Ladder-MGC status, Chandelier books, ATRTrail-MES, and all unrelated registry/scheduler/portfolio state.

## Next
- **24h post-wiring verification** required (per promotion protocol) — confirm it appears in the live forward runner output, drift monitor, and scorecards after the next forward-day run; roll back if any surface is missing it.
- Live/prop remains BLOCKED until DSCL §7 (external CME/secondary-vendor/paper-execution).
- Forward observation accrues toward the 30-trade/30-session SLA before any review or size change.

## Cross-reference
- `docs/fql_forge/paper_packet_drafts/PHASE1C_WIRING_REQUEST_stop_run_reversal_2026-06-14.md`
- `docs/fql_forge/paper_packet_drafts/WAVE1_PHASE1A_PORT_VERIFICATION_2026-06-13.md`
- `docs/fql_forge/GOVERNANCE_REMEDIATION_2026-06-13.md`
