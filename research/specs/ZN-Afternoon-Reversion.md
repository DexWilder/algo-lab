# Strategy Spec: ZN-Afternoon-Reversion

## Origin

Discovered as Variant B during the falsification test of
Treasury-Cash-Close-Reversion-Window (REJECTED 2026-03-20).

The parent hypothesis — that the 15:00 ET cash close creates a uniquely
reversible impulse — was wrong. But the falsification control (identical
logic shifted 1 hour earlier) revealed a genuine edge: fading the
13:45-14:00 ET move at 14:00 works significantly better than fading the
14:45-15:00 move at 15:00.

**This is NOT a salvage of the parent.** It is a new strategy with a
different mechanism, different session window, and independent evidence.
The parent is rejected and archived. This child stands on its own.

## Hypothesis

In the hour before the U.S. Treasury cash close (15:00 ET), institutional
positioning and hedging flows create short-duration directional impulses
in ZN futures. The 13:45-14:00 ET window captures pre-close positioning
that tends to overshoot — the market reverts in the subsequent 25 minutes
(14:00-14:25 ET) as the impulse exhausts.

The edge is not at the cash close itself — it's in the run-up to it.
The positioning effect peaks and reverses BEFORE the 15:00 close, not
after it.

**Factor: STRUCTURAL.** Session-timing microstructure on rates futures.

## Signal Logic

```
Impulse measurement:
  move = close(13:55) - open(13:45)     # 3 bars, 15 minutes
  magnitude = abs(move)
  direction = sign(move)
  median_mag = rolling 20-day median of daily magnitudes
  impulse_ratio = magnitude / median_mag

Entry condition:
  impulse_ratio > 1.5 AND direction != 0

Entry:
  14:00 ET, open of bar. FADE direction (short if impulse was up, long if down).

Exit:
  14:25 ET close of bar (fixed time, 25-minute hold)
  OR 60% retracement of impulse magnitude
  OR 1.5x ATR(20) stop
  Whichever comes first.
```

## Parameters

```python
IMPULSE_THRESHOLD = 1.5     # Impulse must exceed 1.5x 20d median
LOOKBACK = 20               # Rolling median baseline
ATR_LEN = 20                # Stop calculation
SL_ATR_MULT = 1.5           # Stop distance
RETRACE_PCT = 0.60          # Retracement exit target
```

## First-Pass Results

| Metric | Value |
|--------|-------|
| Trades | 300 |
| PnL | +$15,344 |
| PF | 1.32 |
| Win Rate | 56.7% |
| Avg PnL/trade | $51 |
| Max DD | $6,875 |
| Sharpe | 1.48 |
| Walk-forward H1 | PF 1.31 (150 trades) |
| Walk-forward H2 | PF 1.33 (150 trades) |

## Robustness Analysis

### Window Sensitivity

| Window | Trades | PF | H1 PF | H2 PF |
|--------|--------|----|-------|-------|
| 13:15-13:30 → 13:30-13:55 | 306 | 1.14 | 1.35 | 0.99 |
| 13:30-13:45 → 13:45-14:10 | 324 | 0.85 | 0.83 | 0.87 |
| **13:45-14:00 → 14:00-14:25** | **300** | **1.32** | **1.31** | **1.33** |
| 14:00-14:15 → 14:15-14:40 | 318 | 0.94 | 0.76 | 1.23 |
| 14:15-14:30 → 14:30-14:55 | 311 | 0.84 | 0.78 | 0.91 |

**2 of 5 windows pass PF > 1.0.** The base window (13:45-14:00) is the
clear peak. The edge is window-specific — it does not generalize to
arbitrary afternoon times. The 30-minute-earlier window (13:15-13:30) also
works weakly (PF 1.14) but with unstable WF (H2 0.99).

**Assessment: PASS but narrow.** The window specificity is a feature
(structural timing edge) and a risk (if the timing shifts, the edge
vanishes). This is acceptable for STRUCTURAL strategies — session-timing
edges are inherently narrow-window.

### Impulse Threshold Sensitivity

| Threshold | Trades | PF | WR | H1 PF | H2 PF |
|-----------|--------|----|----|----|-------|
| 0.0 (no filter) | 700 | 0.98 | 50.7% | 1.10 | 0.88 |
| 0.5 | 661 | 0.94 | 50.5% | 1.10 | 0.81 |
| 1.0 | 365 | 1.21 | 55.3% | 1.17 | 1.26 |
| 1.25 | 359 | 1.22 | 55.4% | 1.18 | 1.27 |
| **1.5** | **300** | **1.32** | **56.7%** | **1.31** | **1.33** |
| 1.75 | 297 | 1.29 | 56.6% | 1.28 | 1.30 |
| 2.0 | 166 | 1.22 | 59.0% | 1.02 | 1.56 |
| 2.5 | 156 | 1.15 | 59.0% | 0.99 | 1.44 |

**The filter clearly adds value.** Unconditional (thresh=0): PF 0.98.
Filtered (thresh=1.5): PF 1.32. Delta: +0.34. The edge IS the
conditioning — only outsized impulses revert reliably.

Thresholds 1.0 through 1.75 all produce PF > 1.2 with stable WF. The
parameter is not fragile. Above 2.0, sample shrinks and WF destabilizes.

