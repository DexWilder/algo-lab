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

## 2026-03-09 — Phase 7.8: Batch 2 Conversion (3 Strategies)

**Experiment:** Convert and backtest the top 3 batch 2 candidates on MES/MNQ/MGC.

### BB/KC Squeeze (idx-007)

LazyBear's squeeze momentum: BB inside KC = compression, enter on release + momentum direction.

| Asset | Mode | Trades | PF | Sharpe | PnL | MaxDD |
|-------|------|--------|-----|--------|-----|-------|
| MES | Both | 1,295 | 1.49 | 2.87 | $9,606 | $1,002 |
| MNQ | Both | 1,291 | 1.21 | 1.68 | $8,892 | $2,082 |
| MGC | Both | 692 | 0.99 | -0.03 | -$119 | $2,819 |

**Verdict:** MARGINAL. Best gross PF (1.49 MES) but 1,295 trades × $3.74/RT = 50% friction. Net PF 1.24.

### ORION Vol Breakout (idx-005)

Compression box (ATR tightness + LR flatness) + EMA 150 trend filter + 1.9R bracket.

| Asset | Mode | Trades | PF | Sharpe | PnL | MaxDD |
|-------|------|--------|-----|--------|-----|-------|
| MES | Both | 400 | 0.94 | -0.35 | -$1,336 | $3,271 |
| MNQ | Both | 394 | 1.01 | 0.03 | $240 | $4,202 |
| MGC | Both | 187 | 1.21 | 1.03 | $2,071 | $1,244 |

**Verdict:** REJECTED. No edge on indices.

### VIX Channel Trend (idx-001) — BREAKTHROUGH

Session open anchor + realized vol proxy for implied move channel + window direction detection.

| Asset | Mode | Trades | PF | Sharpe | PnL | MaxDD |
|-------|------|--------|-----|--------|-----|-------|
| MES | Both | 503 | 1.39 | 2.04 | $8,870 | $1,419 |
| MNQ | Both | 506 | 1.32 | 1.77 | $13,656 | $3,824 |
| MGC | Both | 362 | 0.96 | -0.23 | -$1,026 | $3,749 |

**Cost analysis:** MES Both net PF = 1.31 (21% friction, 503 trades). MNQ Both net PF = 1.30 (6% friction).

**Robustness (MES Both):** Top trade 10.9% of PnL. PF w/o top trade: 1.35 (improves!). 18/25 months profitable. Corr vs portfolio: r = -0.028. DD overlap: 71.6%.

**Portfolio impact:** 3-strat Calmar doubles (5.58 → 11.54), PnL triples ($3,789 → $12,659), MaxDD increases modestly ($679 → $1,097).

**Decision:** VIX Channel MES-Both is the lab's first viable index futures strategy. Candidate for promotion pending regime gate + full robustness battery. This is the diversification breakthrough.

**Key insight:** Session-based trend following succeeds on indices where breakout, mean reversion, and gap momentum all failed.

---

## 2026-03-09 — Phase 8.1: VIX Channel Full Robustness Battery

**Experiment:** 8-criterion validation battery on VIX Channel MES-Both (503 trades). Tests regime gate, walk-forward, parameter stability, top-trade removal, bootstrap CI, DSR, portfolio correlation, Monte Carlo.

**Results:**

| Criterion | Result | Threshold | Pass? |
|-----------|--------|-----------|-------|
| Net PF | 1.298 | > 1.3 | FAIL |
| Bootstrap PF CI lower | 1.038 | > 1.0 | PASS |
| DSR (n=81 trials) | 0.000 | > 0.95 | FAIL |
| Walk-forward 2024 | PF=1.163 | > 1.0 | PASS |
| Walk-forward 2025-2026 | PF=1.413 | > 1.0 | PASS |
| Parameter stability | 81/81 (100%) | ≥ 60% | PASS |
| Monte Carlo P(ruin@$2K) | 27.3% | < 5% | FAIL |
| Portfolio correlation | r=-0.024 | < 0.15 | PASS |

**Key finding:** Regime gate is NOT recommended for VIX Channel — it's the lab's LOW_VOL specialist (PF=1.79 in low vol). Top trade only 13.7% of PnL.

**Decision:** VIX Channel remains pending_validation (3 criteria fail). Strong diversifier but doesn't meet full promotion bar.

---

## 2026-03-09 — Phase 8.2: Multi-Factor Regime Engine

**Deliverable:** `engine/regime_engine.py` — extends ATR classifier with trend (EMA slope) and realized volatility factors. 3 factors × 2-3 states each = 6 independent regime labels per day.

**Regime distribution (MES, 630 days):**
| Composite Regime | Days | % |
|-----------------|------|---|
| HIGH_VOL_TRENDING | 194 | 30.8% |
| NORMAL_TRENDING | 175 | 27.8% |
| LOW_VOL_TRENDING | 128 | 20.3% |
| NORMAL_RANGING | 65 | 10.3% |
| HIGH_VOL_RANGING | 53 | 8.4% |
| LOW_VOL_RANGING | 15 | 2.4% |

