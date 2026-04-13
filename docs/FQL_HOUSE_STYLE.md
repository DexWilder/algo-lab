# FQL House Style

*What an elite strategy candidate looks like. One page.*

---

## The Standard

A strategy earns its place in FQL when it demonstrates **distributed edge** —
not lottery-ticket tail dependence, not parameter-fitted backtests, not
single-asset curve fits.

Distributed edge means: **most trades contribute to the result, not just a few.**

---

## What We Look For

### Entry: Dense and Frequent
- Produces 500+ trades over the sample period
- Fires continuously across market conditions, not just special events
- Works on multiple assets without modification

### Filter: Noise-Cutting
- Removes 30-40% of counter-signal entries
- Raises win rate without reducing trade density below threshold
- Currently proven: **EMA slope** (EMA21 vs EMA50 trend gate)

### Exit: Positive Median
- The median trade must be profitable, not just the mean
- Ratcheting/milestone exits preferred over pure trailing stops
- Currently proven: **profit ladder** (1R/2R/3R lock ratchet)
- This is the hardest requirement and the most important one

### Cross-Asset: Generalization Required
- Must be profitable on ≥3 assets independently
- Single-asset winners are curve fits until proven otherwise
- Currently validated assets: MNQ, MES, MGC, M2K, MCL

### Concentration: No Lottery Tickets
- Top-3 trades < 30% of total PnL
- Top-10 trades < 55%
- No single year > 40%
- Max drawdown duration < 500 days (workhorse) or 900 days (tail engine)

---

## The Proven Stack

| Component | Name | Role | Status |
|-----------|------|------|--------|
| Entry | **ORB breakout** | 30-min opening range break | Top-tier donor |
| Filter | **EMA slope** | EMA21 vs EMA50 trend gate | Top-tier donor |
| Exit | **Profit ladder** | 1R/2R/3R ratcheting lock | Top-tier donor |
| Stop | **2.0× ATR** | Wide initial stop | Sweep-validated |

This is the only combination that survived 24 alternative component tests,
8 deep validations, and concentration-aware classification across 5 assets.

---

## What We Reject

- **Tail-dependent strategies**: positive PF but negative median trade
- **Single-asset fits**: works on one asset, fails on sisters
- **Concentration-driven results**: top-3 trades > 50% of PnL
- **Single-year dependence**: one lucky period carries the backtest
- **Untestable mechanisms**: requires data we don't have (CFTC, VIX, macro)
- **Complexity without payoff**: if it can't be explained in one sentence, it's suspect

---

## Decision Hierarchy

When choosing what to build next:

1. **Portfolio usefulness** beats isolated backtest attractiveness
2. **Session diversification** is a priority (afternoon/close is the biggest gap)
3. **Proven donor components** raise survival probability
4. **Testability** beats theoretical elegance
5. **Archive means memory**, not deletion — every rejected idea is a future donor

---

## The Autocorrelation Screen

Before testing any new asset: compute 5-min return autocorrelation.

- **> -0.05**: likely works for ORB-style workhorse (momentum-friendly)
- **< -0.05**: likely fails (too mean-reverting for breakout follow-through)
- **Rates (ZN/ZF/ZB)**: always skip for breakout strategies

---

## One Sentence

> FQL builds dense, cross-asset, positive-median strategies from proven
> components — and rejects everything else, no matter how good it looks
> on paper.
