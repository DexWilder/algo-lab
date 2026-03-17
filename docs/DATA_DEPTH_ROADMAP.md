# FQL Data Depth Roadmap

*Where more historical data would unlock better research, and what it costs.*
*Last updated: 2026-03-16*

---

## Current Data Inventory

| Asset | Class | Start | End | Trading Days | Depth Rating |
|-------|-------|-------|-----|-------------|-------------|
| MES | Equity | 2019-06-30 | 2026-03-12 | ~1,688 | DEEP |
| MNQ | Equity | 2019-06-30 | 2026-03-12 | ~1,688 | DEEP |
| MGC | Metal | 2019-06-30 | 2026-03-12 | ~1,688 | DEEP |
| M2K | Equity | 2019-06-30 | 2026-03-11 | ~1,688 | DEEP |
| MCL | Energy | 2021-07-11 | 2026-03-11 | ~1,176 | MODERATE |
| 6E | FX | 2024-02-29 | 2026-03-15 | ~514 | **SHALLOW** |
| 6J | FX | 2024-02-29 | 2026-03-15 | ~514 | **SHALLOW** |
| 6B | FX | 2024-02-29 | 2026-03-15 | ~514 | **SHALLOW** |
| ZN | Rate | 2024-02-29 | 2026-03-11 | ~511 | **SHALLOW** |
| ZB | Rate | 2024-02-29 | 2026-03-11 | ~511 | **SHALLOW** |
| ZF | Rate | 2024-02-29 | 2026-03-13 | ~512 | **SHALLOW** |
| ES | Equity | 2024-02-29 | 2026-03-11 | ~511 | SHALLOW |
| MYM | Equity | 2024-02-29 | 2026-03-11 | ~511 | SHALLOW |

---

## Minimum Useful Lookback by Strategy Type

| Strategy Type | Minimum Depth | Ideal Depth | Why |
|--------------|---------------|-------------|-----|
| Intraday 5m (breakout, MR) | 1 year (~252 days) | 3+ years | Walk-forward needs 2 halves. 1 year = marginal. |
| Daily-bar trend | 3 years (~756 days) | 5+ years | 20-60 trades/year. Need 60+ trades minimum for validation. |
| Event-driven | 3 years | 5+ years | Low frequency (12-50 events/year). Statistical power requires volume. |
| Swing (multi-day) | 2 years | 4+ years | Moderate frequency but needs regime diversity. |
| Cross-asset signals | 3 years | 5+ years | Need multiple regime cycles to validate correlation patterns. |

---

## Research Lanes Blocked by Shallow Data

### 1. FX Daily-Bar Strategies (6E/6J/6B) — BLOCKED

**Current depth:** ~514 trading days (2 years)
**Daily-bar trades generated:** 23-64 per asset
**Problem:** Walk-forward unstable on all FX daily-bar tests. With only 2 years, daily strategies produce 15-30 trades per half — not enough for statistical confidence.

**Impact of backfill to 2019:** Would increase to ~1,700 trading days (~6.7 years). Daily strategies would produce 60-120+ trades. Walk-forward would have 30-60 trades per half — reliable.

**Specific blocked candidates:**
- FX Daily Trend 6J: PF 1.46, 23 trades, WF 3.53/0.63 (unreliable)
- DualThrust 6J: PF 0.59 (but only 64 trades — may improve with more data)

### 2. Rates Daily-Bar Strategies (ZN/ZB/ZF) — BLOCKED

**Current depth:** ~511 trading days (2 years)
**Daily-bar trades generated:** 17-67 per asset
**Problem:** Rate Daily Momentum on ZF showed PF 2.52 but only 17 trades with walk-forward collapsing (11.84 → 0.35). Impossible to validate.

**Impact of backfill to 2019:** 60-120+ trades. The ZF PF 2.52 signal could be confirmed or rejected with confidence.

### 3. Event-Driven Strategies (all assets) — PARTIALLY BLOCKED

**Current depth on MCL:** ~1,176 days (4.6 years) — adequate for EIA
**Current depth on rates:** ~511 days — inadequate for FOMC/CPI strategies
**Problem:** EIA Reaction on MCL had 201 trades (adequate). But macro event strategies on rates would have < 50 events in 2 years.

### 4. 6J Probation Strategies — NOT BLOCKED (but would benefit)

**Current depth:** ~514 days
**Intraday trades:** 43-125 (adequate for probation)
**Benefit of backfill:** Would allow running the full validation battery with proper asset robustness testing. Current validation used 6E as cross-asset (PF 1.72 on 6E), but longer history would strengthen confidence.

---

## Backfill Cost Estimates (Databento)

| Asset | Backfill Period | Cost | Priority |
|-------|----------------|------|----------|
| ZN | 2019-07 to 2024-02 | $4.57 | HIGH |
| ZF | 2019-07 to 2024-02 | $3.76 | HIGH |
| ZB | 2019-07 to 2024-02 | $4.26 | HIGH |
| 6J | 2019-07 to 2024-02 | $1.92 | MEDIUM |
| 6E | 2019-07 to 2024-02 | $2.05 | MEDIUM |
| 6B | 2019-07 to 2024-02 | $1.83 | LOW |
| MCL | 2019-07 to 2021-07 | ~$0.50 | LOW |
| **TOTAL** | | **$18.89** | |

**$18.89 total** to bring all expansion assets to the same depth as core equity assets.

---

## Prioritized Spend Recommendations

### Tier 1 — Highest ROI ($12.59)

**Rates backfill: ZN + ZF + ZB ($12.59)**

Why first:
- Rates are the #1 asset class gap in the portfolio (0 active strategies)
- 4 rate attempts failed — but daily-bar momentum on ZF showed PF 2.52
- That signal CANNOT be validated with current data (17 trades)
- Backfill would produce 60-120 daily trades — enough for real validation
- Rates are genuinely uncorrelated to equities (the whole point of expansion)

### Tier 2 — Medium ROI ($3.97)

**FX backfill: 6J + 6E ($3.97)**

Why second:
- 6J is the lead FX branch with 2 probation strategies
- Current validation is adequate for probation (43-125 trades)
- But deeper history would strengthen the validation battery results
- 6E showed PF 1.72 long-only but failed validation (WF unstable) — more data might change that

### Tier 3 — Lower Priority ($2.33)

**6B + MCL ($2.33)**

Why last:
- 6B has shown no edge on any strategy tested
- MCL showed marginal signals (PF 1.08-1.19) that didn't clear thresholds
- More data is unlikely to change the fundamental finding
- Only backfill if Tier 1 and 2 results are promising

---

## When to Execute

**Not now.** The system is in operate-and-observe mode. Data backfill should happen:

1. After the first probation review cycle confirms the expansion thesis works in forward testing
2. If the Week 8 formal review shows the probation strategies are accumulating evidence normally
3. Before the next major research sprint (evolution engine, rates second attempt, etc.)

**Recommended timing:** After Week 8 review, before any new rate or FX daily-bar research.

---

## What NOT to Spend On

- ES/MYM backfill — already have MES/MNQ/M2K with deep data on the same index family
- Any new asset not in the current expansion plan (NG, SI, HG) — not prioritized yet
- Higher-resolution data (1-second, tick) — current 1-minute/5-minute is sufficient for all FQL strategy types
