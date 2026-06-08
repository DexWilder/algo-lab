# Source Mining Catalog — 2026-06-08

> **Status:** Executed per #110 contingency after VRC archive (cycle 08k).
> **Authority:** Lane B research; report-only.
> **Method:** scan kill_taxonomy + cycle scripts + harvest_results + intake folders for mechanism gaps.

## Scan results — existing testing coverage

| Entry primitive | Tested in cycles | Untested assets |
|---|---|---|
| orb_breakout | 08a/08b/08e/08i (5 assets directional) | none — exhausted |
| donchian_breakout | 08c (MCL/MGC), 08a (MGC fragility pair), 08i (MGC vol overlay) | MES, MYM, MNQ + non-MCL/MGC combinations |
| pb_pullback | 08c (MCL/MGC), 08d (ZN with afternoon) | MES, MYM, MNQ × various filters |
| vwap_continuation | 08c (MCL/MGC) | MES, MYM, MNQ |
| bb_reversion | 08c (MCL/MGC) | MES, MYM, MNQ, ZN — completely untested |
| vol_expansion | 06-04b (MES/MNQ/ZN/MGC partial) | MYM, MCL, broader exit/filter combinations |
| prior_day_break | 08a/08e/08g (MGC) | MES, MYM, MNQ, MCL |
| prior_day_fade | 08c (MGC) | MES, MYM, MNQ, MCL |
| range_compression_break | 08e/08g/08i — RESEARCH_ONLY | n/a — done |
| volatility_regime_compound | 08j/08k — ARCHIVED | n/a — done |

| Filter primitive | Tested with | Untested combos |
|---|---|---|
| ema_slope | default for most | n/a |
| ema_slope_vol_high/low | 08i (RCB only) | other entries |
| vol_regime band | 08i (RCB only) | other entries |
| **hurst_stable_mr** | **NEVER USED in any cycle** | **all entries** |
| **hurst_stable_trend** | **NEVER USED in any cycle** | **all entries** |
| session_morning/afternoon/close | 08c/08d (limited) | many combos |
| bandwidth_squeeze | not used | all entries |

**Critical gap:** Hurst-stability filters were built (cycle 06-03) but **NEVER deployed in candidate cycles**. This is a primitive-coverage waste.

## Mechanism inventory + classification

### RUNNABLE_NOW (highest priority)

1. **Hurst-MR + bb_reversion on equity micros** — MES/MNQ/MYM × bb_reversion × hurst_stable_mr × profit_ladder × both
   - Mechanism: Bollinger reversion only fires when Hurst-proxy indicates mean-reverting regime
   - Theoretical basis: mean-reversion strategies work when H < 0.5; the filter enforces this
   - Untested: hurst_stable filter has never been deployed; bb_reversion never tried on these assets
   - Expected unlock: 3-9 candidates

2. **Vol_expansion + session_morning on equity micros** — MES/MNQ/MYM × vol_expansion × session_morning × profit_ladder × both
   - Mechanism: morning vol-expansion captures opening-drive structural moves
   - Not directly tested in this configuration
   - Expected unlock: 3 candidates

3. **Prior_day_fade + ema_slope on equity micros** — MES/MNQ/MYM × prior_day_fade × ema_slope × profit_ladder × both
   - Mechanism: mean-revert from prior-day extremes when daily trend agrees
   - Tested only on MGC; equity micros completely untested for PDF
   - Expected unlock: 3 candidates

4. **Donchian-breakout + hurst_stable_trend on equity micros** — MES/MNQ/MYM × donchian_breakout × hurst_stable_trend × profit_ladder × both
   - Mechanism: trend-stable filter + breakout entry; restricts breakouts to genuine trending regimes
   - Hurst-trend filter never used; new combo
   - Expected unlock: 3 candidates

5. **VWAP_continuation + session_morning on equity micros** — MES/MNQ/MYM × vwap_continuation × session_morning × profit_ladder × both
   - Mechanism: morning VWAP continuation; captures sustained directional moves
   - Tested only on MCL/MGC; equity micros untested
   - Expected unlock: 3 candidates