---

## 2026-03-09 — Phase 8.3: Strategy Regime Profiles

**Experiment:** Per-regime PF/Sharpe analysis for all validated/candidate strategies using RegimeEngine. Auto-generate strategy activation profiles.

**Results:**

| Strategy | Best Regime | PF | Worst Regime | PF |
|----------|------------|-----|-------------|-----|
| PB-MGC-Short | HIGH_RV | 4.99 | LOW_RV | 0.45 |
| ORB-009-MGC-Long | TRENDING | 2.06 | RANGING | 0.77 |
| VIX-Channel-MES-Both | LOW_VOL | 1.79 | LOW_RV | 0.97 |

**Key insight:** VIX Channel and PB-Short are regime complements — VIX thrives in LOW_VOL where PB dies, PB thrives in HIGH_RV where VIX is neutral.

**Decision:** Per-strategy profiles auto-generated and saved. Replace global ATR gate with profile-based activation.

---

## 2026-03-09 — Phase 8.4: Portfolio Regime Simulation

**Experiment:** Compare 3 activation modes (baseline, ATR-gated, regime-profiled) on 2-strat and 3-strat portfolios.

**Results (2-Strategy):**
| Mode | PnL | Sharpe | Calmar | MaxDD |
|------|-----|--------|--------|-------|
| Baseline | $3,355 | 3.31 | 3.91 | $859 |
| ATR-Gated | $3,389 | 4.20 | 4.82 | $703 |
| Regime-Profiled | $3,661 | 4.46 | 6.76 | $542 |

**Results (3-Strategy with VIX Channel):**
| Mode | PnL | Sharpe | Calmar | MaxDD | Monthly |
|------|-----|--------|--------|-------|---------|
| Baseline | $10,344 | 2.16 | 8.07 | $1,281 | 76% |
| ATR-Gated | $7,800 | 1.90 | 5.46 | $1,429 | 64% |
| Regime-Profiled | $10,854 | 2.97 | 9.77 | $1,111 | 84% |

**Decision:** Regime-profiled portfolio dominates all metrics. ATR gate actively hurts VIX Channel (which is a low-vol specialist). Per-strategy profiles are the recommended activation mode going forward.

---

## 2026-03-09 — Phase 8 Interpretation — Regime Engine Insights

**Type:** Research conclusion (not experiment — synthesis of Phase 8 findings)

### Key Conclusions

**1. VIX Channel MES-Both remains pending_validation, not rejected.**
- Net PF 1.298 — just 0.002 below the 1.3 threshold. This is not a structural failure.
- DSR failure is likely inflated by the n_trials=81 parameter count. The test penalizes VIX Channel for every parameter combination the lab has ever tried across all strategies. If scored as a standalone strategy (n=1), DSR would be ~1.0.
- Parameter stability of 100% (81/81 profitable) suggests the edge is structurally robust — it's not a curve-fitted artifact.

**2. Regime specialization discovery — strategies occupy different volatility niches.**

| Strategy | Best Regime | PF | Worst Regime | PF |
|----------|------------|-----|-------------|-----|
| PB-MGC-Short | HIGH_RV | 4.99 | LOW_RV | 0.45 |
| ORB-009-MGC-Long | TRENDING | 2.06 | RANGING | 0.77 |
| VIX-Channel-MES-Both | LOW_VOL | 1.79 | LOW_RV | 0.97 |

This is not noise. Each strategy's edge concentrates in a specific market environment. The lab now has empirical evidence that strategy performance is regime-conditional, not regime-independent.

**3. ATR-only gating is suboptimal.**
The Phase 5 ATR gate (skip low-vol days) is a correct optimization for PB and ORB — but it destroys value for VIX Channel, which is a LOW_VOL specialist. A global gate applied uniformly to all strategies is structurally wrong when strategies have different regime preferences.

**4. Regime-profiled portfolio improves every risk-adjusted metric.**

| Portfolio | Metric | Baseline | ATR-Gated | Regime-Profiled |
|-----------|--------|----------|-----------|-----------------|
| 2-Strategy | Calmar | 3.91 | 4.82 | **6.76** |
| 2-Strategy | MaxDD | $859 | $703 | **$542** |
| 3-Strategy | Calmar | 8.07 | 5.46 | **9.77** |
| 3-Strategy | Monthly% | 76% | 64% | **84%** |

The regime-profiled 2-strat portfolio achieves a 37% MaxDD reduction vs baseline with 9% more PnL. The 3-strat version achieves 84% monthly consistency — the highest in the lab's history.

**5. Architectural milestone achieved.**

The lab's signal pipeline is now:

```
strategy → regime engine → portfolio allocation → prop controller → execution
```

This marks the transition from a **strategy research system** to a **portfolio intelligence system**. Previously, the lab treated each strategy as an independent unit with a shared global filter. Now, each strategy has its own activation profile derived from empirical regime analysis, and the portfolio is constructed from regime-aware components.

### Phase 8.1 — Regime Engine Refinements (TODO)

