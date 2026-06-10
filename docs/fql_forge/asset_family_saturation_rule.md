# Asset-Family Saturation Rule — Forge Search Pruning Doctrine

> **Status:** CODIFIED FQL doctrine. Locked 2026-06-08 per operator decision #95; **narrow-scope correction locked 2026-06-09** per operator strategic correction.
> **Authority:** Lane B research heuristic; prunes Forge hunt prioritization. Does NOT mutate registry, scheduler, or runtime.
> **Trigger to codify:** Two consecutive focused cycles (08c commodity / 08d rates+FX) wiped out 32 non-ORB candidates with 0 packet-grade. Pattern explained by standard gates (median-negative, asymmetric trap, ARCHITECTURAL_REJECT).

## Strategic correction (2026-06-09) — SATURATION IS NARROW, NOT GLOBAL

**Saturation does NOT make any asset, broad family, or market "off limits."** A path is saturated only at the specific tuple of:

> `(asset, thesis, primitive, filter, exit, holding_period, data_basis)`

**A saturated path becomes REOPENABLE_WITH_NEW_THESIS when ANY of these change:**

1. New thesis (e.g., shift from momentum to fade on same asset)
2. New primitive (new entry/exit/filter mechanism)
3. New filter logic (different gating)
4. New session window (different time-of-day)
5. New holding period (different exit timing)
6. New event/data source (different signal trigger)
7. New asset expression (different contract series, micros vs full size)
8. New portfolio role (workhorse vs tail-engine vs hedge)

**Label REOPENABLE_WITH_NEW_THESIS** is the default disposition. PERMANENT_ARCHIVE is reserved for primitives that are mechanism-anti-edge regardless of pairing (e.g., VRC fade direction is the wrong side of the regime shift).

**The intent:** keep Forge from overfitting on dead exact-setups, NOT from exploring everywhere. Forge should be SEARCHING wide; saturation only stops repetition of an exact failed (asset, thesis, primitive, filter, exit, holding, data) tuple.

## Rule

**If two consecutive focused cycles across the same (asset, family, primitive set) produce no packet-grade candidates and the failures are explained by standard gates, PAUSE that family until one of the following changes:**

1. **New primitive added** to ENTRY_MAP / EXIT_MAP / FILTER_MAP that wasn't part of the prior cycles.
2. **New data source** added that enables an asset/event/regime previously unavailable.
3. **New asset or session** within the family that wasn't tested.
4. **New economic thesis** that re-frames the search basis (not a re-run of the same idea with a tweak).
5. **Explicit operator override** to retry the family despite the saturation flag.

**Do NOT require a third wipeout. Two clean wipeouts are sufficient to pause.**

## Standard gates that must explain the failures (for saturation to qualify)

- `KILL (median neg)` — negative median trade
- `KILL (PF<1.15)` — sub-edge profit factor
- `KILL (asymmetric trap: PF>1.2, median<0)` — wins outweigh losses in count but losses outweigh wins in magnitude
- `ARCHITECTURAL_REJECT (losing era)` — temporal-split exposed a losing middle/end era
- `ARCHITECTURAL_REJECT (<50% yrs+)` — fewer than half the years positive
- `ARCHITECTURAL_REJECT (Era-3 regime-wall fail)` — recent era PF < 1.0
- `KILL (n<30)` — insufficient sample

If failures are explained by these gates, saturation kicks in. If failures are mixed (e.g., one ERROR, one data-pipeline issue, etc.), the cycle does NOT count toward the saturation threshold — re-run with the issue fixed first.

## Legacy `Currently saturated families` table (superseded — see corrected table at top of doc)

This earlier framing implied broader pauses than the corrected narrow-tuple scope (locked 2026-06-09). The authoritative table is the **Currently saturated tuples** section near the top — all entries default to REOPENABLE_WITH_NEW_THESIS.

## How to apply

When designing future hunt cycles:
1. Read the **Currently saturated tuples** table (top of doc, post-2026-06-09 narrow scope).
2. If the proposed cycle reuses an EXACT saturated tuple (same asset + thesis + primitive + filter + exit + holding + data), **skip the exact repeat**.
3. If the proposed cycle DIFFERS from the saturated tuple in ANY dimension (new thesis, new filter, new holding period, new event basis, etc.), it is in scope — RUN IT.
4. When a new primitive is built, the saturation label for any tuple containing that primitive is automatically lifted for the NEXT cycle.
5. Default disposition for failed tuples is REOPENABLE_WITH_NEW_THESIS. PERMANENT_ARCHIVE only for mechanism-anti-edge primitives (e.g., VRC).

## Rationale

A weaker system would keep generating marginal candidates within an exhausted primitive set until something looked good enough for promotion. Codifying saturation forces Forge to spend cycles where they have a chance to produce real edge, not on grinding diminishing-return permutations.

## Counter-example revoke clause

If a future cycle uses a saturated combination AND finds a genuine packet-grade candidate that passes all gates (cheap-screen + temporal + prop-stress + family-review + 8-dim audit), this rule is revoked pending re-evaluation. Until then, the rule stands.

## Unlock criteria activation tracker

| Unlock criterion | Status (2026-06-08) | Notes |
|---|---|---|
| New entry primitive: range_compression_break | **SHIPPED 2026-06-08** (08e/08g) | Productive but not packet-grade: first PASS_STRESS blocked by concentration |
| EIA-Wed-MCL crude inventory calendar | **SHIPPED 2026-06-08** (08h) | First screen wiped out 5/5; calendar reserved for future surprise-conditioned variants |
| Surprise-conditioned crude event signals (EIA print vs consensus) | DATA_REQUIRED | Required to revive crude × calendar-time × event family per #101 |
| Treasury auction calendar | DATA_REQUIRED | Deferred per #99 (one bounded data unlock at a time) |
| Grain asset onboarding (WASDE candidates) | DATA_REQUIRED | Deferred per #99 |
| COT-shift CFTC ingestion | DATA_REQUIRED | Deferred per #99 |
| Vol-regime overlay investigation on RCB candidates | **IN PROGRESS** (08i per #102) | Uses existing vol_regime filters, no new primitive build |

## Source artifacts

- `research/forge_cycle_2026-06-08c.py` + report (18-candidate commodity wipeout)
- `research/forge_cycle_2026-06-08d.py` + report (14-candidate rates+FX wipeout)
- `research/data/fql_forge/non_orb_mcl_mgc_wipeout_insight.md` (08c closed-loop finding)
- `research/data/fql_forge/kill_taxonomy.json` keys `_HEADLINE_2026-06-08c_NON_ORB_MCL_MGC_WIPEOUT` + `_HEADLINE_2026-06-08d_RATES_FX_WIPEOUT` + `_aggregate_2026-06-08c_d`
