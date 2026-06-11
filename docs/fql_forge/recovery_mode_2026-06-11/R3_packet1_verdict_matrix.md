# R3 — Packet #1 Verdict Matrix (3 Filters × Gate Sets)

> **Authority:** Operator #168 R3 (Recovery Mode 2026-06-11).
> **Inputs:** R1 canonical filter (strict+hold-continuity), R2 tail-engine gates, cycle 11j re-audit data.

## The 3×3 verdict matrix

Rows = filter version. Columns = gate set applied. Cell = ALL_PASS verdict.

| Filter | Workhorse #157 gates | Tail-engine R2 gates | Canonical verdict |
|---|---|---|---|
| **Permissive (10g basis)** | FAIL Era3-med | FAIL PF (1.91 below STRONG) — fails STRONG | INVALID FILTER (R1: not canonical) |
| **Strict (next-bar only)** | FAIL Era3-med | **MARGINAL PASS** (PF 2.107, max-yr 38% borderline vs 35%, instance frac 87.5%) | INVALID FILTER (R1: not canonical for hold) |
| **Strict + hold-continuity (CANONICAL per R1)** | **FAIL** (PF 1.25, max-yr 97.9%, Era3-med) | **FAIL** (PF, stress, max-yr 97.9%, instance frac 50%) | **CANONICAL VERDICT** |

## Detailed per-cell evaluation

### Cell A: Permissive × Workhorse gates
- PF 1.905 ✓ / median +$14.26 ✓ / yrs+ 6/8 ✓ / max-yr 40.1% ✓ / Era3 PF 1.72 ✓
- **Era3 median -$22.24 ✗**
- ALL PASS: False
- Disposition: FAIL (1 gate); but FILTER IS INVALID per R1 → not actionable

### Cell B: Permissive × Tail-engine gates
- PF 1.905 < 1.30 STRONG? Wait — 1.905 ≥ 1.30, so ✓
- max-yr 40.1% > 35% ✗ (fails tail-engine concentration)
- yrs+ 6/8 = 75% ≥ 60% ✓
- Stress PF 1.808 ✓
- Era3 PF 1.72 ✓
- ALL PASS: False (max-yr concentration fails)
- But FILTER IS INVALID per R1

### Cell C: Strict × Workhorse gates
- PF 2.107 ✓ / median +$13.76 ✓ / yrs+ 7/8 ✓ / max-yr 38.0% ✓ / Era3 PF 1.70 ✓
- **Era3 median -$22.24 ✗**
- ALL PASS: False (Era3 median)
- But FILTER IS INVALID per R1

### Cell D: Strict × Tail-engine gates (THE BEST CASE FOR PACKET #1)
- PF 2.107 ≥ 1.30 STRONG ✓
- max-yr 38.0% > 35% ✗ (marginal — 3pp over tail-engine limit)
- yrs+ 7/8 = 87.5% ≥ 60% ✓
- Stress PF 1.996 ✓
- Era3 PF 1.70 ✓
- Era3 median -$22.24 (soft flag, not hard fail)
- **ALL HARD GATES: FAIL by 3 percentage points on max-yr**
- Could PASS if max-yr threshold is 40% instead of 35% (operator policy choice)
- **But FILTER IS INVALID per R1**

### Cell E: Strict+hold-continuity × Workhorse gates (CANONICAL FILTER, WORKHORSE GATES)
- PF 1.250 < 1.30 ✗
- max-yr 97.9% > 50% ✗
- Era3 median -$6.24 ✗
- **ALL PASS: False (fails 3 gates)**

### Cell F: Strict+hold-continuity × Tail-engine gates (CANONICAL FILTER, TAIL-ENGINE GATES)
- PF 1.250 < 1.30 STRONG ✗
- Stress PF 1.142 < 1.30 ✗ (knife-edge, not robust)
- max-yr 97.9% > 35% ✗
- yrs+ 4/8 = 50% < 60% ✗
- Era3 PF 1.07 ✓ (barely)
- Era3 median -$6.24 (soft flag)
- **ALL HARD GATES: FAIL** (fails 4 hard gates: PF, stress, max-yr, instance fraction)

## Canonical verdict (Cell F — R1 canonical filter + R2 tail-engine gates)

**Packet #1 NFP-MGC-Long-2h → FAIL canonical re-audit.**

The candidate fails 4 of the 7 hard tail-engine gates on the canonical filter. The PF only marginally exceeds VIABLE (1.15) but is below STRONG (1.30). Stress survival is knife-edge. Concentration is catastrophic (97.9% from 2024 year). Positive instance fraction is exactly the 50% workhorse threshold but below the 60% tail-engine threshold.

## Operator decision path

| Recommended status | Rationale |
|---|---|
| **ARCHIVED (RECOMMENDED)** | Canonical filter + canonical gates clearly fail. The candidate's prior acceptance was based on $4314.96 of fictitious PnL from 21 multi-day data outages. The TRUE underlying edge (42 events, PF 1.25, 97.9% max-yr) is not packet-grade. Best practice: archive with REOPENABLE_WITH_NEW_THESIS label. |
| REOPEN / REVIEW (alternative) | Keep door open if operator believes the next-bar-only strict filter (Cell D, marginal pass with max-yr 38%) is canonical. But this contradicts R1 recommendation. |
| RESTORE_ACCEPTED (NOT RECOMMENDED) | Would require using permissive filter (invalid per R1) or lowering canonical gate thresholds. Either is discretion preserving acceptance, which #162 forbade. |

## Sprint impact

Per R5 sprint reset note, if Packet #1 is archived:
- Accepted packet count: 0
- Day 16/30 of sprint
- 0 active Packet #2 candidates
- 1 conditional portfolio_complement (BBKC-MNQ, cost-required)
- 5 search bases exhausted

Sprint deliverable "1-3 paper packets" is at zero progress; the sprint is in RED Recovery Mode with no clear path to packet-grade in 14 remaining days under existing constraints.