**Assessment: PASS.** Filter adds clear incremental value. Parameter is
stable across a wide range.

### Day-of-Week Split

| Day | Trades | PnL | PF | WR |
|-----|--------|-----|----|----|
| Monday | 62 | +$7,531 | 1.77 | 59.7% |
| Tuesday | 51 | -$1,172 | 0.87 | 45.1% |
| Wednesday | 55 | +$3,984 | 1.44 | 60.0% |
| Thursday | 70 | +$2,797 | 1.24 | 58.6% |
| Friday | 62 | +$2,203 | 1.25 | 58.1% |

**Tuesday is the one weak day (PF 0.87).** All other days positive.
Monday is the strongest (PF 1.77). This pattern is plausible — Tuesday
afternoon may have different institutional flow than other days.

**Assessment: PASS.** 4 of 5 days positive. Tuesday weakness is notable
but not disqualifying — it's 17% of trades.

### Regime Split (ATR Percentile Proxy)

| Regime | Trades | PnL | PF | Avg PnL |
|--------|--------|-----|----|----|
| LOW_VOL (0-33pctile) | 88 | +$516 | 1.04 | $6 |
| NORMAL (33-67pctile) | 105 | +$2,156 | 1.13 | $21 |
| HIGH_VOL (67-100pctile) | 107 | +$12,672 | 1.64 | $118 |

**Strongly vol-regime dependent.** 83% of PnL comes from HIGH_VOL
conditions. LOW_VOL is barely positive (PF 1.04).

**Assessment: CAUTION.** This is a high-vol edge. In sustained low-vol
regimes, the strategy will be nearly flat. This is acceptable IF the
portfolio needs a high-vol contributor (which it does — current portfolio
underperforms in high-vol). But it means the strategy is not a
steady-state workhorse.

### Long/Short Asymmetry

| Mode | Trades | PnL | PF | H1 PF | H2 PF |
|------|--------|-----|----|----|-------|
| Long only | 144 | +$1,687 | 1.06 | 1.10 | 1.02 |
| Short only | 156 | +$13,656 | 1.61 | 1.37 | 1.96 |
| Both | 300 | +$15,344 | 1.32 | 1.31 | 1.33 |

**Dominant short bias.** 89% of PnL from short trades. Short PF 1.61
with accelerating H2 (1.96). Long PF 1.06 is marginal.

**Assessment: PASS for both-direction deployment.** The long side adds
some diversification even at PF 1.06, and removing it would halve the
trade count. But if the strategy enters probation, monitor whether the
long side degrades further.

### Year-by-Year

| Year | Trades | PnL | PF |
|------|--------|-----|------|
| 2019 | 18 | +$1,562 | 1.90 |
| 2020 | 44 | +$2,234 | 1.31 |
| 2021 | 46 | -$4,953 | 0.51 |
| 2022 | 52 | +$9,844 | 2.05 |
| 2023 | 46 | +$1,531 | 1.20 |
| 2024 | 40 | -$156 | 0.98 |
| 2025 | 44 | +$5,828 | 2.36 |
| 2026 | 10 | -$547 | 0.57 |

**2021 is a clear losing year (PF 0.51).** 2024 is flat. 5 of 7 full
years are positive. The 2021 drawdown aligns with the sustained low-vol
regime (post-COVID normalization, pre-2022 rate hikes).

**Assessment: PASS with concern.** Not every year is positive, which is
honest for a real edge. The 2021 loss is consistent with the LOW_VOL
regime weakness. The strategy works when rates are volatile (2019, 2022,
2025) and struggles when they're quiet (2021, 2024).

## Data Caveat

ZN 5m bar coverage at 14:00-14:25 ET is ~82% of weekdays. The missing
18% are low-volume days where Databento doesn't generate bars. Results
are conditioned on afternoon tradability. This creates potential
survivorship bias — the strategy may outperform in backtest because
low-volume days (where reversion may not work) are excluded.

## Expected Portfolio Role

| Dimension | Value |
|-----------|-------|
| **Factor** | STRUCTURAL |
| **Asset** | ZN (rates — no other active rates strategy except Treasury-Rolldown) |
| **Session** | 14:00-14:25 ET (afternoon — zero overlap with morning strategies) |
| **Direction** | Both, short-biased |
| **Horizon** | Intraday (25-minute hold) |
| **Expected trades** | ~45/year |
| **Portfolio role** | Diversifier / Tail Engine (high-vol activated) |
| **Overlap** | Zero with all morning equity strategies. Potential correlation with Treasury-Rolldown on same asset (ZN), but different mechanism and horizon (monthly carry vs 25m intraday). |

### Contribution Expectations

- **In high-vol regimes:** Strong contributor ($118 avg PnL, PF 1.64)
- **In low-vol regimes:** Minimal impact ($6 avg PnL, PF 1.04)
- **Correlation with existing portfolio:** Expected near-zero. Rates
  afternoon microstructure has no mechanism overlap with equity morning
  momentum or commodity daily trend.
- **Marginal Sharpe contribution:** Likely positive due to zero
  correlation even at moderate standalone PF.

## Decision

**ADVANCE to probation.** Probation-only, MICRO tier.

Forward evidence required before any promotion. The vol-regime
dependency and 2021 drawdown mean this strategy must prove it works in
the current regime, not just in backtest.
