# Algo Lab State

*Auto-updated after each milestone. Single source of truth for lab status.*

## Pipeline Counts

| Stage | Count |
|-------|-------|
| Strategies harvested | 91 (76 batch 1 + 15 batch 2) |
| Strategies converted | 15 (12 original + 3 crossbred) |
| Parent strategies | **5** (PB, ORB, VWAP Trend, XB-PB-EMA-TimeStop, BB Equilibrium) |
| Probation | **3** (Donchian GRINDING+PL, XB-ORB-EMA-Ladder, Session VWAP Fade) |
| Phase 12 crossbred | 20 recipes tested, 13 passed quality gate |
| Rejected | 12 (+ XB-PB-Squeeze-Chand, ORB Fade) |
| Pending validation | 2 (VIX Channel MES, Gap-Mom MGC) |
| Effectively dead (costs) | 2 |

## Core Portfolio (Phase 6 — Deployment Validated)

| Strategy | Asset | Mode | Gated PF | Gated Sharpe | DSR | Status |
|----------|-------|------|----------|-------------|-----|--------|
| PB-Trend | MGC | Short | 2.36 | 5.27 | 0.952 SIG | deployment_ready |
| ORB-009 | MGC | Long | 2.07 | 3.93 | 1.000 SIG | deployment_ready |
| VWAP Trend | MNQ | Long | 1.67 | 2.62 | 1.000 SIG | **PARENT** (Phase 11) |
| XB-PB-EMA-TimeStop | MES | Short | 1.82 | 3.56 | 0.9998 SIG | **PARENT** (Phase 12) |
| BB Equilibrium (Gold Snapback) | MGC | Long | 6.48 | 4.00 | — | **PARENT** (Phase 15) |

**Probation:**

| Strategy | Asset | Mode | PF | Sharpe | Status | Blocker |
|----------|-------|------|----|--------|--------|---------|
| Donchian GRINDING+PL | MNQ | Long | 1.99 | 3.97 | probation | 48 trades (sample size) |
| XB-ORB-EMA-Ladder | MNQ | Short | 1.92 | 3.80 | probation | MC ruin at $2K (MNQ sizing) |

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

*VWAP Trend: PROMOTED to parent (Phase 11, stability score 10.0/10). Donchian: PROBATION (7.0/10, sample-size failures).*

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

### Portfolio Metrics (Phase 12.3, 5-Strategy: PB + ORB + VWAP + XB-PB-EMA + Donchian GRINDING+PL)

| Metric | 3-Strat | 5-Strat (Equal) | 5-Strat (Vol Target) |
|--------|---------|-----------------|---------------------|
| Total PnL | $9,131 | $14,458 | $13,489 |
| Sharpe | 3.02 | 3.51 | **3.69** |
| Calmar | 6.76 | 9.02 | **9.84** |
| MaxDD | $1,351 | $1,603 | **$1,370** |
| Trades | 329 | 500 | 500 |
| Monthly | 72% | 84% | 80% |
| MC P($2K ruin) | — | 4.3% | **1.8%** |
| Max correlation | — | r=0.063 | r=0.063 |

**Vol Target Deployment Weights:** PB=1.21x, ORB=1.09x, VWAP=0.76x, XB-PB=1.23x, DONCH=0.71x

### Portfolio Metrics (Phase 15, 6-Strategy: PB + ORB + VWAP + XB-PB-EMA + Donchian + BB Equilibrium)

| Metric | 5-Strat (Vol Target) | 6-Strat (+BB Eq) |
|--------|---------------------|------------------|
| Total PnL | $13,489 | $15,734 |
| Sharpe | 3.69 | **3.89** |
| Calmar | 9.84 | **11.65** |
| MaxDD | $1,370 | **$1,351** |
| Trades | 500 | 554 |
| Monthly | 80% | 84% |
| Max correlation | r=0.063 | r=0.077 |

### Portfolio Metrics (Phase 16, Strategy Controller: Baseline vs Controller-Managed)

| Metric | Baseline (Always-On) | Controller-Managed | Change |
|--------|---------------------|-------------------|--------|
| Total PnL | $17,487 | $16,378 | -6.3% |
| Sharpe | 3.59 | **4.04** | **+0.45** |
| Calmar | 10.33 | 8.16 | -2.17 |
| MaxDD | $1,693 | $2,007 | +$313 |
| Trades | 560 | **391** | **-30%** |
| Monthly | 80% | **84%** | **+4%** |
| Losing months | 5 | **4** | -1 |
| MC Median MaxDD | $1,171 | **$1,011** | **-14%** |
| MC P(ruin $2K) | 4.6% | **1.6%** | **-65%** |

