# May 1 Stale Probation Batch Review

**Purpose:** Companion doc to `docs/MAY_1_CHECKPOINT_TEMPLATE.md`. When
non-XB-ORB probation strategies show zero forward trades at checkpoint,
this template reviews them as a batch — same fields, side-by-side — and
produces one disposition per strategy plus one overall batch pattern
finding.

**When to run:** during May 1 checkpoint, after Treasury-Rolldown
verification completes and before the main checkpoint template's
decision section. Only run if at least one non-XB-ORB probation
strategy shows zero forward trades as of checkpoint date. Skip if all
non-XB-ORB probation strategies have trade evidence.

**Why batch, not case-by-case:** as of 2026-04-17 scorecard, 4
non-XB-ORB probation strategies show 0 forward trades simultaneously.
Case-2 of the exception pipeline diagnosis is systemic, not isolated
to any single strategy. Reviewing them together surfaces patterns
(all data-blocked? all quiet? split?) that case-by-case review would
miss. Also cuts review time — shared fields filled once per column
instead of N times.

**Relationship to other docs:**
- `docs/DATA_BLOCKED_STRATEGY_RULE.md` — data-blocked vs quiet distinction
- `docs/PROBATION_REVIEW_CRITERIA.md` — non-XB-ORB promotion/downgrade thresholds
- `docs/exception_pipeline_design.md` — Phase D STRATEGY_BEHAVIOR sub-classifier; this manual review is the operator-grade equivalent until Phase D ships
- `docs/authority_ladder.md` — this review is T1 by design (operator performs it)

---

## Step 1 — Refresh the strategy list

At checkpoint time, run:

```bash
python3 research/weekly_scorecard.py --save
```

Read section 2 (PROBATION PROGRESS). List here every **non-XB-ORB**
probation strategy with **0 forward trades** since entry. Add/remove
rows in the side-by-side table to match.

**As of 2026-04-17 anchor (may change by May 1):**
1. DailyTrend-MGC-Long — MGC, trend, daily bars, sparse
2. MomPB-6J-Long-US — 6J, momentum, sparse
3. PreFOMC-Drift-Equity — equity, event-driven, sparse
4. TV-NFP-High-Low-Levels — MNQ, event-driven, sparse

---

## Step 2 — Side-by-side review table

Fill one column per strategy. Rows are the common review fields. If
row applies to only some strategies, mark the rest `n/a`.

| Field | DailyTrend-MGC-Long | MomPB-6J-Long-US | PreFOMC-Drift-Equity | TV-NFP-High-Low-Levels |
|-------|---------------------|------------------|----------------------|------------------------|
| Asset | MGC | 6J | ES/MES | MNQ |
| Archetype | trend / sparse | momentum / sparse | event-driven / sparse | event-driven / sparse |
| Probation entry date (from registry) | | | | |
| Days in probation at checkpoint | | | | |
| Expected trade cadence (EXPECTED_FREQ or registry) | | | | |
| Trades observed since entry | 0 | 0 | 0 | 0 |
| Last trade date / "never" | | | | |
| Data feed fresh? (mtime of relevant `data/processed/*.csv` < 2× refresh cadence) | | | | |
| Data freshness class (per `DATA_BLOCKED_STRATEGY_RULE.md`) | ☐ normal ☐ data-blocked-open ☐ data-blocked-resolved ☐ degraded | same | same | same |
| Signal-generation check (did strategy logic produce signals that controller blocked, zero signals, or unable to verify?) | | | | |
| Applicable event window in review period? (for event-driven strategies: did CPI/NFP/FOMC fire between promotion and checkpoint?) | n/a | n/a | | |
| **Classification** (pick one) | ☐ DATA_BLOCKED ☐ CONTROLLER_BLOCKED ☐ QUIET (sparse, in-expectation) ☐ LOGIC_BLOCKED (errors) ☐ INSUFFICIENT_INFO | same | same | same |
| Governance doc for disposition | `PROBATION_REVIEW_CRITERIA.md` | `PROBATION_REVIEW_CRITERIA.md` | `PROBATION_REVIEW_CRITERIA.md` | `PROBATION_REVIEW_CRITERIA.md` |
| **Disposition** (pick one) | ☐ retain ☐ mark DATA_BLOCKED (clock pause) ☐ downgrade to HEALTHY_SLOW ☐ archive ☐ defer to next checkpoint ☐ investigate further | same | same | same |
| Disposition reason (one sentence) | | | | |

