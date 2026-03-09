# Research Log

*Chronological record of every experiment, result, and decision.*

---

## 2026-02-20 — PB Family Baseline Discovery

**Experiment:** Run Lucid v6.3 (PB-Trend) on Databento CME 5m data across MES, MNQ, MGC in long/short/both modes.

**Results:**
| Asset | Mode | PF | Sharpe | Trades | PnL | MaxDD |
|-------|------|-----|--------|--------|-----|-------|
| MGC | Short | 2.02 | 4.18 | 28 | $767 | $283 |
| MGC | Long | 1.26 | 1.50 | 69 | $691 | $662 |
| MNQ | Long | 1.12 | 0.94 | 343 | $1,921 | $1,951 |
| MES | Short | 1.10 | 0.75 | 167 | $586 | $884 |

**Decision:** MGC-Short is standout candidate. MNQ-Long marginal. MES-Short weak.

---

## 2026-02-22 — PB-MGC-Short Robustness Testing

**Experiment:** 8-criterion robustness battery on PB-MGC-Short: top-trade removal, walk-forward splits, session windows, parameter stability (25 variations).

**Results:**
- Top-trade removal: PF stays >1.0 after removing best trade
- Walk-forward: 2024 PF=0.72 (weak), 2025 PF=4.77 (strong)
- Session sweet spot: 09:30-11:00 ET
- Parameter stability: 25/25 variations profitable
- 100% parameter stability score

**Decision:** Promote to candidate_validated. Low trade count (28) remains a concern.

---

## 2026-02-25 — Strategy Harvesting (Batch 1)

**Experiment:** Harvest TradingView Pine Scripts across ORB, VWAP, ICT families. Score and triage for conversion.

**Results:** 76 scripts harvested across 8 families. Triage produced 8 clusters with convert_now/hold/reject labels. Top candidates: ORB-009, VWAP-006, ICT-010.

**Decision:** Convert top 3 candidates to Python for baseline backtesting.

---

## 2026-02-28 — Strategy Conversion Round 1

**Experiment:** Faithful conversion of ORB-009, VWAP-006, ICT-010 from Pine Script to Python. No optimization — preserve original parameters.

### ORB-009 (Opening Range Breakout + VWAP + Volume)
**Results:**
| Asset | Mode | PF | Sharpe | Trades | PnL |
|-------|------|-----|--------|--------|-----|
| MGC | Long | 1.99 | 3.63 | 106 | $3,022 |
| MGC | Both | 1.52 | 1.97 | 199 | $4,201 |
| MNQ | Both | 1.14 | 0.75 | 362 | $4,003 |
| MES | Both | 1.12 | 0.68 | 432 | $2,096 |

**Decision:** ORB-009 MGC-Long is strong. Proceed to validation.

### VWAP-006 (VWAP-RSI Scalper)
**Results:**
| Asset | Mode | PF | Sharpe | Trades | PnL |
|-------|------|-----|--------|--------|-----|
| MES | Long | 1.21 | 1.32 | 572 | $2,879 |
| MGC | Long | 1.32 | 1.89 | 259 | $2,190 |
| MNQ | Both | 1.09 | 0.67 | 976 | $4,602 |

**Decision:** Marginal edge, very high trade count. Hold for cost analysis.

### ICT-010 (Captain Backtest Session Sweep)
**Results:**
| Asset | Mode | PF | Sharpe | Trades | PnL |
|-------|------|-----|--------|--------|-----|
| MES | Both | 0.65 | -2.95 | 232 | -$1,603 |
| MGC | Both | 0.79 | -1.56 | 155 | -$931 |
| MNQ | Both | 0.84 | -1.22 | 264 | -$1,547 |

**Decision:** REJECTED. No edge on any asset/mode combination.

---

## 2026-03-01 — ORB-009 Robustness Validation

**Experiment:** Full 8-criterion robustness battery on ORB-009 MGC-Long.

