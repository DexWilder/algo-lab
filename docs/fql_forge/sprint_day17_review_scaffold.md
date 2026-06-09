# Sprint Day-17 Review Scaffold — Search-Basis Exhaustion Axis

> **Status:** Scaffold codified 2026-06-08 per operator decision #105-B; deep-updated 2026-06-09 (Day 12) per #114 fallback rule + no-idle doctrine.
> **Reviewed at:** Day-17 (2026-06-19) of 30-day Paper-Readiness Sprint.
> **Authority:** Lane B research; informs sprint scope decisions, not registry/portfolio mutation.

## Sprint anchor

- **Sprint start:** 2026-06-02 (Day 1)
- **Current snapshot:** 2026-06-09 (Day 12)
- **Day-17 review:** 2026-06-19 (7 days from snapshot)
- **Sprint end:** 2026-07-02 (Day 30; 18 days from snapshot)
- **Deliverable target:** 1-3 Paper-Readiness Packets accepted
- **Current status:** YELLOW per #114

## Day-12 trajectory math (deep update)

| Day | Packets accepted | Primitives shipped | Notable closed-loops |
|---:|---:|---:|---|
| 1-5 | 0 | n/a (campaign anchor 06-02) | n/a |
| 6 | 1 (EVT-NFP-MGC-Long-2h, 06-05) | 7 cumulative incl. event_window, vol_expansion, prior_day, session_close | NFP regime overlay fix |
| 7-11 | 1 (no new) | 8 cumulative (+RCB) | ORB matrix complete, PL-default codified |
| **12 (today)** | **1 (no new)** | **9 cumulative (+VRC ARCHIVED, BBKC RESEARCH_ONLY, gap_fill RESEARCH_ONLY)** | **cost-fragility hypothesis confirmed; hurst filters non-productive; ema_slope/fade mismatch** |

**Linear extrapolation:** 1 packet by Day 12 → ~2.5 by Day 30 IF the cadence persists. But cadence has DECELERATED — Packet #1 emerged Day 6; no Packet #2 in the 6 days since.

**Honest forecast:** 1 packet by Day 30 (status quo) UNLESS one of three interventions lands:
- Verified prop-cost data unlocks BBKC-MNQ-Both-PL or MCL Short PL/FR2 → potential +1 packet
- Bounded gap_fill retry with `filter=none` produces a viable candidate → potential +1 packet
- New mechanism family from Tier 2 NEEDS_PRIMITIVE (stop_run_reversal, opening_drive_continuation) → uncertain, potential +1 packet

## Day-17 review axes

### Axis 1 — Accepted packets

- Count of packets accepted with GREEN evidence-integrity audit
- Of those, count cleared for paper/live (operator decision separate)
- **Day 12 (2026-06-09):** 1 accepted (EVT-NFP-MGC-Long-2h, audit GREEN, not paper/live approved)

### Axis 2 — Packet candidates in flight

- Count of PASS_STRESS candidates pending family-review + 8-dim audit
- Concrete next-step for each
- **Day 12 (2026-06-09):** 0 (BBKC-MNQ-Both-PL is the closest near-miss but FAIL_STRESS at conservative-bias costs)

### Axis 3 — Portfolio complement candidates

- Count of candidates classified as PORTFOLIO_COMPLEMENT (PASS_STRESS + moderate family overlap)
- Pending operator portfolio-construction review
- **Day 12 (2026-06-09):** 2 (DIR-MES-ORB-Long-PL corr 0.42 to MNQ, DIR-MES-ORB-Short-PL corr 0.62 to MNQ) — unchanged

### Axis 4 — Observational inventory

- Count of OBSERVATIONAL candidates by reason blocked
- Distinct from "search-basis exhausted" — these are individual-candidate blockers
- **Day 12 (2026-06-09, by reason):**
  - DATA_REQUIRED (prop-cost): 2 (MCL Short-PL, MCL Short-FR2)
  - CURRENT_REGIME_WARNING + concentration: 2 (RCB15-MYM-Short, +VolLo variant)
  - **FAIL_STRESS cost-sensitive near-miss: 1 (BBKC-MNQ-Both-PL — PF 1.21, median $2.76, max-yr 44.9% CLEAN, n=837; cost break-even ~$3.00 RT vs current backtest $2.24)**
  - Paused family + FAIL_STRESS: ~7 (DC/PDB/PDF/RCB variants)
  - Filter-mismatch RESEARCH_ONLY: 1 (gap_fill_trigger; needs filter=none retry to fairly classify)
  - Paused family + FAIL_STRESS: ~6 (DC/PDB/PDF variants on MCL/MGC)
  - RCB RESEARCH_ONLY: 4 (08e RCB WATCH variants)

### Axis 5 — NEW: Saturated families (paused per #95 saturation rule)

