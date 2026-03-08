# Round 1 Family Comparison Report

**Date:** 2026-03-07
**Purpose:** Compare all Round 1 conversion candidates against the validated PB family to assess portfolio value and identify deployable strategies.

---

## Candidates Compared

| # | Strategy | Asset | Mode | Family | Status |
|---|----------|-------|------|--------|--------|
| 1 | PB-Trend | MGC | Short | Pullback | candidate_validated |
| 2 | ORB-009 | MGC | Long | ORB Breakout | candidate_validated |
| 3 | VWAP-006 | MES | Long | VWAP Reversion | converted (side-specific) |
| 4 | ICT-010 | — | — | ICT Session Sweep | rejected |

---

## Head-to-Head Metrics

| Metric | PB-MGC-Short | ORB-009 MGC-Long | VWAP-006 MES-Long |
|--------|-------------|-----------------|-------------------|
| **Profit Factor** | 2.22 | 1.99 | 1.21 |
| **Sharpe Ratio** | 5.07 | 3.63 | 1.32 |
| **Trade Count** | 19 | 106 | 572 |
| **Total PnL** | $741 | $3,022 | $2,879 |
| **Max Drawdown** | $283 | $826 | $1,245 |
| **Win Rate** | — | 51.9% | 40.7% |
| **Expectancy** | — | $28.51 | $5.03 |
| **Avg R** | — | 0.47 | 0.12 |
| **Recovery Factor** | 2.62 | 3.66 | 2.31 |
| **Data Period** | ~2 years | 596 days | 630 days |

---

## Strengths & Weaknesses

### PB-Trend MGC-Short
**Strengths:**
- Highest PF (2.22) and Sharpe (5.07) of any candidate
- Very tight drawdown ($283)
- Clean trend-following logic with ATR-based risk

**Weaknesses:**
- Only 19 trades — statistically thin
- Session restricted to 09:30-10:30 ET (narrow window)
- Limited sample makes robustness claims weaker

**Verdict:** Strong edge but needs more data. Keep as core validated strategy.

### ORB-009 MGC-Long
**Strengths:**
- Strong PF (1.99) with 106 trades — better statistical depth than PB
- Best recovery factor (3.66) — earns 3.66x its max drawdown
- Passes ALL 8 robustness criteria (top-trade removal, walk-forward, param stability, monthly consistency)
- 100% parameter stability (25/25 variations profitable)
- Session sweet spot identified (10:00-11:00, PF=2.96)
- Nearly zero correlation with PB family (r < 0.02) — excellent diversification

**Weaknesses:**
- 2024 was a losing year (PF=0.72) — edge is recent (~14 months)
- Moderate trade frequency (~1 per 5.6 days)
- Volume filter is the primary edge contributor — sensitive to VOL_MULT

**Verdict:** Candidate validated. Best diversification candidate for the portfolio.

### VWAP-006 MES-Long
**Strengths:**
- Highest trade count (572) — deepest statistical sample
- Produces $2,879 total PnL with consistent long-side activity
- ATR-based risk management scales with volatility

**Weaknesses:**
- Lowest PF (1.21) — thin edge
- Sharpe only 1.32 — below the 1.2 candidate_validated threshold but barely
- Low win rate (40.7%) with small avg R (0.12)
- Short side loses money (MES-Short PF=1.04, MGC-Short PF=0.59)
- Moderate correlation with PB-MNQ-Long (r=0.30) — less independent
- High max drawdown ($1,245) relative to PnL

**Verdict:** Keep alive as side-specific candidate (long-only on MES). Does not meet candidate_validated thresholds. Needs optimization or combination with other filters.

### ICT-010 (All Assets)
**Result:** Every asset/mode combination lost money (PF < 1.0 everywhere).

| Asset | Mode | PF | PnL |
|-------|------|-----|-----|
| MES | both | 0.65 | -$1,603 |
| MGC | both | 0.79 | -$931 |
| MNQ | both | 0.84 | -$1,547 |

**Root causes:** Noisy sweep detection on 5m bars, unfiltered pullback entries, fixed stops ignoring volatility, 1 trade/day cap with low win rate.
**Verdict:** REJECTED. Postmortem saved. State machine pattern salvageable as component.

---

## Correlation Matrix (Daily PnL)