**Results:**
- Top-trade removal: PF drops to 1.72 (robust)
- Walk-forward: 2024 PF=0.97 (weak), 2025 PF=3.42 (strong)
- Session sweet spot: 10:00-11:00 ET (PF=2.96, Sharpe=6.39)
- Parameter stability: 25/25 variations profitable (100%)
- Monthly consistency: 14/24 months profitable (58%)

**Decision:** Promote to candidate_validated. Session filter recommended.

---

## 2026-03-03 — Correlation Analysis

**Experiment:** Daily PnL correlation between ORB-009 and PB family.

**Results:**
- ORB-009 vs PB-MGC-Short: r < 0.01 (uncorrelated)
- ORB-009 vs PB-MNQ-Long: r < -0.005 (uncorrelated)
- VWAP-006 vs PB-MNQ-Long: r = 0.30 (moderate, both long-biased)

**Decision:** ORB-009 is ideal diversifier for PB family. VWAP-006 adds less portfolio value.

---

## 2026-03-07 — Engine Hardening: Transaction Costs

**Experiment:** Add realistic transaction costs to backtest engine. Commission ($0.62/side) + adverse slippage (1 tick per fill).

**Results (Gross → Net):**
| Strategy | Gross PF | Net PF | Friction | Impact |
|----------|----------|--------|----------|--------|
| PB-MGC-Short | 2.02 | 1.85 | $91 | -11.8% |
| PB-MNQ-Long | 1.13 | 1.08 | $766 | -38.5% |
| ORB-009 MGC-Long | 1.99 | 1.83 | $343 | -11.4% |
| VWAP-006 MES-Long | 1.21 | 1.05 | $2,139 | -74.3% |

**Decision:** VWAP-006 effectively dead (74% friction). PB-MNQ-Long fragile.

---

## 2026-03-07 — Bootstrap Confidence Intervals (10K resamples)

**Experiment:** 95% bootstrap CIs on trade PnL for profit factor, Sharpe, max drawdown.

**Results:**
| Strategy | PF Point | PF 95% CI |
|----------|----------|-----------|
| PB-MGC-Short | 1.85 | [0.72, 4.77] |
| PB-MNQ-Long | 1.08 | [0.82, 1.40] |
| ORB-009 MGC-Long | 1.83 | [1.07, 3.09] |
| Portfolio | 1.23 | [0.98, 1.54] |

**Key Finding:** ORB-009 is the only strategy where bootstrap PF CI excludes <1.0. PB-MGC-Short CI includes <1.0 due to only 28 trades.

---

## 2026-03-07 — Deflated Sharpe Ratio (36 trials)

**Experiment:** López de Prado DSR correcting for 36 strategy/asset/mode combinations tested.

**Results:**
| Strategy | Observed Sharpe | DSR | Significant? |
|----------|----------------|-----|-------------|
| PB-MGC-Short | 3.68 | 0.993 | YES |
| ORB-009 MGC-Long | 3.22 | 1.000 | YES |
| PB-MNQ-Long | 0.60 | 0.000 | NO |
| Portfolio (3-strat) | 1.66 | 0.000 | NO |

**Decision:** PB-MNQ-Long edge is indistinguishable from chance. Remove from portfolio.

---

## 2026-03-07 — ATR Regime Detection (ORB-009)

**Experiment:** Classify trading days by ATR percentile rank into low/medium/high volatility. Measure ORB-009 performance per regime.

**Results:**
| Regime | Trades | PF | Sharpe | PnL | Exp/Trade |
|--------|--------|-----|--------|-----|-----------|
| Low | 31 | 1.11 | 0.58 | $85 | $2.73 |
| Medium | 66 | 2.05 | 4.02 | $2,098 | $31.79 |
| High | 9 | 2.18 | 3.84 | $496 | $55.09 |

**Decision:** Skip low-vol days. Eliminates 31 losing trades, preserves 96% of PnL.

---

## 2026-03-07 — Portfolio Combination Analysis

**Experiment:** Combine PB-MGC-Short + PB-MNQ-Long + ORB-009 MGC-Long with transaction costs. Analyze daily PnL correlations and drawdown overlap.

