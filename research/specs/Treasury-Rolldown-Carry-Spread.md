# Strategy Spec: Treasury-Rolldown-Carry-Spread

## Hypothesis

Different points on the Treasury yield curve offer different carry. In a
normal (upward-sloping) curve, longer maturities yield more than shorter
ones, but the roll-down benefit varies by tenor. A strategy that ranks
ZN (10Y), ZF (5Y), and ZB (30Y) by estimated carry and goes long the
highest-carry tenor while shorting the lowest-carry tenor harvests the
carry differential without taking a directional rates bet.

This is a CARRY factor strategy, not momentum. The signal comes from the
relative attractiveness of different tenors based on their expected return
from holding (carry) rather than from the direction of recent price moves.

## Signal Quality Disclaimer

The carry scores come from `engine/carry_lookup.py` with quality label
**APPROXIMATE**. The signal is a duration-weighted 60-day trailing return,
not a true yield-curve rolldown calculation (which would require cash
yield data we don't have). This means:

- The ranking is directionally useful for identifying which tenor is
  outperforming on a carry-like basis
- The absolute magnitude of carry scores should not be interpreted as
  yield or basis points
- There is carry/momentum conflation, similar to the commodity proxy
  but less severe because duration-weighting partially isolates the
  curve-slope effect from the level effect

**Why this is still a valid v1 test:** If the spread between the
highest-carry and lowest-carry tenor produces a positive PF, the signal
is capturing something real — whether pure rolldown carry, curve-slope
momentum, or a blend. If it fails, the APPROXIMATE signal is likely
too noisy and we need real yield data before retesting. Either outcome
is informative.

## Signal Logic

1. **Compute carry scores** for ZN, ZF, ZB using `carry_lookup.rank_carry()`
2. **Rank tenors** by carry score at each monthly rebalance
3. **Long the highest-carry tenor** (best relative carry)
4. **Short the lowest-carry tenor** (worst relative carry)
5. **Middle tenor** is not traded (stays flat)

This creates a **curve spread**, not a directional bet. If rates rise or
fall uniformly across the curve, both legs move together and the spread
is approximately neutral. The strategy profits only when the carry
differential pays off — i.e., the high-carry tenor outperforms the
low-carry tenor.

## Duration Neutrality

The three tenors have different durations (price sensitivity to yield
changes):

| Tenor | Approx Duration | DV01 |
|-------|----------------|------|
| ZF (5Y) | ~4.7 years | $47 per bp |
| ZN (10Y) | ~7.8 years | $78 per bp |
| ZB (30Y) | ~19.5 years | $195 per bp |

**v1 approach: Equal notional (1 contract each).**

This is NOT duration-neutral. A 1bp parallel yield shift moves ZB ~$195
but ZF only ~$47. The strategy has residual duration exposure.

**Why accept this for v1:** We trade 1 micro/mini contract per side.
True duration-neutral sizing would require fractional contracts (e.g.,
0.4 ZB vs 1.0 ZF), which we can't do. The equal-notional approach is
the simplest testable version. If the signal works, v2 can implement
DV01-weighted sizing.

## Rebalance Logic

- **Frequency:** Monthly (last trading day of each month)
- **Signal evaluation:** `rank_carry(["ZN", "ZF", "ZB"], price_data)`
  computed on rebalance day using trailing 60 daily closes
- **Position change:** At next day's open after rebalance signal
- **Hold through the month** — no intra-month re-ranking
- **Stop:** None in v1 (spread strategies have natural mean-reversion,
  stops tend to hurt)

## Target Assets

| Asset | Role | Data Depth |
|-------|------|------------|
| ZN (10-Year Note) | Spread leg | 2019-06 to present (~6.7 yr, ~2080 daily bars) |
| ZF (5-Year Note) | Spread leg | 2019-06 to present (~6.7 yr, ~1985 daily bars) |
| ZB (30-Year Bond) | Spread leg | 2019-06 to present (~6.7 yr, ~2067 daily bars) |

Common overlap: ~1,978 trading days, ~94 monthly rebalances.

## Parameters (Initial)

```
CARRY_LOOKBACK = 60         # Days for carry score computation
REBALANCE = monthly         # Last trading day of each month
SPREAD_MODE = "long_short"  # Long best carry, short worst carry
DURATION_NEUTRAL = False    # v1: equal notional. v2: DV01-weighted.
USE_STOP = False            # No stop on spread
```

## Backtest Structure

This strategy is unusual because it trades a **spread across assets**,
not a single asset. The backtest needs to:

1. Resample all three tenors to daily bars
2. Align on common dates
3. At each month-end, rank by carry score
4. Compute PnL as: (long leg return × point_value) - (short leg return × point_value)
5. The middle tenor contributes zero PnL

Each leg uses its own `point_value` and `tick_size` from `engine/asset_config.py`.

## Source

- Butler & Butler: "Managed Futures Carry: A Practitioner's Guide" (Return Stacked)
- Koijen et al. (2018): "Carry" — Journal of Financial Economics
- Harvest note: `45_treasury_rolldown_carry_spread.md`

## Key Failure Modes to Watch

1. **APPROXIMATE signal too noisy:** The duration-weighted 60-day return
   may not isolate carry well enough from momentum. If the spread PF is
   near 1.0 with high variance, the signal is noise. Fix: need real yield
   data (v2 or external source).

2. **Parallel rate moves dominate:** If rates move mostly in parallel
   (all tenors move the same direction by the same amount), the spread
   collapses to near-zero PnL every month. The strategy only works when
   the curve reshapes (steepens, flattens, or twists). If most months
   show near-zero PnL, the spread construction is correct but the
   opportunity set is thin.

3. **Duration mismatch on non-parallel moves:** Without DV01 weighting,
   a non-parallel move that hits ZB harder than ZF creates unintended
   PnL from the duration mismatch, not from carry. Check: does the
   PnL correlate with the level of rates (momentum) or the slope of
   rates (carry)?

4. **Low trade count:** ~94 monthly rebalances, but the spread position
   may not change every month (same tenor stays highest carry for
   consecutive months). Expect 30-50 actual position changes over 6.7
   years. Marginal for statistical significance.

5. **2022 rate shock:** The fastest tightening cycle in decades. The
   curve inverted, carry rankings likely whipsawed. This is THE stress
   test — did the spread protect capital or blow up?

## Diversification Role

- **Factor:** CARRY — the #1 open factor gap (0 active, 0 probation)
- **Asset class:** Rates — 0 active strategies, 4 prior failures
  (all were momentum or event, not carry)
- **Horizon:** Monthly rebalance (matches carry proxy and Treasury TSM)
- **Correlation to portfolio:** Should be very low. A curve spread has
  near-zero beta to equity index direction, FX moves, or commodity prices.
- **Portfolio role:** Diversifier (fills two gaps: CARRY factor + rates asset)

## Verification Intent

This strategy is the 2-week verification test for the Carry Lookup Table
v1 unlock. Per the blocked-unlock roadmap:
- If it produces a testable signal (regardless of PF), the unlock is verified
- If Treasury-Rolldown enters testing within 2 weeks, the leverage was real
- If it shows PF > 1.0 with meaningful trade count, CARRY as a factor
  has a foothold in the portfolio for the first time
