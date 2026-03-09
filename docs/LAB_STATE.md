# Algo Lab State

*Auto-updated after each milestone. Single source of truth for lab status.*

## Pipeline Counts

| Stage | Count |
|-------|-------|
| Strategies harvested | 76 |
| Strategies converted | 4 |
| candidate_validated | 2 |
| Rejected | 2 |
| Effectively dead (costs) | 1 |

## Core Portfolio (Phase 6 — Deployment Validated)

| Strategy | Asset | Mode | Gated PF | Gated Sharpe | DSR | Status |
|----------|-------|------|----------|-------------|-----|--------|
| PB-Trend | MGC | Short | 2.36 | 5.27 | 0.952 SIG | deployment_ready |
| ORB-009 | MGC | Long | 2.07 | 3.93 | 1.000 SIG | deployment_ready |

**Regime Gate:** Skip low-vol days (ATR < 33rd percentile). Applied to both strategies.

### Portfolio Metrics (Gated, 2-Strategy)

| Metric | Value |
|--------|-------|
| Total PnL | $3,389 |
| Sharpe | 4.20 |
| MaxDD | $703 (1.40%) |
| Recovery Factor | 4.82 |
| Total Trades | 96 |
| DSR | 1.000 SIGNIFICANT |
| Bootstrap PF CI | [1.245, 3.613] |
| Daily PnL Correlation | -0.009 |
| Profitable Months | 13/19 (68%) |

### Monte Carlo Risk Gate

| Metric | Value |
|--------|-------|
| Median MaxDD (10K sims) | $516 |
| 99th percentile MaxDD | $1,034 |
| P(ruin at $4K DD) | 0.0% |
| P(ruin at $2K DD) | 0.0% |
| Prop survival (all configs) | 100% |

### Prop Account Simulation

| Config | Result | Skipped Trades | Halted Days |
|--------|--------|---------------|-------------|
| Lucid 100K ($4K DD) | PASSED, locked at $3,122 | 0 | 0 |
| Generic $50K ($2.5K DD) | PASSED | 0 | 0 |

### Sizing Research

| Method | Sharpe | Calmar | MaxDD | Best For |
|--------|--------|--------|-------|----------|
| Equal Weight | 3.31 | 7.57 | $859 | Simplicity |
| Equal Risk Contribution | 3.20 | 8.98 | $559 | Prop accounts |
| Vol Target 10% | 3.31 | 7.57 | $2,182 | Growth |

## Demoted / Removed

| Strategy | Asset | Mode | Net PF | DSR | Reason |
|----------|-------|------|--------|-----|--------|
| PB-Trend | MNQ | Long | 1.08 | 0.000 | Fails DSR, 38.5% friction impact |
| VWAP-006 | MES | Long | 1.05 | — | 74% PnL eaten by friction |
| ICT-010 | — | — | <1.0 | — | No edge on any asset/mode |

## Engine Capabilities

- [x] Fill-at-next-open backtest engine
- [x] Transaction costs (commission + slippage per symbol)
- [x] Bootstrap confidence intervals (10K resamples)
- [x] Deflated Sharpe Ratio (multiple testing correction)
- [x] ATR percentile regime detection (low/medium/high vol)
- [x] Regime gate testing (ungated vs gated comparison)
- [x] Portfolio equity curve + drawdown overlap analysis
- [x] Portfolio overlap realism (rolling correlation, trade overlap, DD overlap)
- [x] Sizing comparison (equal weight, ERC, vol target, fractional Kelly)
- [x] Top-trade removal robustness test
- [x] Walk-forward year splits
- [x] Parameter stability testing
- [x] Monthly consistency analysis
- [x] Prop controller enforcement (trailing DD, phases, daily limits)
- [x] Monte Carlo equity simulation (10K resamples)
- [x] Paper trade simulation with prop rules
- [x] Execution architecture design
- [ ] HMM regime detection
- [ ] Alternative data filters (COT, GVZ)
- [ ] Execution infrastructure (Tradovate/Rithmic API)
- [ ] Live execution adapter

## Research Infrastructure

- [x] Intake pipeline (76 scripts, 8 families)
- [x] Triage system (8 clusters, convert_now/hold/reject labels)
- [x] Component catalog (entries/exits/filters/risk/session)
- [x] Validation framework (8-criterion promotion standard)
- [x] Correlation analysis pipeline
- [x] Hardened baselines (gross vs net)
- [x] Research governance (LAB_STATE, research log, phase audits)
- [ ] Strategy evolution engine
- [ ] Automatic combination testing
- [ ] Diversification expansion (MES/MNQ strategies)

## Next Milestone

**Phase 7: Live Paper Trading + Diversification**
- Deploy on Tradovate sim for 2+ weeks
- Monitor for edge decay (ORB-009 2024 weakness)
- Add MES or MNQ strategy for gold-only diversification
- Begin strategy evolution engine design

## Completed Phases

| Phase | Status | Audit |
|-------|--------|-------|
| Phase 1 — Strategy Harvesting | Complete | docs/audits/phase_1_harvest.md |
| Phase 2 — Strategy Conversion | Complete | docs/audits/phase_2_conversion.md |
| Phase 3 — Baseline Backtesting | Complete | docs/audits/phase_3_baselines.md |
| Phase 4 — Engine Hardening | Complete | docs/audits/phase_4_hardening.md |
| Phase 5 — Regime Modeling + Portfolio Optimization | Complete | docs/audits/phase_5_regime_portfolio.md |
| Phase 6 — Deployment Validation | Complete | docs/audits/phase_6_deployment.md |

---
*Last updated: 2026-03-08*