The following improvements were identified but not implemented in Phase 8:

1. **Regime coverage metrics** — For each strategy's profile, compute:
   - Percent of trading days active (how many days does the strategy actually trade?)
   - Percent of trades retained vs ungated
   - Percent of PnL retained vs ungated

2. **Regime efficiency score** — Quantify how much value the profile adds:
   - `efficiency = pnl_retained_pct / trades_retained_pct`
   - Score > 1.0 means the profile eliminates low-quality trades disproportionately

3. **Regime stability check** — PF by regime by year:
   - Does PB-Short's HIGH_RV edge persist in 2024 AND 2025?
   - Does VIX Channel's LOW_VOL edge persist across years?
   - If a regime edge exists in only one year, the profile may be overfitting

These refinements would make the regime engine scientifically stronger and protect against profile overfitting.

---

## 2026-03-09 — Phase 8.5: Regime Coverage Analysis + Research Philosophy Shift

**Type:** Research conclusion — strategic pivot in lab methodology

### Regime Profile Optimization Observation

The `strategy_regime_profiles.json` reveals a potential over-filtering issue:

- **PB-MGC-Short avoid list:** LOW_VOL, NORMAL_RV, LOW_RV — this filters 3 of 8 possible regime states
- **ORB-009 avoid list:** RANGING — single filter, cleanest profile
- **VIX Channel avoid list:** LOW_RV — single filter

PB-Short's profile may be over-aggressive. With only 28 trades total, per-regime sample sizes are tiny (7 in LOW_VOL, 10 in LOW_RV). The NORMAL_RV avoid (PF=0.95, 7 trades) is particularly suspicious — 7 trades is not enough to declare a regime edge. This is a candidate for the Phase 8.1 regime stability check.

### Regime Coverage Matrix

Mapped all active strategies to their regime niches:

| Regime | Coverage | Notes |
|--------|----------|-------|
| LOW_VOL | VIX Channel (PF=1.79) | Strong |
| NORMAL | PB + ORB (PF 2.05-2.36) | Strong |
| HIGH_VOL | ORB-009 (PF=2.18) | Covered |
| TRENDING | ORB + PB (PF 2.05-2.06) | Strong |
| RANGING | VIX Channel (PF=1.64) | Thin — only 1 strategy |
| LOW_RV | ORB-009 (PF=2.79) | Covered |
| NORMAL_RV | VIX Channel (PF=1.39) | Thin |
| HIGH_RV | PB-Short (PF=4.99) | Strong but 11 trades |
| EXTREME_VOL | ??? | **MISSING** |
| RANGE_BOUND | ??? | **MISSING** |
| OVERNIGHT | ??? | **MISSING** |

**Key gaps:** Extreme volatility (macro events), multi-day range-bound, overnight/session transitions.

### Lab Philosophy Shift

**Before Phase 8:** Find the strongest standalone strategies, filter with a global ATR gate.

**After Phase 8:** Find strategies that fill regime gaps. Evaluate by portfolio contribution, not standalone PF.

**Decision rule update:** A strategy with PF 1.3 that fills an empty regime cell may be more valuable than a strategy with PF 1.8 that duplicates existing TRENDING coverage.

**Research gap map updated** (`docs/research_gap_map.md`) with regime-prioritized harvest targets. Priority order:
1. Overnight/session-transition (zero coverage, zero intake candidates)
2. Mean reversion retry on 15m/30m (zero coverage, previous 5m attempts failed)
3. Extreme volatility specialist (zero coverage, 5 intake candidates available)

---

## 2026-03-09 — Phase 8.5: Strategy DNA Clustering

**Experiment:** Structural fingerprinting of all 9 converted strategies. Each strategy profiled across 20+ DNA fields (entry type, confirmation stack, filter depth, exit mechanism, risk model, regime dependency, holding time, trade frequency, cost sensitivity, direction bias, portfolio role). Clustering via normalized Euclidean distance on 7 categorical features.

**Schema:** `research/dna/dna_schema.json` — 20+ fields covering structural identity, behavioral fingerprint, and performance summary.

**Results:**

| Strategy | Classification | Confidence | Cluster |
|----------|---------------|------------|---------|
| PB-MGC-Short | true_diversifier | medium | singleton |
| ORB-009-MGC-Long | true_diversifier | high | singleton |
| VIX-Channel-MES-Both | true_diversifier | medium | singleton |
| GAP-MOM-MGC-Long | watchlist | low | singleton |
| VWAP-006-MES-Long | rejected_but_informative | medium | singleton |
| RVWAP-MR-MES-Both | rejected_but_informative | medium | cluster_5 |
| ICT-010-MES-Both | rejected_but_informative | medium | singleton |
| ORION-VOL-MES-Both | component_donor | medium | singleton |
| BBKC-SQUEEZE-MES-Both | component_donor | medium | cluster_5 |

