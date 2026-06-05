# Directional Weighting Insight — XB-ORB-EMA-Ladder-MGC

> **Status:** Research evidence; NOT a deployment action.
> **Recorded:** 2026-06-05 per operator decision #78.
> **Requires separate operator approval** before any sizing/weighting/registry change.

## Finding

DAILY-DC-EMA-Ladder-MGC's existing probation workhorse (XB-ORB-EMA-Ladder-MGC) trades both directions with default `mode="both"`. Per the 2026-06-05 directional split diagnostic:

| Direction filter | n | PF | Median | Win rate | Sharpe (est) |
|---|---:|---:|---:|---:|---:|
| Both (current default) | 653 | 1.420 | $5.76 | 54.2% | 1.88 |
| Long-only | 387 | 1.362 | $4.76 | — | — |
| **Short-only** | **266** | **1.527** | **$8.76** | **56.4%** | 1.52 |

**MGC ORB SHORT trades show materially higher per-trade quality than LONG trades** (PF 1.527 vs implied LONG ~1.32; median $8.76 vs $4.76). Short side has fewer trades (~41% of total) but each trade has better expectancy.

## Family review (2026-06-05)

DIR-MGC-ORB-Short-PL vs XB-ORB-EMA-Ladder-MGC (both):
- 100% of SHORT days are same-day as BASE days
- All same-day pairs are same direction (no opposite-direction signal)
- Avg time separation: 0 minutes (literally simultaneous trades)
- Daily PnL correlation: 0.538

**Verdict:** DIR-MGC-ORB-Short-PL is a strict subset of XB-ORB-EMA-Ladder-MGC. Not a new candidate; not promotable as Packet #2. The short trades in DIR-MGC-ORB-Short-PL ARE the same short trades XB-ORB-EMA-Ladder-MGC takes — just with long trades excluded.

## Possible operator-led modifications (all REQUIRE separate approval)

1. **Direction-weighted sizing** — current XB-ORB-EMA-Ladder-MGC uses equal sizing per signal regardless of direction. Could be modified to scale SHORT positions larger (e.g., 1.3× short, 1.0× long) since short edge is stronger. Would require: sizing module change, walk-forward validation, audit.
2. **Direction-conditional regime controller** — keep both directions but use directional bias as input to position-sizing controller. Higher complexity.
3. **Pause/disable LONG side** — drop long signals entirely, run as short-only workhorse. Reduces total return but improves per-trade economics. Net portfolio impact unclear.
4. **No change** — accept the asymmetry as known feature of the strategy; deploy as-is.

## Constraints

- **No registry mutation** until operator decides.
- **No sizing change** until walk-forward validation.
- **No portfolio allocation change**.
- **No paper/live promotion** of any variant.
- This is research evidence; future operator decision required.

## Source artifacts

- `research/data/fql_forge/reports/forge_dir_mgc_orb_short_family_review_2026-06-05.json`
- `research/data/fql_forge/reports/forge_fixedratio_directional_lean_2026-06-05.json`
- `research/data/fql_forge/kill_taxonomy.json` (key: `_HEADLINE_2026-06-05_SHORT_PL_SUBSET_FINDING`)
