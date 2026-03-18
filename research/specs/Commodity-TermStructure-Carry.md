# Strategy Spec: Commodity-TermStructure-Carry

## Hypothesis

Commodity futures in backwardation (front > back) tend to deliver positive
roll yield as the contract converges toward spot. Commodities in contango
(front < back) tend to deliver negative roll yield. A simple carry strategy
ranks commodities by curve slope and goes long the most backwardated, short
the most contangoed. This is one of the most documented systematic factors
in the commodity literature (Erb & Harvey 2006, Koijen et al. 2018).

The edge is structural: backwardation reflects convenience yield (physical
holders pay a premium to hold the commodity) while contango reflects storage
costs. These forces are persistent and unrelated to price momentum.

**Important framing: This is a carry-proxy test, not true term-structure
carry.** We only have continuous front-contract data. The 60-day trailing
return proxy conflates carry with momentum. If results are positive, we
cannot claim pure carry until we decompose with real term-structure data.
The first-pass question is: "Does the carry-proxy signal produce a
tradeable edge?" — not "Is this pure carry?"

## Data Constraint

FQL currently has **continuous front-contract data only** for MCL and MGC
(Databento `.c.0` rolls). We do not have second-contract or term-structure
data. This limits the carry signal to a **price-based proxy** rather than
a true front-vs-back spread.

### Carry Proxy: Roll-Return Estimator

Because continuous contracts use Panama-canal or proportional adjustment at
roll, the roll itself is hidden in the adjusted price. We can recover a
carry signal from:

1. **Trailing roll-period return decomposition:** Compare the total return
   over a roll window against the return of a hypothetical non-rolling
   position. The difference is the roll yield — positive = backwardation,
   negative = contango.

