# Algo Lab State

*Auto-updated after each milestone. Single source of truth for lab status.*

## Pipeline Counts

| Stage | Count |
|-------|-------|
| Strategies harvested | 91 (76 batch 1 + 15 batch 2) |
| Strategies converted | 12 |
| candidate_validated | 2 |
| Phase 10 candidates | 3 (Donchian MNQ, Keltner MNQ, VWAP Trend MNQ) |
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

### Portfolio Metrics (Phase 10, 4-Strategy: PB + ORB + VWAP Trend + Donchian GRINDING)

| Metric | 2-Strat Baseline | 3-Strat (+VWAP) | 4-Strat (Full) |
|--------|-----------------|-----------------|----------------|
| Total PnL | $3,355 | $9,131 | $11,113 |
| Sharpe | 3.31 | 3.02 | 3.15 |
| Calmar | 3.91 | 6.76 | 7.52 |
| MaxDD | $859 | $1,351 | $1,477 |
| Trades | 134 | 329 | 377 |
| Profitable Months | 15/25 (60%) | 18/25 (72%) | 20/25 (80%) |

**Correlation Matrix (all near-zero):**

|  | PB | ORB | VWAP | DONCH |
|--|-----|------|------|-------|
| PB | 1.000 | 0.014 | -0.087 | 0.061 |
| ORB | 0.014 | 1.000 | 0.003 | -0.019 |
| VWAP | -0.087 | 0.003 | 1.000 | 0.055 |
| DONCH | 0.061 | -0.019 | 0.055 | 1.000 |

**Per-Strategy Contribution:** VWAP 52% ($5,776), ORB 24% ($2,679), Donchian 18% ($1,981), PB 6% ($676).

*Note: VWAP Trend and Donchian pending full validation battery. Donchian uses GRINDING persistence filter.*

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
7. **Evolution cannot create structural novelty from structurally similar parents.** Batch 2 proved mutations (filter stacking, risk swaps, filter relaxation) optimize existing strategies but cannot discover new strategy families. The 7 THIN regime cells require genuinely new parents, not remixes.
8. **Trend persistence separates grind trends from breakouts.** Added GRINDING/CHOPPY classification (Factor 4). 11% of days are GRINDING — sustained directional drifts where trend-followers should excel. Current strategies have no GRINDING specialist.
9. **Trade duration is a strategy DNA fingerprint.** PB holds 3 bars (scalper), ORB holds 28 bars (intraday swing), VIX holds 42 bars (day swing). True trend-followers should hold 60-200+ bars — a completely different structural profile.
10. **HIGH_VOL_TRENDING_LOW_RV is a $1,399 portfolio bleed**, not just a gap. It's the single most negative PnL cell in the regime grid. Fixing it is the highest-value next step.
11. **The HIGH_VOL + LOW_RV bleed is structural, not an entry model problem.** Three entry types tested (breakout, channel, pullback) all produce similar target cell results (-$823, +$13, -$301). Wide stops + small moves = fundamental contradiction.
12. **VWAP Trend Continuation is the strongest new system.** PF=1.67, Sharpe=2.62, near-zero correlation with all existing strategies. Pullback entries produce better risk-adjusted returns than breakout entries on 5m bars.
13. **On 5m bars, any "close below X" exit degenerates into a scalper.** Keltner EMA exit and VWAP cross exit both produce 10-14 bar holds. Only pure ATR trailing stops achieve 60+ bar holds. Exit mechanism matters more than entry for hold duration.
14. **4-strategy portfolio triples PnL with maintained Sharpe.** PB+ORB+VWAP+Donchian(GRINDING): $11,113 PnL, 3.15 Sharpe, 7.52 Calmar, 80% profitable months. All pairwise correlations near zero. This is the target structure.

## Engine Capabilities

