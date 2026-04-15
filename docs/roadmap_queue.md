# Roadmap Queue

**Deferred roadmap items with evidence thresholds.**

**Purpose:** capture strategic work identified as likely important in
the future, without pre-committing to execution or ordering. Each item
has an explicit **activation evidence** threshold — the observed data
that would make the item earned rather than speculative. Until that
evidence exists, the item waits.

**This is not a to-do list.** Items in this file are deliberately
**not scheduled.** Moving an item into execution requires its
activation evidence to appear, not operator enthusiasm.

**Governing principle:** *the forge earns the roadmap through
operation.* Items activate when running surfaces the need. Items that
never activate are not failures; they are hypotheses the system never
needed.

**Created:** 2026-04-15 (end of FQL Forge v1 day 1)
**Next review:** 2026-04-28 day-14 v1 exit gate (expanded integrity cadence)

---

## Queue format

Each item carries:
- **Item** — short name
- **Why it matters** — the operational gap or future lever it represents
- **Activation evidence** — what observed data would earn this item a real slot in execution
- **Earliest review** — the earliest cadence checkpoint where this is reconsidered

---

## Item 1 — Gap-map targeting engine (formalization)

**Why it matters.** FQL Forge has `docs/PORTFOLIO_TRUTH_TABLE.md` open-gaps
list, a genome map, and gap-directed packet selection as a principle. It
does not yet have an explicit targeting engine that converts gaps into
search priorities, evolution priorities, source-expansion priorities,
and crossbreeding priorities. Without that engine, gap-directed work
remains a discipline applied by hand rather than a systematic steering
mechanism. This is load-bearing because several other roadmap items
depend on it (deployment ladder, portfolio bridge, component economy).

**Activation evidence.** First 2 weekly rollups (2026-04-17 and
2026-04-24) show whether the current gap list is actually steering
packet selection usefully. If gap-addressed packets produce higher-quality
validated artifacts than ungap-directed packets, the targeting engine
earns formalization. If gap direction doesn't move outcomes, the engine
doesn't yet need to be more than an informal discipline.

**Earliest review.** Day-14 gate (2026-04-28).

## Item 2 — Component economy (formalization)

**Why it matters.** FQL Forge already has `component_validation_history`
in the registry schema (populated for 2 strategies as of day 1). The
concept of "extracted components as reusable assets" exists. What's
underdefined is the economy around it: how components get surfaced for
crossbreeding, how their reuse is tracked, how their cumulative
validation value is assessed, how they feed back into discovery. This
is the difference between "we have a components field" and "the forge
actively mines and recombines components."

**Activation evidence.** At least 10 documented components across
validated+rejected parents, with at least 2 cases where a reusable
component from a failed parent plausibly contributes to a new hybrid.
Day-14 gate will show whether the 4-field component schema handles the
volume of extractions produced during 2 operating weeks.

**Earliest review.** Day-14 gate (2026-04-28).

## Item 3 — Validated → deployment ladder (explicit stages)

**Why it matters.** Current lifecycle states in `queues.md` are 5 (Inbox,
In Progress, Validation, Validated, Rejected). The promotion from
Validated into Lane A's controller-eligible state is governed by the
promotion protocol in `LANE_A_B_OPERATING_DOCTRINE.md` but lacks the
intermediate ladder stages: idea → first-pass candidate → validated
artifact → probationary portfolio candidate → controller-eligible
strategy → funded/live-eligible strategy. Each stage deserves explicit
gates. Without them, "good backtest" feels too close to "real
candidate."

**Activation evidence.** The forge reaches a point where at least 1
Validated candidate exists and is ready for Lane A promotion
consideration. At that point, the gaps between Validated and
controller-eligible become operationally visible. No candidate reaches
this state during the hold window; earliest possible is post-2026-05-01
Treasury-Rolldown checkpoint.

**Earliest review.** Post-2026-05-01 checkpoint. Treasury-Rolldown's
monthly rebalance is the first real Lane A promotion test under the
out-of-band execution path; its outcome informs what the ladder needs.

## Item 4 — Portfolio-construction bridge (role-based promotion)

**Why it matters.** Item 3 (ladder) covers stages. Item 4 covers role:
what portfolio role does a candidate play, what existing strategy does
it replace or complement, what correlation burden does it bring, what
dimensions does it improve (pass probability, payout velocity, tail
capture, regime coverage, time-of-day diversification). `ELITE_PROMOTION_STANDARDS.md`
handles shape-to-framework matching. The missing piece is role-to-portfolio
matching at the decision point of "should this candidate enter the live
portfolio at all?"

**Activation evidence.** Two conditions: (a) item 1 (gap targeting)
activated so roles are explicitly defined, (b) a candidate emerges that
plausibly competes with or complements an existing active strategy. The
second condition requires operational runtime; will not exist during
hold window.

**Earliest review.** Post-day-14 gate or post-2026-05-01, whichever
produces the first role-competitive candidate.

## Item 5 — Research ROI / source yield analytics

