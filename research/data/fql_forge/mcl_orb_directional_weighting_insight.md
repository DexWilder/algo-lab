# Directional Weighting Insight — XB-ORB-EMA-Ladder-MCL

> **Status:** Research evidence; NOT a deployment action.
> **Recorded:** 2026-06-05 per operator decision #82.
> **Requires separate operator approval** before any sizing/weighting/registry change.

## Finding

XB-ORB-EMA-Ladder-MCL (existing CANDIDATES probation entry) trades both directions with default `mode="both"`. The 2026-06-05 directional split diagnostic and prior-cycle MCL hunt reveal extreme directional asymmetry — far more extreme than the MGC case.

| Direction filter (MCL ORB) | n | PF | Median | Yrs+ | Verdict |
|---|---:|---:|---:|---|---|
| LONG-only (prior cycle) | 461 | 1.014 | $4.76 | 4/6 | **KILL** (essentially no edge) |
| Both (existing both-direction baseline; XB-DC-EMA-Ladder-MCL similar pattern) | ~930 | ~1.20 | ~$3.76 | 5/6 | WATCH-decaying |
| **SHORT-only profit_ladder** | **469** | **1.408** | **$7.76** | **5/6** | clean cheap-screen |
| **SHORT-only fixed-ratio R2** | **469** | **1.452** | **$3.76** | **6/6 (PERFECT)** | clean cheap-screen |

**MCL ORB SHORT carries the entire edge. LONG side is essentially dead** (PF 1.014 with median $4.76 isn't statistically distinguishable from zero edge once costs/slippage stress in). Combining LONG + SHORT in the existing both-direction baseline → the LONG side acts as **dead-weight drag** on the SHORT edge.

This is materially different from the MGC case where BOTH directions had real edge and short was slightly stronger. In MCL, the asymmetry is **null + alive**, not **good + better**.

## Family review status (2026-06-05)

Family review of P1-MCL-ORB-Short-PL and P1-MCL-ORB-Short-FR2 vs XB-ORB-EMA-Ladder-MCL queued per operator decision #81 — see operator packet for outcome.

## Prop-stress status

**Both MCL SHORT candidates FAIL prop-stress.** Median collapses near zero at 2× cost + 2 tick slip. Cannot promote to PAPER_PACKET tier per strict-prop-stress rule (locked #84).

→ **Classification: OBSERVATIONAL.**

## Possible operator-led modifications (all REQUIRE separate approval)

1. **Remove LONG side of XB-ORB-EMA-Ladder-MCL** — run as MCL ORB SHORT-only workhorse. Would preserve entire edge and eliminate LONG drag.
2. **Disable LONG entries below an edge threshold** — keep LONG capability for future regime changes but require minimum recent PF to fire.
3. **Direction-conditional sizing** — scale LONG positions to half size; SHORT to full size. Less drastic; preserves optionality.
4. **No change** — accept the asymmetric drag as known feature; deploy as-is.

## Constraints

- **No registry mutation** until operator decides.
- **No sizing change** until walk-forward validation.
- **No portfolio allocation change**.
- **No paper/live promotion** of any variant.
- **No scheduler change**.
- This is research evidence; future operator decision required.
- Prop-stress fragility must be resolved or explicitly accepted before deployment in any form.

## Comparison vs MGC ORB pattern

| Asset | LONG edge | SHORT edge | Asymmetry type | Operator action |
|---|---|---|---|---|
| MGC ORB | PF 1.362 (real) | PF 1.527 (better) | Good + Better | Sizing-modifier candidate |
| **MCL ORB** | **PF 1.014 (null)** | **PF 1.41-1.45 (alive)** | **Null + Alive** | **Direction-disable candidate** |

The MCL case is the stronger argument for an operator-led modification because the LONG side is genuinely dead-weight, not just under-performing.

## Source artifacts

- `research/data/fql_forge/reports/forge_non_mgc_orb_hunt_2026-06-05.json`
- `research/data/fql_forge/reports/forge_dir_mgc_orb_short_family_review_2026-06-05.json` (precedent)
- `research/data/fql_forge/kill_taxonomy.json` (key: `_HEADLINE_2026-06-05b_MCL_SHORT_ASYMMETRY`)
- Future MCL family review JSON (pending #81)
