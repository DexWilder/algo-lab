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

## Core Portfolio

| Strategy | Asset | Mode | Net PF | DSR | Status |
|----------|-------|------|--------|-----|--------|
| PB-Trend | MGC | Short | 1.85 | 0.993 SIGNIFICANT | candidate_validated |
| ORB-009 | MGC | Long | 1.83 | 1.000 SIGNIFICANT | candidate_validated |

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
- [x] Portfolio equity curve + drawdown overlap analysis
- [x] Top-trade removal robustness test
- [x] Walk-forward year splits
- [x] Parameter stability testing
- [x] Monthly consistency analysis
- [ ] Prop controller enforcement (stub only)
- [ ] Kelly / risk parity position sizing
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
- [ ] Strategy evolution engine
- [ ] Automatic combination testing

## Key Metrics (with costs)

| Metric | Value |
|--------|-------|
| Portfolio PnL (2-strategy) | ~$3,355 |
| Portfolio Sharpe (est.) | >2.0 |
| ORB-009 bootstrap PF CI | [1.07, 3.09] |
| PB-MGC bootstrap PF CI | [0.72, 4.77] |
| Drawdown overlap | 65-80% |

## Next Milestone

**Phase 5: Regime Modeling + Portfolio Optimization**
- Deploy ATR regime gate on ORB-009 (filter low-vol days)
- Run 2-strategy portfolio (without PB-MNQ-Long)
- Kelly sizing for PB-MGC-Short + ORB-009 MGC-Long
- Paper trade validation

## Completed Phases

| Phase | Status | Audit |
|-------|--------|-------|
| Phase 1 — Strategy Harvesting | Complete | docs/audits/phase_1_harvest.md |
| Phase 2 — Strategy Conversion | Complete | docs/audits/phase_2_conversion.md |
| Phase 3 — Baseline Backtesting | Complete | docs/audits/phase_3_baselines.md |
| Phase 4 — Engine Hardening | Complete | docs/audits/phase_4_hardening.md |

---
*Last updated: 2026-03-07*
