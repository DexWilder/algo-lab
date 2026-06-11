# R2 — Tail-Engine Gate Doctrine for Event-Window Candidates

> **Authority:** Operator #168 R2 (Recovery Mode 2026-06-11).
> **Status:** RECOMMENDATION (operator decision pending ratification).
> **Reference:** CLAUDE.md `Factory Classification` (dual archetype, 2026-04-07), [[feedback_dual_archetype_factory]].

## The mismatch that created the RED verdict

The `Era3_median_>=_0` gate in #157/#162 is a workhorse-leaning gate that assumes the candidate trades hundreds-of-thousands of trades with median trade ≥ 0 as a stability check. For tail-engine candidates (n < 500, sparse high-variance events like Packet #1's 42-68 events), this gate may incorrectly fail candidates whose positive expectancy comes from outlier wins.

CLAUDE.md tail-engine gates do NOT include Era3 median ≥ 0. They focus on instance-level stability (CV, positive instance fraction).

## Recommendation: Tail-engine gate set for event-window candidates

For ANY event-window candidate with n < 500 trades, apply the following gate set:

| # | Gate | Threshold | Rationale |
|---|---|---|---|
| 1 | n ≥ 20 | Hard | Statistical minimum for tail estimation |
| 2 | Positive median trade | recommended but NOT hard-fail | Tail engines may have neg median + pos PF; check but don't auto-kill |
| 3 | **PF ≥ 1.30** | Hard | Per CLAUDE.md STRONG threshold (not the 1.15 VIABLE) |
| 4 | PASS_STRESS at 2× cost + 2 ticks slip | Hard | Cost-robustness baseline |
| 5 | **Max single instance ≤ 35%** | Hard | Per CLAUDE.md tail-engine concentration limit; *applies per-year share* |
| 6 | **Positive instance fraction ≥ 60%** | Hard | Per CLAUDE.md tail-engine stability; *years with positive net* |
| 7 | **Instance CV ≤ 3.0** | Hard | Per CLAUDE.md cross-instance stability; std/mean of per-year nets |
| 8 | Era 3 PF ≥ 1.0 | Hard | Regime-wall; ensures recent regime is not failing |
| 9 | Era 3 median ≥ 0 | **DEMOTED to SOFT** | For tail engines, flag but don't auto-fail; surface to operator |
| 10 | Max DD duration ≤ 900d | Hard | Per CLAUDE.md tail-engine recovery test |

**Soft gates** (flag but don't auto-fail; surface for operator judgment):
- Era 3 median sign
- Year-exclusion PF robustness
- Rolling 12-event PF windows

## Why the change?

For tail engines, the **PF (gross win / gross loss)** is the primary edge measure. Median is informational. Workhorse tactics with thousands of small trades NEED median ≥ 0 because the median IS the typical trade. Tail engines win by outlier capture — median can legitimately be negative with positive PF.

Example (Packet #1 strict): PF 2.107, median +$13.76, Era3 PF 1.70, Era3 median -$22.24. The Era3 median says "in the last third, the typical NFP day loses $22" but Era 3 PF says "in the last third, wins are 1.7× losses by gross dollars." Both are true; both inform; neither alone is decisive for a tail engine.

## What this doctrine does NOT change

- Concentration limits stay strict (max single instance 35% for tail engines, often stricter than workhorses at 40%)
- Stress robustness stays hard
- Era 3 PF ≥ 1.0 stays hard (the regime-wall guard)
- Cross-asset / family-review independence stays required for portfolio-impact decisions

## Applied to Packet #1 strict+hold-continuity (canonical filter per R1)

| Gate | Value | Pass? |
|---|---|---|
| n ≥ 20 | 42 | ✅ |
| Positive median | +$12.26 | ✅ (informational) |
| PF ≥ 1.30 | 1.250 | ❌ |
| PASS_STRESS | PF 1.142 stress | ❌ (barely above 1.0 floor — KNIFE_EDGE) |
| Max-yr ≤ 35% | 97.9% | ❌ |
| Positive instance fraction ≥ 60% | 4/8 = 50% | ❌ |
| Instance CV ≤ 3.0 | (compute pending) | — |
| Era 3 PF ≥ 1.0 | 1.07 | ✅ (barely) |
| Era 3 median (soft) | -$6.24 | flag |
| Max DD duration ≤ 900d | (compute pending) | — |

**Tail-engine gates also FAIL Packet #1 on canonical filter** (fails PF, stress, max-yr, instance fraction).

The gate set choice (workhorse vs tail-engine) does NOT rescue Packet #1 once the canonical filter is applied. The issue is real, not a gate-mismatch artifact.

## Operator action

Ratify or amend per #165-168 response. If ratified:
- Apply tail-engine gates to all future event-window candidates with n < 500
- Update audit doctrine to require gate-set declaration in every audit
- Update verdict matrix (R3) using these gates