**Controller verdict: 4/5 PASS — CONTROLLER IMPROVES PORTFOLIO**

Controller filters: regime gate (blocks avoid_regimes), soft timing (preferred window + conviction override), portfolio coordination (max 4 simultaneous, max 2 per asset, cluster prevention).

Trade filtering: 70% of trades kept. PB 28→9, ORB 106→62, VWAP 195→163, XB-PB 123→88, BB-EQ 60→22, Donchian 48→47.

**Phase 16.1 tuning targets:** Dec 2024 MaxDD cluster, PB/BB Equilibrium filter aggressiveness.

**BB Equilibrium (Gold Snapback) refined params:** EMA_PERIOD=15, ATR_TRAIL_MULT=1.5, BW_MAX_PCT=70, regime gate=avoid NORMAL_TRENDING_HIGH_RV.
Stability score: 9.5/10. Walk-forward: PASS. Gold-only (asset robustness 0.5 penalty accepted).

### Sizing Research (Phase 12.4)

| Method | Sharpe | Calmar | MaxDD | MC Ruin | Best For |
|--------|--------|--------|-------|---------|----------|
| Equal Weight | 3.51 | 9.02 | $1,603 | 4.3% | Simplicity |
| **Vol Target** | **3.69** | **9.84** | **$1,370** | **1.8%** | **Recommended** |
| Risk Parity | 3.69 | 9.84 | $1,370 | 1.8% | Same as Vol Target |
| Half-Kelly | 3.59 | 8.28 | $1,633 | 2.5% | Moderate |
| DD-Adjusted | 3.58 | 9.68 | $1,135 | 0.7% | Max safety |

### Stress Tests (Vol Target, all PASS)

| Test | Result | Details |
|------|--------|---------|
| Leave-one-out | PASS | Worst Sharpe=3.33 (no single-point-of-failure) |
| Top-trade removal | PASS | Survives removing top 5 trades |
| Shuffle MC | PASS | 5th pct Sharpe=4.62 (sequence-independent) |

