# FQL System Architecture

*Definitive reference for the Fisher Quant Lab platform stack.*
*Last updated: 2026-03-15*

---

## System Overview

Fisher Quant Lab (FQL) is the research and trading division of Fisher Intelligence Systems Holdings (FISH). It is a systematic futures trading platform operating on micro contracts (MES, MNQ, MGC, MCL, M2K) and expanding into FX (6E, 6J, 6B) and rates (ZN, ZB, ZF).

For the long-term mission and business vision, see `docs/FISH_VISION.md`.

The system is organized into seven layers, each with strict separation of concerns.

```
Layer 7: Safety & Monitoring
Layer 6: Orchestration & Automation
Layer 5: Strategy Controller
Layer 4: Portfolio Engine
Layer 3: Strategy Library
Layer 2: Research Lab
Layer 1: Data Layer
```

---

## Layer 1: Data Layer

Market data ingestion, storage, and quality assurance.

**Built modules:**
- `data/processed/` -- 5-minute OHLCV bars for MES, MNQ, MGC, M2K, MCL
- `data/databento/` -- Databento market data feeds
- `data/raw/` -- Raw market data archives
- `scripts/update_daily_data.py` -- Automated data fetch and processing
- `research/data_integrity_check.py` -- Data quality validation

**Data sources:**
- Databento (primary, API-driven)
- TradingView (historical imports via `data/load_tv.py`)
- FMP (fundamentals via `data/fetch_fmp.py`)

**State files:**
- `state/data_update_state.json` -- Last sync timestamp
- `state/account_state.json` -- Forward trading account state

---

## Layer 2: Research Lab

Strategy discovery, backtesting, validation, and institutional memory.

**Core modules:**
- `engine/backtest.py` -- Fill-at-next-open backtesting engine
- `research/validation/run_validation_battery.py` -- 10-criterion validation suite
- `research/walk_forward_matrix.py` -- 3-dimension robustness testing
- `research/strategy_genome_map.py` -- Behavioral fingerprinting and exposure clustering
- `research/strategy_registry.py` -- Central registry (57 strategies tracked)
- `research/batch_harvest_validation.py` -- Cheap validation filter for candidates

**Discovery and evolution:**
- `research/harvest_scheduler.py` -- Gap analysis and candidate surfacing
- `research/crossbreeding/crossbreeding_engine.py` -- Component recombination
- `research/evolution/evolution_scheduler.py` -- Parameter mutation and selection
- `research/opportunity_scanner.py` -- Portfolio gap identification

**Research pipeline stages:**
1. Strategy intake and triage
2. Pine-to-Python conversion
3. Baseline backtest
4. Phase 10 evaluation (3 assets x 3 modes + regime + correlation)
5. Strategy genome mapping
6. Portfolio fitness test
7. Validation battery (10 criteria)
8. Promotion decision (parent / probation / rejected)
9. Continuous refinement (exit evolution, regime gating)
10. Deployment

See `docs/research_pipeline.md` for full stage definitions.

---

## Layer 3: Strategy Library

Validated strategy implementations with standardized interfaces.

**Interface contract:** `generate_signals(df) -> df` with columns: signal, exit_signal, stop_price, target_price

**Current core strategies (6 active):**

| ID | Family | Asset | Direction | PnL Share |
|----|--------|-------|-----------|-----------|
| VWAP-MNQ-Long | vwap_trend | MNQ | Long | 32.4% |
| ORB-MGC-Long | orb_009 | MGC | Long | 16.9% |
| BB-EQ-MGC-Long | bb_equilibrium | MGC | Long | 16.6% |
| XB-PB-EMA-MES-Short | xb_pb_ema_timestop | MES | Short | 15.5% |
| Donchian-MNQ-Long | donchian_trend | MNQ | Long | 13.9% |
| PB-MGC-Short | pb_trend | MGC | Short | 4.8% |

**Strategy families:** trend, momentum/pullback, mean reversion, microstructure, volatility expansion, event/structural

