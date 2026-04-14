# Golden System Snapshot — 2026-04-14

**Purpose:** Frozen reference of system state at hold entry. Used as the
"before" comparison for the 2026-05-01 Treasury-Rolldown checkpoint and
any subsequent integrity audit.

This snapshot is **read-only historical record.** Do not edit. To
capture a new snapshot, copy this file with a new date and regenerate
its contents from the live authorities.

---

## Repo state

- **HEAD commit:** `434a4a030580c950570a60432cefcaec5ca02761`
- **Branch:** `main`
- **Remote sync:** HEAD == origin/main (no unpushed commits)
- **Working tree:** operational files only (data CSVs, logs, state JSONs — auto-updated by pipelines; no uncommitted code or doc changes)

## Hold declaration

- **Hold entered:** 2026-04-14
- **Hold expires:** 2026-05-01 (Treasury-Rolldown first live monthly rebalance)
- **Hold scope:** no runtime code changes, no new scheduler entries, no registry status transitions, no strategy promotions/archives except via the pre-defined May 1 checkpoint outcomes
- **Hold exceptions explicitly allowed during window:** documentation (markdown under `docs/`), CLAUDE.md governance alignment, and the MYM data-pipeline fix (already executed 2026-04-14 pre-hold-finalization)

## Active runner universe

Per `build_portfolio_config(include_probation=True)` from
`engine/strategy_universe.py` with the DEAD_STATUSES guard active:

### Active core (3)
- ORB-MGC-Long
- PB-MGC-Short
- XB-PB-EMA-MES-Short

### Active probation — intraday single-asset (6)
- DailyTrend-MGC-Long
- TV-NFP-High-Low-Levels
- VolManaged-EquityIndex-Futures *(excluded from per-trade drift by design)*
- XB-ORB-EMA-Ladder-MCL
- XB-ORB-EMA-Ladder-MNQ
- XB-ORB-EMA-Ladder-MYM *(data-pipeline-gap resolved 2026-04-14; review clock starts from first post-backfill live bar)*
- ZN-Afternoon-Reversion

### Active probation — out-of-band monthly (1)
- Treasury-Rolldown-Carry-Spread *(execution_path=out_of_band_monthly_batch; intraday controller_action=OFF by design; first live rebalance expected 2026-05-01)*

**Total under runner's view: 10** (intraday runner config).
**Total under probation including out-of-band: 11.**

## Registry divergences currently contained

8 strategy entries have `status` ∈ {rejected, archived} with
`controller_action` ∈ {FULL_ON, REDUCED_ON, PROBATION}. All blocked
from the runner by the `DEAD_STATUSES` guard in
`engine/strategy_universe.py`. No operational risk while guard holds.
Listed for future hygiene pass only:

- BB-EQ-MGC-Long (rejected, REDUCED_ON)
- ORBEnh-M2K-Short (archived, PROBATION)
- VWAPMR-MCL-Short (archived, PROBATION)
- GapMom (rejected, PROBATION)
- RangeExpansion (rejected, PROBATION)
- FXBreak-6J-Short-London (rejected, PROBATION)
- PreFOMC-Drift-Equity (rejected, REDUCED_ON)
- Commodity-TermStructure-Carry-EnergyMetals (archived, PROBATION)

## Launch agents loaded

Verified via `launchctl list`:

- `ai.openclaw.gateway`
- `com.fql.claw-control-loop`
- `com.fql.daily-research`
- `com.fql.forward-day`
- `com.fql.operator-digest`
- `com.fql.source-helpers`
- `com.fql.treasury-rolldown-monthly` ← loaded 2026-04-14, first live fire expected 2026-05-01
- `com.fql.twice-weekly-research`
- `com.fql.watchdog`
- `com.fql.weekly-research`

**Total: 10 agents.**

## Health stack freshness

| Layer | File | Fresh as of |
|---|---|---|
| Shell recovery (backoff state) | `research/logs/.watchdog_state.json` | 2026-04-14 (minute-scale, updates every 5 min) |
| SAFE_MODE verdict | `research/data/watchdog_state.json` | 2026-04-14 (refreshed by scheduled `daily_system_watchdog`, priority 0) |
| 60-point hygiene report | `research/reports/health_check_*.json` | latest daily batch |
| Drift monitor | `research/data/live_drift_log.json` | 2026-04-14 (live sources since 2026-04-14 repoint) |

SAFE_MODE gate verdict at hold entry: **inactive** (forward trading would proceed).

## Data freshness per asset

| Asset | Last bar | Age |
|---|---|---|
| 6B | 2026-04-10 14:00 | 3d |
| 6E | 2026-04-12 19:50 | 1d |
| 6J | 2026-04-12 19:20 | 1d |
| M2K | 2026-04-12 19:55 | 1d |
| MCL | 2026-04-09 19:55 | 4d |
| MES | 2026-04-09 19:55 | 4d |
| MGC | 2026-04-10 14:40 | 3d |
| MNQ | 2026-04-12 19:55 | 1d |
| **MYM** | **2026-04-13 19:55** | **0d** *(post-backfill)* |
| ZB | 2026-04-12 19:55 | 1d |
| ZF | 2026-04-12 19:55 | 1d |
| ZN | 2026-04-12 19:55 | 1d |

**Known data exceptions at hold entry:**
- MCL, MES transient read-timeout errors on 2026-04-13 refresh (self-healing on next fire; not pipeline omissions)
- MYM: resolved 2026-04-14 — SYMBOLS dict omission fixed, +6,134 bars backfilled. See `research/data/strategy_registry.json` XB-ORB-EMA-Ladder-MYM `data_pipeline_gap` field for the full incident record.

## Registry state notes

