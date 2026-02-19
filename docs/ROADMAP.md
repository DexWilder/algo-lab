# Roadmap

## Phase 1 — Foundation (current)
- [x] Repo structure + conventions
- [x] Data contract + strategy contract
- [x] Engine stubs (backtest, prop eval, metrics, scoring)
- [x] Working indicator helpers (crossover/crossunder)
- [x] FMP data fetcher for MES 5m
- [x] Sample SMA crossover strategy
- [x] Pipeline runner (`run_all.py`)
- [x] Pine-to-Python conversion prompt

## Phase 2 — Backtest Engine
- [ ] Implement `run_backtest()` with fill-at-next-open logic
- [ ] Track equity curve, trade log, position state
- [ ] Support long-only, short-only, and both modes
- [ ] Implement `compute_metrics()` with real calculations

## Phase 3 — Prop Firm Evaluation
- [ ] Implement Apex 50K rules in `evaluate_prop()`
- [ ] Daily loss limit tracking
- [ ] Trailing drawdown calculation
- [ ] Profit target evaluation
- [ ] Pass/fail determination with detailed report

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