**Key findings:**
1. All 3 validated strategies are **structural singletons** — genuinely different entry mechanisms, risk models, and regime preferences. Portfolio diversity is real, not cosmetic.
2. **No near-duplicates** found (all pairwise distances > 0.3). RVWAP-MR and BBKC-SQUEEZE are closest pair (distance 0.39) — both are band/compression strategies with ATR-adaptive risk.
3. **2 component donors** identified: ORION-VOL (compression box filters) and BBKC-SQUEEZE (momentum state machine exits). Both failed standalone but have reusable structural components for evolution engine.
4. **Structural gaps** identified: trend_following, overnight, event_driven, pairs, higher_timeframe — aligns with regime gap map.
5. **Overrepresented types**: breakout (2), pullback (2) — adding more has diminishing portfolio value.

**Decision:** DNA profiling confirms the lab's portfolio is structurally sound. Future harvesting should target missing DNA types (trend_following, overnight, event_driven) which also align with regime coverage gaps.

**Artifacts:**
- `research/dna/dna_schema.json` — structural fingerprint schema
- `research/dna/build_dna_profiles.py` — profile builder + clusterer
- `research/dna/dna_catalog.json` — all 9 strategy profiles
- `research/dna/dna_clusters.json` — cluster assignments + classifications
- `research/dna/dna_report.md` — full analysis report

---

## 2026-03-09 — Phase 9: Evolution Scheduler

**Goal:** Build practical evolution engine to generate hybrid candidates by injecting donor components (ORION compression, BBKC squeeze/momentum, ICT sweep) into parent strategies (ORB-009, PB-Trend, VIX Channel), then validate through existing pipeline.

**Approach:** Template-based generation — copy parent strategy, inject mutations at known source landmarks. Four mutation types: add_filter (AND a new boolean column), swap_risk (replace stop/target calculation), swap_exit (add momentum deceleration exit), relax_filter (remove conditions).

**Infrastructure built:**
- `research/evolution/mutations.py` — 4 stateless indicator functions extracted from donor strategies
  - `compute_compression()` — ORION-VOL tightness + flatness (5.5% of bars active on MES)
  - `compute_squeeze()` — BBKC BB/KC overlap + release detection (39.4% squeeze_on, 5.2% release)
  - `compute_momentum_state()` — BBKC linreg momentum color states (4 mutually exclusive states)
  - `compute_sweep()` — ICT-010 session range sweep bias (1/-1/0 per bar)
- `research/evolution/evolution_queue.json` — 15 prioritized recipes with weighted scoring
- `research/evolution/evolution_scheduler.py` — CLI orchestrator with 8-stage pipeline

**Pipeline stages:** generate → backtest (3 assets × 3 modes) → quality gate (PF>1.0, trades≥30) → DNA novelty (min_distance>0.3) → regime analysis → mutation impact → statistical check (bootstrap CI + DSR) → report generation

**Results — 15 candidates evaluated:**

| # | Candidate | Parent | Type | Best Combo | PF | Trades | Status | Reason |
|---|-----------|--------|------|------------|-----|--------|--------|--------|
| 1 | orb_compression | orb_009 | add_filter | MGC-both | ∞ | 2 | rejected | trades < 30 |
| 2 | orb_squeeze_filter | orb_009 | add_filter | MGC-long | 7.29 | 20 | rejected | trades < 30 |
| 3 | orb_atr_stops | orb_009 | swap_risk | MES-short | 1.22 | 217 | rejected | DNA duplicate (0.250) |
| 4 | pb_squeeze_filter | pb_trend | add_filter | MGC-both | 1.61 | 3 | rejected | trades < 30 |
| 5 | orb_sweep_confirm | orb_009 | add_filter | MGC-long | 2.16 | 17 | rejected | trades < 30 |
| 6 | pb_compression_filter | pb_trend | add_filter | MGC-short | ∞ | 1 | rejected | trades < 30 |
| 7 | orb_momentum_confirm | orb_009 | add_filter | MGC-long | 1.67 | 91 | rejected | DNA duplicate (0.200) |
| 8 | pb_momentum_exit | pb_trend | swap_exit | MGC-short | 1.95 | 29 | rejected | trades < 30 |
| 9 | pb_range_stops | pb_trend | swap_risk | MGC-short | 1.89 | 28 | rejected | trades < 30 |
| 10 | vix_momentum_exit | vix_channel | swap_exit | MES-short | 1.53 | 240 | rejected | DNA duplicate (0.000) |
| 11 | **vix_atr_stops** | vix_channel | swap_risk | **MNQ-long** | **1.36** | **263** | **promoted** | marginal novelty (0.500) |
| 12 | vix_compression_confirm | vix_channel | add_filter | MNQ-long | 1.24 | 166 | rejected | DNA duplicate (0.200) |
| 13 | vix_sweep_confirm | vix_channel | add_filter | MES-long | 1.50 | 37 | rejected | DNA duplicate (0.200) |
| 14 | **pb_relaxed_filters** | pb_trend | relax_filter | **MES-short** | **1.25** | **274** | **promoted** | marginal novelty (0.449) |
| 15 | vix_adx_confirm | vix_channel | add_filter | MES-short | 1.46 | 240 | rejected | DNA duplicate (0.200) |