2. **Simpler v1 proxy — slope of the curve via trailing return divergence:**
   Compute the trailing 1-month return of the continuous contract. Compare
   it against the trailing 1-month price change of spot (approximated by
   the front contract's behavior near expiry). The gap is a noisy carry
   estimate.

3. **Simplest v1 (recommended for first pass):** Use the trailing 60-day
   return as a carry-direction proxy. This conflates carry with momentum,
   but on commodities the two are correlated (~0.4-0.6 historically).
   If the combined signal works, we can decompose later. If it doesn't,
   pure carry likely doesn't either given our data limitations.

**Recommended first pass: Option 3.** It's testable now with existing data.
If results are promising, invest in front/back contract data to build the
true term-structure signal.

## Signal Logic

- **Carry score:** For each commodity, compute the 60-trading-day trailing
  return of the continuous front contract.
- **Cross-sectional rank:** Rank MCL and MGC by carry score.
  - Highest carry score → long
  - Lowest carry score → short
- **Minimum spread filter:** Only trade if the absolute difference in carry
  scores exceeds a threshold (e.g., 2% over 60 days). If both commodities
  have similar carry, stay flat — there's no cross-sectional signal.
- **Single-asset fallback:** If only one commodity clears the threshold
  vs. zero, take only the one-sided trade (long backwardated OR short
  contangoed) rather than forcing a pair.

## Rebalance Logic

- **Frequency:** Monthly (last trading day of each month)
- **Signal evaluation:** 60-day trailing return computed on rebalance day
- **Position change:** At next day's open after signal
- **Hold through the month** — no intra-month re-ranking
- **Stop:** Toggle (none vs. 2.5x ATR from entry)
- **Max position:** 1 contract per side per asset (micro contracts)

## Asset Universe

| Asset | Class | Contract | Data Depth | Status |
|-------|-------|----------|------------|--------|
| MCL | Energy (Crude Oil) | Micro WTI | 2021-07 to present (~4.7 yr) | Primary |
| MGC | Metal (Gold) | Micro Gold | 2019-06 to present (~6.7 yr) | Primary |

### Future expansion (requires data onboarding)

- SI (Silver) — metal diversification
- HG (Copper) — industrial metal, different carry behavior
- NG (Natural Gas) — extreme backwardation/contango swings
- Ag futures (ZS, ZC, ZW) — seasonal carry patterns

With only 2 assets, the cross-sectional ranking is minimal. This is
acknowledged as a limitation. The v1 test answers: "Does the carry
signal produce a tradeable edge on MCL and MGC individually and as a
simple long/short pair?"

## Weighting / Balancing

- **Equal risk weight:** Normalize position size by 20-day ATR so that
  MCL and MGC contribute roughly equal volatility per contract.
- **No sector tilt:** With only energy + metal, sector balance is
  inherently 50/50. In future expansion, enforce max 40% per sector.
- **Gross exposure cap:** Max 2 micro contracts total (1 long + 1 short,
  or 1 directional if spread filter not met).

## Test Variants

Two variants tested in the first pass:

| Variant | Spread Filter | Purpose |
|---------|---------------|---------|
| **A: Filtered** | MIN_SPREAD_PCT = 0.02 | Only trade when carry scores diverge meaningfully |
| **B: Unfiltered** | MIN_SPREAD_PCT = 0.00 | Always take the rank signal, maximize sample size |

### First-Pass Analysis Checklist

- [ ] Does this behave more like commodity momentum than carry?
      (Compare to simple 60-day momentum — if results are nearly identical,
      the carry label is misleading)
- [ ] Does one asset dominate the result?
      (If MGC drives all the PnL and MCL is flat/negative, the signal is
      asset-specific, not a carry factor)
- [ ] Does the spread filter add value or just reduce sample?
      (Compare Variant A vs B on PF, trade count, and drawdown)
- [ ] Is performance concentrated in crisis periods?
      (If most PnL comes from COVID-2020 or 2022 energy crisis, the edge
      is regime-specific and unreliable going forward)

## Parameters (Initial)

```
CARRY_LOOKBACK_DAYS = 60       # Trailing return window for carry proxy
REBALANCE = monthly            # Last trading day of each month
MIN_SPREAD_PCT = 0.02          # Variant A: 2% filter. Variant B: 0%
ATR_LEN = 20                   # For risk normalization and optional stop
USE_STOP = toggle              # True/False
SL_ATR_MULT = 2.5              # Stop distance in ATR multiples
```

## Source

- Erb & Harvey (2006): "The Strategic and Tactical Value of Commodity Futures"
- Koijen, Moskowitz, Pedersen, Vrugt (2018): "Carry" — Journal of Financial Economics
- Quantpedia: Term Structure Effect in Commodities
- Harvest note: `42_commodity_term_structure_carry_energy_metals.md`

## Key Failure Modes to Watch

1. **Carry proxy conflation with momentum:** The 60-day return proxy
   mixes carry and momentum. If the backtest works, we won't know which
   factor is driving returns until we decompose with true term-structure
   data. This is acceptable for a first pass but must be addressed before
   promotion.

2. **Two-asset cross section is thin:** With only MCL and MGC, the
   cross-sectional ranking is binary (long one, short the other). Real
   commodity carry strategies use 15-30 contracts. Our signal will be
   noisier. If results are weak, the strategy may work with more assets
   but not with two.

3. **MCL data depth (4.7 years):** Only ~56 monthly rebalances. Adequate
   for first-pass but marginal for walk-forward stability. MGC at 6.7
   years is better.

4. **Crude oil regime sensitivity:** MCL carry behavior changed
   dramatically during COVID (extreme contango April 2020) and the
   2022 energy crisis (extreme backwardation). These are both in-sample.
   The strategy should handle both, but a 2-event sample of extremes is
   not robust.

5. **Monthly rebalance = low trade count:** ~12 signal evaluations per
   year, but position may not change every month. Expect 6-10 actual
   position changes per year. With 4.7 years of MCL data: ~28-47 trades.
   Marginal but testable.

## Diversification Role

- **Factor:** Pure CARRY — the #1 open factor gap (0 active, 0 probation)
- **Asset class:** Energy + Metal — no overlap with equity/FX probation set
- **Horizon:** Monthly rebalance — longest horizon in FQL alongside Treasury TSM
- **Correlation to existing portfolio:** Should be very low. Carry is
  structurally different from momentum, breakout, and event factors
  that dominate the current portfolio.
- **Expected contribution:** Even a modest PF (1.15-1.3) would be
  valuable because CARRY is genuinely uncorrelated to existing factors.
  This is a factor-diversification play, not an alpha maximization play.

## Decision Points After First Pass

- **If ADVANCE:** Invest in front/back contract data to build true
  carry signal. Decompose the 60-day proxy into carry vs. momentum
  components. If carry component is positive, proceed to validation
  battery with pure carry signal.
- **If SALVAGE:** Test with true term-structure data before rejecting.
  The proxy may be too noisy but the underlying carry factor may still
  be present.
- **If REJECT:** Log failure mode. If the proxy conflation killed it,
  the idea is not dead — it's blocked by data. If true carry also fails,
  commodity carry is structurally weak in micro futures and the family
  can be narrowed.
