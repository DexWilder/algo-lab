# Portfolio-Role Note: Treasury-Rolldown-Carry-Spread (Family 45)

**Date:** 2026-03-20
**Status:** Active probation challenger, forward runner entry

---

## Signal Frequency

- **Rebalance cadence:** Monthly (last trading day)
- **Rank changes per year:** ~3-5 (not every rebalance changes the spread)
- **Backtest signals over full dataset:** 8 ZN-leg trades across ~5.5 years
- **Expected forward trades per year:** ~1.5-3 (based on historical rank-change frequency)
- **Time to 8 forward trades:** ~3-5 years at historical pace

This is the slowest strategy in the portfolio by a wide margin. Monthly
rebalance with infrequent rank changes means evidence accumulates slowly.

---

## Overlap / Correlation Risk

### Factor Overlap

| Strategy | Primary Factor | Overlap with Family 45 |
|----------|---------------|----------------------|
| VWAP-MNQ-Long | MOMENTUM | None — different factor, asset, horizon |
| XB-PB-EMA-MES-Short | MOMENTUM | None — equity momentum vs rates carry |
| NoiseBoundary-MNQ-Long | MOMENTUM | None |
| BB-EQ-MGC-Long | MOMENTUM | None — metal vs rates |
| PB-MGC-Short | MOMENTUM | None |
| DailyTrend-MGC-Long | MOMENTUM | None — different asset class entirely |
| MomPB-6J-Long-US | MOMENTUM | None — FX vs rates |
| FXBreak-6J-Short-London | STRUCTURAL | None |
| PreFOMC-Drift-Equity | EVENT | None — different asset, event, mechanism |
| TV-NFP-High-Low-Levels | EVENT | None — equity event vs rates carry |
| CloseVWAP-M2K-Short | MEAN_REVERSION | None |

**Factor correlation: effectively zero.** Family 45 is the only CARRY
strategy and the only Rates asset class strategy. It overlaps with nothing.
This is its primary portfolio value — even at marginal PF, it adds a
genuinely independent dimension.

### Asset Overlap

- **ZN/ZF/ZB:** No other active or probation strategy trades rates.
- **Margin impact:** Treasury micro futures are not available — this uses
  full-size ZN/ZF/ZB at 1 contract. Margin per leg: ~$2,000-$4,000.
  Spread margin offset typically reduces this by 50-70%.

### Timing Overlap

- Monthly rebalance with daily close evaluation. No intraday signals.
- Zero overlap with any morning/midday session strategy.
- Trades hold for ~1 month. No same-day conflict with any existing strategy.

### Correlation Confirmation (from first-pass)

