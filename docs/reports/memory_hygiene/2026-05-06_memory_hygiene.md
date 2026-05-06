# Memory Hygiene Audit — 2026-05-06

**Generated:** 2026-05-06T06:23:56
**Scope:** Phase A — manual CLI; report-only, no mutation.

**Verdict:** 🟢 GREEN  |  FAIL: 0  |  WARN: 0  |  INFO: 4

---

## Summary — drift items

| Severity | Check | Detail | Suggested fix |
|---|---|---|---|
| INFO | `repo-not-deployed` | `com.fql.forward-trading` exists in `scripts/` but not deployed | intentional or needs deployment? |
| INFO | `broken-path-reference` | `inbox/_family_queue.md` cited in `CLAUDE.md` but doesn't exist | remove reference or restore file |
| INFO | `broken-path-reference` | `inbox/_family_queue.md` cited in `project_fql_state.md` but doesn't exist | remove reference or restore file |
| INFO | `broken-path-reference` | `inbox/_priorities.md` cited in `CLAUDE.md` but doesn't exist | remove reference or restore file |

---

## Detail per check

### Launchd agents — repo / deployed / loaded coherence

### Inventory

- repo enabled plists (`scripts/com.fql.*.plist`): 5
- repo disabled plists (`*.plist.disabled`): 7: ['com.fql.forge-daily-loop', 'com.fql.forward-day', 'com.fql.monthly-system-review', 'com.fql.operator-digest', 'com.fql.source-helpers', 'com.fql.treasury-rolldown-monthly', 'com.fql.watchdog']
- deployed plists (`~/Library/LaunchAgents/`): 12
- launchctl loaded: 12

### Checks
- INFO: `com.fql.forward-trading` exists in `scripts/` but not deployed

*Drifts: 1*

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
| `com.fql.source-helpers` | Wed 20:00 | Sun+Wed 20:00 | ✅ |
| `com.fql.treasury-rolldown-monthly` | weekdays 17:10 | weekdays 17:10 | ✅ |
| `com.fql.twice-weekly-research` | Tue/Thu 18:00 | Tue+Thu 18:00 | ✅ |
| `com.fql.watchdog` | — | every 5 min | ? |
| `com.fql.weekly-research` | Fri 18:30 | Fri 18:30 | ✅ |

- ✅ No cadence drift detected (or claims too vague to mismatch).

*Drifts: 0*

---

### Registry summary — claimed vs actual

### Actual registry state

- total: 163
- by status: {'idea': 88, 'rejected': 36, 'archived': 26, 'probation': 8, 'core': 3, 'monitor': 2}

### Claims in memory/docs

- `project_fql_state.md`: claims `163` (actual 163, Δ 0) — ✅
  - context: "..._record_2026-05-05.md`.  ### Registry - 163 strategies (idea: 88, rejected: 36, archived: 26,..."
- `CLAUDE.md`: claims `163` (actual 163, Δ 0) — ✅
  - context: "...tem State (2026-05-06)  - **Registry:** 163 strategies, schema v3.2, rejection taxonomy - **Ge..."

### Status breakdown claim found in memory
- match groups: ('88', '8', '3')
- (manual cross-check: compare against actual {'rejected': 36, 'core': 3, 'archived': 26, 'monitor': 2, 'idea': 88, 'probation': 8})

*Drifts: 0*

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

### Strategy IDs mentioned in CLAUDE.md Probation Portfolio section (8)

- DailyTrend-MGC-Long: ✅ in registry as probation
- TV-NFP-High-Low-Levels: ✅ in registry as probation
- Treasury-Rolldown-Carry-Spread: ✅ in registry as probation
- VolManaged-EquityIndex-Futures: ✅ in registry as probation
- XB-ORB-EMA-Ladder-MCL: ✅ in registry as probation
- XB-ORB-EMA-Ladder-MNQ: ✅ in registry as probation
- XB-ORB-EMA-Ladder-MYM: ✅ in registry as probation
- ZN-Afternoon-Reversion: ✅ in registry as probation

*Drifts: 0*

---

### Path references — claimed paths vs filesystem

### Files scanned: 28

### Distinct path references found: 50

### Broken references (3)

- `inbox/_family_queue.md` (referenced in `CLAUDE.md`)
- `inbox/_family_queue.md` (referenced in `project_fql_state.md`)
- `inbox/_priorities.md` (referenced in `CLAUDE.md`)

*Drifts: 3*

---

### Forge candidate pool size — claimed vs actual

### Actual pool size: 19

- memory claims `19-candidate pool` — ✅

*Drifts: 0*

---

## Safety affirmation

- Report-only. No memory / docs / registry / plist / launchd state mutation.

- Operator decides which drifts to fix.
