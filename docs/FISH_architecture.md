# FISH System Architecture

## Naming Conventions

### Parent Organization
**Fisher Intelligence Systems Holdings (FISH)**
- Long-term family quant firm structure
- Parent system managing research, portfolio trading, capital growth

### Research Division
**Fisher Quant Lab (FQL)**
- Research and strategy development division of FISH
- All research tools, strategy discovery, and validation live inside FQL

---

## Architecture Stack

```
FISH (Fisher Intelligence Systems Holdings)
|
+-- FQL Research Lab
|
+-- Strategy Library
|
+-- Portfolio Engine
|
+-- Strategy Controller
|
+-- Execution System
|
+-- Safety & Monitoring
```

### FQL Research Lab
- Strategy discovery
- Backtesting
- Validation battery
- Research tools (opportunity scanner, genome map, contribution analysis)

### Strategy Library
- Validated strategy implementations
- Categorized by family: trend, momentum/pullback, mean reversion, microstructure, volatility expansion, event/structural

### Portfolio Engine
- Portfolio construction
- Correlation analysis
- Risk modeling
- Prop account simulation

### Strategy Controller
- Regime detection (4-factor: ATR vol, trend EMA, realized vol, GRINDING persistence)
- Session logic (preferred/allowed windows)
- Strategy activation/deactivation
- Dynamic risk adjustments

### Execution System
- Broker connectivity (future)
- Order management
- Position tracking

### Safety & Monitoring
- Watchdog systems (see docs/watchdog_architecture.md)
- Fail safes (SAFE_MODE)
- Alerts
- System health monitoring

**AI analysis remains outside the live execution loop.**

---

## Development Roadmap

### Phase 1 — Research Lab Foundation
**Status: COMPLETE**
- Strategy intake
- Backtesting engine (fill-at-next-open)
- Validation battery (6 tests, 10 criteria)
- Monte Carlo simulation
- Research diagnostics

### Phase 2 — Strategy Library Construction
**Status: ACTIVE**
- Goal: Build first diversified portfolio
- Target: 10-12 strategies across families
- Families: Trend, Momentum/Pullback, Mean Reversion, Microstructure, Volatility Expansion, Event/Structural
- Current: 6 core + 5 probation

### Phase 3 — Portfolio Engine
- Correlation matrix
- Contribution analysis
- Portfolio diversification scoring
- Prop account simulation
- Drawdown modeling

### Phase 4 — Strategy Controller
**Status: v1 COMPLETE (v0.16)**
- Volatility regime gating
- Trend strength evaluation
- Time-of-day session logic
- Market structure awareness
- Regime gate optimization identified (+23.6% PnL recovery, queued for deploy)

### Phase 5 — Strategy Factory / Evolution Engine
- Candidate generator
- Parent mutation engine
- Strategy crossbreeding engine (v1 complete: XB-PB-EMA)
- Portfolio fit scoring
- Evolution loop

### Phase 6 — Forward Testing
**Status: ACTIVE (v0.17)**
- Live market data -> forward runner -> simulated trades -> trade logs
- Daily reports + weekly research summaries
- No broker connection yet

### Phase 7 — Execution System
- Broker integration
- Automated trading
- Execution runs on VPS
- AI remains outside live trading loop

### Phase 8 — Safety and Monitoring
- System watchdog (architecture spec complete: docs/watchdog_architecture.md)
- Heartbeat monitoring
- Failure detection (12 scenarios documented)
- Safe shutdown procedures
- Alerting system

### Phase 9 — Prop Capital Extraction
- Prop firm accounts -> validated strategies -> payouts -> capital accumulation
- Prop configs: lucid_100k, lucid_50k, apex_50k, apex_100k, tradeify_50k, generic, cash_account

### Phase 10 — Cash Portfolio Expansion
- Deploy using personal capital
- Expansion targets: futures, equities, crypto

### Phase 11 — Family Quant Firm (FISH)
- FISH becomes parent system managing research, portfolio trading, capital growth
- Goal: system that continues operating across generations