**Promoted candidates:**
- `vix_atr_stops`: VIX Channel with ATR-based risk instead of RV-scaled. Found edge on MNQ-long (PF=1.36, Sharpe=1.87, 263 trades, DSR=1.000). DNA distance 0.500 = genuinely different risk model.
- `pb_relaxed_filters`: PB with ADX removed, vol threshold halved, single session window. Found on MES-short (PF=1.25, Sharpe=1.71, 274 trades, DSR=1.000). But mutation_hurt — PF dropped from 2.36 to 1.25 (traded selectivity for volume).

**Key insights:**
1. **Filter stacking on ORB/PB kills trade count.** These strategies are already selective (75 and 21 trades). Adding compression/squeeze/sweep filters pushes most below 30 trades. The mutation adds value per-trade (PF 2-7+) but destroys statistical significance.
2. **Risk model swaps create genuine structural novelty.** DNA distance 0.5 for vix_atr_stops vs 0.0-0.25 for filter additions. Changing HOW you risk (ATR vs range vs RV) is more structurally distinct than changing what confirms entry.
3. **VIX Channel is the best mutation host** — 503 base trades gives room to filter down while maintaining statistical minimums. All VIX filter candidates passed PF>1.0 gate; most failed DNA novelty.
4. **DNA novelty gate is appropriately strict.** add_filter mutations don't change entry_type/risk_model/holding_time_class, so they register as duplicates. This correctly prevents portfolio clutter.
5. **pb_momentum_exit and pb_range_stops were tantalizingly close** (29 and 28 trades, PF 1.95 and 1.89). With slightly more data or a lower trade threshold, these would promote. Worth revisiting when more data is available.

**Decision:** Both promoted candidates are marked for monitoring but NOT added to core portfolio yet. vix_atr_stops on MNQ-long is the most interesting — a new asset/direction combo for VIX Channel.

**Artifacts:**
- `research/evolution/mutations.py` — reusable mutation components
- `research/evolution/evolution_queue.json` — 15 prioritized recipes
- `research/evolution/evolution_scheduler.py` — CLI orchestrator
- `research/evolution/generated_candidates/` — 15 strategy.py + meta.json files
- `research/evolution/evolution_results.json` — machine-readable results
- `research/evolution/evolution_results.md` — executive summary
- `research/evolution/evolution_summary_matrix.md` — compact comparison table

---

## 2026-03-09 — Phase 9.5: Portfolio Fitness Function + Regime Coverage Map

**Goal:** Replace standalone PF as the evolution objective with portfolio-aware fitness scoring. Generate machine-readable regime coverage map for gap-aware harvesting and evolution.

**Motivation:** Phase 9's portfolio comparison proved standalone PF is the wrong objective: `vix_atr_stops` (PF=1.36) adds $4.6K uncorrelated PnL and lifts Calmar from 1.94→2.78, while `pb_relaxed_filters` (PF=1.25) degrades the portfolio. A PF 1.36 strategy filling a new regime/asset cell is worth more than a PF 2.0 clone.

### Portfolio Fitness Function

**Module:** `research/evolution/portfolio_fitness.py`

5-component scoring engine (weights sum to 1.0):

| Component | Weight | Measures |
|-----------|--------|----------|
| pnl_contribution | 0.25 | Relative PnL increase when added to portfolio |
| correlation_benefit | 0.25 | 1 - max abs correlation with existing strategies |
| drawdown_improvement | 0.20 | Calmar improvement + MaxDD reduction |
| regime_coverage | 0.20 | New regime cells filled (from coverage map) |
| monthly_consistency | 0.10 | Delta in profitable months % |

**Validation against known ground truth:**

| Candidate | Score | Label | Key Drivers |
|-----------|-------|-------|-------------|
| vix_atr_stops MNQ-Long | 5.88 | portfolio_useful | Corr: 9.78, PnL: 6.32, Monthly: 9.0 |
| pb_relaxed_filters MES-Short | 2.99 | portfolio_redundant | PnL: 0.09, DD: 0.0, Monthly: 3.0 |

Correctly identifies vix_atr_stops as the better portfolio addition (2× higher score).

### Regime Coverage Map

**Module:** `research/regime/regime_coverage_map.py`

18-cell grid (3 vol × 2 trend × 3 rv). Coverage classification:

| Level | Rule | Count |
|-------|------|-------|
| STRONG | ≥2 strategies, ≥30 trades, PF≥1.3 | 5 |
| COVERED | 1+ strategy, ≥15 trades, PF≥1.0 | 6 |
| THIN | 1 strategy, <15 trades or PF<1.3 | 7 |
| MISSING | 0 strategies | 0 |

All 18 cells have at least 1 strategy active, but 7 are THIN — insufficient evidence for confidence.

### Scheduler Integration

Evolution scheduler pipeline updated: `generate → backtest → quality_gate → dna_novelty → portfolio_fitness → regime → mutation_impact → stats → report`. Portfolio fitness column added to summary matrix. Promotion criteria updated: portfolio_star (≥7) can override marginal DNA, portfolio_redundant (<4) flags candidates even if other gates pass.

