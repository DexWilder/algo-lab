# Gated Activation/Wiring Spec — Shared Event Executor — 2026-06-16

> **STATUS: DESIGN ONLY. NOT EXECUTED. NON-WIRED.** This document specifies *how* the banked event candidates would be wired to PAPER, so the operator can approve a concrete plan. Nothing here is performed: no registry/scheduler/portfolio mutation, no order routing, no paper/live/prop exposure. Every mutation below is an explicit, separately-gated approval.
> Serves: **ZN-FOMC-week rates sleeve** (`DATA_AUDIT_GREEN`, regime-dependent) + **FOMC-MNQ-Long-1h** (Lane A event-tail). Built on `engine/event_executor.py` (fidelity-GREEN).

## 1. Exact event-executor integration plan
Out-of-band path, modeled on the existing **Treasury-Rolldown** precedent (launchd → script → log; excluded from the intraday runner & per-trade drift):
- **New runner** `run_event_executor.py` (to be written at wiring time): loads event specs + official FOMC calendar; for "today", calls `engine.event_executor` decision logic; if an entry/exit/hold action is due, **writes a paper signal row** (paper log, not `logs/trade_log.csv` which is daily-runner-owned).
- **NOT** added to `build_portfolio_config` / the daily forward runner (these are out-of-band scheduled-event strategies, like treasury-rolldown). The fail-closed gate + `controller_action=OFF` + a dedicated `execution_path` keep the daily runner from ever picking them up.
- Decision flow per session: is today within any spec's event window (calendar ± offsets)? → intended action (enter/hold/exit/flat) + stop check → paper signal.

## 2. Paper-only wiring path (specified, NOT executed)
On approval, the atomic changes would be:
- **Registry** entries `EVT-ZN-FOMC-week`, `EVT-FOMC-MNQ-Long-1h`: `status=probation`, `controller_action=OFF` (out-of-band; never daily-runner-eligible), `executable_state=EXECUTABLE`, **`execution_path="event_oob"`**, `paper_ready=true` (post-approval), spec params, `promotion_date`. (Note: the new fail-closed gate requires positive approval evidence — these get `promotion_date` at approval.)
- **Out-of-band launchd agent** `com.fql.event-executor` (weekday ~17:10 ET, after data refresh — mirrors treasury-rolldown plist); runs `run_event_executor.py`; idempotent (no-op if today not an event window).
- **Drift monitor**: add to `live_drift_monitor.excluded_from_strategy_drift` (out-of-band, per-trade severity N/A, like treasury-rolldown) + a dedicated event-strategy review hook.
- **Paper account routing only.** No live/prop path created.

## 3. Approval gates required before ANY mutation
1. Operator approves THIS spec.
2. Operator approves the `run_event_executor.py` build (report-only dry-run first).
3. Operator approves the atomic registry transition (per-strategy).
4. Operator approves the launchd agent install.
5. Replay-vs-forward validation (§4) passes before counting any forward evidence.
6. **Phase 1C must be cleared first** (activation freeze) — this is downstream of Phase 1C, not concurrent.

## 4. Replay-vs-forward validation requirement
Before forward evidence counts: a **forward-vs-replay reconciliation** (cf. Phase 1C 24h verify). For the first N live event firings, confirm the forward executor's decisions + fills reconcile to the replay (`engine/event_executor.replay`) on the same calendar/data — fidelity must hold live, not just in backtest. Material divergence → fail-closed (halt, alert, no rollback without confirm).

## 5. Event calendar requirements
- ZN-FOMC + FOMC-MNQ: **official scheduled FOMC** (`forge_fomc_calendar_official`, `OFFICIAL_FED_GOV`) — have it; deterministic. Live path needs **forward FOMC dates** (next scheduled meetings) — append upcoming Fed-published dates to the calendar module (operator-verifiable).
- Calendar staleness check: if the calendar lacks an upcoming event window, fail-closed (no firing) + alert.

## 6. Kill switch / fail-closed behavior
- **Per-strategy kills:** rolling-12-event PF < 1.0; realized max-DD > $ ceiling; 3 consecutive event losses.
- **ZN-FOMC regime kill (see §9):** rates-DOWN/hiking regime → block or review-only.
- **Fail-closed triggers:** stale/missing calendar; data gap in the event window (clean-events rule); regime ineligible; spec/contract mismatch → **no firing** (flat), alert. Never fire on uncertain inputs.

## 7. Rollback package
- Pre-change backups of registry + live_drift_monitor + plist to `/tmp` (per no-blind-restore rule).
- Single-commit atomic transition → rollback = `git revert <commit>` + `launchctl bootout` the agent + restore registry from backup. Staged, human-confirmed (no unattended destructive rollback).

## 8. Serves both candidates (shared infra)
One executor (`engine/event_executor.py`), one out-of-band runner, one launchd agent, two specs:
- **ZN-FOMC** (daily, entry −2td, exit +2td, $1200 stop, FOMC, EVENT_TAIL).
- **FOMC-MNQ-Long-1h** (intraday 5m, entry +1 bar, hold 12 bars, FOMC, EVENT_TAIL).
This is the FOMC-MNQ Phase 1D infrastructure too — one build unblocks both.

## 9. ZN-FOMC regime-filter handling (per the regime-dependence caveat)
- **rates-UP/easing regime eligible** (ZN 60-td trend > 0): full size (the edge — PF 4.20).
- **rates-DOWN/hiking regime: BLOCKED or review-only** (flat edge — PF 0.99). Implemented as a fail-closed regime gate in the executor: compute rate-trend at the entry decision; if down-regime, suppress the fire (or flag review-only) per operator choice. This operationalizes the REGIME_DEPENDENT label so the live sleeve only trades its proven regime.

## 10. V1 packet completion checklist (to fill before promotion)
- [x] Robustness (window-family/era/LOO/H1H2/conc) — ZN done; MNQ per Lane A batch
- [x] Prop-survivability (<$2K @ 1 micro w/ stop)
- [x] DATA_AUDIT_GREEN (ZN); FOMC-MNQ per Lane A
- [x] Calendar grade OFFICIAL_FED_GOV
- [x] Executor fidelity GREEN
- [x] **REGIME_DEPENDENT disclosure (ZN)**
- [ ] External DSCL (CME settlement / secondary vendor) — BLOCKED until feeds
- [ ] Atomic registry transition spec — drafted here (§2), unexecuted
- [ ] Out-of-band scheduler wiring spec — drafted here (§1–2), unexecuted
- [ ] Replay-vs-forward validation run — post-wiring (§4)
- [ ] Sizing + portfolio role (ZN primary rates sleeve; MNQ separate event-tail; ZN+ZF not double-size)
- [ ] Operator approval record

## Boundaries
DESIGN ONLY. No mutation performed. Wiring requires §3 approvals + Phase 1C cleared first.
