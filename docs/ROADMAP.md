# Roadmap

## Phase 1 — Foundation
- [x] Repo structure + conventions
- [x] Data contract + strategy contract
- [x] Engine stubs (backtest, prop eval, metrics, scoring)
- [x] Working indicator helpers (crossover/crossunder)
- [x] FMP data fetcher for MES 5m
- [x] Sample SMA crossover strategy
- [x] Pipeline runner (`run_all.py`)
- [x] Pine-to-Python conversion prompt

## Phase 2 — Backtest Engine
- [x] Implement `run_backtest()` with fill-at-next-open logic
- [x] Track equity curve, trade log, position state
- [x] Support long-only, short-only, and both modes
- [x] Implement `compute_metrics()` with real calculations

## Phase 2.5 — Intake Pipeline (v1.1 — portfolio-aware)
- [x] Intake directory structure (by strategy family)
- [x] Script manifest with duplicate detection
- [x] CLI manager (`intake/manage.py`) — add, list, update, score, review, search, stats, export
- [x] Status flow: raw → reviewed → cleaned → standardized → converted → backtested → validated → portfolio_tested → rejected/deployed
- [x] Script metadata template with portfolio-aware fields
- [x] Portfolio metadata: asset_candidates, preferred_timeframes, session_window, strategy_class, entry/risk/exit models, frequency
- [x] Weighted composite scoring (testability 25%, futures_fit 20%, prop_fit 20%, clarity 15%, conversion_difficulty 10%, diversification_potential 10%)
- [x] Lab role system: portfolio_role (core/enhancer/stack_component), layer (A/B/C), roster_target
- [x] Review log storage (`research/review_logs/`)
- [x] Portfolio notes storage (`research/portfolio_notes/`)
- [x] Build doctrine (`docs/BUILD_DOCTRINE.md`)
- [x] Strategy roster with named build targets (`research/roster.json`)
- [x] Algo profile template (`docs/algo_profile_template.json`)
- [x] Platform-agnostic design rule (strategy ↔ controller separation)
- [x] Controller layer (`controllers/`) with prop configs (Lucid 100K, Apex 50K, generic, cash)
- [x] PropController stub with evaluate() interface
- [ ] Clawbot intake spec (`docs/CLAWBOT_INTAKE_SPEC.md`)
- [ ] Clawbot/OpenClaw integration for TradingView harvesting
- [ ] Bulk import from Clawbot output

## Phase 3 — Risk Controllers (prop-agnostic)
- [ ] Implement generic PropController.evaluate() — trailing DD, daily loss, halts
- [ ] Config-driven: load any prop firm rules from JSON
- [ ] Cash account controller
- [ ] Portfolio controller (multi-strategy stacking, correlation limits)
- [ ] Monte Carlo pass/fail probability estimation

## Phase 4 — Strategy Pipeline
- [ ] Convert 5-10 TradingView strategies via LLM prompt
- [ ] Validate each against contract
- [ ] Run full pipeline and populate ranked.csv

## Phase 5 — Optimization
- [ ] Parameter sweep framework
- [ ] Walk-forward validation
- [ ] Out-of-sample testing
- [ ] Monte Carlo simulation for robustness

## Phase 6 — Live Integration
- [ ] Paper trading connector
- [ ] Real-time signal generation
- [ ] Risk management layer
- [ ] Alerting system
