# Packet #2 Hunt Plan — Non-ORB Edge Families

> **Status:** Plan for next hunt cycle after MNQ diagnostic + PL/FR2 n=10 wrap-up.
> **Recorded:** 2026-06-08 per operator directive.
> **Authority:** Lane B autonomous; first cycle's compositions queued for execution.

## Strategic context

ORB-family directional and exit-design behavior is now well-mapped across MGC, MCL, MYM, MES, MNQ. Continuing ORB diagnostics returns diminishing intelligence. **Pivot to genuinely new edge families** for Packet #2.

**Available primitives (verified 2026-06-08):**
- Entries: `bb_reversion`, `donchian_breakout`, `orb_breakout`, `pb_pullback`, `prior_day_break`, `prior_day_fade`, `vol_expansion`, `vwap_continuation`
- Exits: `atr_trail`, `chandelier`, `fixed_ratio`, `midline_target`, `profit_ladder`, `time_stop`
- Filters: `bandwidth_squeeze`, `ema_slope`, `ema_slope_vol_high`, `ema_slope_vol_low`, `hurst_stable_mr`, `hurst_stable_trend`, `none`, `session_afternoon`, `session_close`, `session_morning`, `vol_regime`, `vwap_slope`

## Hunt categories (operator-provided priority order)

### 1. Non-ORB MCL/MGC entries that can survive prop-stress

Target untested entries on MCL/MGC with ema_slope filter + profit_ladder exit:

| Spec | Asset | Entry | Mode | Hypothesis |
|---|---|---|---|---|
| PB-MCL-Long-PL | MCL | pb_pullback | long | Mean-reversion entry on crude micros — different mechanism from ORB |
| PB-MCL-Short-PL | MCL | pb_pullback | short | Captures crude short trend continuation |
| PB-MGC-Long-PL | MGC | pb_pullback | long | Gold mean-reversion long bias |
| PB-MGC-Short-PL | MGC | pb_pullback | short | Gold mean-reversion short bias |
| BB-MCL-Long-PL | MCL | bb_reversion | long | Bollinger reversion — explicit MR entry |
| BB-MCL-Short-PL | MCL | bb_reversion | short | Bollinger reversion short |
| BB-MGC-Long-PL | MGC | bb_reversion | long | Same on gold |
| BB-MGC-Short-PL | MGC | bb_reversion | short | Same |
| VWAP-MCL-Long-PL | MCL | vwap_continuation | long | VWAP continuation — momentum-derivative |
| VWAP-MCL-Short-PL | MCL | vwap_continuation | short | Same |
| PDF-MGC-Long-PL | MGC | prior_day_fade | long | Mean-revert vs prior day (opposite of PDB) |
| PDF-MGC-Short-PL | MGC | prior_day_fade | short | Same |

12 candidates. Skip MES because the MES finding already shows it correlates moderately to MNQ; we want NEW families, not more equity-index micros.

### 2. Rates-native daily strategies (NOT ZN/ZF ORB)

Existing probation has ZN-Afternoon-Reversion. Extensions:

| Spec | Asset | Entry | Filter | Mode | Hypothesis |
|---|---|---|---|---|---|
| AFT-PB-ZN-Long-PL | ZN | pb_pullback | session_afternoon + ema_slope | long | Afternoon pullback on rates |
| AFT-PB-ZN-Short-PL | ZN | pb_pullback | session_afternoon + ema_slope | short | Same |
| AFT-BB-ZN-Long-PL | ZN | bb_reversion | session_afternoon | long | Afternoon Bollinger reversion |
| AFT-BB-ZN-Short-PL | ZN | bb_reversion | session_afternoon | short | Same |
| AFT-BB-ZF-Long-PL | ZF | bb_reversion | session_afternoon | long | ZF afternoon reversion |
| AFT-BB-ZF-Short-PL | ZF | bb_reversion | session_afternoon | short | Same |

6 candidates. Critical: stacked filter (session_afternoon + ema_slope) was a primitive added in earlier cycles.

### 3. FX session handoff

6J/6E/6B data is in tree. Session-transition focus:

