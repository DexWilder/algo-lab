# Anti-Drift Checks

**4 metrics tracked weekly.** These catch the failure mode where the
machine looks busy but stops compounding.

The observable signals in `stale_checks.md` are day-to-day anchors.
These 4 metrics are the aggregate health readings.

---

## Metric 1: Harvest-to-closure ratio

**Definition:** items opened into Inbox this week ÷ items conclusively
resolved this week (Validated + Rejected + explicit archive/salvage-routed).

**Interpretation:**
- **< 1.0** — resolving faster than harvesting. Usually healthy; watch for pipeline drying up.
- **1.0 – 2.0** — sustainable zone. Harvest and closure roughly keep pace.
- **2.0 – 4.0** — harvest growing faster than closure. Tolerable short-term; concerning if sustained.
- **> 4.0** — harvest outpacing closure significantly. Closure discipline is slipping or validation capacity is exhausted. Fallback-mode use (closure days) should increase until this normalizes.

**Compute from:** weekly scorecard `Items opened` and `Items conclusively resolved` counts.

---

## Metric 2: Average queue age by state

**Definition:** for each of Inbox, In Progress, Validation, compute the
average days-in-current-state across all items in that state at end of
week.

**Interpretation (guidance, not law):**
- Inbox average < 3 days: healthy intake
- In Progress average < 3 days: active execution
- Validation average < 7 days: verdicts being rendered
- Averages 2x above the above thresholds: queue aging faster than the machine is working

**Compute from:** timestamps on queue entries, computed at end of week.

**Cross-check with stale thresholds:** if average age is within healthy
range but stale rules are firing, the aging is concentrated in a few
items (bad). If average is high but no stale rules fire, the thresholds
may be too loose (refine in improvement log).

---

## Metric 3: % active items with concrete next action

**Definition:** (items in In Progress + Validation where the current
scorecard entry names a specific next action in the done-for-today
field) ÷ (total items in In Progress + Validation)

**Interpretation:**
- **> 90%** — healthy active queue management
- **70 – 90%** — some drift; catch up during integrity cadence
- **< 70%** — queue contains zombies; dedicated triage pass needed

**Compute from:** scan `In Progress` + `Validation` items, check whether
the latest scorecard entry gives a concrete next action or a blocker
type. Items with neither are zombies.

---

## Metric 4: % closed items with memory payload complete

**Definition:** (items moved to Validated or Rejected this week with
all 6 memory-payload fields complete within 3 days) ÷ (total closed
this week)

**Interpretation:**
- **100%** — memory discipline intact
- **80 – 99%** — routine slippage; surface in integrity check
- **< 80%** — memory is silently eroding; the endless strategy factory's compounding engine is breaking

**Compute from:** registry `data_pipeline_gap`-style inspection of
memory-payload fields on all items with state transitions this week. See
`memory_index.md` for field list.

---

## When anti-drift metrics fire

- **Weekly Friday integrity cadence:** all 4 metrics computed and
  written to the weekly rollup's "Anti-drift snapshot" section.
- **2-week exit gate (day 14):** metrics reviewed across the 2-week
  window as trends, not point values.

---

## What "firing" means

Each metric has an expected range. Values outside that range don't
automatically mean failure — they mean *explain in the weekly rollup
why*. If the explanation is legitimate (harvest burst, validation
capacity spike, deliberate closure week), log it. If the explanation is
"don't know," that's the signal to investigate.

---

## What these metrics do NOT catch (v1 limitations)

- **Per-source signal quality:** source-yield tracking in
  `source_map.md` handles this.
- **Gap-addressed work rate:** tracked in the weekly rollup's gap
  review section, not as an anti-drift metric.
- **Search-pattern effectiveness:** deferred to v2+; needs accumulated
  query-to-outcome data.
- **Strategic staleness** (e.g., validating strategies in a saturated
  family while true gaps go unaddressed): gap review catches it, not
  these metrics.

v2+ will add metrics as real operational experience reveals which
abstractions matter most.

---

## Metrics are descriptive, not prescriptive

These 4 metrics describe the health of the work the machine is doing.
They do not prescribe what work to do. Packet selection, fallback
modes, and gap priorities drive the work. Anti-drift metrics are the
health dashboard — they do not drive; they diagnose.

Confusing the two (treating metrics as KPIs to optimize) produces the
exact theater pattern FQL Forge is designed to prevent.
