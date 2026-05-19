# Pre-Flight: Sentinel v0 — Auto-Surfacing Drift Monitor

**Filed:** 2026-05-19
**Authority:** T1 (pre-flight); T2 (eventual build approval)
**Lane:** B (governance / drift prevention)
**Status:** DRAFT — narrowed spec per three-party convergence 2026-05-19; **Monitor 6 (cost-coverage) added later same day as hard requirement** per evidence-integrity doctrine. **No build today.**

---

## Problem

We have audit *tools* (`governance_audit.py`, `memory_hygiene_audit.py`, `monthly_system_review.py`, `forge_source_feedback.py`) but findings only surface when the operator manually invokes them. Today's example: the registry→runner pool gap (78 unrun ideas) and harvest triage 15-day staleness both surfaced ONLY because the operator prompted a supply-chain audit. Without that prompt, they remained invisible.

**The fix is making the SOP automatic, not building another big infrastructure system.**

## Counter-argument (per pre-flight challenge-layer doctrine)

The strongest case AGAINST building Sentinel v0:

> *Building an auto-audit system is itself the infrastructure drift the audit is supposed to catch. We'd spend 1-2 sessions during the Paper-Readiness Sprint building a tool that doesn't move a single candidate closer to paper. The lesson from 5/18 was "stop building infrastructure"; building Sentinel violates that lesson in service of the same lesson.*

**Why we proceed anyway:**
- The failure mode is RECURRING (this is the 2nd time in 2 weeks operator caught drift via prompt rather than auto-surfacing)
- Sentinel v0 is narrowed to 5 monitors only — not a broad aggregator
- v0 is manual; no activation/scheduling until manual proves value
- Build allowed only in a natural Lane 2 slot that doesn't delay Item #3
- Without Sentinel, every drift detection requires another "operator prompts → audit → finding" cycle

## What would prove this decision wrong

- Building Sentinel v0 takes longer than 1 session
- Item #3 (cost/slippage) slips because Sentinel is in the way
- The first manual run produces findings the operator already knew (i.e., Sentinel adds no new signal)
- Operator review burden of the weekly Sentinel report exceeds the burden saved by not having to prompt audits

## Reversal criteria

If first manual run produces zero new findings beyond what existing audits surface, revert: delete the tool, don't schedule. Sentinel is justified only if it catches drift that existing tools miss.

---

## Scope: v0 (narrowed per GPT critique; Monitor 6 mandatory)

**6 monitors.** Monitors 1-5 are narrowed per critique; Monitor 6 was added 2026-05-19 as a hard requirement after the silent zero-cost defaults incident.

### Monitor 1: Paper-readiness sprint progress

```
Phase 2 outcome: 1-3 paper-readiness packets by 2026-06-17
Days remaining: <auto-computed>
Packets produced: <count>
Candidates advanced this week: <delta from prior report>
Current sprint item: <Item #N>

Triggers:
- 🔴 RED if 0 candidate movement for 2 consecutive reports
- 🔴 RED if sprint exit date arrives with 0 packets
- 🟡 YELLOW if current sprint item hasn't progressed in 7 days
- 🟢 GREEN otherwise
```

### Monitor 2: Registry → runner pool gap

```
Idea-status candidates: <N>
In Forge runner pool: <N>
Gap (registered but not tested): <N>
"cleared_to_convert" / "convert_next" count: <N>
Age distribution of cleared-to-convert items: <histogram>

Triggers:
- 🔴 RED if cleared_to_convert items sit >30 days unrun
- 🟡 YELLOW if gap grows by >10 since prior report
- 🟢 GREEN otherwise
```

### Monitor 3: Harvest triage cadence

```
Days since last harvest_triage file: <N>
Items in inbox/harvest awaiting triage: <N>

Triggers:
- 🟡 YELLOW if >7 days
- 🔴 RED if >14 days
- 🟢 GREEN otherwise
```

### Monitor 4: Watchlist lifecycle aging

```
Watchlist items in memory: <N>
Items with no state change >21 days: <list>
Items with no state change >30 days: <list>

Triggers:
- 🟡 YELLOW at 21 days no change → flag for operator decision
- 🔴 RED at 30 days no change → mandatory decide-or-drop
- 🟢 GREEN otherwise
```

### Monitor 5: Repeated unresolved finding

```
For each finding in this report:
  - Check if same finding appeared in prior 3 reports
  - If yes WITHOUT action route taken → escalate

Triggers:
- 🔴 RED if same finding repeats 3 reports without action route
- 🟡 YELLOW if same finding repeats 2 reports without action route
- 🟢 GREEN if finding is new or has action route logged
```

Requires: prior-report snapshot mechanism (small JSON file `.snapshots/YYYY-MM-DD_sentinel.json`).

### Monitor 6: Cost-coverage integrity (added 2026-05-19; hard requirement per `feedback_evidence_integrity_failsafe.md`)

```
For each active/probation/paper-candidate strategy:
  - Resolve its asset
  - Check engine/backtest.py COST_DEFAULTS for that asset
  - If asset missing → INVALID_COST_ASSUMPTION
  - For each candidate report generated this week:
      - Verify the cost block is present in the report header
      - If absent → INVALID_COST_REPORT

Triggers:
- 🔴 RED if ANY active/probation/paper candidate asset lacks cost defaults
- 🔴 RED if ANY candidate report omits cost assumptions
- 🟢 GREEN only when all active/probation/paper assets are configured AND all reports show explicit cost blocks
```