- Correlation with rates direction: 0.027 (genuinely neutral — not a
  rates bet, it's a relative-value carry bet across tenors)
- Expected correlation with equity portfolio: ~0 (rates carry spread
  is structurally independent of equity momentum)

---

## Monthly Rebalance: Appropriate or Not?

### Arguments For Monthly

- **Carry is slow-moving.** Term-structure carry (yield + rolldown) changes
  gradually. Daily or weekly rebalance would generate noise trades with
  the same ranking most of the time.
- **Academic consensus:** Koijen et al. (2018), Butler & Butler — carry
  strategies are typically monthly or quarterly rebalance.
- **Transaction cost sensitivity:** With 3 full-size Treasury futures per
  rebalance, more frequent rebalance burns PnL on commissions and slippage.
- **Signal quality:** APPROXIMATE carry (price-derived yield). More frequent
  evaluation amplifies approximation noise.

### Arguments Against Monthly

- **Slow evidence accumulation.** At ~2 forward trades/year, it takes
  3+ years to accumulate 8 trades for conviction review.
- **Regime response lag.** If the yield curve inverts sharply, the strategy
  waits until month-end to react. Intra-month carry reversals are missed.
- **Limited granularity for vitality monitoring.** Sparse forward data
  makes edge-decay detection nearly impossible at monthly cadence.

### Verdict

**Monthly is appropriate for v1.** The carry signal is too slow-moving
for higher frequency, and the APPROXIMATE quality would generate more
noise than signal at weekly cadence. Accept the slow evidence pace.

If the strategy survives conviction and moves toward core, consider a
bi-weekly rebalance (2x monthly) in v2 to double the evidence generation
rate while keeping the signal slow enough to reflect real carry dynamics.

---

## 8 Historical Signals: Enough for Probation?

**No, but the question is wrong.**

The 8 ZN-leg signals from `generate_signals()` represent rank changes
visible to the single-asset backtest engine. The actual spread strategy
(`generate_spread_signals()`) produced 79 trades across 3 tenors in
first-pass testing. The discrepancy:

- `generate_spread_signals()`: 79 monthly spread trades (every month that
  has carry scores for all 3 tenors)
- `generate_signals(df, asset='ZN')`: 8 trades (only months where ZN
  changes from long→short or vice versa)

The forward runner sees 8 trades because it runs the single-asset
interface. But the strategy's real evidence base is the 79-trade spread
history.

### Probation Design Implications

1. **Forward evidence will be sparse.** Expect ~1-3 ZN-leg trades per year
   in the forward runner. This is too slow for standard 8-trade conviction.

2. **Alternative evidence path:** Monitor the full spread via
   `generate_spread_signals()` monthly, independent of the forward runner.
   This gives 12 evidence points per year (every monthly rebalance).

3. **June 1 displacement decision** should use full spread PnL (all 3
   legs), not just ZN-leg forward runner trades.

4. **Recommended probation metric:** Track spread-level monthly returns
   as the primary forward evidence, with the forward runner providing
   ZN-leg execution confirmation.

### What "enough" Means for This Strategy

The 79-trade backtest history is adequate for first-pass classification
(MONITOR at PF 1.11). The June 1 displacement decision needs only 3
months of directional spread evidence (positive or negative). Full
conviction requires ~2 years of monthly observations (24 data points)
to match the statistical power of an intraday strategy with 50+ trades.

This is inherently a patience play. The CARRY gap-fill value justifies
the long probation timeline.

---

## Forward Runner Logging Audit

### What Gets Logged

| Log | Family 45 Coverage | Notes |
|-----|-------------------|-------|
| `logs/trade_log.csv` | YES — `status=probation`, `tier=MICRO`, `horizon=monthly` | ZN-leg trades only |
| `logs/signal_log.csv` | YES — daily signal/controller stats | Shows regime blocks if any |
| `logs/daily_report.csv` | YES — daily PnL contribution included | Marginal impact expected |
| `state/account_state.json` | YES — equity updated with spread PnL | ZN-leg PnL contribution |

### What Is NOT Logged (Gaps)

1. **Full spread PnL.** The forward runner only tracks ZN-leg PnL. The
   ZF and ZB legs are computed internally but not logged separately.
   The spread-level contribution is invisible in daily logs.

2. **Carry score at rebalance.** What was the carry ranking that drove
   the signal? The trade log doesn't capture the signal's input data.

3. **Rank change detail.** Which tenor went long → short? The trade log
   shows `side=long` or `side=short` but not the spread composition.

### Recommended Enhancements (Deferred)

These are nice-to-haves, not blockers for the June 1 decision:

- Add a monthly spread report that runs `generate_spread_signals()` and
  logs the full 3-leg spread PnL alongside the forward runner's ZN-only view.
- Log carry scores at each rebalance to the signal log.

For now, the manual review path is: run `generate_spread_signals()` ad-hoc
during Friday reviews to see full spread performance.

---

## June 1 Review Path

| Date | Action |
|------|--------|
| 2026-03-31 | First monthly rebalance in forward runner. Check: did strategy generate a signal? Is ZN data flowing correctly? |
| 2026-04-30 | Second rebalance. Check: any rank change? Spread PnL direction? |
| 2026-05-30 | Third rebalance. Compile 3-month forward spread PnL. |
| 2026-06-01 | **Displacement decision:** Treasury-Rolldown vs MomIgn-M2K-Short. |

### June 1 Decision Criteria

| Outcome | Condition |
|---------|-----------|
| **DISPLACE MomIgn** | 3-month forward spread PnL ≥ 0 AND rubric ≥ 18 AND MomIgn fails promote |
| **EXTEND WATCH** | Forward evidence inconclusive (< 3 rebalances observed) |
| **ARCHIVE** | 3 consecutive negative monthly spread returns |
| **DEFER** | Forward runner data feed issue or strategy code bug invalidates evidence |