- [x] Fill-at-next-open backtest engine
- [x] Transaction costs (commission + slippage per symbol)
- [x] Bootstrap confidence intervals (10K resamples)
- [x] Deflated Sharpe Ratio (multiple testing correction)
- [x] ATR percentile regime detection (low/medium/high vol)
- [x] Multi-factor regime engine (ATR + trend + realized vol + trend persistence)
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
- [x] Portfolio fitness function (5-component scoring: PnL, correlation, DD, regime, monthly)
- [x] Machine-readable regime coverage map (18-cell vol×trend×rv grid)
- [x] Trend persistence scoring (GRINDING vs CHOPPY — separates grind trends from breakout trends)
- [x] Trade duration analysis (median/avg bars per trade — classifies strategy holding profiles)
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
- [x] Strategy evolution engine (15 candidates, 4 mutation types, template-based generation)
- [x] Automatic combination testing (evolution scheduler — mutations + backtest + DNA novelty + regime)
- [x] Diversification expansion (MES/MNQ strategies — VIX Channel candidate found)

## Evolution Engine (Phase 9 + 9.5)

- **Mutations library:** 6 reusable components (compression, squeeze, momentum_state, sweep, ema_alignment, range_fade)
- **Evolution queue:** Batch 1: 15 recipes (generic) | Batch 2: 10 recipes (regime-gap-targeted)
- **Pipeline:** generate → backtest → quality gate → **FAIL_TARGET** → DNA novelty → **portfolio fitness** → regime → stats
- **Safeguards:** ATR stop cap 3.5×, ATR target cap 5.0×, FAIL_TARGET gate (≥10 trades in target regime)
- **Batch 1 results:** 2 promoted, 13 rejected, 0 errors
  - `vix_atr_stops` — VIX + ATR risk model, MNQ-long PF=1.36, 263 trades, portfolio fitness 5.88/10 (portfolio_useful)
  - `pb_relaxed_filters` — PB with relaxed gates, MES-short PF=1.25, 274 trades, portfolio fitness 2.99/10 (portfolio_redundant)
- **Batch 2 results (regime-gap-targeted):** 4 promoted, 6 rejected (2 FAIL_TARGET, 3 DNA duplicate, 1 low trades)
  - `vix_wide_atr_low_rv` — ATR stops 2.0×/3.0×, MES-short PF=1.34, 240 trades, 15 trades in target (HIGH_VOL_TRENDING_LOW_RV), portfolio 2.70/10
  - `vix_tight_targets` — ATR stops 1.0×/1.0× for RANGING, MES-long PF=1.37, 263 trades, 54 trades in RANGING, portfolio 3.75/10
  - `pb_shallow_pullback` — Relaxed PB filters, MES-short PF=1.25, 274 trades, 18 trades in target, portfolio 3.40/10
  - `orb_relaxed_entry` — Relaxed ORB filters, MGC-long PF=1.72, 134 trades, 17 trades in RANGING, portfolio 3.30/10
- **Batch 2 key findings:** (1) FAIL_TARGET caught 2 candidates that passed quality gate but had 0-2 trades in target regime — the gate works. (2) VIX add_filter mutations consistently hit DNA duplicate — VIX DNA is too close to existing catalog. (3) orb_range_fade had PF=4.83 but only 9 trades — shows promise, needs more data. (4) All 4 promoted scored portfolio_redundant — no portfolio_star emerged from Batch 2.
- **Portfolio fitness function (Phase 9.5):** 5-component scorer (PnL 0.25, correlation 0.25, DD improvement 0.20, regime coverage 0.20, monthly consistency 0.10). Validates against ground truth — vix_atr_stops scores 2× higher than pb_relaxed_filters.
- **Regime coverage map (Phase 9.5):** Machine-readable 18-cell (vol×trend×rv) JSON. 5 STRONG, 6 COVERED, 7 THIN, 0 MISSING cells. Guides future harvesting and evolution toward gap filling.
- **Key finding:** Standalone PF is the wrong objective. Portfolio contribution (PnL + correlation + DD + regime) separates genuine improvers from redundant clones.
- **Artifacts:** `research/evolution/` — portfolio_fitness.py, mutations.py, evolution_queue.json, evolution_queue_batch2.json, evolution_scheduler.py, generated_candidates/, evolution_results.json, evolution_results_batch2.json | `research/regime/` — regime_coverage_map.py, regime_coverage.json

## Next Milestone

**Phase 10: New Parent Discovery — Regime-Gap-Targeted Strategy Families** (PENDING)

Evolution Batches 1-2 proved existing parents (PB, ORB, VIX) cannot fill the hardest regime gaps. Phase 10 discovers genuinely new strategy families designed for uncovered cells.

### Priority 1: HIGH_VOL_TRENDING_LOW_RV (Trend Continuation)

