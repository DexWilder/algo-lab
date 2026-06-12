# Cross-Asset Simple Hypothesis — Narrow Saturation Annotation (2026-06-12)

> **Authority:** Operator #199 A.
> **Doctrine:** [[feedback_asset_family_saturation_rule]] — narrow saturation, REOPENABLE_WITH_NEW_THESIS.
> **Status:** Lane B research annotation. No registry mutation.

## What is saturated

**Saturated:** simple cross-asset hypotheses for improving / diversifying MNQ intraday workhorses, specifically:

1. **mes_alignment filter** (substitute MES EMA20 position for MNQ ema_slope on stop_run_reversal)
2. **Direct ZN port** of GREEN MNQ primitives without modification (stop_run_reversal, range_compression_break, first_impulse_pullback)

Evidence:

### mes_alignment filter (cycle 12h)
| Criterion | Baseline | Filtered | Result |
|---|---:|---:|---|
| PF | 1.477 | 0.999 | FAIL Δ -0.478 |
| n | 1414 | 494 | FAIL 65% reduction |
| Era 3 PF | 1.554 | 0.920 | FAIL Δ -0.635 |
| Stress PF | 1.404 | 0.946 | FAIL Δ -0.458 |

### ZN port (cycle 12i, as-is)
| Candidate | n | PF | Median | Verdict |
|---|---:|---:|---:|---|
| WH-ZN-stop_run_reversal | 747 | **0.730** | -$18.73 | KILL |
| WH-ZN-range_compression_break | 750 | **0.682** | -$18.73 | KILL |
| WH-ZN-first_impulse_pullback | 899 | **0.585** | -$34.35 | KILL |

Both hypotheses failed cleanly with no discretion to preserve.

## What the failures showed

### Lesson 1: ema_slope is well-matched to entries

Replacing `ema_slope` with `mes_alignment` REMOVED too many good trades AND admitted bad ones. The MNQ ema_slope filter is doing real work that MES position alone cannot replicate.

This argues for: keep `ema_slope` as the default workhorse filter. Don't substitute lightly.

### Lesson 2: MNQ workhorse edge is asset-class-specific

The mean-reversion / impulse mechanisms that produce PF 1.35-1.48 on MNQ produce PF 0.59-0.73 on ZN — the edge is FULLY REVERSED, not just absent.

Rates microstructure (timing of catalysts, volume profile, order-flow patterns) differs fundamentally from equity-index microstructure. The MNQ edge is not a universal structural pattern.

This argues for: stop trying to make a single mechanism class work across asset families. Different assets need different mechanisms.

## What is NOT saturated

The CROSS-ASSET CONFIRMATION THESIS itself remains open IF combined with a NEW thesis:

1. **MES-MNQ DIVERGENCE filter** (not alignment) — trade MNQ stop_run only when MES is diverging, signaling retail/single-name noise vs institutional unanimity
2. **ZN regime filter on MNQ workhorses** — use ZN trend as a risk-on/risk-off conditioner of MNQ entries (not a substitute filter, but an ADDITIONAL layer)
3. **MGC divergence filter** — MGC rally + MNQ entry suggests USD weakness → conditional LONG
4. **Cross-asset entry primitive** (Goal B from original methodology) — a brand-new entry mechanism that USES cross-asset state, not just filters existing entries
5. **ZN port with rates-specific mechanism redesign** (would require new thesis explaining why rates need a different mechanism, not just parameter tuning)

These are NEW theses, not rescues. Per operator #199 "Do not keep them open for further testing without a genuinely new thesis."

## What is FORBIDDEN

- Parameter sweep on mes_alignment EMA window (would be tuning, not new thesis)
- Threshold tuning on ZN ports (per operator: "no rates-specific refinement without genuinely new thesis")
- Filter substitution loops on Lane A candidates

## REOPEN CRITERIA

- A written new thesis explaining the mechanism (not parameter tuning)
- New data (e.g., order-flow tick data, options Greeks)
- New asset / session combination with theoretical basis
- Operator override with documented rationale

## Status

**Simple cross-asset hypothesis: NARROW SATURATION** (mes_alignment, ZN port).

The 3 GREEN MNQ workhorses remain on the Lane A queue unchanged.

Next Lane B direction (per operator #198 C): DAILY-timeframe primitives — a different exposure profile entirely. See `docs/fql_forge/daily_timeframe_primitive_methodology_2026-06-12.md`.

## Cross-reference

- `docs/fql_forge/cross_asset_confirmation_methodology_2026-06-12.md` — original methodology (Test 1 ARCHIVED per this annotation)
- [[feedback_asset_family_saturation_rule]] — narrow saturation doctrine
- [[feedback_concentration_is_load_bearing]] — concentration primacy
- `docs/fql_forge/daily_timeframe_primitive_methodology_2026-06-12.md` — sibling Lane B next direction