**Registry:** `research/data/strategy_registry.json` (v2.0 schema, 57 strategies including probation, testing, idea, and rejected)

**Design rule:** Strategies output pure signals only. No prop rules, no account sizing, no risk logic in strategy code. See `docs/BUILD_DOCTRINE.md`.

---

## Layer 4: Portfolio Engine

Portfolio construction, contribution analysis, and risk modeling.

**Built modules:**
- `research/strategy_contribution_analysis.py` -- Marginal Sharpe contribution per strategy
- `research/counterfactual_engine.py` -- Opportunity-cost analysis (6 metrics: marginal Sharpe, marginal DD, overlap cost, displaced opportunity, slot efficiency, blocked-signal opportunity)
- `research/portfolio_correlation_matrix.py` -- Strategy correlation analysis
- `research/portfolio_opportunity_map.py` -- Asset/session/regime opportunity discovery
- `research/prop_firm_optimizer.py` -- Prop account risk optimization
- `research/prop_portfolio_simulator.py` -- Prop account PnL simulation

**Key outputs:**
- `research/data/portfolio_activation_matrix.json` -- Daily controller decisions
- `research/reports/daily_decision_*.json` and `*.md` -- Daily portfolio decision reports

---

## Layer 5: Strategy Controller

Two-tier control system: portfolio-level decisions and trade-level execution.

### Portfolio Regime Controller (`research/portfolio_regime_controller.py`)

Adaptive portfolio decision engine that runs daily.

**10-dimension activation scoring model:**

| Dimension | Weight | Source |
|-----------|--------|--------|
| Regime fit | 0.20 | regime_engine |
| Half-life | 0.20 | strategy_half_life_monitor |
| Contribution | 0.15 | strategy_contribution_analysis |
| Redundancy | 0.10 | genome overlap detection |
| Health | 0.10 | fql_health_check |
| Kill criteria | 0.10 | strategy_kill_criteria |
| Session drift | 0.05 | live_drift_monitor |
| Time-of-day | 0.03 | session analysis |
| Asset fit | 0.04 | asset correlation |
| Recent stability | 0.03 | rolling performance |

**Action thresholds:** FULL_ON >= 0.70, REDUCED_ON >= 0.55, PROBATION >= 0.40, OFF >= 0.30, DISABLE >= 0.20

**Configuration:** `research/controller_config.yaml`

### Strategy State Machine (`research/strategy_state_machine.py`)

8 formal states with explicit transition rules:
```
VALIDATED -> PAPER -> ACTIVE -> ACTIVE_REDUCED -> PROBATION -> DISABLED -> ARCHIVED
                                                                      -> RESURRECTION_CANDIDATE
```

Transitions are signal-driven. The state machine evaluates but does not mutate; the controller applies transitions.

### Trade-Level Controller (`engine/strategy_controller.py`)

Real-time signal filtering at execution time:
- Regime gates (preferred/allowed/avoid per strategy)
- Soft timing (session alignment)
- Portfolio coordination
- Prop controller integration

### Regime Engine (`engine/regime_engine.py`)

4-factor regime detection:
- ATR-based volatility regime (HIGH_VOL, NORMAL, LOW_VOL)
- Trend EMA (TRENDING, RANGING)
- Realized volatility regime (HIGH_RV, NORMAL_RV, LOW_RV)
- GRINDING persistence score

---

## Layer 6: Orchestration & Automation

Scheduled execution, daily operations, and system management.

**Scheduler:** `research/fql_research_scheduler.py` -- 19 automated jobs

| Cadence | Jobs |
|---------|------|
| Daily (6) | health_check, half_life, contribution, activation_matrix, decision_report, drift_monitor |
| Twice-weekly (2) | candidate_scan, baseline_backtest |
| Weekly (4) | walk_forward, kill_criteria, registry_update, auto_report |
| Monthly (3) | genome_cluster, full_contribution, half_life_review |
| Quarterly (2) | gap_analysis, research_targeting |

