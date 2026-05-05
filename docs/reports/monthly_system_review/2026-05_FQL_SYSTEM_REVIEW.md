# FQL Monthly System Review — 2026-05

**Generated:** 2026-05-05T10:39:50
**Scope:** full-system strategic governance (read-only)

**Safety contract:** report-only; no registry / Lane A / portfolio / runtime / scheduler / checkpoint mutation.

---

## 1. Executive Summary

### System health overview

- review window: **2026-05**
- sections produced: 8
- wins surfaced: 2
- risks surfaced: 3
- recommendations surfaced: 6

### Major wins

- 2 candidate(s) PASS-every-fire this month
- All 11 expected launchd agents loaded

### Major risks

- 1 watchdog check(s) not OK on last run
- Item 2 cross-pollination criterion: still 0 salvaged_from entries
- Closed-loop Forge→source-helpers feedback not yet wired (roadmap step #6)

### Top recommended next actions

- v2: parse commit log over the month and cross-check against claimed roadmap completions
- Consider batch register pre-flight for PASS-every-fire candidates not yet in registry
- Cross-pollination plumbing thin — prioritize batch registers that populate components_used
- Run `python3 scripts/portfolio_gap_dashboard.py --save` to seed gap data
- Build dedicated memory hygiene job (already on roadmap step #2) — this section is a thin sample

---

## 2. Roadmap Review

### Active roadmap markers (from project memory)

- Ladder steps detected: 9
- Steps marked DONE: 0

### Deferred items in `docs/roadmap_queue.md`

- Deferred-item headers: 14
  - Queue format
  - Item 1 — Gap-map targeting engine (formalization)
  - Item 2 — Component economy (formalization)
  - Item 3 — Validated → deployment ladder (explicit stages)
  - Item 4 — Portfolio-construction bridge (role-based promotion)
  - Item 5 — Research ROI / source yield analytics
  - Item 6 — Execution-side roadmap for live safety
  - Item 7 — Autonomous research factory loop
  - ... and 6 more

### Roadmap drift check

- TODO: compare claimed roadmap vs commit log evidence (deepen in v2).

---

## 3. Lane A Review (protected/live state)

### Watchdog last check

- timestamp: `2026-05-04T17:30:05.348099`
- overall: `HEALTHY`
- safe_mode: `False`
- non-OK checks: 1
  - `data_freshness`: WARN

### Strategy transitions this month

- transitions in window: 0

### Forward-runner log freshness

- no forward_runner*.log files found

---

## 4. Lane B / Forge Review

### Forge fires in window

- daily reports in 2026-05: 1
- verdict totals: {'PASS': 2, 'WATCH': 3, 'KILL': 0, 'RETEST': 0}
- distinct candidates evaluated: 5

### Best/worst candidates this month

- PASS-every-fire (2): ['XB-PB-EMA-Ladder-MCL', 'XB-PB-EMA-Ladder-MYM']
- KILL-every-fire (0): []

### Tripwire events
- tripwire files present: 0

### Autonomous-loop health

- low fire count (1); may be partial-month report or activation lag

---

## 5. Strategy Registry Review

### Registry summary

- total strategies: 151
- schema version: 2.0

### By status

- idea: 76
- rejected: 36
- archived: 26
- probation: 8
- core: 3
- monitor: 2

### By family (top 8)

- breakout: 20
- event_driven: 17
- vol_expansion: 16
- structural: 13
- mean_reversion: 12
- trend: 7
- carry: 7
- ict: 6

### By asset (top 10)

- MES: 26
- multi: 22
- M2K: 13
- MNQ: 11
- MGC: 11
- MCL: 11
- ZN: 9
- 6J: 5
- 6E: 3
- ZN/ZB/UB: 3

### Relationship-field population (Item 2 plumbing)

- components_used populated: 0 / 151 (0.0%)
- salvaged_from populated: 0 / 151 (0.0%)

### Probation roster (8)

- DailyTrend-MGC-Long (MGC, trend)
- TV-NFP-High-Low-Levels (MNQ, event_driven)
- VolManaged-EquityIndex-Futures (MES, volatility)
- Treasury-Rolldown-Carry-Spread (ZN, carry)
- ZN-Afternoon-Reversion (ZN, afternoon_rates_reversion)
- XB-ORB-EMA-Ladder-MNQ (MNQ, crossbreed_breakout)
- XB-ORB-EMA-Ladder-MCL (MCL, crossbreed_breakout)
- XB-ORB-EMA-Ladder-MYM (MYM, crossbreed_breakout)

---

## 6. Portfolio / Gap Review

### Coverage tallies

- distinct assets: 44
- distinct families: 50
- distinct sessions: 22

### Sessions

- daily: 48
- all_day: 29
- morning: 24
- daily_close: 9
- close: 7
- intraday: 6
- monthly: 4
- custom: 3
- afternoon: 3
- overnight: 3
- us_only: 2
- london_open: 2
- london_ny: 2
- midday: 1
- us_rth: 1
- quarterly: 1
- overnight_fomc: 1
- weekly: 1
- multi_day_nfp: 1
- event_window: 1
- afternoon_close: 1
- afternoon (13:30-15:25 ET): 1

### Concentration

- biggest family: `breakout` with 20 strategies (13.2% of registry)
- biggest asset: `MES` with 26 strategies (17.2% of registry)

### Pre-existing portfolio_gap_dashboard outputs

- saved dashboards on disk: 0

---

## 7. Automation Review

### Loaded launchd agents

- loaded: 11
  - `ai.openclaw.gateway`
  - `com.fql.claw-control-loop`
  - `com.fql.daily-research`
  - `com.fql.forge-daily-loop`
  - `com.fql.forward-day`
  - `com.fql.operator-digest`
  - `com.fql.source-helpers`
  - `com.fql.treasury-rolldown-monthly`
  - `com.fql.twice-weekly-research`
  - `com.fql.watchdog`
  - `com.fql.weekly-research`

### Recent launchd plist files in scripts/ vs LaunchAgents

- plists in repo scripts/: 5
- plists deployed to LaunchAgents/: 10

### Recent stderr log audit

- stderr log files: 9 (non-empty: 0)

### Tripwire events this month

- Forge tripwire files present: 0

---

## 8. Memory / Docs Hygiene

### Memory file count
- total: 27

### Memory automation claims vs reality

- agents named in `project_fql_state.md`: 10
- claimed-but-not-loaded: []
- loaded-but-not-mentioned: []

### Registry-count claim vs reality

- memory claims: 151, actual: 151

### Hygiene scan summary

- TODO v2: scan all .md docs for stale dates / broken cross-references / claimed-vs-actual JSON divergences

---

## 9. Source / Harvest Review

### Source quality evidence (memory)

- file present: `project_source_quality_evidence.md` (2193 bytes)

### Source-helper recent runs

- source_helpers*.log files: 9
- latest: `source_helpers_20260503_2000.log` (1d old)

### Closed-loop status (Forge → source-helpers)

- feedback edge: NOT WIRED YET (per roadmap step #6, highest-ROI architectural target)

---

## 10. Recommendations

Aggregated from all sections. **Operator decides** which to act on next month.

### Keep / Change / Add / Remove

- **[Roadmap Review]** v2: parse commit log over the month and cross-check against claimed roadmap completions
- **[Lane B / Forge Review]** Consider batch register pre-flight for PASS-every-fire candidates not yet in registry
- **[Strategy Registry Review]** Cross-pollination plumbing thin — prioritize batch registers that populate components_used
- **[Portfolio / Gap Review]** Run `python3 scripts/portfolio_gap_dashboard.py --save` to seed gap data
- **[Memory / Docs Hygiene]** Build dedicated memory hygiene job (already on roadmap step #2) — this section is a thin sample
- **[Source / Harvest Review]** Build closed-loop feedback edge: Forge PASSes up-weight source-helper priorities

### Highest-ROI next builds (per current roadmap)

- Step #2 — memory hygiene job (next-session priority)
- Step #3 — B.2 morning digest (unlocks higher cadence)
- Step #6 — closed-loop Forge → source-helpers feedback (architectural target)

### Safety affirmation

- Report-only. No registry / Lane A / portfolio / runtime / scheduler / checkpoint changes occurred during generation.
- All recommendations require operator approval before execution.

---