**Problem:** -$1,399 PnL in this cell (7.3% of days, PF=0.39). Biggest portfolio bleed.

Build order (simple → complex):
1. ~~**Donchian Breakout + ATR Trail**~~ — **EVALUATED.** MNQ-Long PF=1.29, 356 trades, median hold 61 bars (true trend-following DNA). GRINDING filter → PF=1.76, Sharpe=3.38 (48 trades). Target cell: -$823. Breakout entry can't solve LOW_RV.
2. ~~**Keltner Channel Breakout**~~ — **EVALUATED.** MNQ-Short PF=1.46, 340 trades, Sharpe=1.90. Median hold 14 bars (momentum scalper — EMA exit too aggressive on 5m). Target cell: +$13 (breakeven). Negative correlation vs ORB (r=-0.170).
3. ~~**VWAP Trend Continuation**~~ — **EVALUATED.** MNQ-Long PF=1.67, 195 trades, Sharpe=2.62. Best risk-adjusted metrics of all three. Target cell: -$301 (improved but not solved). Extraordinary portfolio correlation (r=-0.087 vs PB). Entry at VWAP pullback is structurally superior to breakout.
4. **EMA Crossover + ADX** — harvest `idx-004` (GitHub open source) or `idx-002` (AF=5)
5. **SuperTrend + EMA Pullback** — harvest `idx-011` (AF=4)

**Key finding:** Three different entry models (N-bar breakout, EMA channel, VWAP pullback) all fail to fix the target cell. The HIGH_VOL + LOW_RV contradiction is structural: wide stops required but small realized moves. Next approach: **exit evolution** (time stops, chandelier exits) on existing strategies.

**Validation criteria:** Must show ≥10 trades in HIGH_VOL_TRENDING_LOW_RV, median hold ≥60 bars, trend_persistence=GRINDING affinity.

### Priority 2: RANGING Cells (Range / Equilibrium)

Build order:
1. **Bollinger Band Equilibrium** — touch outer BB, enter on midline reversion (hand-build, leverage `compute_range_fade`)
2. **Failed Volatility Breakout (FVBO)** — squeeze → breakout attempt → failure → fade (harvest `idx-015`)
3. **VWAP Mean Reversion** — harvest `vvedding--rvwap` (AF=5, convert_now)
4. **Session Profile Reversion** — value area fade at POC/VAH/VAL (hand-build)

**Note:** If VWAP reversion fails again on 5m (as RVWAP-MR did), test on 15m/30m bars.

### Watch Candidates
- `orb_range_fade` — PF=4.83 on 9 trades. Re-evaluate with more data.
- `vix_ema_trend` — PF=1.48, Sharpe=2.31. Hit DNA duplicate but shows edge if VIX DNA threshold adjusted.

### Architecture Decision: Event Trading
Event trading (geopolitical, macro news) is NOT a strategy family. It is a **regime override layer**: `event_detected → disable mean reversion → widen stops → activate trend followers`. Fits into existing RegimeEngine as a future enhancement.

### Evolution Roadmap
- VIX add_filter mutations: **frozen** (3/3 DNA duplicate in Batch 2)
- VIX swap_risk mutations: **still valid**
- Existing parents: **no Batch 3** until new parents discovered
- New parents: eligible for evolution after baseline validation

### Paper Trading (deferred)
- Paper trading plan ready: `docs/PHASE_7_PAPER_TRADING_PLAN.md`
- Pending: Tradovate sim account setup
- Execution skeleton ready: `execution/tradovate_adapter.py` + `execution/signal_logger.py`

### Portfolio Status
- 9 strategies converted total, 5 rejected, 2 pending validation
- VIX Channel MES-Both: pending_validation (passes 5/8, fails net PF 1.298, DSR, MC ruin)
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
| Phase 9 — Evolution Scheduler | Complete | research/evolution/evolution_results.md |
| Phase 9.5 — Portfolio Fitness + Regime Coverage | Complete | research/regime/regime_coverage.json |
| Phase 9.5.1 — Evolution Batch 2 (Regime-Targeted) | Complete | research/evolution/evolution_results_batch2.md |

---
*Last updated: 2026-03-09 (Phase 10.1 — 3 trend strategies evaluated, 4-strat portfolio tested, target cell structural)*