**Automation stack:**
- `scripts/run_fql_daily.sh` -- Wrapper script with lockfile, explicit PATH, failure logging
- `scripts/com.fql.daily-research.plist` -- macOS launchd agent (weekdays 17:30 ET)
- `~/.zshrc` -- Backup reminder if scheduler hasn't run

**Operational tools:**
- `scripts/forward_health_report.py` -- Forward-test health check
- `scripts/forward_scorecard.py` -- Performance scorecard
- `scripts/start_forward_day.sh` -- Morning startup routine
- `scripts/dashboard.py` -- Health dashboard
- `scripts/monitor.py` -- System monitoring

**Forward testing:** `research/phase17_paper_trading/` -- 100+ days of daily logs, equity tracking, regime state

---

## Layer 7: Safety & Monitoring

Drift detection, execution quality, system integrity, and safety controls.

**Built and running:**
- `research/live_drift_monitor.py` -- Forward-test drift detection (6 dimensions, 3 alert tiers: NORMAL/DRIFT/ALARM)
- `execution/execution_quality_monitor.py` -- Slippage, latency, fill quality tracking
- `research/counterfactual_engine.py` -- Opportunity-cost analysis
- `research/fql_health_check.py` -- 60-point automated failure detection
- `research/strategy_half_life_monitor.py` -- Edge decay tracking (4 statuses: HEALTHY/MONITOR/DECAYING/ARCHIVE_CANDIDATE)
- `research/strategy_kill_criteria.py` -- Automated kill triggers (4 dimensions: redundancy, dilution, decay, volatility collapse)
- `research/drift_alerts.py` -- Alert generation

**Paper trading safety (built):**
- Kill switch: daily loss $800, trailing DD $4K, 8 consecutive losses, correlated loss
- Duplicate bar protection
- State persistence across restarts

**Broker-connected safety (designed, not yet built):**
- Watchdog heartbeat (60s checks)
- Position reconciliation (5-minute checks)
- Order safety layer (unique IDs, duplicate lockout)
- Failsafe controller
- Incident logger

See `docs/safety_architecture.md` and `docs/watchdog_architecture.md` for broker-phase specifications.

---

## Cross-Cutting: Execution Layer

Broker connectivity and order management.

**Built:**
- `execution/tradovate_adapter.py` -- Tradovate API adapter (skeleton)
- `execution/signal_logger.py` -- Trade signal logging
- `engine/paper_trading_engine.py` -- Forward/paper trading engine
- `controllers/prop_controller.py` -- Prop account risk/sizing management
- `controllers/prop_configs/` -- 9 account configuration variants

**Design:** Strategies produce signals. Controllers apply risk rules. Adapters talk to brokers. See `docs/AUTOMATION_ARCHITECTURE.md`.

---

## Key Configuration Files

| File | Purpose |
|------|---------|
| `research/controller_config.yaml` | Portfolio Regime Controller scoring weights, thresholds, transition rules |
| `research/data/strategy_registry.json` | Central strategy registry (57 strategies) |
| `controllers/prop_configs/*.json` | Prop account configurations |
| `.env` | API keys (Databento, FMP) |
| `requirements.txt` | Python dependencies |

---

## Architectural Priorities (Next Builds)

1. **Portfolio Regime Allocation** -- Move from binary select to regime/session/crowding-aware sizing
2. **Strategy Evolution Engine** -- Automated refinement, crossbreeding, and gap-targeted generation
3. **Safety/Watchdog Layer** -- Required before unattended broker-connected execution
4. **Unified Operations Dashboard** -- Single-pane view of all system health metrics

---

## Maintenance

These documents must be periodically updated as the platform evolves. Any major module added to FQL must be reflected in this architecture documentation.

**Related docs:**
- `docs/BUILD_DOCTRINE.md` -- Build philosophy and strategy evaluation
- `docs/OPERATING_RULES.md` -- Non-negotiable operating rules
- `docs/research_pipeline.md` -- Research stage definitions
- `docs/AUTOMATION_ARCHITECTURE.md` -- Execution layer design
- `docs/safety_architecture.md` -- Safety specifications
- `docs/strategy_controller_spec.md` -- Controller specifications