Not optional. This monitor is the reason Sentinel must exist at all — the silent-cost-defaults incident is the failure mode the broader Sentinel concept was supposed to prevent. Monitor 6 is the load-bearing one.

---

## Explicitly NOT in v0

Per the "do not act on" anti-bloat field:

- ❌ Full aggregation of `governance_audit.py` / `memory_hygiene_audit.py` / `monthly_system_review.py` / `forge_source_feedback.py` findings (those still run separately on demand)
- ❌ Full source-feedback integration
- ❌ Doctrine memory accumulation scoring (the doctrine of "5 doctrines triggers consolidation" exists but Sentinel doesn't enforce it in v0)
- ❌ launchd activation (manual only in v0; scheduling decision deferred)
- ❌ Real-time alerts (weekly is enough)
- ❌ Automatic fixes (surfacing only)
- ❌ Dashboards beyond a single markdown file
- ❌ Source-helper changes
- ❌ Registry mutation
- ❌ Lane A changes

---

## Output format

`docs/reports/sentinel/YYYY-MM-DD_sentinel.md`

```
# Sentinel — YYYY-MM-DD

**Overall status:** 🟢 GREEN / 🟡 YELLOW / 🔴 RED
**Current phase outcome:** Phase 2 — 1-3 paper-readiness packets by 2026-06-17

## Top 3 blockers to outcome (if any)
1. [highest-severity finding]
2. ...
3. ...

## Triggered checks
| Monitor | Status | Finding | Recommended action route |
|---|---|---|---|
| Sprint progress | 🟢 | 2 candidates advanced this week | none |
| Registry→runner gap | 🟡 | 5 cleared_to_convert items aging | sprint backlog |
| Triage cadence | 🔴 | 15 days since last triage | fix now |
| Watchlist aging | 🟢 | no items >21 days | none |
| Repeated finding | 🟢 | no repeats | none |

## Recommended action routes (per finding)
- fix now (this week)
- sprint backlog (during Phase 2)
- post-sprint backlog (after 2026-06-17)
- operator decision
- ignore / expected

## Do not act on (anti-bloat field)
- [findings explicitly noted as known/expected/already-tracked, so they don't become busywork]
```

The "do not act on" section is explicit anti-bloat: surface a finding once, mark it explicitly OK, then it doesn't become recurring noise.

---

## Build rule

**Sentinel v0 may be built only if it does NOT delay Item #3 (cost/slippage model).**

If Item #3 takes the next Lane 2 slot, Sentinel waits.
If Item #3 finishes cleanly with leftover capacity, Sentinel becomes eligible.
If a Lane 2 day appears with no Item #3 work-in-progress and no other sprint blocker, Sentinel can build.

Estimated effort: **~1 session for v0** (5 monitors, single output file, no plist).

---

## Activation gate

v0 is **manual CLI only.** Operator runs: `python3 research/sentinel.py [--save]`.

After 2-3 manual runs prove the report adds new signal beyond existing audits:
- Operator approves scheduling
- Then build the plist + activate
- Pre-flight required for activation step

---

## Where this fits in the four-lane model

- **Lane 2 governance fix** (no truth mutation; report-only)
- Indirectly supports Paper-Readiness Sprint via drift detection
- Directly applies the doctrine `feedback_drift_prevention_patterns.md` (the doctrine exists; this enforces it)
- Does NOT directly move a candidate closer to paper-readiness scoring
- Per the four-lane doctrine: allowed when GREEN if it doesn't delay deliverable work

---

## Sprint sequencing impact

| Item | Status | Order |
|---|---|---|
| Item #1 evidence-tier labels | ✅ DONE | shipped |
| Item #2 correlation matrix | ✅ DONE | shipped |
| Item #2 cluster metadata | ✅ DONE | shipped |
| **Item #3 cost/slippage model** | **NEXT** | **primary** |
| Item #4 lock doctrines (memory only) | queued | quick |
| Sentinel v0 | NEW; eligible only in natural Lane 2 slot | non-blocking |
| Item #5 pool hygiene | queued | |
| Item #6 stale-WATCH | queued | |
| Item #7 validation funnel v0 | queued (heaviest) | |
| Item #8 top-3 selection | queued | |
| Item #9 paper-readiness packets | queued (deliverable) | |

Sentinel does not move into Item #3's slot. It builds in parallel only if a Lane 2 opportunity opens without contention.

---

## Operator decision

| Option | Decision |
|---|---|
| ☐ Approve this pre-flight as written | Sentinel v0 eligible in next natural Lane 2 slot |
| ☐ Approve with edits | (specify) |
| ☐ Defer to post-sprint backlog | Skip until after 2026-06-17 packets ship |
| ☐ Reject | Don't build Sentinel; rely on operator prompts |

---

*Filed 2026-05-19. Lane B / governance. Pre-flight only — NO build today. Item #3 cost/slippage remains the primary next sprint build. Sentinel v0 builds only in natural Lane 2 slot that doesn't delay the deliverable.*
