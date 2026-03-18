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

## Sleeve vs Overlay: Design Decision

This strategy can be implemented two ways. The decision matters for
how it competes for portfolio slots and how it's evaluated.

### Option A: Standalone Sleeve (v1 — recommended for first-pass)

A strategy that holds long MES with vol-managed sizing, evaluated as
an independent return stream alongside other strategies.

- **Pros:** Fits the standard lifecycle. Can be scored on the rubric,
  run through batch_first_pass, and compete for slots. Clean evaluation.
- **Cons:** As a standalone long-equity sleeve, it has directional
  exposure and will lose money in bear markets. Its Sharpe is higher
  than unscaled, but it's not alpha — it's a better way to hold beta.
- **Portfolio role:** Stabilizer (smooths equity exposure) or Diversifier
  (fills VOL factor gap with a sizing mechanism no other strategy uses).

### Option B: Portfolio Overlay (v2 — future consideration)

A risk-management layer that scales the entire portfolio's gross exposure
based on realized vol. Not a strategy that competes for a slot — a
meta-layer that improves all strategies.

- **Pros:** The Moreira & Muir result is strongest as a portfolio overlay.
  Applying vol-management to the whole portfolio would reduce drawdowns
  for all strategies simultaneously.
- **Cons:** Requires multi-strategy position sizing infrastructure that
  FQL doesn't have yet. Complex to implement and evaluate. Not compatible
  with the current 1-contract-per-strategy forward runner.
- **When to build:** After cash-account deployment (Layer C) when
  position sizing moves from 1-lot to volatility-targeted.

**v1 decision: Standalone Sleeve (Option A).** It's testable now, fits
the lifecycle, and proves whether vol-management adds value on our data
before we invest in the overlay infrastructure. If the standalone sleeve
works, the overlay is a natural v2 upgrade.

## FQL Implementation: Standalone Sleeve

For the v1 first-pass, implement as a standalone strategy that generates
daily signals:

- **Signal = 1 (long) every day** — always in the market
- **Position size = weight** (communicated via a sizing field)
- **PnL = daily_return × weight × point_value**

This fits the existing `generate_signals` interface: the strategy
resamples to daily, computes the vol-managed return series, and
outputs signals with the sizing weight embedded.

**Honest framing:** This is primarily a volatility/risk-transformation
mechanism, not a directional timing edge. It does not predict which way
MES will move. It predicts that scaling down during high vol and up
during low vol will improve the risk/return tradeoff of holding MES.
The "edge" is in sizing, not in signal.

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

### First-Pass Comparison Set

Standard PF is less meaningful for an always-long strategy (PF of
buy-and-hold is just the market's PF). The first-pass must answer
three questions, not one:

**Comparison 1: Vol-managed MES vs unscaled MES buy-and-hold**
- Primary metric: Sharpe ratio improvement
- Secondary: max drawdown reduction, Calmar ratio improvement
- Threshold: Sharpe improvement > 30% = ADVANCE, 10-30% = SALVAGE, < 10% = REJECT
- This answers: does vol-management work on our data?

**Comparison 2: Vol-managed MES vs current MES roster contribution**
- The portfolio has 1 MES core strategy (XB-PB-EMA-MES-Short) and
  1 MNQ conviction (NoiseBoundary-MNQ-Long)
- Compute: correlation of vol-managed daily returns with XB-PB-EMA
  and NoiseBoundary daily PnL streams
- If correlation < 0.25 → genuine diversification value
- If correlation > 0.50 → just another way to be long equity
- This answers: does it add something the portfolio doesn't already have?

**Comparison 3: Drawdown and diversification impact**
- Compute: portfolio equity curve WITH vs WITHOUT VolManaged
  (same counterfactual methodology as counterfactual_engine.py)
- Key metrics: does adding VolManaged reduce portfolio max DD?
  Does it reduce the worst monthly loss? Does it improve the
  portfolio's rolling 60-day Sharpe?
- Check specifically: during the March 2020 crash and the 2022
  bear market, did the vol-managed weight scale down fast enough
  to reduce losses?
- This answers: does it make the portfolio more robust, not just higher Sharpe?

**Classification:**
- ADVANCE: Sharpe improvement > 30% AND corr < 0.35 with existing AND DD reduction > 10%
- SALVAGE: Sharpe improvement > 30% but corr > 0.35 (works but overlaps)
- MONITOR: Sharpe improvement 10-30% (marginal, test different params)
- REJECT: Sharpe improvement < 10% or no DD reduction

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