**Fragility: ROBUST — READY FOR DEPLOYMENT**

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
15. **Gold has different intraday microstructure.** Gold mean-reverts cleanly; equity indexes don't. BB Equilibrium PF=3.53 on MGC, PF<0.65 on MES/MNQ. Mean reversion is asset-specific.
16. **VWAP Trend is the strongest validated parent.** 10.0/10 stability score, 100% parameter stability (81/81 combos), all 3 assets profitable, all 3 timeframes profitable. Structural edge, not curve-fit.
17. **Walk-forward instability can be solved by regime alignment.** BB Equilibrium 2024 PF=0.88→1.00 with daily EMA(20) trend filter. Aligning MR entries with macro gold direction eliminates regime-mismatch bleed.
18. **Behavioral genome ≠ structural DNA.** BB Equilibrium is structurally "mean reversion" but behaviorally profits in trending/volatile markets (trends create overextensions that revert). Both labels are correct at different levels.
19. **Portfolio genome reveals concentration risk.** 33.9% of PnL from HIGH_VOL_TRENDING_HIGH_RV. Missing engine types: mean_reversion, counter_trend, session_structure, volatility_compression, overnight_gap.
20. **Crossbreeding amplifies real edges and exposes redundancy.** 5 BB reversion variants all produced PF>2.0 on MGC-long, confirming BB Equilibrium is genuine. But novelty is rare — most crossbred children are parent refinements, not new families.
21. **Multi-asset robustness is the strongest validation signal.** XB-ORB-EMA-Ladder: PF>1.5 on all 3 assets, PF>1.8 on all 3 timeframes, 100% parameter stability. When a strategy works everywhere, the edge is structural.
22. **MES parent gap filled.** XB-PB-EMA-TimeStop (10.0/10 stability) is first MES parent. Portfolio now covers all 3 assets: MES (pullback), MNQ (VWAP continuation), MGC (breakout + MR).
23. **100% parameter stability = real edge.** Both Phase 12 crossbred candidates scored 100% (81/81 and 27/27). This is the gold standard — no combination of reasonable parameters kills profitability.
24. **Vol Target sizing improves everything.** Inverse-volatility weighting (scales up low-vol, scales down high-vol) improves Sharpe 3.51→3.69, Calmar 9.02→9.84, MC ruin 4.3%→1.8%. Vol Target and Risk Parity converge to the same weights — both are inverse-vol. All 3 stress tests pass (LOO worst Sharpe 3.33, top-5 removal survives, shuffle 5th pct Sharpe 4.62).
25. **Portfolio is indestructible across prop configs.** 0% bust rate on 5K MC simulations for Lucid 100K, Apex 50K, and Generic 50K. Even 10 simultaneous accounts have ≤0.2% chance of ANY bust. $2,000 DD shock = 0.1% bust, 2.5x vol spike = 0.3% bust. The bottleneck is payout speed (400 days to first), not survival.
26. **Gold mean-reverts, equity indexes don't — asset-strategy specialization.** Phase 13 tested 4 MR strategies × 3 assets × 3 modes (36 combos). ALL winners are MGC-long. MES/MNQ MR strategies uniformly fail. Gold's hedging/macro flows create intraday overextensions that revert; equity index momentum/gamma dynamics sustain trends. The correct portfolio architecture is: trend engines → indexes, mean reversion → gold.
27. **Two-engine portfolio architecture emerged.** Trend Engine (PB, ORB, VWAP, XB-PB, Donchian) on indexes + Mean Reversion Engine (Sess VWAP Fade, BB Range MR, VWAP Dev MR) on gold. This is how professional multi-strategy systems work: asset-specific strategy families, near-zero correlation, structural diversification.

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
- [x] Full validation battery (10-criterion: WF year+rolling, regime, asset, TF, bootstrap, DSR, MC, param, top-trade)
- [x] Strategy Genome Engine (auto-computed behavioral fingerprints from backtests)
- [x] Portfolio Genome Analysis (redundancy detection, gap analysis, concentration risk, research targets)
- [x] Exit evolution framework (6 variants tested on frozen entries)
- [x] BB Equilibrium evolution (4 variants: vol-gated, trend-aware, time-filtered, extreme-only)
- [x] Strategy Crossbreeding Engine (5 entries × 5 exits × 6 filters, 20 curated recipes, automatic quality gates)
- [x] Portfolio risk-weight optimization (5 schemes: equal, vol target, risk parity, half-Kelly, DD-adjusted)
- [x] Portfolio stress testing (leave-one-out, top-trade removal, shuffle Monte Carlo)
- [x] Prop account simulation engine (multi-account, payout cycles, income projections, stress tests)
- [x] Range strategy discovery pipeline (two-tier gate, RANGING_EDGE_SCORE, portfolio usefulness override)
- [x] Strategy Controller (regime gate + soft timing + portfolio coordination)
- [x] Paper Trading Engine (full 6-strategy pipeline + kill switch + daily state tracking)
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
- [x] Validation battery (generic, CLI-driven, 6 tests + 10 criteria + LOW_SAMPLE handling)
- [x] Strategy Genome Engine (10 strategies fingerprinted — hold, trade structure, sensitivity, regime, session)
- [x] Portfolio Genome Analysis (engine gap detection, similarity matrix, regime concentration, diversification score)
- [x] Crossbreeding Engine (component recombination, quality gates, batch evaluation, crossbreeding_results.json)

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

**Phase 18: Forward Paper Trading / Live Broker Integration**

### Immediate Priorities

1. **Forward Paper Trading**
   - Run paper trading engine on new data as it arrives
   - Validate signals match backtest expectations in real time
   - Goal: 2+ weeks clean forward run before live deployment

2. **XB-ORB-EMA-Ladder: Resolve MC ruin failure**
   - 9.0/10 stability, only fails MC ruin at $2K (MNQ sizing issue, MaxDD=$2,331)
   - Options: (a) accept on MES instead (PF=1.59), (b) position sizing work, (c) wait for more data

3. **Donchian GRINDING+PL: Wait for more data**
   - Re-validate when dataset extends (est. Q3 2026 for 80+ trades)

### Two-Engine Architecture

**Trend Engine Family (Indexes):**
| Strategy | Asset | Mode | Engine | Status |
|----------|-------|------|--------|--------|
| PB-Trend | MGC | Short | pullback_scalper | **PARENT** |
| ORB-009 | MGC | Long | trend_continuation | **PARENT** |
| VWAP Trend | MNQ | Long | breakout/continuation | **PARENT** |
| XB-PB-EMA-TimeStop | MES | Short | pullback_scalper | **PARENT** |
| Donchian GRINDING+PL | MNQ | Long | trend_follower | probation |

