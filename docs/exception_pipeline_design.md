# FQL Exception Pipeline — Design (v1)

**Status:** Design only. No code changes. Drafted 2026-04-16 during the
2026-04-14 → 2026-05-01 hold window. Implementation deferred to a
post-checkpoint go/no-go after May 1.

**Purpose:** Add the missing layer between FQL's detectors and the
operator. Today: detectors fire → operator becomes the routing,
classification, and resolution layer. Target: detectors fire → pipeline
classifies → routes by class → auto-acts where safe → surfaces to
operator only when human judgment is actually required, always with
classification + suggested action attached.

**Success criterion:** Reduce repeated unresolved alerts. Stop the
operator from being the routing layer.

**Anchoring diagnosis:** see commit history `fae4b54` and prior — three
issues (closed-family x10/x17 alerts, MGC-Long stale 31d, watchdog
state frozen 23h) all share one pattern: detect-and-surface, no
classify-and-act. Three issues, one root cause. This pipeline closes it.

This document specifies seven things:

1. Architecture
2. Severity classes (routing × root-cause × urgency)
3. Class-specific auto-actions vs operator-required
4. Ownership boundaries by subsystem
5. Meta-monitoring rules (so monitoring surfaces cannot silently drift)
6. Hold-window / SAFE_MODE behavior
7. Phased rollout after May 1

Plus three anchor case walk-throughs (the issues that prompted this
design), v1.1 refinements, v2 questions, and relationship to the Forge
kernel design.

---

## 1. Architecture

The pipeline is **non-invasive**: existing detectors keep firing and
writing to their existing surfaces. The pipeline reads from the same
sources, adds classification + routing + auto-action on top, and writes
to operator surfaces *in addition to* (eventually replacing) the raw
detector output.

### Five stages

```
DETECT  →  CLASSIFY  →  ROUTE  →  ACT or SURFACE  →  TRACK
(exists)   (new)        (new)     (new)              (new)
```

- **Detect** — existing code (`scripts/fql_alerts.py`,
  `scripts/probation_scoreboard.py`, `scripts/fql_watchdog.sh`,
  `scripts/fql_doctor.py`, watchdog state, etc.) emits a raw signal
- **Classify** — pipeline maps raw signal to a root-cause class +
  severity using `exception_classes.yaml`
- **Route** — pipeline routes the classified exception to the owning
  subsystem
- **Act or Surface** — owner applies class-specific auto-action OR
  emits to operator digest with classification + suggested action
- **Track** — pipeline tracks open exceptions until resolved;
  suppresses duplicate noise; reopens if recurrence detected

### Components (net new code)

- `scripts/exception_pipeline/orchestrator.py` — top-level scheduler/dispatcher
- `scripts/exception_pipeline/classifier.py` — raw signal → class mapping
- `scripts/exception_pipeline/router.py` — class → owner routing
- `scripts/exception_pipeline/closure_tracker.py` — open/closed lifecycle
- `scripts/exception_pipeline/digest_hook.py` — emits classified section into `operator_digest.py`
- `scripts/exception_pipeline/heartbeat.py` — central heartbeat file writer (used by all scheduled jobs)
- `scripts/classify_stale_strategies.py` — STRATEGY_BEHAVIOR sub-classifier (anchor case 2)
- 1 new launchd plist for the pipeline tick (every 15 min)
- Pipeline state files (see §3 Artifacts subsection below)

### State files

| File | Type | Updated by | Read by |
|------|------|-----------|---------|
| `research/data/exceptions/exception_log.jsonl` | append-only | every detection | weekly rollup, post-mortem |
| `research/data/exceptions/exception_state.json` | snapshot | open/close | digest, operator |
| `research/data/exceptions/exception_actions.jsonl` | append-only | every auto-action | weekly rollup, audit |
| `research/data/exceptions/exception_classes.yaml` | config (operator-edited) | operator only | classifier |
| `research/data/exceptions/heartbeats.json` | snapshot | every scheduled job | meta-monitor |

State files .gitignored except `exception_classes.yaml` (config) and
`exception_actions.jsonl` (audit trail) — same discipline as
`forge_promotion_candidates.json` in the kernel design.

### Single intake principle