### NEEDS_PRIMITIVE (queue for operator decision)

- **Bollinger-Keltner squeeze**: Keltner channels not in features (KC_upper/lower); would need ATR-based KC computation. Distinct from RCB which uses Bollinger pctrank.
- **ICT-style liquidity sweep**: would need swing-high/swing-low pivots + reversal-confirmation logic
- **Cross-asset pair MR with HL gate**: scaffolded in research/pairs_backtest infrastructure but not in crossbreeding_engine combinatorial form; would need a pair-aware entry primitive
- **Gap-fill specific trigger**: prior_day_close exists but no explicit gap-open detection
- **Volume-weighted close break**: VWAP exists but VWAP-distance-z signal not formalized

### NEEDS_DATA (queue, deferred per #99 one-unlock-at-a-time)

- Treasury auction calendar
- WASDE / grain asset onboarding
- COT-shift CFTC ingestion
- Surprise-conditioned EIA crude data (would revive crude × event family per #101)

### ALREADY_TESTED — skip

- Session VWAP fade (harvest_results KILL)
- Range compression (RCB completed)
- Vol-regime overlay on RCB (08i completed)
- All NFP/EIA event templates on MCL (NFP-MCL + EIA-MCL, both paused per saturation)
- ORB-family directional asymmetry (5 assets complete)
- PL vs FR2 cost-fragility (codified)

## Top 5 RUNNABLE_NOW proposed for first batch

Per #110 Source Mining Mode goal: "produce 5 runnable candidates":

| # | Mechanism | Cells | Hurst-filter test? |
|---:|---|---|---|
| 1 | bb_reversion × MES × hurst_stable_mr × PL × both | First-ever hurst-filter use | YES |
| 2 | bb_reversion × MNQ × hurst_stable_mr × PL × both | Second hurst-filter use | YES |
| 3 | vol_expansion × MES × session_morning × PL × both | Open-drive vol-expansion | NO |
| 4 | prior_day_fade × MNQ × ema_slope × PL × both | PDF on MNQ untested | NO |
| 5 | vwap_continuation × MES × session_morning × PL × both | Open-drive VWAP continuation | NO |

**Selection rationale:**
- 2 of 5 use the never-deployed `hurst_stable_mr` filter (highest novelty + primitive-coverage value)
- 3 of 5 target MES (largest sample-size asset = best statistical resolution)
- All use PL exit per locked doctrine (#91)
- All target equity micros where existing primitives are best supported by data
- None re-test saturated families (MCL non-ORB, ZN/ZF afternoon, etc.)
- All RUNNABLE_NOW — zero infrastructure cost

## Expected outcome distribution

Based on prior cycle hit-rates (typically 1-4 WATCH per 18 candidates, 0-1 PASS_STRESS):
- Expected 0-2 WATCH from 5 candidates
- Expected 0-1 PASS_STRESS
- Expected 0 PAPER_PACKET (cycle 08c-08i pattern)

Realistic best case: 1 PASS_STRESS candidate from the hurst-filtered MR mechanism that survives all gates. That would be the first Packet #2 candidate.

Realistic typical case: 5 KILL or 4 KILL + 1 OBSERVATIONAL.

## Constraints

- Same strict gates as all prior cycles: median ≥ $2, PASS_STRESS, max-yr ≤ 50%, Era3 ≥ 0
- No primitive build in this Source Mining cycle (RUNNABLE_NOW means existing primitives only)
- No data unlock in this cycle
- No rescue loops
- ONE batch only; surface results for operator decision before any mutation

## Source artifacts

- `research/data/fql_forge/source_mining_mode_plan.md` (contingency plan)
- `research/data/fql_forge/kill_taxonomy.json` (mining source)
- `research/data/harvest_results.json` (mining source)
- `intake/tradingview/*` (mining source — mostly empty)
- All `research/forge_cycle_*.py` (coverage scan)
- `research/crossbreeding/crossbreeding_engine.py` (primitive inventory)
