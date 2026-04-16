# Queues

**FQL Forge v1 — 5 states**

Every candidate lives in exactly one of these five states. Transitions
are explicit; items do not pass between states silently.

---

## State definitions

### 1. Inbox

Harvested, not yet triaged. Raw ideas from any source lane (see
`source_map.md`).

**Required fields per item:**
- Source (lane + URL/reference)
- Harvest date
- One-line description
- Initial tag set (asset, family hint, regime hint)

**Transition out:** triage → (In Progress | Rejected | parked-with-note)

### 2. In Progress

Actively being worked on. Examples: converting Pine → Python, initial
backtest, validation battery, refinement, component extraction.

**Required fields per item:**
- Entry date (when moved from Inbox)
- Current action (what specifically is being done right now)
- Shape per `ELITE_PROMOTION_STANDARDS.md` (intraday single-asset workhorse / sparse event / out-of-band monthly / overlay-sizing / spread)
- Blocker flag + blocker type if blocked (see blocker taxonomy below)

**Transition out:** Validation (when deeper evaluation begins) |
Rejected (with reason) | Validated (if the work is thin enough that In
Progress produced conclusive edge)

### 3. Validation

Under deep evaluation. Walk-forward, cross-asset, parameter
sensitivity, contribution checks — whatever the shape's framework
requires.

**Required fields:**
- Entry date
- Validation framework being applied (must match shape per promotion standards)
- Expected verdict date
- Blocker flag + type if blocked

**Transition out:** Validated | Rejected

### 4. Validated

Passed framework-appropriate validation. Candidate is ready for Lane A
promotion consideration when the promotion seam is open (not during
hold).

**Required fields:**
- Validation verdict date
- Memory payload complete (see `memory_index.md` — 6 fields)
- Portfolio role proposal (gap filled / displacement candidate / new family)
- `lifecycle_stage: "watch"` in the registry, `controller_action: OFF`

**Transition out:** promoted to Lane A (via governed promotion event
per doctrine §Promotion Protocol) | superseded by better candidate (→ Rejected)

### 5. Rejected

Failed with documented reason. Not deleted — the memory compounds.

**Required fields:**
- Rejection date
- Rejection reason (one of: framework failure / concentration catastrophe / data leakage / wrong-direction / correlation breach / silent failure / ill-defined factor / superseded / other)
- Salvage classification within 3 days: `salvage` / `archive` / `extract-components-only`
- Memory payload complete within 3 days of rejection

**Transition out (rare):** re-examined under different framework →
back to In Progress (this happens when a Lane B reviewer identifies a
framework-mismatch failure à la FXBreak-6J). Re-examination requires
explicit rationale in the weekly improvement log.

---

## Views / filters over the 5 states

These are NOT separate queues in v1. They are views over the 5 states
computed when needed:

| View | Definition |
|---|---|
| **Blocked items** | Items in In Progress or Validation with `blocker_flag: true` |
| **Elite watchlist** | Items in Validated awaiting promotion consideration |
| **Gap-targeted items** | Items in Inbox, In Progress, or Validation tagged to fill a specific open portfolio gap |
| **Extracted components** | Memory payload `reusable_parts` field across Validated + Rejected items |
| **Strategy memory** | All items in Validated + Rejected with complete memory payloads |

v2+ may promote any of these views to first-class queues if operational
friction demands. v1 does not.

### Ghost-candidate rule (STANDING POLICY, formalized 2026-04-16)

**Any converted/tested candidate that lacks registry presence is a
same-week integrity issue, not deferred cleanup.** Confirmed systemic:
day-1 scan found 1 ghost (SPX-Lunch-Compression); day-2 scan found 33
more (the entire 2026-04-06 → 2026-04-09 batch_first_pass sweep never
auto-registered results). Root cause: the batch creates `strategies/`
dirs + `first_pass/*.json` results but does not write registry entries.

**Disposition categories for discovered ghosts:**
- `batch_register_reject` — clear REJECT or TAIL_ENGINE_REJECT from first-pass. Queue for bulk memory-closure on fallback days. Does not need individual triage.
- `individual_triage` — SALVAGE or ADVANCE classification. Deserves individual read of first-pass detail + gap relevance assessment. Enters today's or next available packet.
- `monitor_pending` — MONITOR classification (too few trades for verdict). Park; re-evaluate when data grows or strategy cadence produces more observations.

**Standing inventory:** `docs/fql_forge/ghost_inventory.md`

---

## Blocker taxonomy (6 types)

When a candidate is blocked, the blocker type MUST be one of:

1. **data missing** — required data feed absent, stale, or degraded
2. **conversion issue** — Pine → Python conversion failed or ambiguous
3. **framework mismatch** — no clear shape classification yet; needs review
4. **unclear hypothesis** — "why should this work" not yet articulated
5. **validation capacity** — reviewer unavailable; blocked by queue capacity
6. **external dependency** — requires input from Lane A, another system, or a gated decision

Items blocked with no type assigned are caught by the stale check in
`stale_checks.md` and must be resolved within 24 hours.

---

## WIP caps (soft enforcement via observation)

- **Total In Progress:** ≤ 5 simultaneously
- **Total Validation:** ≤ 3 simultaneously
- **At least 1 closure slot** reserved in daily packet (see `active_packet.md`)
- **Soft guideline:** no more than 2 truly new items started per day. If this is violated >1 day/week consistently, anti-drift metrics surface it.

Caps above are not runtime-enforced in v1 — they are discipline
thresholds. Violations are visible in the scorecard and caught by
integrity cadence.

---

## Registry relationship

Queue state maps to registry fields:

| Queue state | Registry `lifecycle_stage` | Registry `status` | Registry `controller_action` |
|---|---|---|---|
| Inbox | discovery | testing | OFF |
| In Progress | first_pass | testing | OFF |
| Validation | validation | testing | OFF |
| Validated | watch | testing | OFF |
| Rejected | archived | rejected or archived | OFF |

**No registry item ever has `status=core`, `status=probation`, or
`controller_action != OFF` while it is being worked on inside FQL
Forge.** Those are Lane A transitions, reached via the explicit
promotion protocol in the doctrine.
