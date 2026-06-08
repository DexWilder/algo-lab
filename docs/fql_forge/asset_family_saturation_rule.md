# Asset-Family Saturation Rule — Forge Search Pruning Doctrine

> **Status:** CODIFIED FQL doctrine. Locked 2026-06-08 per operator decision #95.
> **Authority:** Lane B research heuristic; prunes Forge hunt prioritization. Does NOT mutate registry, scheduler, or runtime.
> **Trigger to codify:** Two consecutive focused cycles (08c commodity / 08d rates+FX) wiped out 32 non-ORB candidates with 0 packet-grade. Pattern explained by standard gates (median-negative, asymmetric trap, ARCHITECTURAL_REJECT).

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

## Currently saturated families (as of 2026-06-08)

| (asset, family, primitive set) | Cycles | Verdict |
|---|---|---|
| MCL/MGC × non-ORB entries (pb_pullback, bb_reversion, vwap_continuation, prior_day_fade) × ema_slope × profit_ladder | 1 (08c: 18 candidates) | **PAUSED** |
| ZN/ZF × afternoon (pb_pullback, bb_reversion) × profit_ladder | 1 (08d: 6 candidates) | **PAUSED** |
| 6E/6J × session-close/morning (pb_pullback, bb_reversion, donchian_breakout) × profit_ladder | 1 (08d: 8 candidates) | **PAUSED** |
| MNQ/MES/MYM × ORB-family × directional-split | 4+ cycles concluded | **DIAGNOSTIC COMPLETE** (per separate ORB directional asymmetry diagnostic) |

**Note:** Aggregated, 08c + 08d constitute the saturation trigger for the broader "non-ORB workhorse hunt with existing primitives" search basis on commodity / rates / FX intraday futures. The hunt is paused until the unlock criteria are met.

## How to apply

When designing future hunt cycles, check this doctrine doc:
1. Read the "Currently saturated families" table.
2. If the proposed cycle reuses a saturated combination, **do not run it** without (a) adding a new primitive, (b) loading a new data source, (c) explicit operator override.
3. When a new primitive is built, the saturation flag for any family containing that primitive is automatically lifted for the NEXT cycle.

## Rationale

A weaker system would keep generating marginal candidates within an exhausted primitive set until something looked good enough for promotion. Codifying saturation forces Forge to spend cycles where they have a chance to produce real edge, not on grinding diminishing-return permutations.

## Counter-example revoke clause

If a future cycle uses a saturated combination AND finds a genuine packet-grade candidate that passes all gates (cheap-screen + temporal + prop-stress + family-review + 8-dim audit), this rule is revoked pending re-evaluation. Until then, the rule stands.

## Unlock criteria activation tracker

| Unlock criterion | Status (2026-06-08) | Notes |
|---|---|---|
| New entry primitive: range_compression_break | **IN PROGRESS** (cycle 08e, per operator decision #94 Hybrid D) | Targets vol-contraction-then-expansion mechanism |
| New data source | none in flight | Treasury auction calendar still DATA_REQUIRED |
| New asset / session | none in flight | Event-window NFP template restart targeted at metals/commodities (Hybrid D leg B) |
| New economic thesis | none in flight | Saturation rule does NOT block thesis-driven sparse-event candidates |

## Source artifacts

- `research/forge_cycle_2026-06-08c.py` + report (18-candidate commodity wipeout)
- `research/forge_cycle_2026-06-08d.py` + report (14-candidate rates+FX wipeout)
- `research/data/fql_forge/non_orb_mcl_mgc_wipeout_insight.md` (08c closed-loop finding)
- `research/data/fql_forge/kill_taxonomy.json` keys `_HEADLINE_2026-06-08c_NON_ORB_MCL_MGC_WIPEOUT` + `_HEADLINE_2026-06-08d_RATES_FX_WIPEOUT` + `_aggregate_2026-06-08c_d`
