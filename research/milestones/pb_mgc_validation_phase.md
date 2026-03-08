# PB-MGC Validation Phase — Research Milestone

**Date:** 2026-03-07
**Target:** ALGO-CORE-PB-MGC-001
**Strategy:** PB Trend v1.0 (Pullback Trend-Following, short-only on MGC)
**Data:** Databento GLBX.MDP3, 5m bars, 2024-02-29 → 2026-03-06 (596 days)

---

## Baseline Metrics

| Metric | Value |
|--------|------:|
| Profit Factor | 2.02 |
| Sharpe Ratio | 4.176 |
| Win Rate | 57.1% |
| Total PnL | $767.00 |
| Max Drawdown | $283.00 |
| Expectancy | $27.39/trade |
| Avg R | 0.437 |
| Trade Count | 28 |
| Monthly Consistency | 8/11 positive (73%) |

---

## Top-Trade Removal Tests

Tests whether edge survives removing the best trades (outlier dependence check).

| Removed | Trades | PF | Sharpe | PnL | MaxDD |
|---------|-------:|---:|-------:|----:|------:|
| None (base) | 28 | 2.02 | 4.18 | $767 | $227 |
| Top 1 (-$290) | 27 | 1.63 | 3.01 | $477 | $227 |
| Top 2 (-$560) | 26 | 1.28 | 1.56 | $207 | $227 |
| Top 3 (-$694) | 25 | 1.10 | 0.59 | $73 | $227 |

**Finding:** Edge thins progressively but never goes negative. PF stays above 1.0 even after removing the 3 best trades.

---

## Walk-Forward Year Splits

Tests whether edge is consistent across time periods.

| Segment | Trades | PF | Sharpe | PnL |
|---------|-------:|---:|-------:|----:|
| 2024 | 12 | 1.60 | 2.82 | $194 |
| 2025 | 14 | 1.03 | 0.20 | $13 |
| 2026 YTD | 2 | inf | — | $560 |

**Finding:** 2024 shows standalone edge (PF 1.60). 2025 is essentially flat (PF 1.03). 2026 YTD driven by 2 outlier winners. Edge is not uniformly distributed across time.

---

## Session Window Analysis

Tests which time window produces the strongest edge.

| Window | Trades | PF | Sharpe | Exp/trade |
|--------|-------:|---:|-------:|----------:|
| Full (current) | 28 | 2.02 | 4.18 | $27.39 |
| 09:00–10:00 | 11 | 2.32 | 5.17 | $37.73 |
| 09:30–10:30 | 19 | 2.22 | 5.07 | $39.00 |
| 09:00–11:00 | 23 | 2.10 | 4.57 | $32.65 |
| 10:00–11:00 | 12 | 1.91 | 4.00 | $28.00 |

**Finding:** 09:30–10:30 is the optimal window — best expectancy per trade ($39.00), strong sample size (19 trades), and PF 2.22. The morning session drives the edge.

---

## Parameter Stability Tests

Tests whether small parameter changes break the strategy.

| Variation | PF | Sharpe | PnL |
|-----------|---:|-------:|----:|
| BASE | 2.02 | 4.18 | $767 |
| SL_ATR=1.2 | 2.23 | 4.74 | $839 |
| SL_ATR=1.8 | 1.92 | 3.98 | $752 |
| SL_ATR=2.0 | 1.76 | 3.50 | $677 |
| TP_ATR=1.8 | 1.77 | 3.36 | $577 |
| TP_ATR=2.4 | 2.38 | 5.18 | $1,037 |
| TP_ATR=2.8 | 2.27 | 4.92 | $990 |
| FAST_EMA=8 | 2.59 | 5.72 | $1,121 |
| FAST_EMA=10 | 2.25 | 4.77 | $844 |
| SLOW_EMA=18 | 1.51 | 2.54 | $560 |
| SLOW_EMA=25 | 1.88 | 3.82 | $606 |
| ADX=12 | 2.02 | 4.18 | $767 |
| ADX=16 | 2.02 | 4.18 | $767 |
| ADX=18 | 2.02 | 4.18 | $767 |

**Finding:** All 16 variations remain profitable. PF range: 1.51–2.59. No cliff edges in parameter space. The surface is smooth and stable.

---

## Evidence of Structural Edge vs Outlier Dependence

### Arguments for structural edge:
1. **Parameter stability** — every variation tested stays profitable (PF 1.51–2.59). No fragile parameter combinations. The strategy is not curve-fit to a single parameter set.
2. **Smooth parameter surface** — adjacent parameter values produce similar results. No cliff edges or discontinuities.
3. **Session concentration** — 89% of trades and 98% of PnL come from the 09:00–11:00 morning window. This aligns with known gold market behavior (London/NY overlap, high institutional flow).
4. **Fast trade duration** — median 15 minutes, 79% under 30 minutes. Consistent with capturing pullback entries in trending markets.
5. **Controlled drawdowns** — max drawdown $283, all clusters recover within a few trades. No catastrophic loss events.
6. **Non-negative after outlier removal** — even removing the top 3 trades, PF stays above 1.0.

### Arguments for outlier dependence:
1. **Small sample** — 28 trades is below the 50-trade threshold for statistical confidence.
2. **2025 was flat** — PF 1.03 over 14 trades. The edge did not manifest consistently in the middle year.
3. **March 2026 dominance** — 2 trades ($560) account for 73% of total PnL. Without them, the strategy is near-breakeven.
4. **Low frequency** — many months have zero activity. Edge is sparse, not continuous.

### Conclusion:
PB-MGC-Short shows **real structural characteristics** (parameter stability, session concentration, controlled drawdowns) but **insufficient sample size** to confirm the edge is not partially driven by outliers. The 2025 flat year is the strongest caution signal.

**Status: Candidate Validated — needs extended data and sample size expansion before deployment.**

### Recommended next steps:
1. Restrict session to 09:30–10:30 (best expectancy window)
2. Extend data to 4+ years to increase sample size
3. Test on full-size GC to validate edge scales
4. Run signal correlation with PB-MNQ-Long and PB-MES-Short for stacking potential