- Count of (asset, family, primitive set) tuples currently paused
- Unlock criteria for each
- **Day 12 (2026-06-09):** 5 active pauses (1 new since 06-08)
  - MCL/MGC × non-ORB entries × ema_slope × profit_ladder (08c)
  - ZN/ZF × afternoon × pb_pullback/bb_reversion (08d)
  - 6E/6J × session-close × pb_pullback/bb_reversion/donchian (08d)
  - MCL × calendar-time event-window × existing event primitive (08f + 08h)
  - **Equity-index × hurst_stable_mr × bb_reversion** (08l deployment confirmed anti-edge)
  - **MES/MNQ × hurst_stable_trend × DC/ORB** (09a deployment confirmed sub-edge)
  - Note: hurst filters generally non-productive at intraday timescales per `research/data/fql_forge/hurst_filter_non_productive_finding.md`

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
- **Day 12 (2026-06-09):** 3 RESEARCH_ONLY + 1 ARCHIVED
  - range_compression_break (RCB) → RESEARCH_ONLY (concentration intrinsic)
  - bb_keltner_squeeze (BBKC) → RESEARCH_ONLY (thin signal; BBKC-MNQ cost-sensitive near-miss)
  - gap_fill_trigger → RESEARCH_ONLY (filter mismatch; needs filter=none retry to fairly classify)
  - volatility_regime_compound (VRC) → **ARCHIVED** (mechanism anti-edge)

### Axis 8 — NEW: DATA_REQUIRED queue

- Data unlocks proposed but not yet authorized
- Current queue order
- **Day 12 (2026-06-09), in priority order:**
  1. **Prop-firm cost rate sheet for MCL/MNQ/MES** (highest leverage per cumulative cost-fragility hypothesis — template ready at `docs/reports/prop_cost_verification/prop_cost_unlock_template_OPERATOR_TO_FILL.md`; pending operator submission)
  2. Surprise-conditioned EIA data (would revive crude × event family if added)
  3. Treasury auction calendar
  4. WASDE / grain asset onboarding
  5. COT-shift CFTC ingestion
  6. OPEC curated outcome list

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

| Requirement | Status as of Day 12 (2026-06-09) |
|---|---|
| Existing primitive set + existing data | EXHAUSTED (confirmed across 4 mechanism families: RCB, VRC, BBKC, gap_fill) |
| New primitive (Hybrid D-A pattern) | 3 attempted, 0 productive at packet-grade. Tier 2 remaining: stop_run_reversal, opening_drive_continuation. |
| **New data source — prop-firm cost rate sheet** | **HIGHEST LEVERAGE** — would directly test the cumulative cost-fragility hypothesis. Template ready; operator submission pending. |
| Other new data source (Treasury/WASDE/COT/EIA surprise) | Deferred per one-unlock-at-a-time rule |
| Bounded retry (gap_fill filter=none) | Pending #118 |
| Sprint scope revision | YELLOW status maintained per #114; not yet recommended |

### Day-12 cumulative-evidence narrative

After 4 mechanism-family explorations (compression, vol-regime, squeeze, gap-fade) all classify as RESEARCH_ONLY or ARCHIVED, the binding constraint emerging across all near-misses is **cost stress at conservative-bias backtest assumptions**, not mechanism discovery. The single most cost-sensitive candidate (BBKC-MNQ-Both-PL) would PASS_STRESS at a verified MNQ round-trip cost ≤ $3.00 vs. current backtest $2.24. **Operator-provided rate sheet is the most leveraged single intervention available.**

## Day-17 review template

When the Day-17 review fires (2026-06-19), produce a single document with:

1. **One-line sprint state**: "Day 17 of 30. N packets accepted. K candidates in flight. M paused families."
2. **Per-axis table** (axes 1-10 with current values)
3. **Trajectory analysis**: are we trending toward 1-3 packets by Day 30?
4. **Operator decisions needed**: explicit list of decisions blocking forward motion
5. **Sprint scope recommendation**: continue as-is / scope reduction / extension

## Trajectory math (updated Day 12)

At Day 12, Packet count = 1 (since Day 6). 5 additional cycles 08m/09a/09b explored 3 mechanism families with 0 new packets.

- **Linear extrapolation** (1 packet / 12 days observed): would project ~2.5 by Day 30.
- **Deceleration reality**: 0 new packets in the 6 days since Packet #1 (Day 6 → Day 12). If deceleration continues at current rate, expect ~1 by Day 30.
- **Honest forecast** (3 scenarios for Day 30):
  - Status quo (no operator intervention): **1 packet** (=Packet #1 only)
  - Operator prop-cost rate sheet provided AND BBKC-MNQ unlocks: **2 packets** (Packet #1 + BBKC-MNQ-Both-PL pending family review)
  - Operator prop-cost + filter-aligned gap_fill retry succeeds AND BBKC-MNQ unlocks: **2-3 packets**
  - Operator builds Tier 2 NEEDS_PRIMITIVE (stop_run_reversal) AND any preceding intervention productive: **2-3 packets**

**Recommendation:** Sprint stays YELLOW. Do not revise target until Day 17 review.

## Boundaries

- No Lane A change, no registry mutation, no scheduler change, no portfolio allocation change, no paper/live promotion, no OpenClaw upgrade.
- Lane B research-only.

## Source artifacts

- `research/data/fql_forge/observational_inventory_audit_2026-06-08.md` (Day-10 audit)
- `docs/fql_forge/asset_family_saturation_rule.md` (saturation taxonomy)
- `docs/fql_forge/exit_design_pl_workhorse_default.md` (PL-default doctrine)
- `research/data/fql_forge/kill_taxonomy.json` (campaign trail)