After Phase E (full rollout), detectors emit to the pipeline only.
Operator-facing alert files (`_alerts.md`, etc.) become reads off the
pipeline state, not separate writes from each detector. This eliminates
the divergence problem (different detectors writing different surfaces
that drift apart). During phased rollout, both the old surfaces and the
pipeline output coexist — the pipeline is additive until proven.

---

## 2. Severity classes

Three orthogonal axes. An exception has one value on each.

### Routing class (where does it go?)

- **AUTO_RESOLVE** — pipeline takes action; no operator involvement;
  logged in `exception_actions.jsonl`
- **OPERATOR_REQUIRED** — needs human judgment; surfaced via digest with
  classification + suggested action
- **ESCALATE_IMMEDIATE** — critical; bypasses digest via existing
  `scripts/fql_alerts.py` (macOS notification)

### Root-cause class (what kind of issue?)

- **HARVEST_NOISE** — closed-family match, duplicate, low-quality intake
- **STRATEGY_BEHAVIOR** — staleness, kill-criteria, drift (sub-classifier
  resolves to DATA_BLOCKED / CONTROLLER_BLOCKED / QUIET / LOGIC_BLOCKED)
- **DATA_PIPELINE** — data freshness, ingestion failure, schema mismatch
- **INFRASTRUCTURE** — process health, gateway, watchdog, launchd
- **META_MONITORING** — monitoring-surface freshness, state-file drift,
  inconsistent reporting between layers
- **LANE_A_INTEGRITY** — anything touching live trading state. Always
  ESCALATE_IMMEDIATE; never AUTO_RESOLVE (by design)

### Severity (how urgent?)

- **INFO** — log only, no surface
- **WARN** — surface in next digest with classification
- **ALERT** — surface in next digest with action taken (or recommended action)
- **CRITICAL** — fire fql_alerts.py immediately + surface in next digest

The three axes combine: e.g., `(OPERATOR_REQUIRED, STRATEGY_BEHAVIOR,
ALERT)` for a stale strategy that classifier could not auto-resolve.

---

## 3. Class-specific auto-actions vs operator-required

The matrix below is the **policy table**. Stored in
`exception_classes.yaml` so it's operator-tunable without code change.

| Root-cause class | Default routing | Auto-action (if AUTO_RESOLVE) | Operator surface (if OPERATOR_REQUIRED) |
|------------------|-----------------|-------------------------------|----------------------------------------|
| HARVEST_NOISE / closed-family | AUTO_RESOLVE | Move note to `~/openclaw-intake/rejected/closed_family/`, write reason file, suppress alert | Only if note contains `addresses_failure_mode:` field → surface with classification "potential_failure_mode_address" |
| HARVEST_NOISE / duplicate | AUTO_RESOLVE | Reject in `harvest_engine.py` (already exists); silent | — |
| STRATEGY_BEHAVIOR / DATA_BLOCKED | AUTO_RESOLVE | Set `data_pipeline_gap=true` in registry, pause review clock per `docs/DATA_BLOCKED_STRATEGY_RULE.md` | WARN: "MGC-Long classified DATA_BLOCKED, clock paused" |
| STRATEGY_BEHAVIOR / CONTROLLER_BLOCKED | OPERATOR_REQUIRED | — | ALERT: "Controller blocking signals — investigate config" |
| STRATEGY_BEHAVIOR / QUIET | AUTO_RESOLVE if cadence sparse | Downgrade to HEALTHY_SLOW; clear stale flag | INFO if cadence non-sparse |
| STRATEGY_BEHAVIOR / LOGIC_BLOCKED | OPERATOR_REQUIRED | — | ALERT: "Strategy logic returning errors — investigate" |
| DATA_PIPELINE / data stale | AUTO_RESOLVE (with retry cooldown) | Re-run data refresh once; if successful → INFO; if fails 3× in 24h → ALERT | "Data refresh failed 3× for <asset>" |
| INFRASTRUCTURE / launchd agent crash | AUTO_RESOLVE | Kickstart once via existing watchdog logic; verify | If recovery fails → ESCALATE_IMMEDIATE |
| META_MONITORING / state file frozen | OPERATOR_REQUIRED first occurrence; ESCALATE_IMMEDIATE on second | — | "watchdog_state.json frozen >10min — verify state-write logic" |
| LANE_A_INTEGRITY / anything | ESCALATE_IMMEDIATE | None ever | Always operator |

### Override mechanism

