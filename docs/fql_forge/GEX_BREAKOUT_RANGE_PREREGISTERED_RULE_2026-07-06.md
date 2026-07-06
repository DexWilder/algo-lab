# Pre-Registered Rule — GEX-Conditioned Breakout/Range (2026-07-06)

> FROZEN before extending GEX coverage. NO tweaking while adding data. Coverage extension is TRUE OUT-OF-SAMPLE: run this
> exact rule first, report without optimization, only then sensitivity. Label: `SCREEN_PASS_PENDING_COVERAGE` — not WH /
> candidate / validated / DSR-credible.

## Data
- **Source:** Databento GLBX.MDP3. Options: ES weekly parents `EW1.OPT..EW4.OPT`, schema `definition` (strike/expiration/instrument_class C|P) + `statistics` filtered `stat_type=9` (Open Interest). Index: `MES/MNQ/MYM` 1m OHLCV (continuous `.c.0`).
- **Current sample:** `ES_OPT_weekly_oi.csv` = 124 OI days, 2024-10-31..2025-04-29 (partial). Monetized test n≈50 trading days.

## Signed-GEX construction (per trading date d, from OI AS-OF prior settlement)
1. Front expiry E = soonest weekly with **DTE ∈ [1,5]** having OI that date.
2. **Strike universe:** near-money, strike ∈ (0.97, 1.03) × spot.
3. **Spot mapping:** MES RTH session open that date (MES = S&P index level; shared reference for MNQ/MYM regime).
4. **Gamma proxy weight:** `w(K) = exp(-0.5 × ((K − spot)/(0.007×spot))^2)` (bell peaked at spot, ~0.7% width). No IV inversion.
5. **Signed GEX:** `GEX = Σ_near w(K) × OI(K) × (+1 if Call, −1 if Put)` (dealer-long-gamma convention).
6. **Regime:** `pos-GEX (long-gamma/compression)` if GEX > median(GEX); else `neg-GEX (short-gamma/expansion)`.
7. **Availability / causality:** OI as-of date d is published by CME the morning of d+1. Rule uses **prior-settlement OI** — regime for session d comes from `GEX(d−1)` (known before session d). Implemented as `regime.shift(1)`. NO same-day/future OI.

## Trade rule (index, per session d)
- **Opening range (OR):** first 30 min of detected RTH (volume-detected 390-min window). `or_move = OR_end − open`.
- **Signal:** `side = sign(or_move)`; in **neg-GEX (expansion)** regime **follow** the OR (`+side`); in **pos-GEX (compression)** regime **fade** it (`−side`).
- **Entry:** at OR end (30 min in). **Exit:** session close. `pnl = signal × (close − OR_end) × point_value − cost`.
- **Costs:** round-trip $3 MES / $3 MNQ / $2 MYM (realistic-to-conservative; ES ~1-tick spread confirmed via bbo-1m).
- **Instruments:** MES, MNQ, MYM (INDEX_DIRECT), regime = INDEX_REGIME_INPUT (GEX).
- **Excluded days:** none (no filtering beyond OI-availability + near-money OI ≥ 500).

## Current metrics (causality-CORRECTED, this is the honest baseline)
| Instrument | Sharpe | n | max-year | DSR@N | 2024 | 2025 |
|---|---|---|---|---|---|---|
| MES | 1.05 | 50 | 149% | 0.69 | **−$670** | +$2040 |
| MNQ | 1.30 | 50 | 94% | 0.73 | +$178 | +$2608 |
| MYM | 2.42 | 50 | 96% | 0.91 | +$78 | +$1951 |

## Failure flags (why this is a LEAD, not a candidate)
- **2025-CONCENTRATED**: 2024 flat-to-negative on all three (the earlier "both-years-positive" was an alignment-bug artifact, now RETRACTED).
- **DSR 0.69–0.91 < 0.95** (not DSR-credible).
- **n≈50 underpowered**; GEX coverage only ~6 months.
- Adversarial review: FAIL (`SINGLE_YEAR_DOMINATES`).

## Regime finding (separate, stronger than the trade rule)
Signed-GEX compression is descriptive & robust at n=51: **pos-GEX next-day range ~half of neg-GEX, consistent across both 2024 & 2025**. The REGIME (vol compression/expansion) is the durable observation; the TRADE monetization is the fragile part.

## Confirmation plan (NOT optimization)
Extend GEX coverage (bounded single-slice) → run THIS frozen rule OOS on new months → does 2024/2026 hold, or is it 2025-only? Then regime-only verification (range by year/quarter/DTE/magnitude/distance) + robustness + adversarial. Advance only if it survives.
