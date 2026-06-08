# Directional Symmetry Insight — XB-ORB-EMA-Ladder-MYM

> **Status:** Research evidence; supports existing both-direction MYM probation strategy.
> **Recorded:** 2026-06-08 per operator decision #86 (directional asymmetry expansion).
> **No registry/portfolio change.** Validation of an existing probation strategy, not a new candidate.

## Finding

XB-ORB-EMA-Ladder-MYM (existing probation workhorse, promoted 2026-04-13 via intraday-autocorrelation expansion screen) trades both directions with default `mode="both"`. Unlike MCL and MGC where directional asymmetry is material, **MYM is symmetric — both directions carry essentially equal edge**.

| Direction filter (MYM ORB) | n | PF | Median | Net | Verdict |
|---|---:|---:|---:|---:|---|
| Both-direction baseline (existing probation) | 380 | 1.573 | $13.76 | $6,947 | reference |
| LONG-only | 238 | 1.568 | $13.76 | $3,672 | symmetric |
| SHORT-only | 142 | 1.578 | $14.26 | $3,275 | symmetric |

**Both directions carry edge. There is NO LONG drag to remove. No SHORT drag to remove.**

## Cross-asset directional asymmetry matrix (consolidated)

| Asset | LONG-only edge | SHORT-only edge | Asymmetry type | Operator action implication |
|---|---|---|---|---|
| MGC ORB | PF 1.362 (real) | PF 1.527 (better) | Good + Better | Possible sizing-modifier (under #85 verification) |
| MCL ORB | PF 1.014 (null) | PF 1.41-1.45 (alive) | Null + Alive | Direction-disable candidate (under #85 verification) |
| **MYM ORB** | **PF 1.568 (real)** | **PF 1.578 (real)** | **Symmetric** | **No change needed — existing both-direction is optimal** |
| MES ORB (this cycle, no existing probation) | PF 1.394 (real) | PF 1.482 (real) | Mildly better short | New PORTFOLIO_COMPLEMENT candidate |
| MNQ ORB | n/a (treated as both via existing probation; no directional split run this cycle) | n/a | n/a (worth running for completeness) | Re-run later |

## Implication

- The existing XB-ORB-EMA-Ladder-MYM probation strategy is **not** carrying directional drag. Both directions earn their place. No mutation is justified.
- This is the OPPOSITE finding from MCL (where the LONG side is dead weight). MCL/MGC modifications under #85 verification are NOT a template that automatically transfers to MYM.
- The cross-asset directional matrix is now richer: asymmetry is asset-specific and must be characterized per asset before any sizing/weighting decision.

## Comparison vs MGC pattern

MGC: SHORT slightly better than LONG; both real. Possible mild sizing modifier.

MYM: SHORT essentially equal to LONG; both real. No modifier justified.

## Constraints

- **No registry mutation.** No probation strategy change.
- **No sizing change.** Existing both-direction MYM is validated.
- This is positive evidence for the existing MYM probation strategy.
- Research-only Lane B finding.

## Source artifacts

- `research/forge_cycle_2026-06-08a.py` (directional batch)
- `research/forge_cycle_2026-06-08a_family_review.py` (family review)
- `research/data/fql_forge/reports/forge_cycle_2026-06-08a_family_review.json` (subset overlap analysis)
- `research/data/fql_forge/reports/forge_cycle_2026-06-08a.json` (stress + directional)
