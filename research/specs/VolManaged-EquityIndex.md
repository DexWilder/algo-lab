# Strategy Spec: VolManaged-EquityIndex-Futures

## Hypothesis

Higher realized volatility on equity index futures is not compensated by
proportionally higher expected returns. When vol doubles, returns do not
double — but risk does. A strategy that scales position size inversely
with recent realized volatility captures the same expected return with
lower risk, improving risk-adjusted performance.

This is one of the most replicated results in quantitative finance.
Moreira & Muir (2017, Journal of Finance) showed it across equities,
bonds, credit, and FX. The mechanism is structural: volatility clusters
(high vol persists) while expected returns mean-revert faster. Scaling
down during vol clusters avoids the worst drawdowns without sacrificing
much expected return.

**Why this is genuinely different from everything in the current portfolio:**
Every existing FQL strategy decides WHEN to trade (entry/exit timing).
This strategy decides HOW MUCH to hold. It's a sizing regime, not a
signal. It can be run standalone (long MES with vol-managed sizing) or
eventually as a portfolio overlay. The v1 spec is standalone.

## Quick Feasibility (Already Tested)

On MES daily data (2019-2026, 2,091 days):
- **Unscaled buy-and-hold Sharpe: 0.64**
- **Vol-managed Sharpe: 0.92** (+44% improvement)
- Target vol: 15% annualized, leverage caps 0.25x-2.0x
- MES vol range: 4.2% to 84.6% (median 13.0%, current 16.6%)

This is not a backtest of a complex strategy — it's a mechanical
transformation of position size. The improvement is structural and
well-documented across decades and asset classes.

## Signal Logic

1. Compute 20-day realized volatility (annualized) from daily returns
2. Compute target weight: `weight = target_vol / realized_vol`
3. Cap weight: `weight = clip(weight, MIN_WEIGHT, MAX_WEIGHT)`
4. Hold long MES with position scaled by weight
5. Rebalance daily (weight changes as vol changes)

There is no entry/exit signal. The strategy is always long. The only
variable is HOW MUCH — which changes daily based on the vol estimate.

## FQL Implementation: Standalone Sleeve

For the v1 first-pass, implement as a standalone strategy that generates
daily signals:

- **Signal = 1 (long) every day** — always in the market
- **Position size = weight** (communicated via a sizing field)
- **PnL = daily_return × weight × point_value**

This fits the existing `generate_signals` interface: the strategy
resamples to daily, computes the vol-managed return series, and
outputs signals with the sizing weight embedded.

For backtest evaluation, the key metric is: does the vol-managed
equity curve have a higher Sharpe than unscaled buy-and-hold?

## Parameters (Initial)

```
VOL_LOOKBACK = 20          # Days for realized vol estimate
TARGET_VOL = 0.15          # 15% annualized target
MIN_WEIGHT = 0.25          # Don't go below 25% position (never fully out)
MAX_WEIGHT = 2.0           # Don't exceed 2x leverage
REBALANCE = daily          # Weight updated every trading day
```

### Parameter Sensitivity Expectations

- VOL_LOOKBACK: 10-60 days should all work. Shorter = more responsive,
  noisier. Longer = smoother, slower. 20 is the standard in the
  literature.
- TARGET_VOL: 10-20% range. Lower = more conservative. Higher = more
  aggressive. 15% is standard for a single-asset sleeve.
- MIN_WEIGHT: 0.0 (can go fully flat) vs 0.25 (always some exposure).
  Literature typically uses 0.0 but 0.25 is more practical for a
  standalone sleeve.
- MAX_WEIGHT: 1.5-3.0 range. Higher = more leverage in calm markets.
  2.0 is conservative.

The strategy should be VERY parameter-stable because the mechanism is
structural (vol clustering) not parameter-dependent.

## Target Assets

| Asset | Data Depth | Status |
|-------|------------|--------|
| MES | 2019-06 to present (~6.7 yr, 2091 daily bars) | Primary |
| MNQ | Same depth | Secondary (test for robustness) |

Extension to non-equity assets (MGC, MCL, 6J) is a v2 consideration.
The Moreira & Muir result applies to bonds and commodities too.

## Source

- Moreira & Muir (2017): "Volatility-Managed Portfolios" — Journal of Finance
- NBER Working Paper w22208
- Harvest note: `46_equity_index_volatility_managed_futures.md`