**Results:**
- Portfolio PnL: $4,577 | Sharpe: 1.66 | MaxDD: $1,566
- Daily PnL correlations: all < 0.03 (excellent)
- Drawdown overlap: 65-80% (poor — simultaneous drawdowns)

**Decision:** Run 2-strategy portfolio (drop PB-MNQ-Long). Remaining strategies both gold-focused with near-zero correlation.

---

## 2026-03-08 — Phase 5.1: Regime Gate Testing (Both Strategies)

**Experiment:** Run ATR regime classification on both validated strategies. Test whether a simple low-vol gate improves net performance.

**Results:**

| Strategy | Metric | Ungated | Gated | Delta |
|----------|--------|---------|-------|-------|
| ORB-009 MGC-Long | PF | 1.83 | 2.07 | +0.24 |
| ORB-009 MGC-Long | Sharpe | 3.22 | 3.93 | +0.71 |
| ORB-009 MGC-Long | MaxDD | $933 | $685 | -$248 |
| PB-MGC-Short | PF | 1.85 | 2.36 | +0.51 |
| PB-MGC-Short | Sharpe | 3.68 | 5.27 | +1.60 |
| PB-MGC-Short | PnL | $676 | $795 | +$119 |

PB-MGC-Short: low-vol trades were net losers (PF=0.43), so gating actually increases PnL. Zero trades in high-vol regime.

**Decision:** Gate both strategies. Skip low-vol days (ATR < 33rd percentile).

---

## 2026-03-08 — Phase 5.2: Portfolio Overlap Realism

**Experiment:** Deep dive into 2-strategy portfolio (PB-MGC-Short + ORB-009 MGC-Long) — return correlation, trade overlap, drawdown overlap, rolling 30-day metrics.

**Results:**
- Daily PnL correlation: 0.004 (zero)
- Trade date overlap: 1.5% (2 out of 130 days)
- Drawdown overlap: 61.9% (structural — same asset)
- Rolling 30d correlation: median 0.001, range [-0.11, 0.32]
- Rolling 30d DD overlap: mean 59.7%
- Profitable months: 15/23 (65%)

**Decision:** Overlap is structural (both trade MGC). Acceptable for initial deployment. Adding a non-gold strategy would reduce DD overlap.

---

## 2026-03-08 — Phase 5.3: Sizing Comparison

**Experiment:** Compare 4 sizing methods — equal weight, equal risk contribution, vol targeting (10% annual), quarter-Kelly.

**Results:**
| Method | Sharpe | Calmar | MaxDD |
|--------|--------|--------|-------|
| Equal Weight | 3.31 | 7.57 | $859 |
| ERC | 3.20 | 8.98 | $559 |
| Vol Target 10% | 3.31 | 7.57 | $2,182 |
| Quarter Kelly | 3.31 | 7.72 | $39,868 |

**Decision:** ERC for prop accounts (best Calmar, lowest MaxDD). Vol targeting for growth. Kelly impractical at 46-50 contracts on $50K.

---

## 2026-03-08 — Phase 5.4: Gated Portfolio Equity Simulation

**Experiment:** Full equity simulation with regime gate active on both strategies. Compare ungated vs gated.

**Results:**
| Metric | Ungated | Gated |
|--------|---------|-------|
| PnL | $3,355 | $3,389 |
| Sharpe | 3.31 | 4.20 |
| MaxDD | $859 | $703 |
| Trades | 134 | 96 |
| Portfolio DSR | — | 1.000 SIG |
| Bootstrap PF CI | — | [1.25, 3.61] |

**Decision:** Regime-gated portfolio is the final Phase 5 output. Both strategies pass DSR individually. Portfolio DSR = 1.000 SIGNIFICANT. Proceed to paper trade validation.

---

## 2026-03-08 — Phase 6.1: Prop Controller Implementation

**Experiment:** Replace prop controller stub with full trade-by-trade simulation. Enforce trailing drawdown, daily loss limits, contract caps, profit lock, and phase transitions.