Key correlations against the PB family:

| Strategy Pair | Correlation | Assessment |
|---------------|-------------|------------|
| ORB-009 MGC-Long vs PB-MGC-Short | < 0.01 | Uncorrelated — excellent |
| ORB-009 MGC-Long vs PB-MNQ-Long | -0.005 | Uncorrelated — excellent |
| ORB-009 MGC-Long vs PB-MES-Short | < 0.01 | Uncorrelated — excellent |
| VWAP-006 MES-Long vs PB-MNQ-Long | 0.30 | Moderate — less independent |
| VWAP-006 MES-Long vs PB-MES-Short | -0.007 | Uncorrelated |
| VWAP-006 MES-Long vs PB-MGC-Short | -0.007 | Uncorrelated |

**ORB-009 is nearly perfectly uncorrelated with the entire PB family.** This makes it the ideal portfolio addition — it adds return without adding correlated risk.

VWAP-006 shows moderate correlation (r=0.30) with PB-MNQ-Long, both being long-biased strategies on equity futures. Portfolio benefit is present but diminished.

---

## Portfolio Implications

### Current Validated Portfolio (PB Family Only)
| Metric | Value |
|--------|-------|
| Combined PnL | $3,341 |
| Combined Sharpe | 1.20 |
| Combined MaxDD | $1,950 |
| Strategies | 3 (MGC-Short, MNQ-Long, MES-Short) |

### Projected Portfolio (PB + ORB-009 MGC-Long)
| Metric | Value | Change |
|--------|-------|--------|
| Combined PnL | ~$6,363 | +90% |
| Expected Sharpe | >1.5 (est.) | +25%+ |
| Diversification | 4 uncorrelated streams | +1 new axis |
| Asset Coverage | MGC (both sides), MNQ-Long, MES-Short | MGC long-side coverage added |

Adding ORB-009 MGC-Long to the PB portfolio:
1. **Doubles total PnL** — $3,022 from ORB-009 alone
2. **Fills the MGC long-side gap** — PB only trades MGC short
3. **Zero correlation overlap** — doesn't increase portfolio risk proportionally
4. **Different family** — ORB breakout ≠ pullback trend, true strategy diversification

### Role of VWAP-006
VWAP-006 MES-Long could serve as an **enhancer** (Layer B) rather than a core strategy:
- It adds volume (572 trades) and PnL ($2,879) but with thinner edge
- Moderate correlation with PB-MNQ-Long limits its diversification value
- Best deployed if PF can be improved through session restriction or parameter refinement

---

## Recommendations

### Immediate
1. **Promote ORB-009 MGC-Long** to `candidate_deployable` pipeline
   - Restrict entry window to 10:00-11:00 ET
   - Compute prop account sizing (position size, max contracts)
   - Create prop controller config
2. **Maintain VWAP-006 MES-Long** as `converted (side-specific)`
   - Run optimization experiments on session window and RSI parameters
   - Re-evaluate after parameter tuning

### Next Conversion Round
Priority candidates from triage (ordered by expected portfolio value):
1. **RVWAP Mean Reversion** — fills mean_reversion gap, likely uncorrelated with breakout/trend
2. **Gold ORB Strategy** — gold-specific, may complement ORB-009 with different timeframe
3. **Liquidity Sweeper** — ICT family but different approach than ICT-010

### Research Priorities
1. Extend ORB-009 validation with Monte Carlo simulation
2. Investigate ORB-009's 2024 weakness — correlate with gold volatility regime
3. Test VWAP-006 with tighter session windows (09:30-11:00 only)
4. Build portfolio equity curve combining PB family + ORB-009

---

## Status Summary

| Strategy | Asset | Mode | Status | Portfolio Role |
|----------|-------|------|--------|---------------|
| pb_trend | MGC | Short | candidate_validated | Core (Layer A) |
| pb_trend | MNQ | Long | candidate_validated | Core (Layer A) |
| pb_trend | MES | Short | candidate_validated | Core (Layer A) |
| orb_009 | MGC | Long | candidate_validated | Core candidate (Layer A) |
| vwap_006 | MES | Long | converted (side-specific) | Enhancer candidate (Layer B) |
| ict_010 | — | — | rejected | — |

---
*Report generated 2026-03-07*
