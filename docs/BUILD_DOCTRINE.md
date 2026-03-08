# Algo Lab Build Doctrine

Every strategy in the lab is judged on two axes: standalone power and portfolio power.

## Two Judgment Axes

### 1. Standalone Power — Can it survive and produce on its own?

- Clear, identifiable edge
- Sufficient trade frequency
- Controlled drawdown
- Robust across assets or regimes
- Prop-rule compatible

### 2. Portfolio Power — Does it make the full stack stronger?

- Low correlation to existing algos
- Different session behavior
- Different failure mode
- Different entry logic
- Different market regime strength

A strategy that is only "pretty good" alone can still be extremely valuable if it fills a portfolio gap.

## What "Most Powerful" Means

The strongest algo is not just the highest return. It scores highest across:

- Expectancy
- Drawdown control
- Prop survivability
- Consistency rule friendliness
- Robustness across test windows
- Low fragility
- Stackability with other systems

Optimizing for: **power + survivability + stack synergy**.

## Three Strategy Layers

### Layer A — Core Standalone Killers

Flagship systems strong enough to trade alone.

Examples: opening breakout engine, trend pullback engine, VWAP reversion engine, liquidity sweep engine.

### Layer B — Specialist Enhancers

Not necessarily the biggest earners alone, but they improve the portfolio.

Examples: defensive low-frequency mean reversion, high-volatility expansion strategy, post-open continuation filter, trend-day-only overlay.

### Layer C — Master Stack

Final prop deployment engine:

- Regime aware
- Asset aware
- Session aware
- Risk aware
- Built from the best pieces of A and B

## Required Algo Profile

Every algo must eventually have:

### Identity

- Strategy ID (e.g. ALGO-CORE-ORB-001)
- Version
- Strategy class
- Asset variants
- Portfolio role (core / enhancer / stack component)
- Layer (A / B / C)

### Logic Profile

- Entry model
- Exit model
- Risk model
- Regime fit
- Session fit
- Trade frequency

### Performance Profile

- Profit factor (PF)
- Sharpe ratio
- Expectancy
- Max drawdown
- Trade count
- Pass probability (prop eval)
- Fail probability
- Payout probability

### Failure Profile

- Invalidation reason
- Primary failure mode
- Fragility notes
- Overlap risk with other algos

## Research Mission — Three Build Tracks

### Product 1 — Best Standalone Breakout Algo
ORB / session breakout / continuation focused.

### Product 2 — Best Standalone Reversion Algo
VWAP / sweep / mean-reversion focused.

### Product 3 — Best Prop Master Stack
Combination of breakout + reversion + trend + filter layers.

Target: one elite breakout weapon, one elite reversion weapon, one elite portfolio engine.

## Platform-Agnostic Design Rule

Strategies must remain pure trading logic. Prop firm rules, account constraints, and portfolio allocation live in separate controllers.

### Three Execution Layers

```
Strategy Engine  →  pure signals (entry, exit, stop, target, filters)
       ↓
Risk Controller  →  adapts signals to account environment
       ↓
Execution        →  sends orders to broker/platform
```

### Layer 1 — Strategy Engine (Universal)

Contains ONLY:
- Entry logic
- Exit logic
- Stop logic
- Target logic
- Filters (session, volatility, regime, MTF)

No prop rules. No account sizing. No drawdown limits. The same strategy runs identically on MES, MNQ, MGC, prop accounts, or cash accounts.

### Layer 2 — Risk Controller (Environment-Specific)

Adapts strategy signals to the trading environment:

- **Generic Prop Controller** — trailing DD, daily loss limit, contract caps, consistency rules (configurable per firm)
- **Cash Account Controller** — % risk per trade, max leverage, portfolio exposure
- **Portfolio Controller** — multi-strategy stacking, capital allocation, correlation limits

Controller configs are swappable without touching strategy code:

```json
{
  "account_size": 100000,
  "trailing_drawdown": 4000,
  "daily_loss_limit": 2000,
  "max_contracts": 5,
  "consistency_rule": 0.20
}
```

### Layer 3 — Execution Adapter (Broker-Specific)

Translates controlled orders to broker API calls. Separate from strategy and controller logic.

### Why This Matters

- If a prop firm changes rules → swap the controller config, not the algo
- If you move from prop to cash → swap the controller, not the algo
- Strategy library remains valid across all environments
- Enables questions like: "which algo passes the most prop firms?" and "which portfolio scales best on cash?"

### Rule

> **Never embed prop rules into strategies. Strategies output signals. Controllers apply risk rules.**

## Core Principle

> "Import many, trust few, validate all."

The advantage comes from structure, iteration, ruthless testing, version control, learning from every result, and stacking edges intelligently.
