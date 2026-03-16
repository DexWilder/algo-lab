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
- Strategy discovery and harvesting
- Backtesting and validation battery
- Walk-forward matrix (3-dimension robustness)
- Exposure clustering and genome mapping
- Strategy contribution analysis (marginal Sharpe)
- Kill criteria framework (4 automated triggers)
- Half-life monitoring (edge decay tracking)
- Health check system (60 automated failure-point checks)
- Strategy registry (57 strategies, institutional memory)

### Strategy Library
- Validated strategy implementations
- Categorized by family: trend, momentum/pullback, mean reversion, microstructure, volatility expansion, event/structural

### Portfolio Engine
- Portfolio construction
- Correlation analysis
- Risk modeling
- Prop account simulation
- Strategy contribution analysis (marginal Sharpe per strategy)
- Portfolio Regime Controller (activation scoring, state machine)

### Strategy Controller
- **Trade-Level Controller** (`engine/strategy_controller.py`): Regime gate, soft timing, portfolio coordination
- **Portfolio Regime Controller** (`research/portfolio_regime_controller.py`): Adaptive portfolio decision engine
  - Activation scoring model (9 weighted dimensions)
  - Strategy State Machine (8 states, explicit transitions)
  - Daily portfolio decision reports (JSON + Markdown)
  - Reason codes for every decision
- Regime detection (4-factor: ATR vol, trend EMA, realized vol, GRINDING persistence)
- Session logic (preferred/allowed windows)
- Strategy activation/deactivation

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
**Status: v1 COMPLETE**
- Correlation matrix (contribution analysis)
- Contribution analysis (marginal Sharpe per strategy)
- Portfolio diversification scoring (genome map, exposure clustering)
- Strategy contribution analysis
- Portfolio Regime Controller (activation scoring, state machine, daily reports)

### Phase 4 — Strategy Controller
**Status: v2 COMPLETE (v0.18)**
- Trade-level controller: regime gating, soft timing, portfolio coordination (v0.16)
- Portfolio Regime Controller: 9-dimension activation scoring model
- Strategy State Machine: 8 formal states, explicit transition rules
- Daily portfolio decision reports (JSON + Markdown)
- Reason codes for all controller decisions
- Registry schema v2.0 with controller state, history, scores
- Market structure awareness
- Regime gate optimization identified (+23.6% PnL recovery, queued for deploy)

### Phase 5 — Strategy Factory / Evolution Engine
**Goal**: Build a system that continuously generates, validates, and ranks new strategy candidates.

**Evolution stages:**
1. **Stage 1 — Guided Factory** (current): Human + Claude propose ideas, system validates automatically
2. **Stage 2 — Semi-Automatic Factory**: System proposes variants from gaps, parents, parameter families
3. **Stage 3 — Evolution Engine**: System continuously tests replacements, ranks incumbents, flags decay

**Core modules:**
1. **Candidate Generator** — produces new strategy variants constrained by:
   - Strategy family gaps (opportunity map)
   - Asset gaps (M2K/MCL underrepresented)
   - Session gaps (close, overnight)
   - Regime gaps (cells with no edge)
   - Validated parent strategies as building blocks
2. **Parent Mutation Engine** — systematic parameter/filter variations of proven parents
3. **Strategy Crossbreeding Engine** (v1 complete: XB-PB-EMA) — combine entry/exit/filter from different parents
4. **Portfolio Fit Scorer** — evaluates candidates by: PF, Sharpe, drawdown, correlation, family gap filled, session gap filled, asset diversification
5. **Evolution Loop** — monitor live strategies, detect decay, search for replacements, suggest improved variants

**Input sources:**
- Strategy family templates (trend, MR, vol expansion, event/structural)
- ICT concepts translated to mechanical rules
- TradingView scripts / community ideas
- Parent strategy mutations
- Portfolio gap-driven generation

**Pipeline:**
```
idea in → systematic generation → validation battery → ranking → portfolio fit check → probation → promotion or rejection
```

**What already exists:**
- Validation battery, DNA clustering, opportunity map, edge decay monitor
- Auto-review report, probation board, extended-history checks
- Crossbreeding engine (Phase 12)
- Strategy genome map

**What's needed:**
- Candidate generator with template system
- Portfolio fit scorer (beyond individual strategy validation)
- Automated gap-to-candidate pipeline

### Phase 5.5 — Strategy Harvest / Strategy Memory
**Status: COMPLETE**
Continuous expansion of the strategy knowledge base while optimizing the current portfolio.