**Mean Reversion Engine Family (Gold):**
| Strategy | Asset | Mode | PF | Trades | Status |
|----------|-------|------|----|--------|--------|
| BB Equilibrium (Gold Snapback) | MGC | Long | 6.48 | 54 | **PARENT** (Phase 15) |
| Session VWAP Fade | MGC | Long | 2.13 | 104 | probation |
| VWAP Dev MR | MGC | Long | 1.31 | 94 | rejected (Phase 14) |
| BB Range MR | MGC | Long | 3.05 | 40 | rejected (Phase 14) |

### Portfolio Status
- **5 Parents**: PB(MGC-S), ORB(MGC-L), VWAP-Trend(MNQ-L), XB-PB-EMA-TimeStop(MES-S), BB Equilibrium(MGC-L)
- **3 Probation**: Donchian(MNQ-L), XB-ORB-EMA-Ladder(MNQ-S), Session VWAP Fade(MGC-L)
- **14 Rejected**: see strategy_registry.md
- **Portfolio Diversification Score**: ~8.0/10 (up from 7.5 — MR engine added)
- **Asset Coverage**: MES, MNQ, MGC — all covered
- **Engine Coverage**: trend/momentum/pullback + **mean_reversion (gold-specific, validated)**

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
| Phase 10 — New Parent Discovery | Complete | research/phase10_eval.py |
| Phase 10.6 — Exit Evolution (Donchian) | Complete | research/exit_evolution.py |
| Phase 11 — Validation Battery + VWAP Trend Promotion | Complete | research/validation/run_validation_battery.py |
| Phase 11.5 — Strategy Genome Engine | Complete | research/genome/strategy_genome.py |
| Phase 11.6 — BB Equilibrium Evolution | Complete | research/bb_eq_evolution.py |
| Phase 11.7 — Gold MR Family Test | Complete | strategies/vwap_mr_gold, session_reversion_gold, bb_compression_gold |
| Phase 12 — Strategy Crossbreeding Engine | Complete | research/crossbreeding/crossbreeding_engine.py |
| Phase 12.1 — Crossbred Candidate Evaluation | Complete | strategies/xb_pb_ema_timestop, xb_orb_ema_ladder, xb_pb_squeeze_chand |
| Phase 12.2 — Crossbred Validation + MES Parent Promotion | Complete | XB-PB-EMA-TimeStop 10.0/10 → PARENT |
| Phase 12.3 — 5-Strategy Portfolio Simulation | Complete | 5/5 PASS, Sharpe 3.51, Calmar 9.02 |
| Phase 12.4 — Portfolio Risk-Weight Optimization | Complete | Vol Target best (Sharpe 3.69), all stress tests PASS |
| Phase 12.5 — Prop Account Simulation Engine | Complete | 0% bust rate, 7 payouts, $5K/yr per account (Apex 50K) |
| Phase 13 — Range Strategy Discovery | Complete | 3 MR candidates (all MGC-long), Sess VWAP Fade → probation |
| Phase 14 — Gold MR Refinement | Complete | 4 candidates tested, BB Equilibrium best (PROBATION → refinement) |
| Phase 15 — Gold Snapback Engine | Complete | BB Equilibrium PROMOTED to 5th parent (9.5/10, EMA-15, Trail-1.5) |
| Phase 16 — Strategy Controller | Complete | Sharpe 3.59→4.04, MC ruin 4.6%→1.6%, 4/5 verdict PASS |
| Phase 16.1 — Controller Tuning | Complete | Original config confirmed optimal. Loosening degrades all metrics. |
| Phase 17 — Paper Trading Architecture | Complete | 7/8 validation PASS, Lucid 100K PASSED (locked 2025-04-07) |

## Milestone Tags

| Tag | Date | Description |
|-----|------|-------------|
| `v0.15-phase15-gold-snapback-parent` | 2026-03-10 | BB Equilibrium promoted to 5th parent. 6-strategy portfolio: Sharpe 3.89, Calmar 11.65. |
| `v0.16-phase16-strategy-controller` | 2026-03-11 | Strategy Controller: Sharpe 4.04, MC ruin 1.6%, 84% monthly. Controller 4/5 PASS. |
| `v0.17-phase17-paper-trading-engine` | 2026-03-11 | Paper Trading Engine: 7/8 validation, Lucid 100K PASSED, kill switch validated. |

*See `docs/release_workflow.md` for milestone creation rules and naming format.*

---
*Last updated: 2026-03-11 (Phase 17 — Paper Trading Engine validated, Lucid 100K PASSED)*