- Schema version: `2.0`
- Total strategies tracked: 116
- Active (core or probation eligible): 11
- Rejected or archived: 105 (historical research record; 8 have divergent controller_action, all contained by guard)
- Strategies with `execution_path` field: 1 (Treasury-Rolldown, `out_of_band_monthly_batch`)
- Strategies with `data_pipeline_gap` field: 1 (XB-ORB-EMA-Ladder-MYM, resolved)

## Audit target paths (for May 1 checkpoint)

Exact file paths and fields the checkpoint procedures inspect. Captured
here so future reviewers don't have to rediscover them.

| Audit target | Path | Fields / checks |
|---|---|---|
| Spread log | `logs/spread_rebalance_log.csv` | 14 columns: `rebalance_date, strategy, spread_id, long_leg_asset, long_leg_entry_price, short_leg_asset, short_leg_entry_price, size_long, size_short, previous_long_leg_asset, previous_short_leg_asset, realized_pnl_prior_spread, days_held_prior_spread, notes` |
| Treasury-Rolldown stdout | `research/logs/treasury_rolldown_monthly_stdout.log` | launchd fire confirmation; script messages |
| Treasury-Rolldown stderr | `research/logs/treasury_rolldown_monthly_stderr.log` | tracebacks if any |
| Registry — Treasury-Rolldown entry | `research/data/strategy_registry.json` → `strategies[].strategy_id == "Treasury-Rolldown-Carry-Spread"` | `status`, `controller_action`, `execution_path`, `last_controller_date`, `notes` (re-probation record) |
| Registry — MYM entry (data-blocked record) | `research/data/strategy_registry.json` → `strategies[].strategy_id == "XB-ORB-EMA-Ladder-MYM"` | `data_pipeline_gap` structured field, `review_clock_start_source` enum |
| Drift monitor output | `research/data/live_drift_log.json` | most recent entry's `overall_status`, `forward_days`, `forward_trades`, `portfolio_status` |
| Drift monitor BASELINE (code) | `research/live_drift_monitor.py` | `BASELINE["excluded_from_strategy_drift"]` must still contain Treasury-Rolldown |
| Trade log (should NOT contain Treasury-Rolldown) | `logs/trade_log.csv` | confirm no rows with `strategy == "Treasury-Rolldown-Carry-Spread"` |
| Forward runner universe | `engine/strategy_universe.py` → `build_portfolio_config(include_probation=True)` | should return 10 strategies; Treasury-Rolldown should NOT be in that set (controller_action=OFF keeps it out) |
| SAFE_MODE verdict | `research/data/watchdog_state.json` | `safe_mode` boolean; should be false for forward trading to proceed |
| Scheduler log | `research/data/scheduler_log.json` | recent entries for `daily_system_watchdog` (priority 0, should show SUCCESS), `weekly_walk_forward` (should show MANUAL not ERROR) |

## Key documentation commit refs (authoritative sources)

All docs at HEAD `434a4a0`:

- `CLAUDE.md` — authoritative operating doc (updated 2026-04-14 to reflect probation line)
- `docs/PROBATION_REVIEW_CRITERIA.md` — non-XB-ORB probation governance (struck §2, §3, §6 with historical context)
- `docs/XB_ORB_PROBATION_FRAMEWORK.md` — XB-ORB probation governance
- `docs/PORTFOLIO_TRUTH_TABLE.md` — operator summary (derived, not authoritative)
- `docs/MAY_1_TREASURY_ROLLDOWN_VERIFICATION.md` — verification mechanics
- `docs/ELITE_PROMOTION_STANDARDS.md` — framework by strategy shape

## Hardening queue (deferred, named only)

Order: 3 → 5 → 1 → 2 → 4

1. **Shared dead-strategy guard helper** — extract `DEAD_STATUSES` check into reusable import
2. **Execution-shape field standardization** — `execution_path` pattern across all strategies
3. **Atomic lifecycle updater** — function that updates status + controller_action + notes in one call, refuses partial transitions
4. **Daily authority-consistency validator** — fails loudly when registry / docs / baseline / scorecards diverge
5. **Weekly stale-reference audit** — greps for archived names in active-target dicts

**All deferred to post-2026-05-01 checkpoint.**

## Session commit trail (this hold window preparation)

17 commits since 2026-04-14 start:

```
434a4a0 Close MYM data pipeline gap: SYMBOLS dict omission + backfill
03be5e7 Decision-quality trio: truth table, May 1 verification, promotion standards
b0ac5d0 Drop CARRY from replacement_scoreboard FACTOR_GAPS
c2ef4f6 Remove FXBreak-6J active-probation hardcoding from 4 runtime files
6fd3e04 Remove FXBreak-6J hardcoding from two runtime scripts
9eb6adf Document verified FXBreak-6J failure mode in criteria doc §3
b7e011b Re-probate Treasury-Rolldown-Carry-Spread via out-of-band monthly path
5fd8157 Reconcile probation authority: registry wins over stale criteria/baseline
f547920 Disable 4 rejected-but-live strategies + status guard in portfolio config
90d7972 Schedule system_watchdog so SAFE_MODE pre-flight reads fresh state
9c0387f Window-aware missing-signal severity + mute weekly_walk_forward
5da468c Refresh drift baseline to current live portfolio + tier-aware severity
f947af5 Repoint live drift monitor at live data + invalidate stale log
3e96a11 Redirect LAB_STATE authority pointers to current governance docs
91d57d7 Neutralize three stale governance anchors
af93049 Consolidate XB-ORB governance + kill README drift
f052c05 Decision readiness: review template + post-gate rules + standby candidate
```

---

*Snapshot captured 2026-04-14 at hold entry. Next snapshot: post-2026-05-01 checkpoint outcome.*
