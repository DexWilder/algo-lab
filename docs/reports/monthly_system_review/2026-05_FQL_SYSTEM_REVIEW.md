# FQL Monthly System Review — 2026-05

**Generated:** 2026-05-05T10:49:07
**Scope:** full-system strategic governance (read-only)
**Schema:** v1.1 — decision report (state → risks → deltas → decisions → recommendations)

**Safety contract:** report-only; no registry / Lane A / portfolio / runtime / scheduler / checkpoint mutation.

---

## 1. Executive Summary

### One-line state

**Window:** 2026-05  |  **Vision alignment:** YELLOW  |  **Wins:** 1  |  **Risks:** 4  |  **Decisions pending:** 1

### Major wins
- 2 candidate(s) PASS-every-fire this month

### Major risks
- 1 watchdog check(s) not OK on last run
- Item 2 cross-pollination criterion: 0 salvaged_from entries
- Memory drift: ['com.fql.monthly-system-review'] claimed but not loaded
- Closed-loop Forge→source-helpers feedback not yet wired (roadmap step #6)

### Read order for this report
1. **Decision Required** — what needs operator action
2. **Top 5 System Risks** — structural concerns ranked
3. **Vision Alignment Score** — overall direction check
4. **Recommended Roadmap Edits** — what to change next month
5. Detail sections below for evidence

---

## 2. Decision Required

**Operator action items aggregated from all sections. Triage before acting.**

| # | Section | Decision |
|---|---|---|
| 1 | Lane B / Forge Review | Operator: pre-flight batch register for 2 PASS-every-fire candidate(s)? |

### Highest-ROI next action

- See **Recommended Roadmap Edits** section for prioritized recommendations.

---

## 3. Top 5 System Risks

**Structural risks ranked by severity** (not raw errors — patterns that compound if unaddressed)

| # | Risk | Detail | Severity |
|---|---|---|---:|
| 1 | **Thin cross-pollination plumbing** | 0 salvaged_from entries — Item 2 criterion stalled | 75 |
| 2 | **Memory/docs drift** | 1 agents disagree between memory and reality | 65 |

---

## 4. Vision Alignment Score

### Score: 🟡 **YELLOW**

**Explanation:**

- 1 fires, 2 PASS verdicts — Forge producing signal at expected rate.
- Cross-pollination: 0 salvaged_from — Item 2 criterion not yet moving.

### Tooling-vs-strategy balance check

- v2 TODO: parse commit log to compute tooling-commits vs strategy-additions ratio.
- For v1.1: heuristic only — score above reflects PASS yield + cross-pollination flow.

### Drift indicators (watch for)

- Tooling commits accumulating without registry growth → drift toward overengineering
- PASSes generated faster than they're registered → drift toward backlog
- Same candidates re-tested without new combinations → drift toward noise

---

## 5. Month-over-Month Delta

**No prior snapshot for 2026-04 — this is the baseline month.**
Snapshot saved at `.snapshots/2026-05_snapshot.json` for next month's comparison.

| Metric | This month | Prior month | Δ |
|---|---:|---:|---:|
| Total strategies | 151 | — | — |
| Status: idea | 76 | — | — |
| Status: probation | 8 | — | — |
| Status: core | 3 | — | — |
| Status: monitor | 2 | — | — |
| Status: rejected | 36 | — | — |
| Status: archived | 26 | — | — |
| Forge fires (reports) | 1 | — | — |
| PASS verdicts (cumulative) | 2 | — | — |
| WATCH verdicts | 3 | — | — |
| KILL verdicts | 0 | — | — |
| RETEST verdicts | 0 | — | — |
| Candidate pool size | 19 | — | — |
| Loaded launchd agents | 11 | — | — |
| Tripwire files unresolved | 0 | — | — |
| salvaged_from populated | 0 | — | — |
| components_used populated | 0 | — | — |

---

## 6. Evidence Absorption Rate

### Generation side

- candidates tested this month: 5
- PASS verdicts (counting repeats): 2
- distinct PASS candidates: 2
- Forge daily reports on disk: 1

### Absorption side

- v2 TODO: parse registry `_generated` timestamps to count entries added this month
- v2 TODO: count operator-acknowledged reports (no ack-marker convention exists yet)
- For v1.1: assume zero acknowledged unless proven otherwise

### Status: **IN_BALANCE**

---

## 7. Automation Truth Table

**Expected vs actual launchd state. OK / WARN / FAIL per agent.**

| Agent | Lane | Expected cadence | Loaded | Last log age | Status |
|---|---|---|---|---|---|
| `ai.openclaw.gateway` | infra | KeepAlive (continuous) | ✅ | — | ✅ OK |
| `com.fql.watchdog` | infra | every 5 min | ✅ | 0.0h | ✅ OK |
| `com.fql.claw-control-loop` | Lane B | every 30 min | ✅ | — | ⚠️ WARN |
| `com.fql.forward-day` | Lane A | weekdays 17:00 | ✅ | — | ⚠️ WARN |
| `com.fql.daily-research` | Lane A | weekdays 17:30 | ✅ | 17.0h | ✅ OK |
| `com.fql.operator-digest` | Lane A | weekdays 18:00 | ✅ | — | ⚠️ WARN |
| `com.fql.twice-weekly-research` | Lane A | Tue/Thu 18:00 | ✅ | 4.7d | ✅ OK |
| `com.fql.weekly-research` | Lane A | Fri 18:30 | ✅ | 3.7d | ✅ OK |
| `com.fql.source-helpers` | Lane B | Sun + Wed 20:00 | ✅ | 38.8h | ✅ OK |
| `com.fql.treasury-rolldown-monthly` | Lane A | weekdays 17:10 (1st-biz guard) | ✅ | 17.7h | ✅ OK |
| `com.fql.forge-daily-loop` | Lane B | weekdays 19:00 | ✅ | — | ⚠️ WARN |

---

## 8. Roadmap Review

### Active roadmap markers (from project memory)

- ladder steps detected: 9
- steps marked DONE: 0

### Deferred items in `docs/roadmap_queue.md`

- deferred-item headers: 14
  - Queue format
  - Item 1 — Gap-map targeting engine (formalization)
  - Item 2 — Component economy (formalization)
  - Item 3 — Validated → deployment ladder (explicit stages)
  - Item 4 — Portfolio-construction bridge (role-based promotion)
  - Item 5 — Research ROI / source yield analytics
  - ... and 8 more

### Roadmap drift check

- v2 TODO: parse commit log over month vs claimed completions for drift detection.

---

## 9. Lane A Review (protected/live state)

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

## 10. Lane B / Forge Review

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

- low fire count (1); may be partial-month or activation lag

---

## 11. Strategy Registry Review

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

## 12. Portfolio / Gap Review

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

- biggest family: `breakout` (20, 13.2% of registry)
- biggest asset: `MES` (26, 17.2% of registry)

### Pre-existing portfolio_gap_dashboard outputs

- saved dashboards on disk: 0

---

## 13. Memory / Docs Hygiene

### Memory file count
- total: 27

### Memory automation claims vs reality

- agents named in `project_fql_state.md`: 11
- claimed-but-not-loaded: ['com.fql.monthly-system-review']
- loaded-but-not-mentioned: []

### Registry-count claim vs reality

- memory claims: 151, actual: 151

---

## 14. Source / Harvest Review

### Source quality evidence (memory)

- file present: `project_source_quality_evidence.md` (2193 bytes)

### Source-helper recent runs
- source_helpers*.log files: 9
- latest: `source_helpers_20260503_2000.log` (1d old)

### Closed-loop status (Forge → source-helpers)

- feedback edge: NOT WIRED YET (per roadmap step #6, highest-ROI architectural target)

---

## 15. Recommended Roadmap Edits

**Specific add / change / remove recommendations for the active roadmap.**

### From section findings

- **[Strategy Registry Review]** Cross-pollination plumbing thin — prioritize batch registers that populate components_used
- **[Portfolio / Gap Review]** Run `python3 scripts/portfolio_gap_dashboard.py --save` to seed gap data
- **[Memory / Docs Hygiene]** Build dedicated memory hygiene job (roadmap step #2) — this section is a thin sample

### Standing roadmap reminders

- Step #2 — memory hygiene job (next-session priority)
- Step #3 — B.2 morning digest (unlocks higher cadence)
- Step #6 — closed-loop Forge → source-helpers feedback (highest-ROI architectural target)

### Suggested ladder edits

- v2 TODO: detect if a step has been DONE for 30+ days without next-step start → flag stall
- v2 TODO: detect if a step has been pending for 60+ days → flag for re-scoping or removal

---

## 16. Next Month Watchlist

**3-7 items the next monthly report should explicitly revisit.**

1. Forge fires next month — confirm rotation visited all candidates at least once
2. Registry total strategies (current: 151)
3. salvaged_from population (currently 0 — first non-zero entry would move Item 2 criterion)
4. Closed-loop feedback edge — has step #6 progressed?

### Standing watchlist (always check)

- Tripwire files in `/Users/chasefisher/projects/Algo Trading/algo-lab/research/data/fql_forge/reports/_TRIPWIRE_*.md`
- Memory drift (claimed agents vs `launchctl list`)
- Roadmap step movement (any DONE / IN-PROGRESS state changes)
- salvaged_from population (Item 2 criterion movement)

---

## 17. Source Artifacts

**Paths and links to all source artifacts referenced in this report.**

### Live data
- registry: `research/data/strategy_registry.json`
- watchdog state: `research/data/watchdog_state.json`
- transition log: `research/data/strategy_transition_log.json`
- scheduler log: `research/data/scheduler_log.json`

### Forge
- daily reports: `research/data/fql_forge/reports/`
- runner: `research/fql_forge_batch_runner.py`

### Automation
- repo plists: `scripts/com.fql.*.plist`
- deployed plists: `~/Library/LaunchAgents/`
- launchd logs: `research/logs/launchd_*_stdout.log`, `*_stderr.log`

### Roadmap & docs
- `docs/roadmap_queue.md`
- `docs/fql_forge/post_may1_build_sequence.md`
- `docs/fql_forge/forge_automation_design.md`
- `docs/fql_forge/ELITE_OPERATING_PRINCIPLES.md`
- `CLAUDE.md`

### Memory
- `~/.claude/projects/-Users-chasefisher/memory/` (project + feedback memory)

### Operator review packets
- `docs/fql_forge/operator_review_packet_*.md`
- `docs/_DRAFT_*.md` (pre-flights)

### This review
- output: `docs/reports/monthly_system_review/{YYYY-MM}_FQL_SYSTEM_REVIEW.md`
- snapshots: `docs/reports/monthly_system_review/.snapshots/`
- pre-flight: `docs/_DRAFT_2026-05-05_monthly_system_review_preflight.md`
- plist (disabled): `scripts/com.fql.monthly-system-review.plist.disabled`

---

## 18. Pre-Activation Checklist

**One-time checklist while plist remains `.disabled`. Operator reviews before `launchctl bootstrap`.**

| Check | Status | Notes |
|---|:---:|---|
| Smoke test report exists | ✅ | 1 report(s) in `docs/reports/monthly_system_review/` |
| Report path follows convention | ✅ | Format: `YYYY-MM_FQL_SYSTEM_REVIEW.md` |
| First-Saturday self-guard verified | ✅ | Tested manually 2026-05-05 (Tue) — exits cleanly |
| plutil lint on disabled plist | ✅ | `com.fql.monthly-system-review.plist.disabled` |
| Logs path declared in plist | ✅ | stdout/stderr → `research/logs/launchd_monthly_review_*.log` |
| Plist NOT yet deployed | ✅ | `/Users/chasefisher/Library/LaunchAgents/com.fql.monthly-system-review.plist` should not exist until activation |
| Snapshot dir writable | ✅ | `docs/reports/monthly_system_review/.snapshots` |
| No mutation paths in script | ✅ | Reads-only against registry/watchdog/forge/launchctl; only writes to monthly_system_review/ |
| Activation commands documented | ✅ | See `docs/_DRAFT_2026-05-05_monthly_system_review_preflight.md` §Activation |
| v1.1 sections present | ✅ | Decision Required, Top 5 Risks, Vision Alignment, MoM Delta, Evidence Absorption, Truth Table, Roadmap Edits, Watchlist, Artifacts, Checklist |

### Activation recommendation

**All checks pass.** Plist is safe to activate per pre-flight `Activation steps`.

---