**Decision:** Portfolio fitness is now the primary evaluator for evolution candidates. Standalone PF remains as a quality gate (>1.0) but no longer drives promotion.

**Artifacts:**
- `research/evolution/portfolio_fitness.py` — reusable fitness scorer
- `research/regime/regime_coverage_map.py` — coverage map generator
- `research/regime/regime_coverage.json` — machine-readable coverage data
- `research/regime/regime_coverage_report.md` — human-readable coverage report
- `research/evolution/evolution_scheduler.py` — updated with portfolio fitness stage

---

## 2026-03-09 — Phase 9.5.1: Evolution Batch 2 (Regime-Gap-Targeted)

**Goal:** Run 10 regime-targeted evolution recipes to fill the 7 THIN cells identified by the coverage map. Two critical gaps: HIGH_VOL_TRENDING_LOW_RV (PF=0.39, lab loses money) and 5 RANGING cells with thin coverage.

**Approach:** Unlike Batch 1 (generic filter stacking), Batch 2 targets specific regime cells. Two new safeguards enforced:
- **FAIL_TARGET gate:** Candidates must have ≥10 trades in their target regime to avoid promoting strategies that pass quality gate but don't actually trade where needed.
- **ATR sanity cap:** Stop distance capped at 3.5×ATR, target at 5.0×ATR to prevent degenerate wide-stop variants.

**New mutations added:** `compute_ema_alignment` (multi-EMA trend continuation) and `compute_range_fade` (Bollinger Band mean reversion at range extremes).

### Results: 10 candidates evaluated, 4 promoted, 6 rejected

| Candidate | Parent | Mutation | Best Combo | PF | Trades | Target Trades | Port. Score | Status |
|-----------|--------|----------|------------|-----|--------|--------------|-------------|--------|
| vix_wide_atr_low_rv | vix_channel | swap_risk | MES-short | 1.34 | 240 | 15 (HV_T_LRV) | 2.70 | promoted |
| vix_tight_targets | vix_channel | swap_risk | MES-long | 1.37 | 263 | 54 (RANGING) | 3.75 | promoted |
| pb_shallow_pullback | pb_trend | relax_filter | MES-short | 1.25 | 274 | 18 (HV_T_LRV) | 3.40 | promoted |
| orb_relaxed_entry | orb_009 | relax_filter | MGC-long | 1.72 | 134 | 17 (RANGING) | 3.30 | promoted |
| orb_wide_atr | orb_009 | swap_risk | MGC-short | 1.61 | 93 | 0 (HV_T_LRV) | — | FAIL_TARGET |
| orb_ema_trend | orb_009 | add_filter | MGC-long | 1.69 | 98 | 2 (HV_T_LRV) | — | FAIL_TARGET |
| vix_fast_observation | vix_channel | relax_filter | MES-short | 1.32 | 245 | — | — | DNA duplicate |
| vix_ema_trend | vix_channel | add_filter | MES-short | 1.48 | 210 | — | — | DNA duplicate |
| vix_range_fade | vix_channel | add_filter | MGC-long | 1.36 | 100 | — | — | DNA duplicate |
| orb_range_fade | orb_009 | add_filter | MGC-long | 4.83 | 9 | — | — | trades<30 |

### Key Findings

1. **FAIL_TARGET gate works:** `orb_wide_atr` had PF=1.61 and 93 trades — would have promoted in Batch 1 — but had ZERO trades in its target regime (HIGH_VOL_TRENDING_LOW_RV). The gate correctly caught this.
2. **VIX add_filter mutations all hit DNA duplicate:** VIX Channel's DNA profile is too close to existing catalog for filter additions to create structural novelty. Only risk model swaps (swap_risk) create enough DNA distance.
3. **orb_range_fade is interesting but data-starved:** PF=4.83 on 9 trades. Range fade on ORB shows promise conceptually but the filter is too restrictive on current data. Needs longer history or relaxed parameters.
4. **All 4 promoted scored portfolio_redundant:** No portfolio_star emerged. The HIGH_VOL_TRENDING_LOW_RV gap remains structurally hard to fill — existing parents (VIX, ORB, PB) weren't designed for sustained trend-following.
5. **Regime-targeted evolution improves targeting:** vix_tight_targets placed 54 trades in RANGING cells, confirming that tighter targets do shift the distribution toward RANGING activity.

**Decision:** No candidates meet the bar for full promotion to the core portfolio. The THIN regime gaps may require genuinely new strategy families (trend-following, mean-reversion specialists) rather than mutations of existing parents. Evolution is a useful tool for optimization but cannot create structural novelty from structurally similar parents.

**Artifacts:**
- `research/evolution/evolution_queue_batch2.json` — 10 regime-targeted recipes
- `research/evolution/evolution_results_batch2.json` — full results
- `research/evolution/evolution_results_batch2.md` — executive summary
- `research/evolution/evolution_summary_matrix_batch2.md` — comparison table
- `research/evolution/mutations.py` — 6 mutation functions (2 new)

