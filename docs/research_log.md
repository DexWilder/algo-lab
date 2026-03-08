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

*Last updated: 2026-03-07*