**Why it matters.** `source_map.md` day-1 baseline populates lifetime
per-source yield counts but cannot yet compute weekly rates or
component-attribution-by-source. Research economics (time-spent by
source, cost-per-validated-artifact, false-positive rates by source
class) become meaningful only once multiple operating weeks exist. This
is a **descriptive** layer, not a decision layer — helps calibrate where
to double down and where to demote, but does not itself promote or
reject strategies.

**Activation evidence.** 4+ operating weeks of weekly rollup data,
including source-yield columns populated with observed weekly rates
(not just lifetime counts). This minimum is required to distinguish
signal from noise in any per-source trend.

**Earliest review.** Week 4 (approximately 2026-05-13) assuming
continuous operation.

## Item 6 — Execution-side roadmap for live safety

**Why it matters.** This is the production-engineering branch of the
roadmap. Watchdog, reconciliation, alerting, SAFE_MODE hardening,
broker/data/process health checks, incident response, secrets hygiene,
environment separation. The current system has most of these in partial
form. The roadmap is about what happens as live capital exposure grows.

**Activation evidence.** Either (a) a Lane A promotion event moves
capital exposure into a new execution mode (e.g., first real-capital
strategy, or out-of-band execution expands beyond Treasury-Rolldown) and
surfaces a specific safety gap, or (b) an incident exposes a concrete
failure mode worth generalizing from.

**Earliest review.** After Treasury-Rolldown's first 2-3 live monthly
cycles complete, or immediately if a specific incident warrants.

## Item 7 — Autonomous research factory loop

**Why it matters.** The full closed-loop research factory — harvest →
dedupe → classify → convert → first-pass → validate → salvage → extract →
store → compare → target gaps → regenerate new packets automatically. Most
pieces exist in partial form. What's missing is the orchestration that
connects them into a self-feeding loop. This is deliberately last in
priority because every other roadmap item feeds it; building it without
the substrate in place produces a brittle loop that can't adapt.

**Activation evidence.** Items 1, 2, 3, and 5 must have working
evidence before item 7 has a foundation. Specifically: the gap-map
targeting engine (item 1), the component economy (item 2), the
deployment ladder (item 3), and the research ROI layer (item 5) all
need to be producing real data before autonomous orchestration has
anything meaningful to automate.

**Earliest review.** After items 1, 2, 3, and 5 have each reached their
own activation state. Realistically not before 2026-06-15.

## Item 8 — Maturity checkpoints (graduation milestones)

**Why it matters.** Roadmap has many module-level items but few
maturity checkpoints: *when is FQL Forge considered operationally stable?
When is strategy memory considered rich enough for serious
crossbreeding? When is search-pattern learning justified? When is
autonomous refinement justified? When is promotion automation
justified?* These thresholds prevent premature automation and give the
system objective definitions of "earned the next phase."

**Activation evidence.** After the day-14 v1 exit gate produces its
first set of data-driven calibration answers. Those answers will
reveal what maturity checkpoints are worth writing versus which are
theoretical.

**Earliest review.** Day-14 gate (2026-04-28).

---

## What this queue is NOT

- **Not a commitment to execute any of these items.** Items that never activate are not failures.
- **Not a priority list.** The ordering above reflects dependency and earliest-possible review, not importance. The gap-map targeting engine (item 1) is listed first because several other items depend on it, not because it's the most urgent to build today.
- **Not a substitute for FQL Forge's improvement log.** Items that surface during operation (like the ghost-candidate pattern from day 1) go into `docs/fql_forge/improvement_log.md`. Items here are strategic hypotheses awaiting evidence.
- **Not a parking lot for vague topics.** Every item has a named activation threshold. Items without one are either collapsed into another item or rejected.

## How items leave this queue

An item leaves this queue via **activation** (observed evidence meets
the threshold → item moves into execution) or **rejection** (2+ review
cycles pass without activation evidence appearing → item is retired
with a note about why it never earned a slot).

Rejection is a valid outcome. It means the hypothesis was worth logging
but the operational reality didn't need it.

## Current status

All 8 items are **queued** as of 2026-04-15. None are in execution.
Next review: day-14 gate, which will evaluate items 1, 2, 6 (partial),
and 8 against their activation evidence.

## Related authorities

- `docs/LANE_A_B_OPERATING_DOCTRINE.md` — governs the promotion seam referenced in items 3 and 4
- `docs/fql_forge/` — the operating kernel that generates the evidence these items wait on
- `docs/ELITE_PROMOTION_STANDARDS.md` — the framework items 3 and 4 extend
- `docs/PORTFOLIO_TRUTH_TABLE.md` — the gap inventory item 1 formalizes
- `docs/HOLD_STATE_CHECKLIST.md` — items here are NOT hold breaches; the queue is strategic hypothesis storage, not active work

---

*This file is itself hold-safe: it's a strategic hypothesis log, not
runtime code and not a lifecycle surface. Amendments follow the same
discipline as the items themselves — change with evidence, not
enthusiasm.*