**Strategy Registry** (`research/data/strategy_registry.json`, schema v1.1):
- Institutional memory of ALL strategy ideas — core, probation, rejected, ideas
- 57 strategies tracked (5 core, 9 probation, 23 ideas, 20 rejected)
- Kill flags: dilution, redundancy, decay, regime_failure
- Every idea preserved with metadata: family, asset, session, source, rule summary, validation scores

**Research Modules:**
| Module | Purpose |
|---|---|
| `batch_harvest_validation.py` | Multi-asset backtest with research gate (PF≥1.25, Sharpe≥1.4) |
| `walk_forward_matrix.py` | 3-dimension robustness (rolling windows, cross-asset, param sensitivity) |
| `strategy_genome_map.py` | Exposure clustering, diversity scoring (8 edge types) |
| `strategy_contribution_analysis.py` | Marginal Sharpe per strategy, correlation matrix |
| `strategy_kill_criteria.py` | 4-trigger kill framework (dilution, redundancy, decay, regime failure) |
| `strategy_half_life_monitor.py` | Rolling Sharpe/win rate/expectancy decay tracking |
| `fql_health_check.py` | 60 automated checks across 5 categories |
| `data_integrity_check.py` | Data quality validation (OHLC, duplicates, spikes, coverage) |
| `auto_report.py` | Daily/weekly research summaries |
| `harvest_scheduler.py` | Gap analysis, validation queue, research stats |

**Exposure Taxonomy (8 types):**
trend_persistence, mean_reversion, volatility_expansion, liquidity_sweep, gap_continuation, inventory_reversion, opening_range, session_structure

### Phase 5.6 — Autonomous Research Engine
**Status: ARCHITECTURE DEFINED, PARTIALLY BUILT**

Goal: Create a continuously operating quant lab with four parallel loops.

**Loop 1 — Discovery (Strategy Creation)**
Sources: TradingView, SSRN, strategy mutation, crossbreeding, genome gap targeting.
Schedule: Weekly harvests, continuous gap-driven generation.
Status: Harvest scheduler built, candidate generator needed.

**Loop 2 — Validation (Research Engine)**
Pipeline: backtest → parameter stability → walk-forward matrix → asset robustness → portfolio compatibility.
Status: BUILT. All validation modules operational.

**Loop 3 — Portfolio Evolution**
Tools: contribution analysis, exposure clustering, kill criteria, half-life monitor.
Actions: promote, demote, archive, prioritize research for missing edges.
Status: BUILT. First kill review completed — Donchian dilutive, GapMom-MNQ dead.

**Loop 4 — Health & Data (Safety System)**
Checks: data integrity, registry validation, scheduler health, automation monitoring.
Principle: No silent failures.
Status: BUILT. 60 automated checks, 52 PASS / 7 WARN / 1 FAIL.

**What's needed to make it fully autonomous:**
- Candidate Generator (automated gap-to-strategy pipeline)
- Scheduler wiring (cron-based loop execution)
- Dynamic Portfolio Allocation (regime-driven capital sizing)

### Phase 5.7 — Advanced Monitoring Modules
**Status: ROADMAP (not yet built)**

Three modules that move FQL from reactive diagnostics to proactive portfolio intelligence:

**Module 1 — Live Drift Monitor**
- Compare forward-test performance windows against backtest reference distributions
- Metrics tracked: rolling Sharpe, win rate, avg win/loss, max drawdown
- Alert tiers: NORMAL (within 1σ), DRIFT (>1σ deviation for 2+ weeks), ALARM (>2σ or structural break)
- Integration: feeds `half_life_status` and `recent_sharpe` signals to Portfolio Regime Controller
- Schedule: daily (after forward day completes)

**Module 2 — Execution Quality Monitor**
- Track slippage, fill rates, and execution timing across strategies
- Compare expected entry/exit prices (signal prices) vs actual fill prices
- Metrics: slippage per trade (ticks), slippage as % of edge, fill rejection rate
- Alert if slippage erodes >20% of expected edge for any strategy
- Integration: feeds `health_status` signal to Portfolio Regime Controller
- Schedule: daily

**Module 3 — Counterfactual Engine**
- Answer "what if we had followed the controller's recommendations?"
- Replay historical controller decisions against actual market outcomes
- Track: counterfactual PnL, strategies that would have been activated/deactivated, opportunity cost of delays
- Use cases: controller parameter tuning, threshold validation, confidence calibration
- Schedule: weekly (Saturday batch)

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
