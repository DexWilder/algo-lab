# Stale Checks

**Explicit list of stale conditions with thresholds.** v1 runs these
manually as part of the daily operating cadence (review pass at start
of day) and the weekly Friday integrity cadence (expanded pass).

---

## Stale rules (9 total)

### 1. Inbox → not triaged
- **Threshold:** 7 days since harvest
- **Action on trigger:** triage immediately or assign a blocker type. Items that cannot be triaged in 7 days usually indicate unclear hypothesis — accept into In Progress blocked with `unclear hypothesis` or reject.

### 2. In Progress → no output or blocker note
- **Threshold:** 5 days without a scorecard entry mentioning an artifact or a blocker-with-type
- **Action on trigger:** either advance with a concrete artifact or flag `blocker_flag: true` with a type from the taxonomy. Items silently sitting are the primary queue-fossilization risk.

### 3. Validation → no verdict
- **Threshold:** 10 days in Validation state
- **Action on trigger:** render a verdict (Validated or Rejected) or downgrade back to In Progress with a specific refinement to attempt. Validation rot is dangerous — the strict threshold catches it before concentration-of-time issues.

### 4. Blocked without unblock plan
- **Threshold:** 5 days flagged blocked without a documented "how this gets unblocked" note
- **Action on trigger:** add the plan, or reject the item (if unblockable), or route to external-dependency resolution (if blocked on Lane A).

### 5. Rejected without reason
- **Threshold:** 1 day (i.e., rejections must carry reason the same day they are filed)
- **Action on trigger:** add the reason or un-reject and return to In Progress. Rejections without reasons are memory-destruction.

### 6. Failed without salvage classification
- **Threshold:** 3 days since entering Rejected state
- **Action on trigger:** classify the candidate as `salvage` (try again with adjusted framework), `archive` (preserve as reference only), or `extract-components-only` (the candidate is dead but some parts are reusable).

### 7. Closed without memory payload complete
- **Threshold:** 3 days since entering Validated or Rejected state
- **Scope:** applies to items whose closure date is ≥ 2026-04-14 (v1 launch). Pre-v1 closures are handled via dedicated "pre-v1 memory backfill" workstream that runs as fallback work on memory-cleanup days — not under the 3-day deadline (refinement applied 2026-04-15 per day-1 improvement log; day-1 stale scan found 28 pre-v1 closures with incomplete payloads, impossible to force retroactive 3-day compliance).
- **Action on trigger:** fill the 6-field memory payload (see `memory_index.md`). Candidates without memory payloads do not compound.

### 8. Blocker without type
- **Threshold:** 1 day from `blocker_flag: true` being set
- **Action on trigger:** assign one of the 6 blocker types from the taxonomy in `queues.md`. Untyped blockers make the blocker-taxonomy summary meaningless.

### 9. Harvested but uncatalogued
- **Threshold:** 2 days since appearing in `~/openclaw-intake/inbox/` or equivalent harvest drop-zone without a registry Inbox entry
- **Action on trigger:** either add to Inbox with required fields or discard with a one-line "not worth triaging: <reason>" note. Harvest drop-zones that accumulate outside the queue are shadow work.

---

## Observable pressure signals (anchors for the stale metrics)

These are the behaviors the stale rules are designed to catch. Naming
them makes abstract thresholds legible.

### Under-pressure observable signals

- Daily packet was empty or had only 1 item for 2+ days running
- No new items entered Inbox for 5+ days
- No closure (Validated or Rejected) recorded for 5+ days
- Memory payloads consistently filled at the 3-day deadline edge, never early
- Fallback modes chosen >40% of days (primary track not functional)

### Over-pressure observable signals

- Packet cap exceeded 2+ days in a row
- Same candidate touched 3+ days without state change
- Stale items accumulating faster than being cleared (net stale count rising week over week)
- Weekly rollup becoming hand-wavy or skipped
- Blocker count climbing while closure ratio falls
- New items entering Inbox at >2/day sustained while closure ratio <0.7

### Process-drift observable signals

- Scorecard entries missing the "Produced artifact" line or conflating it with "State change"
- Rotation dimensions repeatedly hitting only 1-2 of 5 per window with no "why" note
- Blocker types absent on flagged items
- Docs referencing procedures that are no longer being followed in practice

---

## When stale checks fire

- **Daily operating cadence (start of day):** review rules 2, 4, 5, 8, 9. Any trigger routes the day's packet toward clearing it, or (if several trigger) into a fallback mode (see `cadence.md`).
- **Weekly Friday integrity cadence:** review all 9 rules + all observable signals. Summarize in the weekly rollup's integrity self-check.
- **2-week exit gate (day 14):** expanded review — every rule, every signal, plus calibration question "are thresholds firing at the right rate?" (see `cadence.md` for the gate questions).

---

## Thresholds are hypotheses, not laws

The 9 thresholds above are v1 defaults. They will fire too often or not
enough. The improvement log tracks which thresholds need adjustment.
Calibration happens via observation, not debate.

**Explicit v1 guidance:**
- If a threshold fires >3 times in a single week and each firing feels
  premature, loosen it and log the change in the improvement log.
- If a threshold never fires in 2 weeks, tighten it and log the change.
- If a threshold fires correctly but the action is consistently the
  same ("clear this by filling X"), consider whether that action should
  be automated (v2+ work).

The thresholds themselves are part of what FQL Forge learns to
calibrate over time.
