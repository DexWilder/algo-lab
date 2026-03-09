# Algo Lab State

*Auto-updated after each milestone. Single source of truth for lab status.*

## Pipeline Counts

| Stage | Count |
|-------|-------|
| Strategies harvested | 91 (76 batch 1 + 15 batch 2) |
| Strategies converted | 9 |
| candidate_validated | 2 |
| Rejected | 5 |
| Pending validation | 2 (VIX Channel MES, Gap-Mom MGC) |
| Effectively dead (costs) | 2 |

## Core Portfolio (Phase 6 — Deployment Validated)

| Strategy | Asset | Mode | Gated PF | Gated Sharpe | DSR | Status |
|----------|-------|------|----------|-------------|-----|--------|
| PB-Trend | MGC | Short | 2.36 | 5.27 | 0.952 SIG | deployment_ready |
| ORB-009 | MGC | Long | 2.07 | 3.93 | 1.000 SIG | deployment_ready |

**Regime Gate:** Per-strategy regime profiles via multi-factor RegimeEngine (Phase 8). Replaces single ATR gate.

### Portfolio Metrics (Regime-Profiled, 2-Strategy)

| Metric | Value |
|--------|-------|
| Total PnL | $3,661 |
| Sharpe | 4.46 |
| Calmar | 6.76 |
| MaxDD | $542 (1.08%) |
| Total Trades | 104 |
| DSR | 1.000 SIGNIFICANT |
| Bootstrap PF CI | [1.245, 3.613] |
| Daily PnL Correlation | -0.009 |
| Profitable Months | 13/25 (52%) |

### Portfolio Metrics (Regime-Profiled, 3-Strategy incl. VIX Channel)

| Metric | Value |
|--------|-------|
| Total PnL | $10,854 |
| Sharpe | 2.97 |
| Calmar | 9.77 |
| MaxDD | $1,111 |
| Total Trades | 413 |
| Profitable Months | 21/25 (84%) |
| *Note* | VIX Channel pending full promotion |

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
| RVWAP-MR | MES/MNQ/MGC | Both | <1.01 | — | No edge; VWAP mean reversion thesis fails on 5m |
| ORB-009 | MNQ | Long | 1.20 | — | Marginal after costs; below 1.3 threshold |
| Gap-Mom | MES | Long | 0.24 | — | No edge on index futures |
| Gap-Mom | MNQ | Long | 0.48 | — | No edge on index futures |
| ORION Vol | MES/MNQ | Both | <1.1 | — | No edge on indices; marginal on MGC |
| BB/KC Squeeze | MES | Both | 1.24 | — | 50% friction impact (1,295 trades × $3.74/RT) |

## Major Insights

1. **Strategies occupy different volatility niches.** PB thrives in HIGH_RV, ORB in TRENDING, VIX Channel in LOW_VOL. A global gate applied uniformly is structurally wrong.
2. **Regime-profiled portfolio dominates ATR-gated.** 2-strat Calmar 3.91→6.76, MaxDD $859→$542. 3-strat monthly consistency 76%→84%.
3. **Lab architecture transition:** strategy research system → portfolio intelligence system. Signal pipeline: `strategy → regime engine → portfolio allocation → prop controller → execution`.
4. **VIX Channel is a regime complement**, not a standalone powerhouse. Its value is filling the LOW_VOL gap where PB and ORB are inactive.
5. **Research philosophy shift:** Future harvesting prioritizes regime gap coverage over standalone PF. A PF 1.3 strategy filling an empty regime cell beats a PF 1.8 strategy duplicating existing coverage. See `docs/research_gap_map.md` for regime coverage matrix.
6. **DNA clustering confirms genuine structural diversity.** All 3 validated strategies are singletons — different entry types, risk models, and regime preferences. No near-duplicates detected. 2 rejected strategies identified as component donors (ORION compression filters, BBKC momentum states). See `research/dna/dna_report.md`.

## Engine Capabilities

- [x] Fill-at-next-open backtest engine
- [x] Transaction costs (commission + slippage per symbol)
- [x] Bootstrap confidence intervals (10K resamples)
- [x] Deflated Sharpe Ratio (multiple testing correction)
- [x] ATR percentile regime detection (low/medium/high vol)
- [x] Multi-factor regime engine (ATR + trend + realized vol)
- [x] Per-strategy regime activation profiles
- [x] Regime-aware portfolio simulation
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
- [x] Execution adapter skeleton (Tradovate, no-op mode)
- [x] Paper trade signal/equity logger
- [x] Strategy DNA profiling + structural clustering
- [ ] HMM regime detection
- [ ] Alternative data filters (COT, GVZ)
- [ ] Execution infrastructure (Tradovate/Rithmic API)
- [ ] Live execution adapter

## Research Infrastructure

- [x] Intake pipeline (91 scripts, 8 families — batch 1 + batch 2)
- [x] Triage system (8 clusters, convert_now/hold/reject labels)
- [x] Component catalog (entries/exits/filters/risk/session)
- [x] Validation framework (8-criterion promotion standard)
- [x] Correlation analysis pipeline
- [x] Hardened baselines (gross vs net)
- [x] Research governance (LAB_STATE, research log, phase audits)
- [x] Strategy DNA profiling (9 strategies fingerprinted, 8 clusters, 3 true diversifiers)
- [ ] Strategy evolution engine
- [ ] Automatic combination testing
- [x] Diversification expansion (MES/MNQ strategies — VIX Channel candidate found)

## Next Milestone

**Phase 9: Live Paper Trading + Strategy Evolution** (PENDING)
- Paper trading plan ready: `docs/PHASE_7_PAPER_TRADING_PLAN.md`
- Pending: Tradovate sim account setup for live paper trading
- Execution skeleton ready: `execution/tradovate_adapter.py` + `execution/signal_logger.py`
- Evolution engine spec: `docs/EVOLUTION_ENGINE_SPEC.md` (design only)
- **VIX Channel MES-Both:** Passes 5/8 robustness criteria, fails 3 (net PF 1.298, DSR, MC ruin)
  - Remains pending_validation — strong diversifier (r=-0.024) but doesn't meet full promotion bar
  - Regime-profiled 3-strat portfolio: Calmar 9.77, 84% monthly consistency
  - Per-strategy regime profiles replace global ATR gate
- 9 strategies converted total, 5 rejected, 2 pending validation
- Research gaps documented: `docs/research_gap_map.md`

## Completed Phases

| Phase | Status | Audit |
|-------|--------|-------|
| Phase 1 — Strategy Harvesting | Complete | docs/audits/phase_1_harvest.md |
| Phase 2 — Strategy Conversion | Complete | docs/audits/phase_2_conversion.md |
| Phase 3 — Baseline Backtesting | Complete | docs/audits/phase_3_baselines.md |
| Phase 4 — Engine Hardening | Complete | docs/audits/phase_4_hardening.md |
| Phase 5 — Regime Modeling + Portfolio Optimization | Complete | docs/audits/phase_5_regime_portfolio.md |
| Phase 6 — Deployment Validation | Complete | docs/audits/phase_6_deployment.md |
| Phase 7 — Diversification + Paper Trading Prep | Complete | (entries in research_log.md) |
| Phase 8 — Regime Engine + Portfolio Intelligence | Complete | docs/audits/phase_8_regime_engine.md |
| Phase 8.5 — Strategy DNA Clustering | Complete | docs/audits/phase_8_5_dna_clustering.md |

---
*Last updated: 2026-03-09*
