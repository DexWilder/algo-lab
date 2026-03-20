# Strategy Spec: Overnight-Z-VolRatio-OpenDrive

## Hypothesis

Most overnight price moves are noise — insufficient to predict the
regular-session open direction. But on days when the overnight range is
unusually large (z-score > threshold) AND early RTH volume confirms
institutional participation (volume ratio > threshold), the overnight
directional tilt has follow-through value into the first 75 minutes.

The edge is the conditioning filter, not the overnight direction itself.
Unconditional overnight drift is MONITOR at PF 1.09 in FQL's registry.
This strategy tests whether a volatility + participation filter transforms
a marginal signal into a tradeable one.

**Factor: VOLATILITY.** The signal fires on vol-expansion conditions
and is silent during normal volatility. It is not a momentum strategy —
it doesn't care about trend direction, only about the overnight vol
regime and opening participation level.

## Data Constraint

Requires continuous 5m futures data spanning the overnight session
(18:00 ET prior day through 09:30 ET) and the first 90 minutes of RTH
(09:30-11:00 ET). FQL has this for MES and MNQ (2019-06 to present,
~6.7 years).

## Signal Logic

### Overnight Session Definition

- **Start:** 18:00 ET (prior day's globex open after regular close)
- **End:** 09:30 ET (current day's RTH open)
- Overnight high = max(high) of all 5m bars from 18:00 to 09:25
- Overnight low = min(low) of all 5m bars from 18:00 to 09:25
- Overnight range = overnight high - overnight low
- Overnight direction = sign(close at 09:25 - open at 18:00)

### Z-Score Calculation

- rolling_mean = 20-day trailing mean of daily overnight ranges
- rolling_std = 20-day trailing std of daily overnight ranges
- overnight_z = (today's overnight range - rolling_mean) / rolling_std

### Volume Ratio Calculation

- opening_volume = sum of volume for 09:30, 09:35, 09:40 bars (first 15 min RTH)
- rolling_mean_vol = 20-day trailing mean of daily opening_volume
- volume_ratio = today's opening_volume / rolling_mean_vol

### Entry Condition

ALL of:
1. overnight_z > Z_THRESHOLD (default 1.5)
2. volume_ratio > VOL_THRESHOLD (default 1.2)
3. overnight_direction != 0

### Entry

- Time: 09:45 ET (after 15-minute open confirmation window)
- Direction: overnight_direction (long if overnight was up, short if down)
- Price: open of the 09:45 bar

### Exit

- **Time exit:** 11:00 ET (close of 10:55 bar, or open of 11:00 bar)
- **Stop:** entry price ± SL_ATR_MULT * ATR(20) (against the trade)
- Whichever comes first.

### Position Sizing

1 micro contract. MICRO tier. No scaling.

## Parameters (Initial)

```
Z_THRESHOLD = 1.5          # Overnight range z-score threshold
VOL_THRESHOLD = 1.2        # Opening volume ratio threshold
OVERNIGHT_LOOKBACK = 20    # Days for z-score baseline
VOLUME_LOOKBACK = 20       # Days for volume ratio baseline
ATR_LEN = 20               # For stop calculation
SL_ATR_MULT = 1.5          # Stop distance in ATR
ENTRY_TIME = "09:45"       # ET
EXIT_TIME = "11:00"        # ET (fixed time exit)
```

## Decomposition Test Design

The first-pass must run 4 variants to isolate the filter's contribution:

| Variant | Z Filter | Vol Filter | Purpose |
|---------|----------|------------|---------|
| A: Unconditional | OFF | OFF | Baseline: raw overnight direction at 09:45 |
| B: Z-score only | ON (1.5) | OFF | Does overnight range size predict follow-through? |
| C: Volume only | OFF | ON (1.2) | Does opening volume predict follow-through? |
| D: Combined | ON (1.5) | ON (1.2) | Does the combined filter add value? |

**The candidate only advances if Variant D is meaningfully better than
Variant A.** "Meaningfully better" = PF improvement ≥ 0.3 AND trade count
still ≥ 30 AND walk-forward stability maintained.

If Variant B or C alone matches Variant D, the combined filter is
unnecessary — use the simpler single filter.

## Asset Universe

| Asset | Class | Data Depth | Status |
|-------|-------|------------|--------|
| MES | Equity Index (S&P 500) | 6.7 years | Primary |
| MNQ | Equity Index (Nasdaq) | 6.7 years | Secondary |

Cross-asset check on M2K (informational only — not required to pass).

## Test Variants

All variants tested with both long and short modes:

| Variant | Parameters | Purpose |
|---------|-----------|---------|
| D-both | Z=1.5, V=1.2, both directions | Primary combined test |
| D-long | Z=1.5, V=1.2, long only | Directional decomposition |
| D-short | Z=1.5, V=1.2, short only | Directional decomposition |
| A-both | No filter, both directions | Unconditional baseline |

## Source

- TradingView: "Overnight Z-VolRatio Signal" by FoxchaseTrading
- Harvest note: `2026-03-19_04_overnight_z_volratio_open_drive.md`

## Key Failure Modes

1. **Filter doesn't add value over unconditional baseline.** If Variant D
   PF ≈ Variant A PF, the z-score and volume conditions are noise, not
   signal. Archive immediately.

2. **Morning session crowding.** Entry at 09:45 on MES/MNQ overlaps with
   VWAP-MNQ-Long, NoiseBoundary-MNQ-Long, and XB-PB-EMA-MES-Short.
   Even if the strategy works in isolation, it may add correlated risk
   and not improve the portfolio.

3. **Regime concentration.** If most profits come from high-vol crisis
   periods (COVID 2020, 2022 rate hikes), the strategy is regime-specific
   and may not work in normal conditions.

4. **Short-side failure.** Overnight gap-down follow-through may be
   structurally different from gap-up follow-through. If the short side
   fails, this is a long-only strategy on an already long-crowded asset.

## Diversification Role

- **Factor:** VOLATILITY — fills the #2 gap (0 active, 0 probation)
- **Asset:** MES/MNQ — already at concentration limit (4-5 strategies)
- **Session:** Overnight signal → morning execution (09:45-11:00 ET)
- **Horizon:** Intraday (75-minute hold)
- **Correlation risk:** MEDIUM — same assets, same morning session as
  existing momentum strategies. Factor independence must be confirmed.

## Decision Points After First Pass

- **If D >> A and both pass WF:** ADVANCE to validation battery.
  Proceed to probation only after morning session overlap analysis.
- **If D ≈ A:** ARCHIVE. Filter is noise. Do not iterate.
- **If D > A but short side fails:** Evaluate as long-only variant.
  But caution — long-only on MES/MNQ adds to directional crowding.
- **If D works but correlation > 0.35 with existing MES/MNQ strategies:**
  The edge is real but not additive. Park in testing, revisit for a
  different asset class or session.
