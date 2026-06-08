# Sprint Day-17 Review Scaffold — Search-Basis Exhaustion Axis

> **Status:** Scaffold. Codified 2026-06-08 per operator decision #105-B.
> **Reviewed at:** Day-17 (2026-06-19) of 30-day Paper-Readiness Sprint.
> **Authority:** Lane B research; informs sprint scope decisions, not registry/portfolio mutation.

## Sprint anchor

- **Sprint start:** 2026-06-02 (Day 1)
- **Day-17 review:** 2026-06-19
- **Sprint end:** 2026-07-02 (Day 30)
- **Deliverable target:** 1-3 Paper-Readiness Packets accepted

## Day-17 review axes

### Axis 1 — Accepted packets

- Count of packets accepted with GREEN evidence-integrity audit
- Of those, count cleared for paper/live (operator decision separate)
- **Current (2026-06-08):** 1 accepted (EVT-NFP-MGC-Long-2h, audit GREEN, not paper/live approved)

### Axis 2 — Packet candidates in flight

- Count of PASS_STRESS candidates pending family-review + 8-dim audit
- Concrete next-step for each
- **Current (2026-06-08):** 0

### Axis 3 — Portfolio complement candidates

- Count of candidates classified as PORTFOLIO_COMPLEMENT (PASS_STRESS + moderate family overlap)
- Pending operator portfolio-construction review
- **Current (2026-06-08):** 2 (DIR-MES-ORB-Long-PL, DIR-MES-ORB-Short-PL)

### Axis 4 — Observational inventory

- Count of OBSERVATIONAL candidates by reason blocked
- Distinct from "search-basis exhausted" — these are individual-candidate blockers
- **Current (2026-06-08, by reason):**
  - DATA_REQUIRED (prop-cost): 2 (MCL Short-PL, MCL Short-FR2)
  - CURRENT_REGIME_WARNING + concentration: 2 (RCB15-MYM-Short, +VolLo variant)
  - Paused family + FAIL_STRESS: ~6 (DC/PDB/PDF variants on MCL/MGC)
  - RCB RESEARCH_ONLY: 4 (08e RCB WATCH variants)

### Axis 5 — NEW: Saturated families (paused per #95 saturation rule)

- Count of (asset, family, primitive set) tuples currently paused
- Unlock criteria for each
- **Current (2026-06-08):** 4 active pauses
  - MCL/MGC × non-ORB entries × ema_slope × profit_ladder (08c)
  - ZN/ZF × afternoon × pb_pullback/bb_reversion (08d)
  - 6E/6J × session-close × pb_pullback/bb_reversion/donchian (08d)
  - MCL × calendar-time event-window × existing event primitive (08f + 08h)

### Axis 6 — NEW: Exhausted primitive layers

- Count and list of primitive layers that have been fully diagnosed
- Distinct from saturated families (saturation = specific tuple; exhaustion = whole layer)
- **Current (2026-06-08):**
  - ORB-family directional asymmetry diagnostic = COMPLETE (5/5 assets characterized; no more directional insight to extract)
  - PL vs FR2 cost-fragility diagnostic = COMPLETE (n=10 + codification)
  - Vol-regime overlay on RCB = COMPLETE (mechanism-intrinsic concentration confirmed)

### Axis 7 — NEW: Productive primitives that failed packet gates

- Primitives that shipped, tested, and produced signal but did not reach packet-grade
- Classification: RESEARCH_ONLY available for future thesis-driven use
- **Current (2026-06-08):** 1 (range_compression_break — RESEARCH_ONLY per #104)

### Axis 8 — NEW: DATA_REQUIRED queue

- Data unlocks proposed but not yet authorized
- Current queue order
- **Current (2026-06-08), in queued order:**
  1. Surprise-conditioned EIA data (would revive crude × event family if added)
  2. Treasury auction calendar
  3. WASDE / grain asset onboarding
  4. COT-shift CFTC ingestion
  5. OPEC curated outcome list

### Axis 9 — NEW: Candidate quality by reason blocked

For each PASS_STRESS or near-PASS_STRESS candidate, classify by blocking reason:
- **FAIL_STRESS** (most common): edge too thin for prop-firm cost ladder
- **Family overlap**: duplicate exposure to existing probation
- **Concentration**: max-yr ≥ 50%
- **Current-regime weakness**: Era3 median ≤ 0
- **Asymmetric P&L**: PF > 1.2 with median < 0 (locked NEVER-packet)
- **DATA_REQUIRED**: pending operator-approved data unlock
- **Sample collapse**: filter mechanically removed signal (e.g., RCB+VolHi)

**Current (2026-06-08) blocking-reason distribution:**
- FAIL_STRESS: ~10
- Family overlap: 6 (4 directional-insight subsets + 2 PORTFOLIO_COMPLEMENT)
- Concentration: 2 (RCB-MYM family)
- Current-regime weakness: 2 (RCB-MYM, PDF-MGC)
- DATA_REQUIRED: 2 (MCL Short PL/FR2)

### Axis 10 — NEW: Packet #2 next-direction requirement

Explicit operator-facing question: **what does Packet #2 need?**

| Requirement | Status |
|---|---|
| Existing primitive set + existing data | EXHAUSTED |
| New primitive (Hybrid D-A pattern) | One needed (volatility_regime_compound recommended) |
| New data source | At least one needed (surprise-conditioned crude or Treasury or WASDE) |
| Sprint scope revision | If Packet #2 cannot fit in 30 days, consider scope reduction (e.g., Packet #2 = PORTFOLIO_COMPLEMENT not paper-packet) |

## Day-17 review template

When the Day-17 review fires (2026-06-19), produce a single document with:

1. **One-line sprint state**: "Day 17 of 30. N packets accepted. K candidates in flight. M paused families."
2. **Per-axis table** (axes 1-10 with current values)
3. **Trajectory analysis**: are we trending toward 1-3 packets by Day 30?
4. **Operator decisions needed**: explicit list of decisions blocking forward motion
5. **Sprint scope recommendation**: continue as-is / scope reduction / extension

## Trajectory math (current)

At Day 10, Packet count = 1. Cycle 08a-08i produced ~85 candidates, 0 new packets.

- **Linear extrapolation** (1 packet / 10 days): expect ~3 by Day 30 — meets target.
- **Conditional reality**: 0 packets emerged in last 4 cycles (08c+08d+08g+08i wipeouts/no-upgrade). Linear extrapolation overstates if current search-basis exhaustion continues.
- **Honest forecast**: Without new primitive or new data, expect 1 (current) packet by Day 30. With one new primitive build, expect 1-2. With one new data unlock, expect 1-2. With both, expect 1-3.

## Boundaries

- No Lane A change, no registry mutation, no scheduler change, no portfolio allocation change, no paper/live promotion, no OpenClaw upgrade.
- Lane B research-only.

## Source artifacts

- `research/data/fql_forge/observational_inventory_audit_2026-06-08.md` (Day-10 audit)
- `docs/fql_forge/asset_family_saturation_rule.md` (saturation taxonomy)
- `docs/fql_forge/exit_design_pl_workhorse_default.md` (PL-default doctrine)
- `research/data/fql_forge/kill_taxonomy.json` (campaign trail)
