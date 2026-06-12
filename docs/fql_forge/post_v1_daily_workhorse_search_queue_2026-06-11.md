# Post-V1 Daily Workhorse Search Queue — 2026-06-11

> **Date:** 2026-06-11 (Day 16 / 30)
> **Authority:** Operator decision #176 C amended.
> **Mission pivot:** From event-driven tail-engine to DAILY WORKHORSE FOUNDATION.
> **Replaces:** `post_v1_nonstop_search_queue_2026-06-11.md` (event-heavy).

## Mission clarification

The operator's core need is a **daily/near-daily intraday workhorse** that trades many times per session with stable expectancy. FOMC-MNQ-Long-1h is a real V1 candidate but is event-driven (8/year) — not the foundation.

This queue prioritizes WORKHORSE archetype mechanisms on MNQ/MES (cleanest data, deepest liquidity).

## Priority asset order

1. **MNQ** (primary — Nasdaq micro)
2. **MES** (secondary — S&P micro)
3. **ZN** (rates session behavior)
4. MYM — only if data coverage supports it (currently DATA_REQUIRED)
5. MGC — only after data-provider validation / backfill resolution
6. MCL — only if cost/data are clean

## Required workhorse reporting (per operator #176)

Every daily workhorse audit must include:

- Trade count
- Trades per day
- % days traded
- % profitable days
- Median day PnL
- Worst day
- Average losing day
- Max consecutive losing days
- Daily loss limit breach simulation
- Max intraday drawdown
- Time in market
- PF
- Median trade
- Era 3 PF / median
- Stress (PF + median at 2× cost + 2 ticks slip)
- Cost tolerance ladder
- Family overlap vs existing XB-ORB probation

## Ranked queue (15 daily/near-daily mechanisms)

### 1. abnormal_range_followup on MNQ/MES (RUNNABLE_NOW — primitive exists)

| Field | Value |
|---|---|
| Archetype | WORKHORSE |
| Asset | MNQ, MES |
| Thesis | Abnormal early-session range (above 90th pctile) signals trend day; trade in direction of breakout |
| Primitive | abnormal_range_followup (already in crossbreeding engine) |
| Status | RUNNABLE_NOW |
| Expected sample size | ~50-150 abnormal-range days/year × 8 yrs |
| Why different | Different mechanism class from ORB; specifically targets abnormal-volatility days |
| First test | abnormal_range_followup × ema_slope × profit_ladder |
| Operator list match | #9 (abnormal early range mean reversion) — actually CONTINUATION variant |

### 2. range_compression_break on MNQ/MES (RUNNABLE_NOW — primitive exists)

| Field | Value |
|---|---|
| Archetype | WORKHORSE |
| Asset | MNQ, MES |
| Thesis | Range compression (low-vol) followed by directional breakout — classic volatility-clustering |
| Primitive | range_compression_break (exists) |
| Status | RUNNABLE_NOW |
| Expected sample size | Multi-hundred per asset |
| Why different | Compression → expansion entry, NOT ORB-based |
| First test | range_compression_break × ema_slope × profit_ladder |
| Operator list match | #15 (range expansion after compression) |

### 3. stop_run_reversal on MNQ/MES (RUNNABLE_NOW — primitive exists)

| Field | Value |
|---|---|
| Archetype | WORKHORSE |
| Asset | MNQ, MES |
| Thesis | Liquidity sweep through prior swing low/high, then immediate reversal back through level |
| Primitive | stop_run_reversal (exists) |
| Status | RUNNABLE_NOW |
| Expected sample size | High frequency (multiple per session) |
| Why different | Mean-reversion / liquidity-sweep mechanism, NOT trend-following |
| First test | stop_run_reversal × ema_slope × profit_ladder |
| Operator list match | #14 (morning liquidity sweep reversal) |

### 4. volatility_regime_compound on MNQ/MES (RUNNABLE_NOW)

| Field | Value |
|---|---|
| Archetype | WORKHORSE |
| Primitive | volatility_regime_compound (exists) |
| Thesis | Compound vol-regime change signal entries |
| Status | RUNNABLE_NOW |
| Operator list match | #10 (volatility-normalized intraday breakout) |

### 5. ORB with directional asymmetry filter on MNQ/MES (RUNNABLE_NOW)

| Field | Value |
|---|---|
| Archetype | WORKHORSE |
| Thesis | ORB only on bullish-bias days (e.g., after up-close); avoid bearish-bias ORB |
| Primitive | orb_breakout (exists) + new directional filter |
| Status | RUNNABLE_NOW (extends probation candidate) |
| Operator list match | #2 (ORB with improved risk model) |

### 6. First-impulse pullback continuation on MNQ/MES (NEEDS_PRIMITIVE)

