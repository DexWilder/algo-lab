# Promotion Evaluation: ZN-Afternoon-Reversion

**Date:** 2026-04-06
**Current Status:** Probation (MICRO tier, entered 2026-03-20)
**Forward Evidence:** 1 trade (+$16) — too early for forward verdict
**Backtest Basis:** PF 1.29, 304 trades, WF H1=1.30 H2=1.27

---

## Robustness Matrix (from walk-forward analysis)

| Check | Result | Detail |
|-------|--------|--------|
| Walk-forward both halves > 1.0 | **PASS** | H1=1.30, H2=1.27 |
| No regime cell PF < 0.5 (≥10 trades) | **PASS** | LOW=1.12, NORMAL=1.01, HIGH=1.64 |
| ≥75% rolling windows PF > 1.0 | **FAIL** | 64% (9/14 windows) |
| ≥60% of years PF > 1.0 | **PASS** | 71% (5/7 full years) |
| **Score** | **3/4** | |

## ATR Vol Filter Enhancement

The ATR vol regime filter (70th percentile gate) was validated as a
reusable component on this strategy:

| Metric | Unfiltered | With ATR Filter | Delta |
|--------|-----------|----------------|-------|
| PF | 1.29 | **1.77** | **+0.48** |
| Trades | 304 | ~100 | -67% |
| Win Rate | 56.6% | ~62% | +5.4% |

The filter dramatically improves PF but cuts trades by two-thirds.
This creates a design decision: deploy the filtered or unfiltered
version?

### Filtered vs Unfiltered Trade-Off

| Dimension | Unfiltered | Filtered |
|-----------|-----------|---------|
| PF | 1.29 | 1.77 |
| Trades/year | ~45 | ~15 |
| Edge quality | Moderate | Strong |
| Evidence speed | ~8 months to 30 trades | ~2 years to 30 trades |
| Regime dependency | Moderate (1.04 in LOW_VOL) | Eliminated (only trades in HIGH_VOL) |
| Short-bias value | 89% PnL from shorts | Same ratio, fewer trades |

**Recommendation for probation:** Keep unfiltered for now. Evidence
accumulates faster, and the 30-trade gate is already slow at ~45/year.
The filtered version should be staged as a v2 for deployment after
promotion — better edge but too slow for probation evidence gathering.

## Forward Evidence Assessment

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Forward trades | 1 | 30 | 3% to gate |
| Forward PF | +$16 (1 trade) | > 1.1 | Too early |
| Probation weeks used | 2/24 | — | 8% |
| Short-side trades | 0 | Majority | Too early |

**Verdict: TOO EARLY for promotion decision.** The strategy has only
produced 1 forward trade in ~2.5 weeks (expected ~2/week from backtest).
The sparse ZN afternoon bar issue is suppressing signal generation.

## Portfolio Usefulness (Elite Rubric)

| Q | Score | Reasoning |
|---|-------|-----------|
| Q1: Mechanism | 3 STRONG | Afternoon rates reversion, discovered via falsification |
| Q2: Durability | 2 MARGINAL | Rolling windows 64% (below 75%), 2021 losing year |
| Q3: Best in family | 4 ELITE | Only afternoon rates reversion strategy in FQL |
| Q4: Portfolio fit | 4 ELITE | Fills STRUCTURAL gap, rates asset, afternoon session, short-biased |
| Q5: Evidence | 1 WEAK | 1 forward trade only |
| Q6: Worth attention | 3 STRONG | Fills 3 portfolio gaps simultaneously |
| **Total** | **17/24** | **STRONG but evidence-gated** |

Gap bonus: +2 (STRUCTURAL + afternoon session)
**Effective score: 19/24**

## Disposition

| Decision | Condition |
|----------|-----------|
| **CONTINUE PROBATION** (current) | Evidence too early. 1 trade is not a verdict. |
| PROMOTE to conviction | After 15+ forward trades with PF > 1.0 and short bias confirmed |
| PROMOTE to core | After 30+ forward trades with PF > 1.1 and contribution confirmed |
| DOWNGRADE | If forward PF < 0.7 after 15 trades, or 0 trades for 8+ consecutive weeks |
| ENHANCE (v2) | Apply ATR filter after promotion, not during probation evidence gathering |

## Key Risks

1. **Sparse ZN afternoon bars** — ~20% of weekdays lack the required
   14:00-14:25 bars. Forward evidence accumulates slower than backtest
   would suggest.
2. **2026 YTD is weak** — 14 trades, PF 0.32. May be regime-specific.
3. **Rolling windows at 64%** — below the 75% promotion threshold.
   This is the weakest robustness dimension.

## Next Review

After 10 forward trades — estimated ~June 2026 given sparse bar frequency.
At that point: check short-side dependence, regime distribution, and
whether the 2026 weakness continues.