Operator can override default routing for any class via
`exception_classes.yaml`:

```yaml
classes:
  harvest_noise.closed_family:
    routing: OPERATOR_REQUIRED   # downgrade auto-resolve while testing
  strategy_behavior.data_blocked:
    routing: AUTO_RESOLVE        # default
    auto_action_during_hold: true  # explicit hold-window opt-in
```

Override changes are append-logged to `exception_actions.jsonl` so the
operating posture is auditable.

---

## 4. Ownership boundaries

Each root-cause class is owned by one subsystem. Owner == the code path
that reasonably applies the auto-action. The pipeline routes; the owner
acts.

| Class | Owner subsystem | Owner code (existing or new) |
|-------|-----------------|------------------------------|
| HARVEST_NOISE | Harvest engine | `research/harvest_engine.py` (extend) |
| STRATEGY_BEHAVIOR | Stale strategy classifier | `scripts/classify_stale_strategies.py` (NEW) |
| DATA_PIPELINE | Data refresh | `scripts/start_forward_day.sh` chain (extend) |
| INFRASTRUCTURE | Watchdog | `scripts/fql_watchdog.sh` (already auto-recovers) |
| META_MONITORING | Doctor | `scripts/fql_doctor.py` (extend with freshness audit) |
| LANE_A_INTEGRITY | None — operator only | — |

The pipeline orchestrator does not contain class-specific logic. It
calls owner code via a stable interface
(`owner.handle_exception(exception)`). Owners can be changed/replaced
without touching the pipeline.

### Why one owner per class

Multiple owners == ambiguous responsibility == nothing happens. Today's
state: closed-family alerts fire from `fql_alerts.py`, but
`harvest_engine.py` doesn't know to act on them. Single owner per class
forces the wiring to be explicit.

---

## 5. Meta-monitoring rules

The principle: **any monitoring surface that's expected fresh must have
a freshness check. No exceptions.** This catches issue #3 (watchdog
state frozen) systemically, not as a one-off cross-check.

### Heartbeat discipline

Every scheduled job (claw-control-loop, daily-research, watchdog,
forward-day, weekly-research, source-helpers, twice-weekly-research,
operator-digest, treasury-rolldown-monthly, and the new pipeline tick)
writes a heartbeat to `research/data/exceptions/heartbeats.json` on
every run, not only on state change:

```json
{
  "claw-control-loop": {"last_run": "2026-04-17T14:00:00-04:00", "outcome": "OK", "next_expected": "2026-04-17T14:30:00-04:00"},
  "watchdog": {"last_run": "2026-04-17T14:25:00-04:00", "outcome": "OK", "next_expected": "2026-04-17T14:30:00-04:00"},
  ...
}
```

`fql_doctor.py` runs the freshness audit hourly and emits
META_MONITORING exceptions for any heartbeat where
`now - last_run > next_expected + grace_window`.

### State-file freshness rules

For state files expected to be fresh, the pipeline enforces freshness
SLOs. SLO violation → META_MONITORING exception:

| File | Freshness SLO | Owner |
|------|---------------|-------|
| `watchdog_state.json` | ≤ 10 min | watchdog |
| `data_update_state.json` | ≤ 30 min during weekday business hours | data refresh |
| `account_state.json` | ≤ 24h | forward day |
| `forge_kernel_state.json` (when built) | ≤ 30 min | kernel orchestrator |
| `exception_state.json` | ≤ 60 min | pipeline orchestrator |

State-file `as_of` field convention: every snapshot state file MUST
contain a top-level `as_of` ISO 8601 timestamp written by the writer,
not inferred from mtime. mtime + as_of mismatch → META_MONITORING
exception (silent state writer corruption).

### The "who watches the watchdog" rule

