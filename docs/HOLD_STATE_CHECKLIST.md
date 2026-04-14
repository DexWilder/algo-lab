# Hold State Checklist

**Current hold:** 2026-04-14 → 2026-05-01
**Expiry trigger:** Treasury-Rolldown-Carry-Spread first live monthly rebalance (2026-05-01, or next business day if holiday) + checkpoint outcome per `docs/MAY_1_CHECKPOINT_TEMPLATE.md`.

**Governance authority:** `CLAUDE.md` is the operating authority during hold.
This checklist governs the hold window itself, not strategy-level
decisions. Individual strategy gates continue to live in their
authority docs (`docs/PROBATION_REVIEW_CRITERIA.md`,
`docs/XB_ORB_PROBATION_FRAMEWORK.md`, `docs/ELITE_PROMOTION_STANDARDS.md`).

---

## Frozen during hold

These must not change until the hold expires cleanly.

### Runtime code
- `engine/**/*.py` — no edits (strategy_universe status guard, backtest, metrics, scoring)
- `research/live_drift_monitor.py` — no edits (BASELINE, tier logic, loaders)
- `research/fql_research_scheduler.py` — no new jobs, no cadence changes
- `research/system_watchdog.py` — no edits
- `scripts/fql_watchdog.sh` — no edits
- `scripts/run_fql_forward.sh` — no edits
- `run_forward_paper.py` — no edits
- `strategies/**/*.py` — no edits to strategy logic
- `research/run_treasury_rolldown_spread.py` — no edits

### Strategy lifecycle state
- No strategy promotions (probation → core)
- No strategy demotions (core → probation / probation → archived)
- No `status` field changes in the registry, except to record data-state transitions per `docs/DATA_BLOCKED_STRATEGY_RULE.md`
- No `controller_action` changes
- No new strategies added to the registry

### Portfolio composition
- The 10-strategy intraday runner universe + 1 out-of-band strategy is the locked portfolio
- No new research lanes opened (FX, STRUCTURAL, or any other gap)
- No re-probation decisions on archived/rejected strategies

### Launchd agents
- No new agents added
- No existing agents modified or unloaded
- Already-loaded at hold entry (10 agents listed in `docs/GOLDEN_SNAPSHOT_2026-04-14.md`)

### Authority documents
- `CLAUDE.md` content frozen except for the exception below
- `docs/PROBATION_REVIEW_CRITERIA.md` frozen
- `docs/XB_ORB_PROBATION_FRAMEWORK.md` frozen
- `docs/ELITE_PROMOTION_STANDARDS.md` frozen
- `research/data/strategy_registry.json` frozen on `status` / `controller_action` / `promoted_date` / `lifecycle_stage` fields

---

## Allowed during hold

These are explicitly not hold breaches.

### Documentation
- New markdown docs under `docs/` that are read-only reference material (e.g., this file, golden snapshot, checkpoint template, data-blocked rule, spread-log audit procedure)
- Typo/clarity edits to existing docs that do not change policy
- Appending to historical records (commit trail, changelog)

### Data operations
- Data refresh via existing pipelines (daily databento fetch, backfills via `scripts/update_daily_data.py --symbol X`)
- Fixing data pipeline gaps (e.g., the MYM SYMBOLS dict omission fix from 2026-04-14 was in-hold but was a data-pipeline repair, explicitly allowed)

### Registry hygiene
- Adding structured annotation fields that describe **state**, not **policy** — e.g., `data_pipeline_gap`, `review_clock_start_source`, `notes` appendages documenting observed facts
- Correcting field typos or normalizing field values

### Observation
- Running reporting scripts (drift monitor, watchdog, scorecards) read-only
- Inspecting logs
- Generating snapshots

### Preparation without execution
- Pre-writing post-hold documents (e.g., May 1 verification template, checkpoint template, hardening queue scope docs)
- Planning the post-checkpoint hardening queue (3 → 5 → 1 → 2 → 4)

---

## Hold breach conditions

Any of the following ends the hold and requires explicit re-authorization from the operator before resuming:

### Code changes to frozen surfaces
- Any commit that modifies a file listed under "Frozen during hold § Runtime code"
- Any commit that adds a new scheduler entry
- Any commit that adds a new launchd agent
- Any commit that modifies strategy logic

### Lifecycle transitions
- Any commit that changes a `status`, `controller_action`, `promoted_date`, or `lifecycle_stage` field in the registry without corresponding authorization
- Any commit that opens a new research lane (creates `strategies/<new>` or `research/specs/<new>.md` for production candidacy)
- Any re-probation of archived/rejected strategies beyond Treasury-Rolldown (which was already completed at hold entry)

### Monitor or policy changes
- Any edit to BASELINE in `live_drift_monitor.py`
- Any edit to tier logic, severity classification, or framework docs
- Any edit to `DEAD_STATUSES` or the status guard in `engine/strategy_universe.py`

### Premature checkpoint actions
- Taking a decision based on Treasury-Rolldown's May 1 outcome before the verification checklist (`docs/MAY_1_TREASURY_ROLLDOWN_VERIFICATION.md`) is actually executed
- Opening the hardening queue before the checkpoint decision is rendered via `docs/MAY_1_CHECKPOINT_TEMPLATE.md`

---

## Hold-window discipline

The hold is a control mechanism, not a passive wait. During this window:

- Use the time to remove ambiguity (more docs, clearer conventions, pre-wired decisions)
- Use the time to inspect and observe (run read-only reports; build confidence in the current state)
- Do NOT use the time to invent new trading logic
- Do NOT use the time to "just improve" runtime code
- Do NOT use the time to pre-implement the hardening queue

If a genuine operational emergency surfaces (e.g., a new data-pipeline
gap on a different symbol; a scheduler failure; a SAFE_MODE trigger),
it is acceptable to fix it in-hold using the same pattern as the MYM
pipeline fix: document the incident, apply the smallest correct fix,
commit with a clear message, update relevant records. Emergency
handling is not a breach — pretending the hold is broken is.

---

## Exit criteria

The hold expires cleanly when **all** of the following are true:

1. Treasury-Rolldown-Carry-Spread first live monthly rebalance has fired on or after 2026-05-01
2. The verification checklist in `docs/MAY_1_TREASURY_ROLLDOWN_VERIFICATION.md` has been executed
3. A decision has been rendered via `docs/MAY_1_CHECKPOINT_TEMPLATE.md`, producing exactly one of:
   - Remain in stable state
   - Open fresh FX/STRUCTURAL design lane
   - Resume hardening queue
   - Do not expand; investigate anomaly first

Until all three are true, the hold remains in effect.

---

## Current hold status indicator

Check this value before every commit during the hold window:

- **HOLD ACTIVE** — all frozen surfaces remain unchanged since 2026-04-14; the commit under consideration is in the "Allowed during hold" category
- **HOLD BREACH PENDING** — the commit under consideration touches a frozen surface; requires explicit operator re-authorization

If a commit is made under HOLD BREACH PENDING without re-authorization, that is itself a breach and should be reverted or re-scoped.

---

*This document is itself subject to the "Allowed during hold" category (markdown under docs/). It may be amended during the hold window to clarify rules that were ambiguous, but its three main sections — Frozen / Allowed / Breach — must not be weakened without an explicit operator decision.*
