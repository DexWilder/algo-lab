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
