# Directional Asymmetry Insight — XB-ORB-EMA-Ladder-MNQ

> **Status:** Research evidence; supports existing both-direction MNQ probation strategy.
> **Recorded:** 2026-06-08 per operator decision #89 (MNQ directional split diagnostic).
> **No registry/portfolio change.** Subsets of existing probation, NOT new candidates.

## Finding

XB-ORB-EMA-Ladder-MNQ (existing primary workhorse, promoted 2026-04-06; live forward; PF 1.62 / 1183 trades on probation) trades both directions with default `mode="both"`. The 2026-06-08 directional split diagnostic reveals **a LONG > SHORT asymmetry — the OPPOSITE direction from MGC/MCL.**

| Direction filter (MNQ ORB) | n | PF | Median | Net | Verdict |
|---|---:|---:|---:|---:|---|
| Both-direction baseline (existing probation) | 1216 | 1.608 | $42.76 | $49,495 | reference |
| **LONG-only** | **811** | **1.726** | $41.76 | $36,200 (est) | **strongest LONG of any asset** |
| SHORT-only | 405 | 1.489 | $46.26 | $19,200 (est) | strong but weaker than LONG |
| Both directions PASS_STRESS | — | — | — | — | confirmed |

**Both directions carry edge. LONG side carries the stronger PF; SHORT side has slightly higher median per trade. Neither side is dead weight.**

## Family review

- MNQ-Long vs MNQ-both: corr 0.604, day-overlap 100% of MNQ-Long days
- MNQ-Short vs MNQ-both: corr 0.789, day-overlap 100% of MNQ-Short days
- **Verdict for both:** DIRECTIONAL_INSIGHT_OF_EXISTING_PROBATION — explicit subsets, not new candidates

## Updated cross-asset directional asymmetry matrix (5 assets characterized)

| Asset | LONG PF | SHORT PF | LONG-SHORT direction | Asymmetry type |
|---|---:|---:|---|---|
| MGC ORB | 1.362 | 1.527 | SHORT stronger | Good + Better (mild SHORT bias) |
| MCL ORB | 1.014 (null) | 1.41-1.45 | SHORT only | Null + Alive (LONG dead) |
| MYM ORB | 1.568 | 1.578 | tied | Symmetric |
| MES ORB | 1.394 | 1.482 | SHORT slightly stronger | Symmetric-leaning |
| **MNQ ORB** | **1.726** | **1.489** | **LONG stronger** | **Good + Better (LONG bias)** |

**MNQ is the ONLY asset where LONG is stronger than SHORT.** Mechanism: Nasdaq has strong upward bias over the historical window; LONG ORB breakouts catch sustained trend-up moves more frequently than SHORT catches trend-down moves.

## Implication

- The existing XB-ORB-EMA-Ladder-MNQ probation strategy uses `mode="both"` — this is appropriate because both sides carry real edge.
- The LONG-bias finding is research evidence; would NOT recommend tilting MNQ sizing because BOTH sides have strong PF and the asymmetry could revert under different equity regimes.
- The MCL/MGC modification template (remove LONG / sizing-modifier) does NOT transfer to MNQ. Each asset's directional asymmetry must be characterized independently.

## ORB-family directional asymmetry diagnostic — COMPLETE

This concludes the cross-asset ORB-family directional diagnostic per operator's pivot directive. All five XB-ORB-EMA-Ladder-eligible assets (MGC/MCL/MYM/MES/MNQ) have been characterized. **Pivoting next-cycle hunt to non-ORB edge families for Packet #2.**

## Constraints

- **No registry mutation.** No probation strategy change.
- **No sizing change.** Existing both-direction MNQ is validated as optimal under current evidence.
- **No portfolio allocation change.**
- Research-only Lane B finding.

## Source artifacts

- `research/forge_cycle_2026-06-08b.py` (MNQ diagnostic + PL/FR2 n+5)
- `research/data/fql_forge/reports/forge_cycle_2026-06-08b.json`
- `research/data/fql_forge/kill_taxonomy.json` key `_HEADLINE_2026-06-08b_MNQ_LONG_BIAS_ASYMMETRY`
