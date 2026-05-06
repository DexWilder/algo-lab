# Memory Hygiene Audit — 2026-05-06

**Generated:** 2026-05-06T05:58:33
**Scope:** Phase A — manual CLI; report-only, no mutation.

**Verdict:** 🟡 YELLOW  |  FAIL: 0  |  WARN: 12  |  INFO: 5

---

## Summary — drift items

| Severity | Check | Detail | Suggested fix |
|---|---|---|---|
| WARN | `deployed-not-in-repo` | `com.fql.forward-day` deployed but no source in repo | add to repo or remove deployment |
| WARN | `deployed-not-in-repo` | `com.fql.operator-digest` deployed but no source in repo | add to repo or remove deployment |
| WARN | `deployed-not-in-repo` | `com.fql.source-helpers` deployed but no source in repo | add to repo or remove deployment |
| WARN | `deployed-not-in-repo` | `com.fql.treasury-rolldown-monthly` deployed but no source in repo | add to repo or remove deployment |
| WARN | `deployed-not-in-repo` | `com.fql.watchdog` deployed but no source in repo | add to repo or remove deployment |
| WARN | `cadence-drift` | `com.fql.source-helpers`: claimed `every 3 days` vs actual `Sun+Wed 20:00` | update memory/CLAUDE.md to say `Sun+Wed 20:00` |
| WARN | `registry-count-drift` | `project_fql_state.md` claims 151 strategies, actual is 163 (Δ -12) | update project_fql_state.md to say `163` |
| WARN | `registry-count-drift` | `CLAUDE.md` claims 115 strategies, actual is 163 (Δ -48) | update CLAUDE.md to say `163` |
| WARN | `probation-roster-drift` | `FXBreak-6J-Short-London` in CLAUDE.md probation table; actual status: `rejected` | update CLAUDE.md or re-probate |
| WARN | `probation-roster-drift` | `MomPB-6J-Long-US` in CLAUDE.md probation table; actual status: `archived` | update CLAUDE.md or re-probate |
| WARN | `probation-roster-drift` | `NoiseBoundary-MNQ-Long` in CLAUDE.md probation table; actual status: `archived` | update CLAUDE.md or re-probate |
| WARN | `probation-roster-drift` | `PreFOMC-Drift-Equity` in CLAUDE.md probation table; actual status: `rejected` | update CLAUDE.md or re-probate |
| INFO | `repo-not-deployed` | `com.fql.forward-trading` exists in `scripts/` but not deployed | intentional or needs deployment? |
| INFO | `broken-path-reference` | `docs/_DRAFT_2026-05-XX_batch_register_xb_hybrids.md` cited in `project_fql_state.md` but doesn't exist | remove reference or restore file |
| INFO | `broken-path-reference` | `inbox/_family_queue.md` cited in `CLAUDE.md` but doesn't exist | remove reference or restore file |
| INFO | `broken-path-reference` | `inbox/_family_queue.md` cited in `project_fql_state.md` but doesn't exist | remove reference or restore file |
| INFO | `broken-path-reference` | `inbox/_priorities.md` cited in `CLAUDE.md` but doesn't exist | remove reference or restore file |

---

## Detail per check

### Launchd agents — repo / deployed / loaded coherence

### Inventory

- repo enabled plists (`scripts/com.fql.*.plist`): 5
- repo disabled plists (`*.plist.disabled`): 2: ['com.fql.forge-daily-loop', 'com.fql.monthly-system-review']
- deployed plists (`~/Library/LaunchAgents/`): 12
- launchctl loaded: 12

### Checks
- INFO: `com.fql.forward-trading` exists in `scripts/` but not deployed
- WARN: `com.fql.forward-day` deployed but no source in repo
- WARN: `com.fql.operator-digest` deployed but no source in repo
- WARN: `com.fql.source-helpers` deployed but no source in repo
- WARN: `com.fql.treasury-rolldown-monthly` deployed but no source in repo
- WARN: `com.fql.watchdog` deployed but no source in repo

*Drifts: 6*

---

### Plist cadence — claimed vs actual

### Per-agent claimed vs actual cadence