**Result:** Controller implemented with simulate() method. Handles EOD trailing DD, per-phase rules, and profit locking. Tested with Lucid 100K config — correctly identifies P1→P2 transition at $3,100 profit.

---

## 2026-03-08 — Phase 6.2: Monte Carlo Risk Gate

**Experiment:** Reshuffle 96 gated portfolio trades 10,000 times. Measure MaxDD distribution and prop account survival.

**Results:**
| Metric | Value |
|--------|-------|
| Median MaxDD | $516 |
| 95th pct MaxDD | $840 |
| 99th pct MaxDD | $1,034 |
| P(ruin at $2K DD) | 0.0% |
| P(ruin at $4K DD) | 0.0% |
| Prop survival | 100% (all configs) |

**Decision:** PASS. Portfolio survives all 10,000 orderings under every prop DD limit tested. Not path-dependent.

---

## 2026-03-08 — Phase 6.3: Paper Trade Simulation

**Experiment:** Run gated portfolio through Lucid 100K and Generic $50K prop controllers. Track skipped trades, halted days, phase transitions.

**Results:**
| Config | Result | Skipped | Halted Days | Lock |
|--------|--------|---------|-------------|------|
| Lucid 100K | PASSED | 0 | 0 | YES ($3,122) |
| Generic $50K | PASSED | 0 | 0 | N/A |

Monthly pass rate: 13/19 (68%). No prop guardrails triggered.

**Decision:** Portfolio is deployment-ready. Proceed to live paper trading.

---

## 2026-03-08 — Phase 6.4: Execution Architecture

**Deliverable:** Design document for live trading infrastructure — signal pipeline, order routing, failure handling, kill switch, logging, monitoring.

**Recommendation:** Tradovate REST API for initial deployment. 5-minute bar latency budget. 12-step deployment checklist.

---

## 2026-03-08 — Phase 7.0: Paper Trading Plan

**Deliverable:** Full paper trading plan with portfolio config, expected behavior, pass/fail conditions, invalidation criteria, weekly review checklist, and transition criteria.

**Key parameters:** 2-4 week duration, regime-gated PB-MGC-Short + ORB-009 MGC-Long, equal weight 1 contract, $0.62/side + 1 tick slippage.

---

## 2026-03-08 — Phase 7.1: Diversification Search

**Experiment:** Identify non-gold (MES/MNQ) strategies to reduce MGC concentration risk. Evaluated triage queue candidates and existing cross-asset data.

**Top candidates identified:** RVWAP Mean Reversion (AF=5), HYE Mean Reversion VWAP (AF=5), Open Drive (AF=4).

**Existing data:** ORB-009 MNQ-Long gross PF=1.237 (net PF=1.201 after costs — marginal).

---

## 2026-03-08 — Phase 7.2: RVWAP Mean Reversion Conversion

**Experiment:** Faithful conversion of RVWAP Mean Reversion (vvedding) from Pine Script to Python. Session-anchored VWAP with rolling stdev bands. Long on lower band crossover, short on upper band crossover. Exit at VWAP center cross.

**Results:**
| Asset | Mode | Trades | PF | Sharpe | PnL |
|-------|------|--------|-----|--------|-----|
| MES | Both | 1,004 | 0.83 | -1.83 | -$5,373 |
| MGC | Both | 405 | 1.01 | 0.04 | $117 |
| MNQ | Both | 904 | 0.87 | -1.21 | -$7,263 |

**Decision:** REJECTED. No edge on any asset/mode. VWAP mean reversion via stdev bands does not produce an edge on 5m futures data with fill-at-next-open engine.

---

## 2026-03-08 — Phase 7.3: Gap Momentum Conversion (ORB-018)

**Experiment:** Faithful conversion of Perry Kaufman's Gap Momentum System from TASC 2024.01. Cumulative gap series (today's open - yesterday's close) with 20-day SMA signal line. Long when gap momentum crosses above signal. Exit on reversal, stop, or EOD.