| Spec | Asset | Entry | Filter | Mode | Hypothesis |
|---|---|---|---|---|---|
| CLOSE-PB-6J-Long-PL | 6J | pb_pullback | session_close | long | NY close transition into Asian open |
| CLOSE-PB-6E-Long-PL | 6E | pb_pullback | session_close | long | NY close transition for EUR |
| CLOSE-PB-6E-Short-PL | 6E | pb_pullback | session_close | short | Same |
| CLOSE-BB-6E-Long-PL | 6E | bb_reversion | session_close | long | NY close mean-reversion EUR |
| CLOSE-BB-6J-Long-PL | 6J | bb_reversion | session_close | long | NY close mean-reversion JPY |
| MORN-DC-6E-Long-PL | 6E | donchian_breakout | session_morning | long | European-session breakout |

6 candidates. Cross-asset: FX has different cost profile (commission $2.50/side per asset_config) — prop-stress likely binding.

### 4. Commodity events/spreads with half-life gate

Mostly DATA_REQUIRED (EIA, OPEC, USDA calendars not in tree). Skip until data unblocked. Defer.

### 5. Overnight/close/afternoon strategies

Already covered in #1-3 via session filters. Additionally:

| Spec | Asset | Entry | Filter | Mode | Hypothesis |
|---|---|---|---|---|---|
| CLOSE-DC-MGC-Long-PL | MGC | donchian_breakout | session_close | long | Last-hour gold breakout |
| CLOSE-DC-MGC-Short-PL | MGC | donchian_breakout | session_close | short | Same short |
| CLOSE-DC-MCL-Long-PL | MCL | donchian_breakout | session_close | long | Last-hour crude breakout |
| CLOSE-DC-MCL-Short-PL | MCL | donchian_breakout | session_close | short | Same |
| AFT-DC-MGC-Long-PL | MGC | donchian_breakout | session_afternoon | long | Afternoon gold breakout |
| AFT-DC-MCL-Short-PL | MCL | donchian_breakout | session_afternoon | short | Afternoon crude short |

6 candidates.

### 6. MGC/MCL non-ORB trend or mean-reversion

Covered in #1.

## Execution plan

### Cycle 2026-06-08c (next): Hunt batch — non-ORB MCL/MGC + session variants

Priority: combine categories 1 + 5 (highest-conviction entries on already-validated assets). 18 candidates:

- 12 from category 1 (pb_pullback, bb_reversion, vwap_continuation, prior_day_fade on MCL/MGC)
- 6 from category 5 (donchian + session_close/afternoon on MCL/MGC)

Standard pipeline: cheap-screen → temporal split → prop-stress on WATCH → family review for any survivor.

Expected outcomes: most will KILL fast (high-conviction entries on commodities have historically been hard). Anything that passes prop-stress AND has low correlation to ORB-EMA-Ladder family is a Packet #2 candidate.

### Cycle 2026-06-08d (after c): Rates-afternoon + FX session-handoff

6 rates candidates + 6 FX candidates = 12 candidates. Lower hit-rate expected; cost-prop-stress is the binding constraint.

### Cycle 2026-06-08e (later, if c/d unproductive): Composite mutations

Test successful primitives in unfamiliar combinations.

## Hard rules (operator-stated)

- Every WATCH gets prop-stress immediately.
- Stress fail = OBSERVATIONAL.
- Same-family subset = insight, not packet.
- Median-negative PF>1.2 = KILL.
- Short data window = OBSERVATIONAL only.
- No registry mutation, no scheduler change, no portfolio change, no paper/live promotion.
- Report-only Lane B.

## Expected timeline

Assuming feature-cache hit rate ~80% after warm-up, 18 candidates × ~30s avg = ~9 min per cycle. Cycles c+d can complete in 2-3 hours of autonomous Forge time.

## Success criterion

**One** of:
1. Packet #2 candidate emerges with all 8 evidence-integrity dimensions GREEN (full audit)
2. Forge correctly KILLs entire backlog with documented rationale per primitive family, surfacing primitive-coverage as the next bottleneck