| Agent | Claimed (memory/CLAUDE.md) | Actual (plist) | Match? |
|---|---|---|:---:|
| `com.fql.claw-control-loop` | — | every 30 min | ? |
| `com.fql.daily-research` | weekdays 17:30 | weekdays 17:30 | ✅ |
| `com.fql.forge-daily-loop` | weekdays 19:00 | weekdays 19:00 | ✅ |
| `com.fql.forward-day` | weekdays 17:00 | weekdays 17:00 | ✅ |
| `com.fql.monthly-system-review` | — | Sat 09:00 | ? |
| `com.fql.operator-digest` | weekdays 18:00 | weekdays 18:00 | ✅ |
| `com.fql.source-helpers` | every 3 days | Sun+Wed 20:00 | ❌ |
| `com.fql.treasury-rolldown-monthly` | weekdays 17:10 | weekdays 17:10 | ✅ |
| `com.fql.twice-weekly-research` | Tue/Thu 18:00 | Tue+Thu 18:00 | ✅ |
| `com.fql.watchdog` | — | every 5 min | ? |
| `com.fql.weekly-research` | Fri 18:30 | Fri 18:30 | ✅ |

*Drifts: 1*

---

### Registry summary — claimed vs actual

### Actual registry state

- total: 163
- by status: {'idea': 88, 'rejected': 36, 'archived': 26, 'probation': 8, 'core': 3, 'monitor': 2}

### Claims in memory/docs

- `project_fql_state.md`: claims `151` (actual 163, Δ -12) — ❌
  - context: "..._record_2026-05-05.md`.  ### Registry - 151 strategies (idea: 76, rejected: 36, archived: 26,..."
- `CLAUDE.md`: claims `115` (actual 163, Δ -48) — ❌
  - context: "...tem State (2026-04-14)  - **Registry:** 115+ strategies, schema v3.2, rejection taxonomy - **Ge..."

### Status breakdown claim found in memory
- match groups: ('76', '8', '3')
- (manual cross-check: compare against actual {'rejected': 36, 'core': 3, 'archived': 26, 'monitor': 2, 'idea': 88, 'probation': 8})

*Drifts: 2*

---

### Probation roster — CLAUDE.md vs registry

### Actual probation roster (8)

- DailyTrend-MGC-Long
- TV-NFP-High-Low-Levels
- Treasury-Rolldown-Carry-Spread
- VolManaged-EquityIndex-Futures
- XB-ORB-EMA-Ladder-MCL
- XB-ORB-EMA-Ladder-MNQ
- XB-ORB-EMA-Ladder-MYM
- ZN-Afternoon-Reversion

### Strategy IDs mentioned in CLAUDE.md Probation Portfolio section (12)

- DailyTrend-MGC-Long: ✅ in registry as probation
- FXBreak-6J-Short-London: ❌ NOT probation in registry
- MomPB-6J-Long-US: ❌ NOT probation in registry
- NoiseBoundary-MNQ-Long: ❌ NOT probation in registry
- PreFOMC-Drift-Equity: ❌ NOT probation in registry
- TV-NFP-High-Low-Levels: ✅ in registry as probation
- Treasury-Rolldown-Carry-Spread: ✅ in registry as probation
- VolManaged-EquityIndex-Futures: ✅ in registry as probation
- XB-ORB-EMA-Ladder-MCL: ✅ in registry as probation
- XB-ORB-EMA-Ladder-MNQ: ✅ in registry as probation
- XB-ORB-EMA-Ladder-MYM: ✅ in registry as probation
- ZN-Afternoon-Reversion: ✅ in registry as probation

*Drifts: 4*

---

### Path references — claimed paths vs filesystem

### Files scanned: 28

### Distinct path references found: 51

### Broken references (4)

- `docs/_DRAFT_2026-05-XX_batch_register_xb_hybrids.md` (referenced in `project_fql_state.md`)
- `inbox/_family_queue.md` (referenced in `CLAUDE.md`)
- `inbox/_family_queue.md` (referenced in `project_fql_state.md`)
- `inbox/_priorities.md` (referenced in `CLAUDE.md`)

*Drifts: 4*

---

### Forge candidate pool size — claimed vs actual

### Actual pool size: 19

- memory claims `19-candidate pool` — ✅

*Drifts: 0*

---

## Safety affirmation

- Report-only. No memory / docs / registry / plist / launchd state mutation.

- Operator decides which drifts to fix.