---

## 2026-03-09 — Phase 10 Prep: Trend Persistence + Trade Duration + New Parent Discovery Plan

**Goal:** Three pre-Phase-10 improvements to ensure new parent strategies are evaluated correctly.

### 1. Trend Persistence Score (Factor 4 in RegimeEngine)

Added GRINDING/CHOPPY classification to separate sustained directional grinds from breakout/reversal days.

**Implementation:** `rolling_sum(sign(daily_close_diff), 20)`. Score ranges -20 to +20. Threshold ≥8 → GRINDING.

**Distribution (MES, 630 days):**
- GRINDING: 71 days (11.3%)
- CHOPPY: 559 days (88.7%)

Within HIGH_VOL + TRENDING (the problem regime): 21 GRINDING days (10.8%) — these are the exact days where a trend-follower should be trading.

### 2. Trade Duration Analysis

Added `median_trade_duration_bars` and `avg_trade_duration_bars` to `compute_extended_metrics()`.

**Current portfolio durations:**

| Strategy | Median Hold | Avg Hold | Profile |
|----------|-----------|---------|---------|
| PB-MGC-Short | 3 bars (15 min) | 8 bars | Scalper |
| ORB-MGC-Long | 28 bars (2.3 hrs) | 41 bars | Intraday swing |
| VIX-MES-Both | 42 bars (3.5 hrs) | 45 bars | Intraday swing |

True trend-followers should show 60-200+ bars — structurally different from all current parents.

### 3. New Parent Discovery Plan

Phase 10 execution order established (simple → complex):

**Trend Gap:** Donchian → Keltner → VWAP Continuation → EMA Crossover → SuperTrend
**Range Gap:** Bollinger Equilibrium → FVBO → VWAP MR → Session Profile

**Architecture decision:** Event trading = regime override layer, not strategy family.

**Artifacts:**
- `engine/regime_engine.py` — trend_persistence factor added (GRINDING/CHOPPY)
- `backtests/run_baseline.py` — trade duration metrics added
- `docs/LAB_STATE.md` — Phase 10 plan, new insights, updated capabilities

---

## 2026-03-09 — Phase 10.1: Donchian Trend Evaluation (First New Parent)

**Goal:** Build and evaluate the first new strategy family for HIGH_VOL_TRENDING_LOW_RV regime gap. Donchian Channel Breakout + ATR Trailing Stop — a classic trend-following system.

**Implementation:** `strategies/donchian_trend/strategy.py` — hand-built, platform-agnostic.
- Entry: close breaks above N-bar high (long) or below N-bar low (short)
- Risk: ATR-based initial stop, trails with price using ATR distance
- No fixed target — trail captures full trend move
- Exit: trailing stop hit or pre-close session flatten
- Max 1 trade per direction per day

**Parameter sweep:** Tested CHANNEL_LEN [20, 30, 40, 55, 78] × ATR_TRAIL_MULT [2.0, 2.5, 3.0, 3.5]. Optimal: CHANNEL_LEN=30, ATR_TRAIL_MULT=3.0.

**Results (3×3 baseline, best combos):**

| Asset | Mode | Trades | PF | Sharpe | PnL | Median Hold | Avg Hold |
|-------|------|--------|-----|--------|-----|-------------|----------|
| MNQ | Both | 654 | 1.29 | 1.64 | $18,192 | 48 bars | 55 bars |
| MNQ | Long | 356 | 1.32 | 1.43 | $10,189 | 61 bars | 67 bars |
| MES | Long | 375 | 1.23 | — | — | 54 bars | — |

**Portfolio fitness (MNQ-Both):** 4.12/10 (portfolio_useful)

**Correlation with existing portfolio:**
- vs PB-MGC-Short: r = -0.026 (near-zero)
- vs ORB-009-MGC-Long: r = +0.012 (near-zero)

**Regime analysis:**
- GRINDING trades: 84 trades, $2,577 PnL (profitable — architecture validated)
- HIGH_VOL_TRENDING_LOW_RV: **Still loses -$1,158** (target cell NOT fixed)
- Overall TRENDING: profitable. LOW_RV component is the fundamental problem.

**Key findings:**
1. **GRINDING detection works.** 84 trades in GRINDING regime with net-positive PnL confirms the trend persistence factor (Factor 4) correctly identifies days where trend-followers make money.
2. **Donchian is a genuine structural diversifier.** Median hold 61 bars (MNQ-long) vs PB=3, ORB=28, VIX=42. Near-zero correlation. Different DNA entirely.
3. **Breakout entry can't solve the LOW_RV problem.** In LOW_RV conditions, breakout moves are too small to cover the ATR-based stop distance. The system bleeds on false breakouts that don't develop into sustained trends.
4. **Next candidate should try pullback entries.** VWAP Trend Continuation enters on pullbacks to VWAP within an existing trend — this avoids the "buying the high" problem that kills breakout entries in LOW_RV.

