# Improvement Log

**Process-improvement standing section.** One entry per week minimum,
more as needed.

The machine must improve itself. This log is the record of what was
learned and changed.

---

## Entry format

```
## [YYYY-MM-DD] Week ending

### What slowed us down this week
- <specific friction observed>

### What repeated manual step should be templated or automated
- <specific repeated work; v2+ candidate for automation>

### What stale check caught something useful
- <rule N fired on item X; confirmed it was worth catching>

### What false-positive stale rule should be refined
- <rule N fired but the action was "no action needed"; threshold may be wrong>

### What queue definition needs adjustment
- <ambiguity observed between states; proposed clarification>

### What automation would increase validation capacity
- <specific v2+ tooling idea with sizing>

### What source lane should be expanded or demoted
- <observation from source_map.md yield review>

### What rotation dimension was repeatedly missed
- <if <3 dimensions touched in any 5-day window; why>

### Process changes applied this week
- <documented change to stale threshold, fallback rule, queue definition, etc.>

### Process changes deferred to v2+
- <ideas that earn place after more data>
```

---

## Mandatory weekly entry

**The improvement log entry is not optional.** Missing it for 2+
consecutive weeks is itself an integrity-cadence failure. If nothing
can be said, the entry should say exactly that:

```
## [YYYY-MM-DD] Week ending
No improvements identified this week. (If this is the second consecutive
such entry, the 2-week exit gate should address whether the integrity
cadence is actually being run.)
```

The goal is visibility, not content bulk.

---

## Seed entries

v1 ships with these initial known-limitations as pre-loaded
improvement candidates:

### 2026-04-14 (v1 seed)
Known limitations of v1 design that may need addressing after observation:
- Thresholds in `stale_checks.md` are initial guesses. Expect calibration.
- Fallback-mode usage rate (>40% alert) may be too loose or too tight depending on observation.
- Soft cap of 2 new items/day may need to harden or loosen.
- 5-day rotation heuristic may need scope adjustment.
- Memory-payload 6 fields may be incomplete or excessive; observation will tell.
- Weekly Friday rollup scope may be too large for practical execution; tighten if running >1 hour regularly.

These are starting positions. They become real improvement log entries
once the machine has run for at least one full week.

---

## 2026-04-15 — Day 1 operational seed entry

### Day-1 stale scan against existing registry

Ran the 9 stale rules against current registry reality. Findings:

- **Rule #5 (rejected without reason):** 2 items. Legitimate stale triggers — these registry entries are `status=rejected` but carry no `rejection_reason` field. Clearing requires filling the reason or un-rejecting. **Action:** enumerate and clear during first weekly cadence (2026-04-17).
- **Rule #7 (closed without memory payload):** 28 items. A large backlog. Most are historical rejected/archived entries that predate FQL Forge's 6-field payload schema. They were closed under the old implicit "write some notes and move on" pattern, not the new explicit 6-field discipline.

**Scale of rule #7 backlog vs the 3-day deadline rule:**

The rule says "closed items must have memory payload complete within 3 days of closure." Applied retroactively to 28 historical items, this is impossible — they closed weeks or months ago. The rule is intended to govern **new closures going forward**, not force retroactive compliance on historical data.

**Proposed v1 refinement (immediate, applied today):**

- Rule #7 applies to items whose closure date is ≥ 2026-04-14 (v1 launch). Pre-v1 closures carry a different disposition: they should get memory payloads completed via a dedicated backfill effort (6 required fields), but not under the 3-day deadline — under a separate "pre-v1 memory backfill" workstream that runs as fallback work on memory-cleanup days.
- Document pre-v1 items with incomplete payloads in an explicit queue / note, separate from active stale-firing items.

Without this refinement, the day-1 integrity check reports 28 stale firings, which would trigger Rule #7 as critically exceeded and collapse the machine's signal value. With it, Rule #7 reports 0 new-closure firings and the pre-v1 backlog becomes scheduled work on memory-cleanup fallback days.

**This is exactly the kind of friction day-1 execution is supposed to surface.** Logging as a v1 refinement.

### Immediate friction from day 1 (other items)

1. **`source_map.md` lifetime yield table has `unknown` in the "yielded components" column for every lane.** Per-source component attribution isn't in the historical registry — component_validation_history is per-strategy but not aggregated upward. v2+ candidate: add per-source aggregation helper or retrofit historical items. For v1, accept `unknown` as honest.

2. **Packet item naming is awkward when an item is technically two actions on the same parent** (e.g., "FXBreak-6J memory payload" + "FXBreak-6J component extraction"). Day-1 compromise: list as two rows with shared parent. If this becomes frequent, v1 refinement: packet supports "sub-tasks" per parent, or v2+ refinement: packet structure allows parent-item + action-list nesting.

3. **5-day rotation hint showed 4 of 5 dimensions on day 1.** Validation dimension not hit because no candidate in Validation state today. This is expected for v1 day 1 — no Validation work inherited, Validation queue at zero. The hint is "note why if <3" — noted. Not a concern until week 1 rollup shows repeated misses.

4. **Day 1 scorecard entry format worked but raised a question:** should the scorecard show the packet **before** execution (planning view) or **after** execution (results view)? Today's entry captures "day not yet executed at append time" which is awkward. Proposed: v1 convention = append scorecard at end of work day, after packet execution. Day-1 is a special case (seed).

### v1 refinements applied today (from friction observed)

- **Rule #7 scope clarified:** applies to closures ≥ 2026-04-14. Pre-v1 closures handled via dedicated backfill on memory-cleanup fallback days. This change is a v1 refinement, not v2 work. Update to `stale_checks.md` will be applied in next commit.

### v1 → v2 upgrade candidates surfaced today

Added to the queue:
- **Per-source component attribution** — aggregate `component_validation_history` up to source category. (Noted in `source_map.md` as candidate.)
- **Packet sub-task structure** — if parent-child action pairs become common. Watch frequency over first 2 weeks.

### Open questions (no answer yet)

- Will rule #5 (rejected without reason) be chronic at volume, or does it reflect a one-time historical bookkeeping gap?
- How often will fallback modes chosen exceed 40% sustained? Day-1 is 100% fallback mode (seed day); legitimate but establishes nothing about steady-state.

Both to be revisited at 2026-04-17 first weekly rollup and 2026-04-28 day-14 gate.


---

## v1 → v2 upgrade candidates

These are already-named v2+ items earning their place here as a record
(they are NOT v1 work):

- Automated source-lane ranking from accumulated yield data
- Search-pattern learning (queries → outcomes)
- Refinement-playbook auto-generation from memory payloads
- Automated stale detection replacing manual checklist
- Dashboard / scorecard automation
- Atomic lifecycle updater (hardening queue item #1)
- Shared DEAD_STATUSES guard helper (hardening queue item #3)
- Execution-shape field standardization (hardening queue item #5)
- Daily authority-consistency validator (hardening queue item #2)
- Weekly stale-reference audit (hardening queue item #4)

The 2-week exit gate decides which of these are promoted into v2 work.

---

## Change discipline

Changes to FQL Forge structure (thresholds, rules, queue definitions)
must be:

1. Identified in the improvement log with the observation that motivated the change
2. Applied to the specific file affected with a dated inline comment
3. Summarized in the next weekly rollup

Changes that skip this discipline are themselves a process fault and
should be caught by the integrity cadence (docs/process definitions
drifting from actual behavior).