| Field | Value |
|---|---|
| Archetype | WORKHORSE |
| Thesis | First 30-min impulse establishes direction; pullback to 50% retrace → continuation entry |
| Primitive | NEW — first_impulse_pullback |
| Status | NEEDS_PRIMITIVE (build if ≥2 candidates blocked) |
| Operator list match | #3 (first impulse pullback continuation) |

### 7. ORB failure / failed-breakout reversal on MNQ/MES (NEEDS_PRIMITIVE)

| Field | Value |
|---|---|
| Archetype | WORKHORSE |
| Thesis | ORB breakout fails to hold within N bars → reverse short/long |
| Primitive | NEW — orb_failure_reversal |
| Status | NEEDS_PRIMITIVE |
| Operator list match | #1 (opening-range failure / failed-breakout reversal) |

### 8. VWAP reclaim / rejection on MNQ/MES (NEEDS_PRIMITIVE)

| Field | Value |
|---|---|
| Archetype | WORKHORSE |
| Thesis | Price reclaims VWAP after being above/below → continuation |
| Primitive | NEW — vwap_reclaim |
| Status | NEEDS_PRIMITIVE (VWAP feature) |
| Operator list match | #4 |

### 9. Prior-day high/low sweep and reclaim on MNQ/MES (NEEDS_PRIMITIVE)

| Field | Value |
|---|---|
| Archetype | WORKHORSE |
| Thesis | Sweep prior day H/L, reclaim, fade |
| Primitive | NEW — pdh_pdl_sweep |
| Status | NEEDS_PRIMITIVE |
| Operator list match | #5 |

### 10. First-hour trend continuation on MNQ/MES (NEEDS_PRIMITIVE)

| Field | Value |
|---|---|
| Archetype | WORKHORSE |
| Thesis | First hour direction sets day; trade continuation through 2nd hour |
| Status | NEEDS_PRIMITIVE |
| Operator list match | #6 |

### 11. Mid-morning compression breakout (NEEDS_PRIMITIVE)

Status: NEEDS_PRIMITIVE (10am-11am ET compression detection)
Operator list match: #7

### 12. Trend-day identification + pullback entry (NEEDS_PRIMITIVE)

Status: NEEDS_PRIMITIVE (trend-day classifier)
Operator list match: #8

### 13. ZN session-open momentum (RUNNABLE_NOW with new primitive)

Status: NEEDS_PRIMITIVE (session-open momentum detector)
Operator list match: #13

### 14. MNQ/MES confirmation or divergence (NEEDS_RESEARCH)

Status: NEEDS_RESEARCH (cross-asset confirmation methodology)
Operator list match: #12

### 15. Session transition setup (NEEDS_PRIMITIVE)

Status: NEEDS_PRIMITIVE (session-boundary detector — defined hours)
Operator list match: #11

## First-batch execution plan

**Run cycles 11p-q (immediate, no operator wait):**
- Cycle 11p: 4 RUNNABLE_NOW primitives × MNQ/MES = 8 candidates
  - abnormal_range_followup + ema_slope + profit_ladder
  - range_compression_break + ema_slope + profit_ladder
  - stop_run_reversal + ema_slope + profit_ladder
  - volatility_regime_compound + ema_slope + profit_ladder
- Cycle 11q: V1 8-dim audit + family review on any WATCH

**If no candidate survives first batch:**
- Build NEEDS_PRIMITIVE items in priority order: ORB-failure-reversal (#7), first-impulse-pullback (#6), VWAP-reclaim (#8)
- Per infrastructure budget rule: build only if ≥2 candidates blocked

## Diversity check

Mechanism classes in first 5 RUNNABLE_NOW:
- Volatility regime / abnormal range (1, 2, 4)
- Mean reversion / liquidity sweep (3)
- Trend / ORB variant (5)

Adequate diversity for first batch.

## Stop conditions

- If first-batch primitives produce 0 PF > 1.30 candidates: pivot to building #6-#8 NEEDS_PRIMITIVE
- If 2 consecutive batches in same mechanism class fail: per [[feedback_asset_family_saturation_rule]] narrow saturation
- If candidate surfaces: V1 8-dim audit + workhorse family review (vs XB-ORB-MNQ probation specifically)

## Scoreboard (Day 16 / 30, post-pivot)

| Category | Count |
|---|---:|
| **Event tail packet candidates** | 1 (FOMC-MNQ-Long-1h pending robustness review) |
| **Daily workhorse candidates** | **0** |
| **Daily workhorse accepted packets** | 0 |
| Portfolio complements | 0 |
| Accepted paper/live | 0 |
| Archived/reopenable | ~22 (includes FOMC-MES duplicate) |

**The core mission is the daily workhorse line. FOMC-MNQ exists but is not the foundation.**