---

## Step 3 — Cross-strategy pattern analysis

After filling the side-by-side table, answer:

| Question | Answer |
|----------|--------|
| How many classified DATA_BLOCKED? | |
| How many CONTROLLER_BLOCKED? | |
| How many QUIET? | |
| How many LOGIC_BLOCKED? | |
| How many INSUFFICIENT_INFO? | |
| Dominant class | |
| Shared root cause (if any)? — e.g., common data feed, common strategy component, common promotion date | |
| Shared asset class / session / event-type? | |

**Pattern verdict (pick one):**

- ☐ **Systemic cause** — shared root; fix upstream once and the whole batch resolves
- ☐ **Coincidental cluster** — 4 independent quiet periods; no shared mechanism
- ☐ **Mixed** — some data-blocked, some quiet; disposition varies per strategy
- ☐ **Insufficient information** — need investigation before classifying

**If systemic:** the upstream fix should be scoped and logged as a follow-up item; batch disposition deferred until the fix is verified.

---

## Step 4 — Hold-window compliance check

Per `docs/HOLD_STATE_CHECKLIST.md` + `docs/authority_ladder.md` T3
class: demotions and archives are Lane A governance surfaces requiring
checkpoint authority.

| Action | Permitted as part of this checkpoint? |
|--------|---------------------------------------|
| Retain (no change) | ✓ always |
| Mark DATA_BLOCKED + set `data_pipeline_gap` field + pause review clock | ✓ per `DATA_BLOCKED_STRATEGY_RULE.md` (registry field add, not status change) |
| Downgrade to HEALTHY_SLOW (status change) | ✓ with checkpoint authority |
| Archive (status change) | ✓ with checkpoint authority |
| Defer to next checkpoint | ✓ always |
| Investigate further (no immediate disposition) | ✓ always |

DATA_BLOCKED classification is the ONE disposition that can happen
outside a checkpoint — appending a registry field is T2 authority and
is allowed during hold. Every other status change waits for checkpoint.

---

## Step 5 — Batch outcome summary

| Strategy | Classification | Disposition | Reason |
|----------|----------------|-------------|--------|
| DailyTrend-MGC-Long | | | |
| MomPB-6J-Long-US | | | |
| PreFOMC-Drift-Equity | | | |
| TV-NFP-High-Low-Levels | | | |

**Batch-level decision (pick one):**

- ☐ All retain — classifications explain silence; no governance action
- ☐ Mixed dispositions per table above
- ☐ At least one archive — non-trivial governance outcome; reflects in portfolio truth table
- ☐ Investigation required before any disposition — batch deferred

**Rationale (one paragraph):**

---

## Step 6 — Post-review actions

1. **Update each strategy's registry entry** with the classification field (`data_pipeline_gap` for DATA_BLOCKED, or `status` change for downgrade/archive).
2. **Record batch verdict in `docs/PORTFOLIO_TRUTH_TABLE.md`** probation section.
3. **Feed outcome into main checkpoint decision** — the batch-level decision informs the "Remain / Open lane / Resume hardening / Investigate" choice in `docs/MAY_1_CHECKPOINT_TEMPLATE.md` Decision output. Any archive or "investigation required" verdict routes to the "Investigate anomaly" decision branch.
4. **If any LOGIC_BLOCKED:** file a follow-up investigation task — strategy code returning errors needs engineering investigation, not just governance disposition.
5. **If any INSUFFICIENT_INFO:** extend defer period by one checkpoint cycle; do not force a decision without evidence.
6. **Commit this filled-in template** to the repo with message `May 1 stale probation batch review: [batch-level decision summary]`.

---

## Reviewer attestation

- **Reviewer:** _________________________
- **Checkpoint date executed:** _________________________
- **Number of strategies reviewed:** _________________________
- **Batch-level decision:** _________________________

---

*Purpose: prevent case-by-case review from missing systemic patterns.
4 strategies at 0 trades simultaneously is either a 4-way coincidence
or a shared root cause. Batch review surfaces which it is. The
template stays applicable even if the 4 strategies change or the count
shifts — the structure is stale-probation-count-agnostic.*
