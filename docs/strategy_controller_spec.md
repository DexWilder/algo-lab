# Strategy Controller Spec — Phase 16

## Purpose

The Strategy Controller sits between strategy signal generation and execution.
It decides **which strategies are active**, **when they should trade**, and
**how portfolio-level risk is coordinated**.

```
Strategy Signals → Strategy Controller → Filtered Trades → Prop Controller → Execution
```

## Architecture

### Three-Layer Filter Pipeline

1. **Regime Gate** — blocks strategies in their `avoid_regimes`
2. **Soft Timing** — prefers entries in preferred window, allows outside with conviction
3. **Portfolio Coordination** — caps simultaneous positions, limits asset overlap, prevents clusters

### Regime Gate

Each strategy defines `avoid_regimes` — a list of regime factor values that block trading.
Uses the existing 4-factor `RegimeEngine`:

| Factor | States |
|--------|--------|
| Volatility (ATR) | LOW_VOL, NORMAL, HIGH_VOL |
| Trend (EMA slope) | TRENDING, RANGING |
| Realized Vol | LOW_RV, NORMAL_RV, HIGH_RV |
| Persistence | GRINDING, CHOPPY |

If **any** current regime factor appears in the strategy's `avoid_regimes`, the entry is blocked.

### Soft Timing Preferences

Each strategy defines:
- `preferred_window`: (start, end) — entries freely allowed
- `allowed_window`: (start, end) — entries allowed only if conviction exceeds threshold
- `conviction_threshold_outside`: minimum conviction score to trade outside preferred window

**Conviction Score** (0–4): count of current regime factors that appear in the strategy's
`preferred_regimes` list. A score of 3 means 3 out of 4 regime factors favor this strategy.

This is **not** a hard time filter. A high-conviction signal at 13:30 for a strategy that
prefers 10:00–12:00 will still fire if the regime alignment is strong enough.

### Portfolio Coordination

Applied after per-strategy filtering:

| Rule | Default |
|------|---------|
| Max simultaneous positions | 4 |
| Max positions per asset | 2 |
| Cluster window | 15 minutes |
| Max entries per cluster | 2 |

When conflicts arise, higher-priority strategies win. Priority is assigned per strategy
based on validation confidence:

| Priority | Strategies |
|----------|-----------|
| 6 | VWAP Trend (highest-validated) |
| 5 | PB, ORB (core parents) |
| 4 | XB-PB-EMA, BB Equilibrium |
| 3 | Donchian GRINDING (probation) |

## Strategy Activation Map

| Strategy | Asset | Mode | Avoid Regimes | Preferred Regimes | Preferred Window |
|----------|-------|------|---------------|-------------------|-----------------|
| PB-MGC-Short | MGC | Short | LOW_VOL, NORMAL_RV, LOW_RV | TRENDING, HIGH_RV | 08:30–12:00 |
| ORB-MGC-Long | MGC | Long | RANGING | HIGH_VOL, TRENDING, HIGH_RV | 10:00–12:00 |
| VWAP-MNQ-Long | MNQ | Long | RANGING | TRENDING, LOW_VOL, NORMAL_RV | 10:00–13:00 |
| XB-PB-EMA-MES-Short | MES | Short | LOW_VOL, RANGING | TRENDING, HIGH_VOL, HIGH_RV | 09:30–12:00 |
| BB-EQ-MGC-Long | MGC | Long | RANGING, LOW_RV | TRENDING, HIGH_RV, NORMAL_RV | 09:45–14:45 |
| Donchian-MNQ-Long | MNQ | Long | (GRINDING gate) | TRENDING, HIGH_VOL | 09:30–14:00 |

## Simulation Methodology

### Baseline
Run all 6 strategies always-on (with existing regime profiles for Donchian GRINDING gate).

### Controlled
Run same trades through the controller pipeline:
1. Per-trade regime gate check
2. Per-trade soft timing check
3. Portfolio coordination across all strategies

### Comparison Metrics
- Sharpe, Calmar, MaxDD, Total PnL
- Monthly consistency
- Trade count reduction
- Entry time distribution shift
- Clustered drawdown reduction
- Monte Carlo ruin probability

### Verdict Criteria
| Criterion | Threshold |
|-----------|-----------|
| PnL preserved | ≥ 90% of baseline |
| Sharpe preserved | ≥ 95% of baseline |
| MaxDD reduced | ≤ baseline |
| Monthly consistency | within 5% of baseline |
| Trade reduction | < 40% reduction |

Pass 4/5 → deploy to prop simulation. Pass 3/5 → tune and re-test.

## Files

| File | Purpose |
|------|---------|
| `engine/strategy_controller.py` | Core controller class + portfolio config |
| `research/phase16_strategy_controller.py` | Simulation comparing baseline vs controlled |
| `docs/strategy_controller_spec.md` | This document |
| `research/phase16_strategy_controller_results.json` | Output metrics (auto-generated) |
