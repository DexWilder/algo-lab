# Authority Ladder

**One-page standing reference.** Every FQL component's decision-weight
is named here. No component's authority is inferred; all are explicit.

## Purpose

As FQL grows, the dominant failure mode shifts from bad auto-actions
to *advisory-only drift* (see `feedback_advisory_drift` memory + smell
#1 in `bad_automation_smells.md`). The cure is explicit authority:
every component carries a tier label, and consuming output without
respecting that tier is a process failure, not an accident.

This ladder answers three operator questions:

1. Can I act on this component's output without thinking?
2. Does this component need corroboration before action?
3. What tier does a new component ship at by default?

## The four tiers

### Tier 0 — ADVISORY

**Authority:** Informational only. May surface in digests, logs, or
dashboards but MUST NOT drive decisions or auto-actions.

**Default tier for:** new components, untested detectors, components
with unmeasured precision, anything whose failure mode has not been
analyzed.

**Operator rule:** acting on output is the operator's decision, not
the component's. Attribution for any resulting action lands on the
operator, not the component.

### Tier 1 — VERIFIED-INFORMATIONAL

**Authority:** Output has measured quality (FP/TP rate, accuracy,
coverage, or equivalent) recorded in a dated artifact. Operator can
integrate into normal judgment without re-verifying each output.

**Promotion from T0 requires:** at least one batch validation against
labeled truth, documented in a commit or report file. "We tested this
in conversation" is not sufficient.

**Operator rule:** trust general direction. Case-by-case manual
confirmation still required before any reversible action.

### Tier 2 — DECISION-GRADE

**Authority:** Trusted enough to drive automated actions that are
reversible and within Lane B scope. Consumed directly by exception
pipeline auto-actions or Forge kernel decisions.

**Promotion from T1 requires:** 30+ days of operation with stable
precision, edge-case coverage documented, failure recovery path
tested, integrity metrics green.

**Operator rule:** component acts autonomously within its scope.
Operator reviews aggregate behavior (weekly rollup), not individual
outputs.

### Tier 3 — NEVER-ALONE

**Authority:** Regardless of measured trust, CANNOT be the sole
authority for an action. Requires at least one independent
corroborating source: a second detector with different logic, human
review, backtest/validation battery, or external ground truth.

**Mandatory for:** Lane A surface changes, irreversible state
mutations, anything touching `state/`, `engine/strategy_universe.py`,
portfolio composition, or strategy status.

**Operator rule:** no single-source decision, ever, even if all
sources are Decision-Grade individually. T3 is a *category*, not a
trust level — components live here because of what they touch, not how
well they perform.

## Current component classification (2026-04-17)

| Component | Tier | Notes / basis |
|-----------|------|---------------|
| `state/account_state.json` edits | T3 | Lane A surface — operator + checkpoint only |
| `engine/strategy_universe.py` probation list | T3 | Lane A governance |
| `research/data/portfolio_activation_matrix.json` | T3 | Lane A composition |
| Strategy registry `status` field changes | T3 | Promotion/demotion is Lane A |
| `research/data/strategy_registry.json` status write paths | T3 | Only the `status` field; appends are T2 |
| `scripts/fql_watchdog.sh` process recovery | T2 | Reversible infrastructure action; already auto-kickstarts |
| `research/harvest_engine.py` dedup | T2 | Objective content-hash matching |
| Registry append (new idea, no status) | T2 | Purely additive; reversible via commit |
| `research/validation/run_validation_battery.py` | T2 | 6-gate precision measured and documented |
| `research/batch_first_pass.py` classifier (REJECT verdict) | T2 | Concentration + PF rules well-specified |
| `research/batch_first_pass.py` classifier (SALVAGE/MONITOR/ADVANCE) | T1 | Operator confirms edge cases |
| `scripts/probation_scoreboard.py` aging | T1 | Evidence-ratio logic sound; STALE→action needs operator |
| `scripts/operator_digest.py` | T1 | Aggregator — tier inherited from weakest source it reads |
| Claw cluster review reports | T1 | Track record confirmed 2026-04-17 vs detector (8/8 agreement with ground truth) |
| `scripts/fql_doctor.py` health | T1 | Log-based; drops to T0 if freshness SLO goes untested |
| `scripts/fql_alerts.py` closed-family detector | T0 | **Demoted 2026-04-17.** 8/8 FP on batch spot-check. Replacement queued post-May-1. |
| Any new detector before measurement | T0 | Default — no exceptions |
| Factory SALVAGE/MONITOR/ADVANCE suggestions | T0 | Operator triage is the decision layer |
| Forge candidate generator outputs | T0 | Enqueue for backtest, not for promotion |
| `scripts/fql_alerts.py` non-closed-family checks | T0 | Not yet batch-validated; inherited default |

## Tier-movement rules

**Promotion (T0 → T1 → T2):**
- Requires evidence: measured precision on actual data, not inferred from design.
- Must be recorded in a dated doc or commit. "We tested this" without a record keeps the component at its existing tier.
- Promotion is an explicit decision with operator approval.

**Demotion (down the ladder):**
- Any observed failure mode not explained by known limitations → demote one tier immediately, document.
- Pending investigation counts as demotion — "we're not sure yet" is T0 by default.
- Demotion does NOT wait for a rollup; do it when evidence lands. (Today's closed-family demotion was same-day, not queued for Friday.)

**T3 is sticky:**
- Components never leave T3 based on measured quality alone. T3 is a category (Lane A surfaces + irreversible actions), not a trust tier.
- Moving something into T3 requires operator approval and a documented reason.

## Default tier for new components

**All new components ship at T0.** No exceptions.

This is not pessimism; it is prerequisite discipline. The time between
"component exists" and "component has measured precision" is exactly
when silent drift accumulates. T0 default makes that interval safe.

A component can move to T1 on its ship day *if* the shipping commit
includes measured precision on labeled data. The order is: measure
first, then classify. Never reverse.

## Relationship to other FQL documents

- **`docs/bad_automation_smells.md`** smell #1 (advisory-only-treated-as-decision) becomes mechanically impossible when every component carries an explicit tier.
- **`docs/exception_pipeline_design.md`** Phase C HARVEST_NOISE auto-reject requires its source detector to be T1+; closed-family detector is T0 today, which structurally blocks Phase C build. Pipeline Phase C gate = detector promotion to T1.
- **`docs/fql_forge/kernel_design.md`** hard-prohibitions list maps directly to T3 components — kernel code cannot touch them.
- **`feedback_advisory_drift` memory** is the standing watch; this ladder is its enforcement mechanism.
- **`CLAUDE.md`** hold-window allowed actions correspond to editing T0/T1 docs and components; T2/T3 changes require checkpoint authority.

## Growth discipline

This ladder is a living doc:

- Every new component added to FQL gets classified before shipping (T0 minimum).
- Every promotion/demotion recorded with date + evidence in the table above.
- Weekly rollup skims the table: any T0 component with no path to T1? Any T2 showing failures that warrant demotion?

**Out of scope for v1 (deferred to v1.1):**
- Numeric precision thresholds per tier (e.g., "T2 requires FP < 0.05"). Set after observing which components earn promotion and what evidence justified it.
- Automated tier-verification audit. Manual review is sufficient for current component count (~20).

## Authority-ladder usage during hold

During hold periods (2026-04-14 → 2026-05-01 is current), allowed-action
scope maps cleanly to tiers:

- **Safe hold-window work:** editing T0/T1 docs, adding new T0 components, re-measuring component precision, batch-reviewing T0 outputs (as done today with closed-family detector).
- **Not allowed during hold:** T2 auto-action wiring, T3 surface changes, tier promotions requiring 30+ day evidence windows that span checkpoint, changing the ladder itself.
- **Always allowed regardless of hold:** demotions when evidence lands, documentation of current state, governance notes.

This is the practical answer to "what can I work on during hold without
breaking discipline" — check the ladder.