`fql_doctor.py` watches the watchdog. The pipeline watches `fql_doctor.py`
(via heartbeat + freshness SLO on the doctor's own report file). The
operator watches the pipeline (via digest). Each layer is watched by the
next, with no leaf node unwatched.

If the pipeline itself stalls, the watchdog catches it (kernel
heartbeat check is identical to claw-control-loop check). Mutual
monitoring closes the loop.

---

## 6. Hold-window / SAFE_MODE behavior

### During hold (2026-04-14 → 2026-05-01)

Per `docs/HOLD_STATE_CHECKLIST.md`, the hold restricts Lane A surface
changes. Auto-actions are evaluated against this principle:

> **During hold, auto-actions are permitted ONLY for classification and
> clock-control style actions. Auto-actions are NEVER permitted for
> anything that changes Lane A governance, promotion state, or archive
> state — those remain operator-only regardless of class.**

Per-class application:

| Class | Permitted during hold? | Reasoning |
|-------|------------------------|-----------|
| HARVEST_NOISE auto-reject | YES | No Lane A surface; reversible (rejected/ folder); pre-registry, so no governance touched |
| DATA_PIPELINE auto-retry | YES | Operational, not strategic |
| STRATEGY_BEHAVIOR / DATA_BLOCKED — *classification + clock pause only* | YES | Aligns with `DATA_BLOCKED_STRATEGY_RULE.md`; registry field append, no status change |
| STRATEGY_BEHAVIOR / DATA_BLOCKED — promotion / archive / status change | NO during hold (or post-hold without operator) | Lane A governance surface |
| STRATEGY_BEHAVIOR / QUIET → HEALTHY_SLOW downgrade | NO during hold | Status change = Lane A surface |
| INFRASTRUCTURE auto-recovery | YES | Watchdog already does this |
| META_MONITORING surfacing | YES | Detection-only, no action |
| LANE_A_INTEGRITY | NEVER auto-acts (regardless of hold) | By design |

The pipeline reads `docs/HOLD_STATE_CHECKLIST.md`'s active flag (or a
parallel `state/hold_active.json`) and gates auto-actions accordingly.

### During SAFE_MODE (watchdog flagged a critical issue)

When `watchdog_state.json.safe_mode = true`:

