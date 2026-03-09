# Regime Engine Summary

*Phase 8 — Plain-language explanation of the multi-factor regime engine.*

---

## What the Regime Engine Does

The regime engine classifies each trading day into one of several market states using only price data (OHLCV). It answers: "What kind of market environment is this?" — then decides which strategies should trade today.

## Inputs

All computed from OHLCV bars. No external data feeds required.

| Factor | How It's Computed | What It Measures |
|--------|-------------------|------------------|
| **Volatility** | 20-bar ATR, percentile-ranked over 252 days | How volatile is today vs recent history? |
| **Trend** | 20-day EMA slope (pct_change) | Is the market trending or ranging? |
| **Realized Vol** | 14-day rolling stdev of daily returns × √252 | What's the annualized volatility? |

### Why These Three Factors

- **ATR Volatility** captures intraday range expansion — breakout strategies need it, mean reversion strategies get hurt by it.
- **Trend** captures directional conviction — trend-following strategies need it, reversal strategies need its absence.
- **Realized Vol** captures the broader volatility environment — distinct from ATR because it weights daily close-to-close moves, not intraday ranges.

## States

| Factor | States |
|--------|--------|
| Volatility | LOW_VOL (bottom third) / NORMAL (middle) / HIGH_VOL (top third) |
| Trend | TRENDING (abs slope ≥ 0.05%) / RANGING (below threshold) |
| Realized Vol | LOW_RV (bottom third) / NORMAL_RV (middle) / HIGH_RV (top third) |

**Composite regime** = vol + trend combination (e.g., `HIGH_VOL_TRENDING`). States are not mutually exclusive — a day can be HIGH_VOL + TRENDING + HIGH_RV simultaneously.

## Strategy Activation Logic

Each strategy has a **regime profile** — a set of preferred and avoided regime states, generated empirically from backtested per-regime performance.

**Decision rule:** A strategy is **active** unless the current day includes a regime state in its `avoid_regimes` list.

This is conservative by design — strategies are active by default and only deactivated when the data shows a specific regime state is harmful to that strategy.

## What This Analysis Proves

1. **Not all market days are equal.** Strategies have measurably different performance across regime states.
2. **Selective activation improves risk-adjusted returns.** Skipping harmful regime days reduces MaxDD and increases Sharpe/Calmar without proportionally reducing PnL.
3. **Different strategies respond differently to regimes.** A regime that helps one strategy may hurt another — this is precisely why portfolio-level regime management matters more than a single global gate.

## What This Does NOT Prove

1. **Not a prediction engine.** The regime engine classifies the current state — it does not predict tomorrow's regime.
2. **Not adaptive to new regimes.** If market structure fundamentally changes (new regime type), the engine will misclassify until recalibrated.
3. **Historical only.** All regime profiles are derived from historical backtests. Out-of-sample behavior may differ.
4. **Not a substitute for strategy quality.** A bad strategy with perfect regime filtering is still a bad strategy. Regimes improve good strategies — they don't create edge from nothing.

## Relationship to Previous ATR Gate

The Phase 5 ATR gate (skip low-vol days) was a single-factor simplification. The regime engine extends this:

| Feature | ATR Gate (Phase 5) | Regime Engine (Phase 8) |
|---------|-------------------|------------------------|
| Factors | 1 (ATR percentile) | 3 (ATR + trend + realized vol) |
| Gate rule | Same for all strategies | Per-strategy profiles |
| States | low / medium / high | 6 independent states |
| Customization | Global threshold | Strategy-specific avoid lists |

The ATR gate remains valid — it's now one factor within the broader regime engine.

---
*Generated as part of Phase 8 — Regime Engine + Portfolio Intelligence*
