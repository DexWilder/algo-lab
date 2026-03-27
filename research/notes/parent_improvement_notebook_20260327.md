# Parent Improvement Notebook

*What current core + probation strategies might be missing.*
*Which fragments could improve them. Where they're vulnerable.*
*Date: 2026-03-27*

---

## Core Strategies

### VWAP-MNQ-Long (Workhorse, MOMENTUM)
- **Vulnerability:** Morning session only. Fails in RANGING regimes.
- **What could improve it:**
  - Vol regime filter (only trade when ATR > median) — component exists as concept
  - Afternoon extension variant (test if VWAP signal works after 12:00)
  - Better exit: trailing ATR stop vs fixed time exit comparison needed
- **Fragment to watch for:** `filter` type — vol regime gate

### XB-PB-EMA-MES-Short (Workhorse, MOMENTUM)
- **Vulnerability:** Short-only on MES. Underperforms in strong bull trends.
- **What could improve it:**
  - Trend persistence filter (only short when trend_persistence = CHOPPY)
  - Faster exit in trending markets
- **Fragment to watch for:** `regime_logic` — trend persistence gate

### NoiseBoundary-MNQ-Long (Workhorse, MOMENTUM)
- **Vulnerability:** Forward PF 0.00 so far (3 trades, all losers). Too early to judge but concerning.
- **What could improve it:**
  - Session filter (restrict to strongest hours)
  - Minimum range filter (only trade when daily range exceeds threshold)
- **Fragment to watch for:** `session_effect` or `filter`

### BB-EQ-MGC-Long (Tail Engine, MEAN_REVERSION)
- **Vulnerability:** MGC is at 4-strategy limit. Any new MGC strategy requires displacing this or PB-MGC.
- **What could improve it:**
  - Combined squeeze + vol expansion confirmation
  - Better target: dynamic rather than midline reversion
- **Fragment to watch for:** `exit_logic` — dynamic target methods

### PB-MGC-Short (Core, MOMENTUM)
- **Vulnerability:** Weakest core by rubric (16/24). First displacement target.
- **What could improve it:**
  - Vol filter: only short when vol is elevated
  - Session restriction: morning-only may be too broad
- **Fragment to watch for:** Any new MGC strategy with rubric > 16 displaces this

---

## Probation Challengers

### VolManaged-EquityIndex-Futures (Stabilizer, VOLATILITY)
- **Current evidence:** 7 daily contributions, near-zero PnL (expected early)
- **Vulnerability:** Long-only MES. Crisis DD is the key risk.
- **What could improve it:**
  - Crisis detector that reduces weight faster (current: vol lookback only)
  - Regime-aware target vol (lower target in HIGH_VOL, higher in LOW_VOL)
- **Fragment to watch for:** `sizing_overlay` — adaptive vol targeting

### Treasury-Rolldown-Carry-Spread (Stabilizer, CARRY)
- **Current evidence:** 0 trades (next signal: March 31 month-end)
- **Vulnerability:** PF 1.11 is thin. 2025-2026 was negative.
- **What could improve it:**
  - Curve-steepness filter: only trade when the curve is steep enough
  - DV01-weighted vs equal-notional: already has both variants
- **Fragment to watch for:** `filter` — yield curve steepness gate

### ZN-Afternoon-Reversion (Diversifier, STRUCTURAL)
- **Current evidence:** 0 trades (sparse ZN afternoon bars)
- **Vulnerability:** HIGH_VOL dependent (PF 1.04 in LOW_VOL). Window-specific.
- **What could improve it:**
  - Vol regime gate: only trade when ATR > 70th percentile (component exists)
  - Tuesday exclusion (backtest PF 0.87 on Tuesdays)
- **Fragment to watch for:** `filter` — vol percentile gate, day-of-week filter

### PreFOMC-Drift-Equity (Event Sleeve, EVENT)
- **Current evidence:** 0 trades (next FOMC: April 29-30)
- **Vulnerability:** Sparse events (~8/year). Can't accumulate evidence fast.
- **What could improve it:**
  - Pre-event vol scaling (reduce position when VIX is already elevated)
  - Multi-event generalization (does the same drift exist before CPI? NFP?)
- **Fragment to watch for:** `session_effect` — pre-event drift patterns

### TV-NFP-High-Low-Levels (Event Sleeve, EVENT)
- **Current evidence:** 0 trades. Half-life: ARCHIVE_CANDIDATE (sparse event floor applied).
- **Vulnerability:** Bootstrap CI < 1.0. Monte Carlo ruin probability high.
- **What could improve it:**
  - Tighter confirmation (1 close vs 2 closes above/below level)
  - Direction bias filter based on prior-month trend
- **Fragment to watch for:** `filter` — directional bias based on trend

---

## Cross-Cutting Improvement Opportunities

| Fragment Type | Strategies That Could Benefit | Priority |
|--------------|------------------------------|----------|
| Vol regime filter (ATR percentile) | VWAP-MNQ, NoiseBoundary, ZN-Afternoon | HIGH — most parents would benefit |
| Trend persistence gate | XB-PB-MES, PB-MGC | MEDIUM — helps short strategies |
| Session restriction | NoiseBoundary, BB-EQ-MGC | MEDIUM — may reduce noise |
| Adaptive exit (trailing vs time) | All intraday strategies | MEDIUM — exit quality is undertested |
| Day-of-week filter | ZN-Afternoon (Tuesday weak) | LOW — small sample |
| Pre-event vol scaling | PreFOMC, TV-NFP | LOW — sparse events limit testing |
