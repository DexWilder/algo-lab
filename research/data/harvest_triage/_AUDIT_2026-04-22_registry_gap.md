# Audit: Harvest→Registry Coordination Gap (2026-04-22)

**Authority:** T1 diagnostic (operator judgment)
**Purpose:** Quantify the gap between structured-triage accept decisions and
actual registry state. Pure diagnostic — no remediation applied today.

---

## Findings

### Harvest engine status
- **Last scan timestamp in manifest:** 2026-03-17 (5 weeks old)
- **Total items in manifest:** 17
- **Logged to registry (historical):** 27
- **`harvest_engine.py --run` invocations during hold window (2026-04-14 → today):** 0 observed

### Registry state
- **Total strategies:** 117
- **Last content change commit:** 2026-04-14 (`bdff4e3` — SPX-Lunch-Compression manual append during Forge day 1 packet item 3)
- **Registry changes during hold since 2026-04-14:** 0

### Triage decisions this week
| Day | Notes triaged | ACCEPT HIGH | ACCEPT COMPONENT | Total accepts |
|-----|---------------|-------------|-------------------|----------------|
| Mon 2026-04-20 | 38 | 18 | 9 | 27 |
| Tue 2026-04-21 | 15 | 2 | 3 | 5 |
| Wed 2026-04-22 | 15 | 3 | 3 | 6 |
| **Total** | **68** | **23** | **15** | **38** |

**Gap: 23 HIGH-priority canonical accepts + 15 components sit in triage files with zero registry reflection.**

---

## Root cause (structural, not bug)

The Forge v1 packet workflow is artisanal — 1–3 items worked fully per day, each including manual registry append (see commits `bdff4e3` / `a8d6f96` / `421bded` from 2026-04-15 pattern). Each packet item corresponds to one registry change.

The structured triage pattern introduced 2026-04-20 operates at industrial scale — 15-38 disposition decisions per day. The triage writes T1 records to `research/data/harvest_triage/*.md`; it does not trigger registry appends.

The two rates don't match:
- Triage inflow: ~15 accepts per weekday on average this week
- Packet throughput: ~1-3 items per day, and packet items don't necessarily map 1:1 to triage accepts

Result: triage decisions accumulate as records; registry doesn't move. This is `docs/bad_automation_smells.md` smell #4 ("queue growth masking lack of closure") manifesting — the triage files make it look like processing is happening, but the authoritative state (registry) hasn't updated.

---

## Why this matters

**For May 1 checkpoint:**
- Section 4 of `docs/MAY_1_CHECKPOINT_TEMPLATE.md` compares registry state to Golden Snapshot (2026-04-14, 117 strategies). Under current state, the delta will report "0 registry changes" — which is technically accurate but hides the 23+ accepts in the triage files.
- The checkpoint's "Remain in stable state" decision criterion says "Section 4 deltas are docs-only." Zero registry change meets that criterion but misrepresents the operational reality — Claw + triage have produced 38 decisions worth of intake work that just hasn't been cashed in.

**For Forge v1 integrity:**
- Scorecard rule: "100% memory-payload-complete on new closures" is being honored on rejections but not on accepts — an accept in triage isn't a closure into registry.
- The scorecard says the machine is running; the registry says it isn't. Only one of those is the authoritative state.

**For post-May-1 exception pipeline design:**
- This is direct evidence that HARVEST_NOISE auto-reject (pipeline Phase C) needs a matched HARVEST_ACCEPT auto-register step. Rejecting at scale + accepting at packet speed = same gap from the other direction.

---

## Options for Friday decision

**A. Batch-register the 23 HIGH-priority accepts now** (close the backlog)
- Mechanism: either `harvest_engine.py --run` on the accepted subset, or manual append to registry for each
- Risk: low — registry append of new `idea` entries is T2 per authority ladder (no `status` field mutations, additive only); allowed during hold
- Upside: registry matches triage reality before checkpoint
- Downside: 23 at-once append is unusual; needs careful review; some "ACCEPT HIGH" may warrant second-look before registry commitment

**B. Absorb gradually into packet work** (status quo)
- Mechanism: each daily packet picks 1-3 triage accepts to work through (memory payload, validation prep, registry entry)
- Risk: triage file accumulates indefinitely; at current inflow (~15/day), backlog grows faster than packets close it
- Upside: preserves packet quality discipline
- Downside: structural mismatch continues; by May 1 the gap will be 50-100+ unresolved accepts

**C. Redefine triage's role** — triage file IS the authoritative intermediate state
- Mechanism: stop treating triage accepts as "should become registry entries"; treat triage as its own durable record of disposition
- Risk: registry loses its completeness property; "registry" and "accepted ideas" diverge semantically
- Upside: no forced coordination between two workflows
- Downside: violates FQL's doc discipline (single source of truth)

**D. Hybrid** — batch-register HIGH-priority canonicals only, absorb COMPONENTS gradually
- 23 canonical registry appends as a bounded operation
- 15 components absorbed via packet work when relevant
- Closes the urgent gap without blanket batch-appending everything
- Likely the defensible middle path

---

## Recommendation for Friday

Not rendered today — this is diagnostic input, not a decision. But surface-level read:

- Option A or D before May 1 checkpoint. The checkpoint's Section 4 registry-state comparison should reflect what actually happened during the week, not the pre-triage baseline.
- Option B creates a growing structural gap that will hurt.
- Option C is defensible but requires updating authority_ladder and bad_automation_smells to reflect the new semantics — heavier change.

---

## Related artifacts

- `research/data/harvest_triage/2026-04-20.md` (38 notes triaged)
- `research/data/harvest_triage/2026-04-21.md` (15 notes)
- `research/data/harvest_triage/2026-04-22.md` (15 notes)
- `docs/MAY_1_CHECKPOINT_TEMPLATE.md` Section 4 (Golden Snapshot divergence)
- `docs/bad_automation_smells.md` smell #4 (queue growth masking closure)
- `docs/authority_ladder.md` T2 registry-append authority

---

*Audit performed 2026-04-22 Wednesday afternoon as hold-safe diagnostic.
No remediation applied. Friday rollup is the decision point.*
