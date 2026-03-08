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

## Core Portfolio (Phase 5 — Regime-Gated)

| Strategy | Asset | Mode | Gated PF | Gated Sharpe | DSR | Status |
|----------|-------|------|----------|-------------|-----|--------|
| PB-Trend | MGC | Short | 2.36 | 5.27 | 0.952 SIG | candidate_validated |
| ORB-009 | MGC | Long | 2.07 | 3.93 | 1.000 SIG | candidate_validated |

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

### Sizing Research (Equal Weight baseline)

| Method | Sharpe | Calmar | MaxDD | Best For |
|--------|--------|--------|-------|----------|
| Equal Weight | 3.31 | 7.57 | $859 | Simplicity |
| Equal Risk Contribution | 3.20 | 8.98 | $559 | Prop accounts (hard DD limits) |
| Vol Target 10% | 3.31 | 7.57 | $2,182 | Growth (2.5 contracts) |

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
- [ ] Prop controller enforcement (stub only)
- [ ] Monte Carlo equity simulation
- [ ] HMM regime detection
- [ ] Alternative data filters (COT, GVZ)
- [ ] Execution infrastructure (Tradovate/Rithmic API)

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

## Next Milestone

**Phase 6: Paper Trade Validation + Execution Prep**
- Paper trade both strategies with regime gate active
- Monitor for edge decay (ORB-009 had weak 2024)
- Build prop controller enforcement
- Monte Carlo equity simulation for account sizing
- Connect execution infrastructure (Tradovate/Rithmic)

## Completed Phases

| Phase | Status | Audit |
|-------|--------|-------|
| Phase 1 — Strategy Harvesting | Complete | docs/audits/phase_1_harvest.md |
| Phase 2 — Strategy Conversion | Complete | docs/audits/phase_2_conversion.md |
| Phase 3 — Baseline Backtesting | Complete | docs/audits/phase_3_baselines.md |
| Phase 4 — Engine Hardening | Complete | docs/audits/phase_4_hardening.md |
| Phase 5 — Regime Modeling + Portfolio Optimization | Complete | docs/audits/phase_5_regime_portfolio.md |

---
*Last updated: 2026-03-08*
