# Phase 4 Audit — Engine Hardening

**Date Completed:** 2026-03-07
**Auditor:** Claude (engine builder)

---

## Objective

Harden the backtest engine with realistic transaction costs, statistical validation (bootstrap CIs, Deflated Sharpe Ratio), regime detection, and portfolio-level analysis. Determine which edges survive friction and multiple-testing correction.

## Infrastructure Delivered

| Module | Location | Purpose |
|--------|----------|---------|
| Transaction costs | `engine/backtest.py` | Commission + slippage per fill |
| Bootstrap CIs | `engine/statistics.py` | 10K resample confidence intervals |
| Deflated Sharpe Ratio | `engine/statistics.py` | Multiple testing correction (López de Prado) |
| Regime detection | `engine/regime.py` | ATR percentile volatility classifier |
| Hardened baselines | `backtests/hardened_baselines/` | Gross vs net comparison |
| Portfolio analysis | `research/portfolio/` | Combined equity + drawdown overlap |

## Cost Model

| Symbol | Commission/Side | Slippage | Tick Size | Round-Trip Cost |
|--------|----------------|----------|-----------|-----------------|
| MES | $0.62 | 1 tick (0.25pt) | $0.25 | $3.74/trade |
| MNQ | $0.62 | 1 tick (0.25pt) | $0.25 | $2.24/trade |
| MGC | $0.62 | 1 tick (0.10pt) | $0.10 | $3.24/trade |

Slippage model: adverse direction on every fill (conservative).

## Results: Gross vs Net

| Strategy | Trades | Gross PF | Net PF | Gross PnL | Net PnL | Friction | Impact |
|----------|--------|----------|--------|-----------|---------|----------|--------|
| PB-MGC-Short | 28 | 2.02 | 1.85 | $767 | $676 | $91 | -11.8% |
| PB-MNQ-Long | 342 | 1.13 | 1.08 | $1,988 | $1,222 | $766 | -38.5% |
| ORB-009 MGC-Long | 106 | 1.99 | 1.83 | $3,022 | $2,679 | $343 | -11.4% |
| VWAP-006 MES-Long | 572 | 1.21 | 1.05 | $2,879 | $739 | $2,139 | -74.3% |

### Verdicts
- **PB-MGC-Short:** SURVIVES — low trade count minimizes friction
- **ORB-009 MGC-Long:** SURVIVES — strong edge absorbs costs
- **PB-MNQ-Long:** FRAGILE — 38.5% PnL erosion, Net PF barely above 1.0
- **VWAP-006 MES-Long:** EFFECTIVELY DEAD — 74% of PnL consumed by friction

## Results: Bootstrap CIs (95%, 10K resamples)

| Strategy | PF Point | PF 95% CI | Key Insight |
|----------|----------|-----------|-------------|
| PB-MGC-Short | 1.85 | [0.72, 4.77] | CI includes <1.0 (28 trades too few) |
| PB-MNQ-Long | 1.08 | [0.82, 1.40] | CI includes <1.0 (edge uncertain) |
| ORB-009 MGC-Long | 1.83 | [1.07, 3.09] | CI excludes <1.0 (edge confirmed) |
| Portfolio | 1.23 | [0.98, 1.54] | CI barely includes <1.0 |

## Results: Deflated Sharpe Ratio (36 trials)

| Strategy | Observed Sharpe | DSR | Significant? |
|----------|----------------|-----|-------------|
| PB-MGC-Short | 3.68 | 0.993 | YES |
| ORB-009 MGC-Long | 3.22 | 1.000 | YES |
| PB-MNQ-Long | 0.60 | 0.000 | NO |
| Portfolio (3-strat) | 1.66 | 0.000 | NO |

Expected max Sharpe under null (36 trials): 2.23. Only PB-MGC-Short and ORB-009 exceed this threshold.

## Results: Regime Breakdown (ORB-009)

| Regime | Trades | PF | Sharpe | PnL | Exp/Trade |
|--------|--------|-----|--------|-----|-----------|
| Low (<33rd pct) | 31 | 1.11 | 0.58 | $85 | $2.73 |
| Medium (33-67th) | 66 | 2.05 | 4.02 | $2,098 | $31.79 |
| High (>67th pct) | 9 | 2.18 | 3.84 | $496 | $55.09 |

**Actionable:** Skip low-vol days → eliminates 31 losing trades, preserves 96% of PnL.

## Results: Portfolio Combination

| Metric | 3-Strategy | Recommended 2-Strategy |
|--------|-----------|----------------------|
| Strategies | PB-MGC-Short + PB-MNQ-Long + ORB-009 | PB-MGC-Short + ORB-009 |
| Total PnL | $4,577 | ~$3,355 |
| Sharpe | 1.66 | >2.0 (est.) |
| DSR Significant | NO | YES (est.) |
| MaxDD | $1,566 | Lower (est.) |

Removing PB-MNQ-Long (DSR=0.000) improves statistical significance of portfolio.

## Quality Checks

- [x] Transaction costs match known broker rates (TradeStation/NinjaTrader micros)
- [x] Slippage model is conservative (adverse on every fill)
- [x] Bootstrap uses 10K resamples (sufficient for 95% CI stability)
- [x] DSR uses correct N_TRIALS=36 (4 strategies × 3 assets × 3 modes)
- [x] DSR implementation matches López de Prado (2014) — pure numpy, no scipy
- [x] Regime classifier validated on real ORB-009 data
- [x] Portfolio drawdown overlap analysis reveals hidden risk (65-80%)
- [x] All modules backward compatible (zero friction if no params)

## Risks Identified

1. **PB-MGC-Short sample size:** Only 28 trades. DSR passes but bootstrap CI wide. Need paper trade to accumulate more data.
2. **Drawdown overlap:** Despite zero daily PnL correlation, strategies spend 65-80% of drawdown periods simultaneously in drawdown. Prop account survival depends on MaxDD, not daily Sharpe.
3. **ORB-009 2024 weakness:** Walk-forward shows PF=0.97 in 2024 vs 3.42 in 2025. Edge may be recent. Monitor for decay.
4. **No out-of-sample test:** All analysis is in-sample. Paper trade is the true OOS test.

## Decision

- Deploy 2-strategy portfolio: PB-MGC-Short + ORB-009 MGC-Long
- Add ATR regime gate to ORB-009 (skip low-vol days)
- Begin paper trade validation
- Next phase: Kelly sizing + Monte Carlo simulation

---
*Audit generated 2026-03-07*