- All auto-actions pause EXCEPT INFRASTRUCTURE (which is what's trying to recover)
- Pipeline becomes detection + classification only; everything surfaces to operator with classification
- Pipeline auto-resumes when SAFE_MODE clears
- Mirrors the Forge kernel's SAFE_MODE behavior (see kernel design §2 general pause rule) — same principle, different subsystem

### Treasury-Rolldown verification carveout (2026-04-30 → 2026-05-02)

Same calendar pause as the Forge kernel — operator attention belongs to
Lane A during this window. Pipeline runs in detection-only mode, no
auto-actions, no digest noise.

---

## 7. Phased rollout (post-checkpoint)

Build is **not** authorized during the hold. Sequence after May 1
checkpoint clears + Treasury-Rolldown verification carveout ends
2026-05-02. Each phase mirrors the Forge kernel's discipline pattern.

**Phase A (week 1 post-hold) — meta-monitoring foundation:**
1. Build `heartbeat.py` and update all 9+ scheduled jobs to write heartbeats every run
2. Update `fql_watchdog.sh` to write heartbeat every run (not only on state change)
3. Add freshness audit to `fql_doctor.py`
4. **This phase fixes Issue #3 (watchdog freshness) entirely** and is a prerequisite for everything else — without reliable heartbeats, the pipeline can't trust its inputs

**Phase B (week 2–3) — read-only classifier (no actions):**
5. Build pipeline orchestrator + `exception_log.jsonl` + `exception_classes.yaml`
6. Wire classifier to read existing detector outputs (`fql_alerts.py` output, `probation_scoreboard.py` output, watchdog state)
7. Run for 14 days classifying every alert into root-cause class WITHOUT taking any action — operator reviews classification quality. Surface classifications in digest as additional context next to existing alerts

**Phase C (week 4) — HARVEST_NOISE auto-action:**
8. Wire `harvest_engine.py` auto-reject for closed-family matches
9. **This phase fixes Issue #1 (closed-family alerts)**
10. Lowest-risk auto-action class (no Lane A surface, easy to reverse via rejected/ folder). Watch for false-rejects for 7 days

**Phase D (week 5–6) — STRATEGY_BEHAVIOR sub-classifier:**
11. Build `classify_stale_strategies.py`
12. Apply DATA_BLOCKED auto-action only (registry field + clock pause)
13. Surface CONTROLLER_BLOCKED, LOGIC_BLOCKED, QUIET classifications to operator
14. **This phase fixes Issue #2 (MGC-Long stale)** at the DATA_BLOCKED level
15. Watch for misclassification for 14 days; QUIET auto-downgrade enabled in Phase D+7 if no false positives

**Phase E (week 7+) — broader auto-action:**
16. Add DATA_PIPELINE auto-retry
17. Add closure tracker recurrence detection
18. Migrate operator-facing alert files to read off pipeline state (single intake)
19. Old detector surfaces remain as fallback for 30 days, then deprecated

### Phase stop conditions

Halt (do not advance) if:

- New unexpected exception class appears
- False-positive auto-reject rate >5% in any class
- Operator overrides classifier decisions >20% of the time
- Pipeline tick heartbeat stalls
- Daily compute budget for pipeline >30 min wallclock

Halt → revise design → resume from same phase.

### Crash / restart recovery

Same pattern as Forge kernel: cycle ID per pipeline tick, in-flight
exceptions marked INTERRUPTED on restart, no automatic retry, schema
re-validation, lock file to prevent concurrent orchestrators.

---

## 8. Anchor case walk-throughs

The three issues that prompted this design, traced through the
pipeline:

### Case 1: closed-family harvest match

- **Detect:** `fql_alerts.py:179` pattern-matches note against `harvest_config.yaml.targeting.high_bar_families`
- **Classify:** root-cause `HARVEST_NOISE.closed_family`
- **Route:** owner = `harvest_engine.py`
- **Act:** check note for `addresses_failure_mode:` field. If absent → AUTO_RESOLVE: move to `~/openclaw-intake/rejected/closed_family/<note>` + write reason file. If present → OPERATOR_REQUIRED with classification "potential_failure_mode_address"
- **Track:** logged to `exception_actions.jsonl`. If same note pattern recurs from same source ≥3 times in 7d → ESCALATE_IMMEDIATE (Claw is generating noise — source-side issue)
- **Result vs today:** zero operator alerts for the 5 routine closed-family matches; 0–1 operator alerts for borderline cases. Today: 5 alerts × 17 days = 85 alert-instances unresolved

### Case 2: stale probation strategy

- **Detect:** `probation_scoreboard.py:76` flags MGC-Long STALE on day 29
- **Classify:** root-cause `STRATEGY_BEHAVIOR` → call `classify_stale_strategies.py` sub-classifier
  - Check data freshness for MGC: if latest bar > 24h old → DATA_BLOCKED
  - Else: run sanity backtest on last 30d. If backtest expects trades but real=0 → CONTROLLER_BLOCKED. If expects 0 → QUIET. If errors → LOGIC_BLOCKED
- **Route:** owner = `classify_stale_strategies.py`
- **Act:** per sub-class (see §3 matrix). For DATA_BLOCKED: AUTO_RESOLVE — set `data_pipeline_gap=true`, pause review clock, surface WARN with classification. For others: OPERATOR_REQUIRED with classification + suggested action
- **Track:** open exception until cause is resolved (data flows again, or controller fix, etc.). Recurrence in 60d → escalate
- **Result vs today:** classification + auto-clock-pause happens day 29. Today: 31 days unresolved, "Investigate: controller blocking? Data feed? Strategy logic?" — operator does the routing manually

### Case 3: watchdog state file frozen

- **Detect:** Phase A `fql_doctor.py` freshness audit. `watchdog_state.json.as_of` > 10 min old, but `heartbeats.json.watchdog.last_run` is recent → inconsistency
- **Classify:** root-cause `META_MONITORING.state_file_frozen`
- **Route:** owner = `fql_doctor.py`
- **Act:** OPERATOR_REQUIRED with classification "watchdog running but state writer not firing — likely save_state() bug or state-change-only write". If recurs in 24h → ESCALATE_IMMEDIATE
- **Track:** open until state file becomes fresh
- **Prevention:** Phase A change makes watchdog write heartbeat every run, so state-only-on-change is no longer the failure mode. The classification path is for residual / regression detection
- **Result vs today:** issue caught within 1 hour of first stale tick. Today: caught only because human noticed mtime; could have been frozen for weeks silently

---

## 9. v1.1 evidence-driven refinements

Implement v1 with placeholder values; refine after 30+ days of pipeline data:

1. **Closed-family auto-reject false-positive threshold (5%)** — may want stricter (2%) if false rejects are catching real ideas
2. **Heartbeat freshness grace_window (default 2× expected interval)** — may need per-job tuning
3. **STRATEGY_BEHAVIOR sub-classifier sanity-backtest window (default 30d)** — may need per-strategy tuning based on cadence
4. **Recurrence detection window (3 occurrences in 7d)** — observed data may suggest different threshold per class
5. **DATA_PIPELINE auto-retry cap (3 in 24h)** — may need lower if retries thrash, higher if transient failures are common

---

## 10. v2 open questions

- **Learned classifier** (ML on alert outcomes → classification) — needs labeled data first
- **Auto-resolution for CONTROLLER_BLOCKED** (config diff + apply) — high-risk, defer
- **Cross-class correlation** (e.g., DATA_PIPELINE + STRATEGY_BEHAVIOR co-occurrences) — needs longitudinal data
- **Operator-action telemetry** (what does operator do when surfaced; close the feedback loop) — privacy implications
- **Auto-retry policy for OPERATOR_REQUIRED items** — when should pipeline re-surface stale operator items?

---

## 11. Operator decisions (RESOLVED 2026-04-16)

1. **Auto-action permitted during hold for HARVEST_NOISE?** — **YES.** No Lane A surface; reversible via rejected/ folder.
2. **Auto-action permitted during hold for STRATEGY_BEHAVIOR / DATA_BLOCKED?** — **YES, but bounded:** classification + clock-pause actions only. NO for promotion, archive, or any status change that touches Lane A governance — those remain operator-only regardless of hold state. See §6 principle statement.
3. **Phase A heartbeat update — coordinated or per-job rollout?** — **Single coordinated change.** Foundational monitoring hygiene; better done coherently than patchwork.
4. **`exception_state.json` tracked in git?** — **NO.** High churn, low audit value. `exception_actions.jsonl` is the audit trail (gitignored locally — operator can promote selected actions to git if needed).

---

## Appendix A — Compatibility with existing principles

- **Continuous discovery, selective deployment** — pipeline reduces operator toil on the discovery side; selective deployment seam preserved (LANE_A_INTEGRITY never auto-acts)
- **Elite standard** — auto-rejecting closed-family noise enforces the elite filter at machine speed instead of bleeding through to operator review
- **Lane A/B operating doctrine** — pipeline auto-actions are Lane B operations; LANE_A_INTEGRITY is the explicit seam
- **Doc discipline** — `exception_classes.yaml` IS the executable version of doc playbooks like `DATA_BLOCKED_STRATEGY_RULE.md` (codified, not just written)
- **IP protection** — pipeline state .gitignored except `exception_classes.yaml` (config) and `exception_actions.jsonl` (audit trail)
- **Operating discipline** — pipeline does not introduce a new build lane; it codifies existing manual decision rules. Aligns with "do not build new infrastructure unless scorecard flags an issue" — issue is now flagged

---

## Appendix B — Relationship to Forge kernel design

Sister documents:

- `docs/fql_forge/kernel_design.md` — always-on Lane B research engine (continuous discovery)
- `docs/exception_pipeline_design.md` (this doc) — operational classifier-router-actioner (continuous handling)

| Concern | Forge kernel | Exception pipeline |
|---------|--------------|--------------------|
| Domain | Strategy discovery + validation (Lane B research) | Operational alerts + auto-resolution (whole system) |
| Triggered by | Cadence (continuous) | Detector signal |
| Lane A protection | Hard prohibitions in kernel guardrails | LANE_A_INTEGRITY class always escalates, never auto-acts |
| Operator surface | Promotion candidates + integrity flags | Classified exceptions + suggested actions |
| Hold behavior | Runs hot during hold; no Lane A change | Auto-actions gated per class during hold |
| SAFE_MODE behavior | Auto-pauses on watchdog SAFE_MODE | Detection-only during SAFE_MODE except INFRASTRUCTURE |
| Build phase | Phased A→D (5 weeks post-hold) | Phased A→E (7 weeks post-hold) |
| Heartbeat dependency | Will register with central heartbeat (Phase A of pipeline) | Provides the central heartbeat |

The pipeline's Phase A (heartbeat foundation) is a prerequisite for the
kernel's full integrity tracking. Sequence both builds so pipeline Phase
A completes before kernel Phase D.

The two designs together convert FQL into:
- **Continuous research** (kernel) on the discovery side
- **Continuous handling** (pipeline) on the operational side

Both gated at Lane A; both phased; both designed to surface only what
genuinely requires human judgment.