## Key Failure Modes to Watch

1. **Post-2020 vol regime:** The MES data includes the 2020 COVID crash
   (vol spiked to 84.6%) and the 2022 tightening (sustained high vol).
   Both are in-sample. If the Sharpe improvement comes mainly from
   scaling down during these two events, the strategy is regime-dependent.
   Check year-by-year Sharpe improvement — it should be positive in
   most years, not just crisis years.

2. **Transaction costs of daily rebalancing:** In a 1-contract micro
   futures account, "scaling" the position means you're either in (1
   contract) or out (0 contracts). True position scaling requires
   fractional sizing, which micros approximate poorly. The v1 backtest
   should compute PnL as if fractional sizing is available (continuous
   weight), then separately check: if forced to 0 or 1 contract, does
   the binary version still help?

3. **The strategy is always long.** It has directional exposure. In a
   bear market (2022), it will lose money — just less than unscaled.
   It is NOT market-neutral. The claim is better risk-adjusted returns,
   not absolute returns in all environments.

4. **Overlap with existing MES/MNQ strategies.** XB-PB-EMA-MES-Short
   is the only MES core strategy. NoiseBoundary-MNQ-Long is probation.
   VolManaged is long-biased MES — check correlation with NoiseBoundary
   and XB-PB-EMA. If the vol-managed return series is highly correlated
   with existing strategies, the diversification value drops.

## Diversification Role

- **Factor:** VOLATILITY — 0 active strategies in this factor. 1 in
  watch (TTMSqueeze-M2K). This would be the first conviction-level
  VOL strategy.
- **Asset:** MES — only 1 core strategy (XB-PB-EMA). Underpopulated.
- **Mechanism:** Sizing, not timing. Genuinely different from every
  other strategy in the portfolio (all are entry/exit timing strategies).
- **Horizon:** Daily rebalance — adds to daily-bar diversity alongside
  DailyTrend-MGC.
- **Correlation:** Expected to be low-moderate with existing strategies.
  The vol-managed return is the same asset (MES) but the sizing creates
  a different return profile — lower vol, fewer drawdowns, higher Sharpe.

## Displacement Framework

### If First-Pass = ADVANCE (PF metric not standard — use Sharpe comparison)

For this strategy, the standard PF metric is less meaningful because it's
always long (PF of buy-and-hold is just the market's PF). The right
metric is: **does vol-managed Sharpe > unscaled Sharpe?**

- If Sharpe improvement > 30% → ADVANCE equivalent
- If Sharpe improvement 10-30% → SALVAGE (test different params)
- If Sharpe improvement < 10% → REJECT (vol-management doesn't help on this data)

### Rubric Estimate

| Q | Est. Score | Reasoning |
|---|-----------|-----------|
| Q1 Mechanism | 4 ELITE | Moreira & Muir (Journal of Finance), replicated across asset classes |
| Q2 Durability | 3 STRONG | Documented across decades. Quick test shows +44% Sharpe on our data. |
| Q3 Best in family | 4 ELITE | Only vol-management strategy with a code path. No competition. |
| Q4 Portfolio fit | 3 STRONG | Fills VOL gap. MES underpopulated. Different mechanism (sizing vs timing). |
| Q5 Evidence | 2 MARGINAL | Quick test promising. No formal first-pass yet. |
| Q6 Worth attention | 3 STRONG | Simple to build, high academic confidence, fills clear gap. |
| **Total** | **19 raw** | + 2 gap bonus = **21 effective** |

### Displacement Targets

- **MomIgn-M2K-Short (watch, 14):** Decisive advantage (+7 effective).
  VolManaged fills VOL gap; MomIgn adds to MOMENTUM overcrowding.
- **PB-MGC-Short (core, 16):** Strong advantage (+5 effective).
  VolManaged fills VOL gap on MES; PB-MGC adds to MGC concentration.
- **TTMSqueeze-M2K-Short (watch, 17):** VolManaged (21 effective)
  would be the stronger VOL representative if both advance.

### Conversion Timing

Treasury-Rolldown remains the lead active challenger (#1 in upgrade
sequence). VolManaged is #2 — the next conversion slot opens after:
- Treasury-Rolldown's June 1 displacement decision, OR
- If Treasury-Rolldown weakens materially (fallback trigger)

This spec is ready for immediate conversion when the slot opens.