**Results:**
| Asset | Mode | Trades | PF | Sharpe | PnL | MaxDD |
|-------|------|--------|-----|--------|-----|-------|
| MES | Long | 27 | 0.24 | -9.87 | -$984 | $1,160 |
| MGC | Long | 24 | 3.41 | 3.67 | $2,718 | $518 |
| MNQ | Long | 28 | 0.48 | -4.71 | -$1,412 | $1,905 |

**Cost analysis (MGC):** Net PF=3.26, friction 2.9% ($78). Correlation with existing portfolio: r=-0.01 (zero).

**WARNING:** Best trade = $2,332 (86% of total PnL). Only 24 trades.

**Decision:** FAILS diversification goal (no MES/MNQ edge). MGC result is interesting but doesn't reduce gold concentration. Potential as 3rd gold strategy pending robustness validation.

---

## 2026-03-08 — Phase 7.4: Evolution Engine Design

**Deliverable:** Strategy evolution engine architecture specification. Covers component registry, combiner, evaluator, promotion pipeline, portfolio optimizer, and automation roadmap in three phases (semi-automated → fully automated → adaptive).

**Status:** Design only. No code until Phase 7 paper trading completes.

---

## 2026-03-08 — Phase 7.5: Execution Infrastructure Skeleton

**Deliverable:** Execution adapter skeleton (`execution/tradovate_adapter.py`) and signal logger (`execution/signal_logger.py`).

**Adapter:** Connects signal engine → regime gate → prop controller → Tradovate API. Currently all methods are no-ops that log intent. Covers: authentication, market/bracket orders, position management, kill switch, daily reconciliation, heartbeat.

**Logger:** Produces daily JSON logs matching PHASE_7_PAPER_TRADING_PLAN.md format. Records: regime state, signals, trades, controller state, operational notes. Summary statistics across all logged days.

**Status:** Skeleton mode — logs everything, executes nothing. Will be activated after paper trading validation.

---

## 2026-03-09 — Phase 7.6: ORB-018 Portfolio Assessment

**Experiment:** Full portfolio assessment of Gap Momentum MGC-Long as potential 3rd gold strategy.

**Results:**
| Metric | Value | Threshold | Pass? |
|--------|-------|-----------|-------|
| Correlation vs ORB-009 | -0.011 | < 0.3 | YES |
| Correlation vs PB-Short | -0.010 | < 0.3 | YES |
| DD overlap vs PB-Short | 82.5% | < 60% | NO |
| DD overlap vs ORB-009 | 69.3% | < 60% | NO |
| Top-trade removal PF | 1.34 | > 1.0 | YES (barely) |

3-strategy portfolio: Calmar improves (5.58→7.45) but MaxDD increases ($679→$874) and Sharpe drops (3.75→3.07).

**Decision:** Not ready for portfolio inclusion. 86% PnL from one trade, fails DD overlap, top-trade removal barely passes. Keep as watch candidate.

---

## 2026-03-09 — Phase 7.7: Targeted MES/MNQ Harvest (Batch 2)

**Experiment:** Targeted harvest of 15 index-specific strategy candidates. Focused on families proven to work on index futures: session trend following, volatility compression breakout, trend following, range expansion momentum.

**Results:** 15 candidates harvested across 4 families:
- Session trend following: 4 (VIX Channel, EMA+RSI+ADX, EMA+Sessions, 8-55 EMA NQ)
- Volatility compression breakout: 5 (ORION, Vol Expansion, BB/KC Squeeze, Vol Compress, BB+ST+KC)
- Trend following: 4 (MTF EMA ALMA, SuperTrend+EMA, ES/NQ Scripts, Momentum)
- Range expansion: 2 (Larry Williams Vol Breakout, FVBO Squeeze)

**Top 3 for conversion:**
1. NY VIX Channel Trend (idx-001) — only strategy in pipeline using VIX/implied volatility
2. ORION Hybrid Volatility Breakout (idx-005) — best compression→expansion framework
3. BB/KC Squeeze Strategy (idx-007) — classic squeeze, simplest to convert

**Decision:** Proceed with conversion of top 3. This resolves the "new harvest needed" blocker.

---

*Last updated: 2026-03-09*
