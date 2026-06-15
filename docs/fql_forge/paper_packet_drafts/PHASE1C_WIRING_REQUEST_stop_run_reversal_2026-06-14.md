# Phase 1C Wiring Request — WH-MNQ-stop_run_reversal — 2026-06-14

> **This is a REQUEST for your explicit go-ahead — not an executed change.** Registry/runner remain untouched until you approve. On approval I apply the atomic transition below, commit/push, run 24h verification, and report.
> **All governance gates are now PASS.** This is the first real execution mutation (puts the strategy into live paper), so per our rhythm I'm confirming before wiring.

## Gate status — all clear

| Gate | Status |
|---|---|
| Phase 1A port verification | ✅ PORT_VERIFIED_GREEN (byte-identical to DATA_AUDIT_GREEN, signal hash exact) |
| MNQ exposure rationalization | ✅ daily-workhorse MNQ books 3→1 |
| DSCL in-repo source verification | ✅ DSCL_IN_REPO_VERIFIED (Databento-backed, canonical for paper) |
| Org-hygiene / elite classification | ✅ ORG_HYGIENE_CLEAN (activation-risk mismatches 0) |
| Fail-closed execution gate | ✅ live (controller intent ≠ approval) |
| Ladder-MGC contradiction | ✅ decision (c): gated, review opened, non-blocking |

## Exposure cap check (≤2 MNQ daily-workhorse books)

- Active MNQ daily-workhorse now: **1** — `XB-ORB-EMA-Ladder-MNQ`.
- After wiring stop_run_reversal: **2** → **at the cap, within limit** ✅.
- Excluded from execution (confirmed): `XB-ORB-EMA-Chandelier-MNQ`, `XB-PB-EMA-Chandelier-MNQ`, `XB-ORB-EMA-ATRTrail-MES` (Track 2 shadow), `XB-ORB-EMA-Ladder-MGC` (gated, under review).
- `TV-NFP-High-Low-Levels` remains separate sparse-event MNQ exposure (not a daily workhorse).

## Atomic registry transition (applied together in one commit on approval)

New registry entry `WH-MNQ-stop_run_reversal-ema_slope-PL`:

| Field | Value | Why |
|---|---|---|
| `strategy_name` | `xb_stop_run_reversal_ema_ladder` | must equal the verified module dir |
| `asset` / `direction` | `MNQ` / `both` | → runner `mode="both"` (matches validated baseline) |
| `session` | `all_day` | matches incumbent; primitive sets its own RTH window |
| `status` | `probation` | paper probation |
| `controller_action` | `PROBATION` | eligible under `include_probation=True` |
| `executable_state` | `EXECUTABLE` | module exists + port-verified |
| **`execution_config.exit_variant`** | **`null`** | **critical — avoids the donchian trap; routes runner to `mod.generate_signals`** |
| `execution_config` (other) | `avoid_regimes:[], preferred_regimes:[], conviction_threshold_outside:2, windows=session defaults` | fail-closed decision-grade fields explicit |
| `promotion_date` | `2026-06-14` | **positive approval evidence** → passes the new fail-closed gate (APPROVED_PROMOTION_DATE) |
| `paper_ready` / `promotion_eligible` | (not set false) | no contradiction — genuinely paper-approved |
| `portfolio_role` | `workhorse` | |
| `notes` | port-verification + DSCL + approval lineage (commits b90c501 / d8ea1b6 / 09d61ad) | provenance |

Plus:
- Add to `research/live_drift_monitor.py` BASELINE with the **workhorse** classifier.
- Confirm scorecards/daily digest recognize the new ID.

## Paper sizing, kill switches, SLA

- **Sizing:** 1 MNQ contract (foundation-lead). No size increase during paper.
- **Kill switches:** (a) rolling-12-trade Era-3 PF < 1.0; (b) realized max-DD beyond your $ ceiling *(please set the dollar figure)*; (c) Mon PF < 0.9 over first 6 Mondays (Mon-weakness flag); (d) 13h-bucket PF < 0.85 (H13 knife-edge).
- **Forward-monitoring SLA:** 30 forward trades OR 30 sessions, whichever later, before any review/size change.
- **Carry-over monitors:** `MON_WEAKNESS_MONITOR`, `H13_KNIFE_EDGE_MONITOR`, `ACTIVE_EXPOSURE_WARNING_XB_ORB_PROBATION` (corr 0.327 to incumbent).

## Post-wiring verification (within 24h, per promotion protocol)
Confirm stop_run_reversal appears correctly in: (a) the forward runner universe (`build_portfolio_config`), (b) the drift monitor baseline, (c) the daily digest/scorecards — and that the fail-closed gate admits it (`APPROVED_PROMOTION_DATE`) with `exit_variant=null`. If any surface is missing it, roll back.

## DSCL reminder
DATA_AUDIT_GREEN + DSCL in-repo = feed-internal reproducibility → **paper only**. Live/prop remains BLOCKED until DSCL §7 (external CME settlement, secondary vendor, paper-execution reconciliation).

## What I need from you
1. **Approve Phase 1C wiring** as specified above? (or adjust)
2. **Set the max-DD dollar kill-switch ceiling** for kill switch (b).
3. Confirm sizing (1 MNQ) and SLA (30 trades/30 sessions).

On your go, I execute the atomic transition, commit/push, run 24h verification, and report. **Phase 1D (FOMC executor), Wave 2/3, Lane B, live/prop remain untouched.**