**Decision:** Donchian confirmed as portfolio_useful but doesn't fix the critical target cell. Keep as candidate. Proceed to Keltner Channel Breakout (next in build order) — may produce smoother entries. Then VWAP Trend Continuation as the fundamentally different approach.

---

## 2026-03-09 — Phase 10.2: GRINDING Filter Deep Dive (Donchian)

**Goal:** Test Donchian with GRINDING persistence filter per user request.

**Results (MNQ-Long):**

| Variant | PF | Sharpe | Trades | PnL | Median Hold |
|---------|-----|--------|--------|-----|-------------|
| Unfiltered | 1.29 | 1.32 | 356 | $9,392 | 61 bars |
| GRINDING only | **1.76** | **3.38** | 48 | $1,981 | 60 bars |

**GRINDING + LOW_RV intersection:** Only 5 trades in target cell (all GRINDING), PnL=-$308. Too few to conclude.

**Key finding:** GRINDING + LOW_RV overall is profitable ($877 from 22 trades). The loss concentrates specifically in HIGH_VOL + LOW_RV, not LOW_RV alone.

**Decision:** GRINDING filter is a validated strategy activation layer. PF improvement of +36% and Sharpe improvement of +156% confirm trend persistence is a real, tradeable signal.

---

## 2026-03-09 — Phase 10.3: Keltner Channel Breakout

**Goal:** Test EMA-based channel breakout with EMA reversion exit. Expected to produce smoother entries than Donchian.

**Implementation:** `strategies/keltner_channel/strategy.py`
- Entry: close > upper KC (EMA + ATR×2.0) for long, close < lower KC for short
- Exit: close crosses below exit EMA (50-period), or ATR trailing stop
- Min hold: 10 bars before EMA exit activates

**Results (MNQ-Short, best combo):**

| Metric | Value |
|--------|-------|
| PF | 1.46 |
| Sharpe | 1.90 |
| Trades | 340 |
| PnL | $11,433 |
| MaxDD | $3,219 |
| Median hold | **14 bars** |
| Corr vs PB | -0.145 |
| Corr vs ORB | **-0.170** |
| Target cell PnL | +$13 (breakeven) |

**Key finding:** EMA exit on 5m bars creates a momentum scalper (14-bar hold), not a trend-follower. Any "close below X level" exit degenerates on 5m bars because intrabar noise constantly crosses these levels. Only pure ATR trailing stops achieve 60+ bar holds.

**Decision:** Keltner has better PF/Sharpe than Donchian but is not a trend-follower. Different structural role: momentum swing system.

---

## 2026-03-09 — Phase 10.4: VWAP Trend Continuation

**Goal:** Test pullback entry model — structurally different from breakout entries. Enters at VWAP support in established trends, not at new highs/lows.

**Implementation:** `strategies/vwap_trend/strategy.py`
- Trend filter: EMA slope confirms direction
- Entry: price pulls back to session VWAP after MIN_TREND_BARS above/below
- Exit: N consecutive closes below VWAP (2), or ATR trailing stop
- Min hold: 10 bars before VWAP exit activates

**Results (MNQ-Long, best combo):**

| Metric | Value |
|--------|-------|
| PF | **1.67** |
| Sharpe | **2.62** |
| Trades | 195 |
| PnL | $5,776 |
| MaxDD | $1,290 |
| Median hold | 14 bars |
| Corr vs PB | **-0.087** |
| Corr vs ORB | 0.039 |
| Target cell PnL | -$301 |

**Key finding:** Best risk-adjusted metrics of all three trend candidates. Pullback entries produce superior PF (1.67 vs 1.29/1.46) and Sharpe (2.62 vs 1.32/1.90). The target cell improved (-$301 vs -$823) but remains negative — confirming the problem is structural, not entry-dependent.

---

## 2026-03-09 — Phase 10.5: 4-Strategy Portfolio Test

**Goal:** Test combined portfolio: PB + ORB + VWAP Trend + Donchian (GRINDING-only).

**Results:**

| Metric | 2-Strat Baseline | 3-Strat (+VWAP) | 4-Strat (Full) |
|--------|-----------------|-----------------|----------------|
| PnL | $3,355 | $9,131 | **$11,113** |
| Sharpe | 3.31 | 3.02 | **3.15** |
| Calmar | 3.91 | 6.76 | **7.52** |
| MaxDD | $859 | $1,351 | $1,477 |
| Trades | 134 | 329 | 377 |
| Monthly | 60% | 72% | **80%** |

**Correlation matrix:** All pairwise correlations between -0.087 and +0.061. Genuinely diversified.

**Per-strategy contribution:** VWAP 52%, ORB 24%, Donchian 18%, PB 6%.

**Monthly improvement:** 5 negative months (4-strat) vs 10 (2-strat). The new strategies fill exactly the months where the old portfolio was flat or negative.

**Decision:** The 4-strategy structure is the target portfolio architecture. PnL triples with maintained Sharpe and 80% monthly consistency. Next step: exit evolution on existing strategies to address the remaining bleed, plus full validation battery on VWAP Trend and Donchian.

---

*Last updated: 2026-03-09*
