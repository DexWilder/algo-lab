# Memory Index

**Strategy memory payload schema.** What every closed candidate must
preserve for compounding.

The endless strategy factory only compounds if memory compounds.
Candidates that fail today are often the parents of winning hybrids
tomorrow — but only if what we learned survives.

---

## Required memory payload — 6 fields

Every candidate entering Validated or Rejected state must have these 6
fields populated within 3 days of the state transition. (Caught by
stale rule #7 in `stale_checks.md`.)

### 1. Core idea
One-line summary of what the strategy does and why it should work.
"Breakout on London open 6J, expecting Asian-range resolution" is a
core idea. "Breakout strategy" is not.

### 2. Family / structure
Primary factor (MOMENTUM / MEAN_REVERSION / VOLATILITY / CARRY /
STRUCTURAL / VALUE / EVENT) + family (breakout / pullback / trend / event-driven / carry-spread / etc.) + shape per `ELITE_PROMOTION_STANDARDS.md` (intraday single-asset / sparse event / out-of-band monthly / overlay-sizing / spread).

### 3. Why it worked or failed
Specific mechanism. Not "concentration was high" but "98.7% of PnL from
3 trades out of 128; edge was tail-event luck, not reproducible."
Framework-mismatch cases should explicitly say so.

### 4. Salvageability classification
One of: `salvage` (retry with specific adjustment), `archive` (preserve
as reference, no retry planned), `extract-components-only` (parent is
dead but specific parts are reusable), `permanent-kill` (failure mode
structural; don't retry).

### 5. Reusable parts
What specific components (entries, exits, filters, regimes, sizing
rules, session logic) are extractable and reusable in future
crossbreeding. Even failed strategies often have one or two genuinely
useful pieces.

### 6. Portfolio-role observation
If the candidate had reached Lane A: what factor / asset / session /
regime / role would it have filled? Includes notes like "would have
been STRUCTURAL primary" or "overcrowds existing momentum cluster."

---

## Where memory lives

Memory payload maps to registry fields in `research/data/strategy_registry.json`:

| Memory field | Registry location |
|---|---|
| Core idea | `rule_summary` + `strategy_name` |
| Family / structure | `family` + `session` + `direction` + genome map primary factor + `execution_path`-implied shape |
| Why it worked/failed | `notes` (narrative) + `rejection_reason` (structured) + `classification_reasons` (from first-pass) |
| Salvageability classification | `lifecycle_stage` (salvage → `watch-salvage`; archive → `archived`; extract-only → `archived` with `reusable_as_component: true`; permanent-kill → `archived` with `reusable_as_component: false`) |
| Reusable parts | `component_validation_history[].reusable_in` array + `extractable_components` field |
| Portfolio-role observation | `portfolio_role` + `notes` context |

v1 uses existing registry fields; it does not introduce new memory
schema. The improvement log tracks whether the 6 fields map cleanly to
registry or whether v2+ needs a dedicated `memory_payload` structured
field.

---

## Component memory (second-class but important)

Individual extracted components live in `component_validation_history`
entries per parent strategy. Fields:

- `component` — name of the component
- `type` — entry_logic / exit_logic / filter / regime / sizing / timing
- `context` — the shape/asset/regime it was validated in
- `result` — validated / inconclusive / failed
- `evidence` — what the validation showed
- `reusable_in` — where it might transfer
- `failure_contexts` — where it did not transfer

Crossbreeding work draws from this pool. A validated component from a
rejected parent is gold.

---

## Memory completeness metric

Tracked weekly (see `anti_drift_checks.md` metric 4):
`% closed items with memory payload complete`. Target: 100%. Threshold
for concern: <80%.

If memory completeness drops, the machine has stopped compounding — the
strategies are moving through the queue but the learnings are not
persisting. This is a theater failure mode even if closure counts look
healthy.

---

## Memory read patterns

How memory is actually used going forward:

1. **Crossbreeding** — query registry for all items with
   `component_validation_history[].result == "validated"` and
   `reusable_as_component: true`; combine components into new hybrids.

2. **Gap-directed search** — when a portfolio gap is identified (e.g.,
   FX + STRUCTURAL), query registry for archived strategies with
   matching family/primary-factor to reconsider under improved
   framework.

3. **Failure-mode avoidance** — when a new candidate is being evaluated,
   query registry for `rejection_reason` patterns that match its profile
   and apply specific checks (e.g., always test concentration if the
   family has historical concentration-catastrophe rejections).

4. **Regime / asset / session observations** — aggregate `portfolio_role`
   and `regime_tendency` across validated strategies to inform which
   regimes/sessions are over- or under-represented in the active set.

v1 supports these reads manually. v2+ may add helper scripts to
automate common queries — but the read patterns should be documented
here first, tools second.

---

## Memory is the endless-strategy-factory's compounding engine

No candidate is ever "just rejected." Every candidate leaves behind:
- a framework lesson
- potentially-reusable parts
- a portfolio-role observation
- a signal about which sources produce which kinds of ideas

If any of those are discarded with the rejection, the compounding
breaks. The 3-day memory-payload deadline and the 80% completeness
target exist specifically to prevent that breakage.
