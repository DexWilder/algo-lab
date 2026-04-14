# Research Pipeline

*Canonical operating manual for the algo lab. Describes every stage from intake to deployment.*

---

## Pipeline Overview

```
1. Strategy Intake
   ↓
2. Conversion (Pine → Python)
   ↓
3. Baseline Backtest
   ↓
4. Phase 10 Evaluation (3 assets × 3 modes + regime + correlation)
   ↓
5. Strategy Genome Mapping (behavioral fingerprint)
   ↓
6. Portfolio Fitness Test (correlation + diversification)
   ↓
7. Validation Battery (10-criterion robustness)
   ↓
8. Promotion Decision (Parent / Probation / Rejected)
   ↓
9. Continuous Refinement (exit evolution, regime gating, param tuning)
   ↓
10. Deployment (prop controller + execution adapter)
```

---

## Stage 1: Strategy Intake

**Tool:** `intake/manage.py`
**Input:** TradingView Pine Scripts (harvested by Clawbot or manually)
**Output:** `intake/manifest.json` — metadata, scores, status labels

**Process:**
1. Add script to manifest with metadata (family, source, URL)
2. Score on 6 criteria (testability, futures_fit, prop_fit, clarity, conversion_difficulty, diversification)
3. Triage into convert_now / hold_for_later / component_only / reject
4. Cluster by family to detect duplicates

**Artifacts:** `research/triage/`, `research/review_logs/`

---

## Stage 2: Conversion

**Tool:** `backtests/run_conversion_baseline.py`
**Interface contract:** `generate_signals(df) -> df` with columns: signal, exit_signal, stop_price, target_price

**Rules:**
- Faithful conversion — preserve original parameters, no optimization
- Platform-agnostic — NO prop rules, NO phase sizing in strategy code
- Session boundaries defined in strategy (SESSION_START, SESSION_END, etc.)
- TICK_SIZE patched per asset by runner

**Output:** `strategies/<name>/strategy.py`

---

## Stage 3: Baseline Backtest

**Tool:** `backtests/run_conversion_baseline.py --strategy <name>`
**Engine:** `engine/backtest.py` — fill-at-next-open, configurable slippage/commission

**Output:**
- `backtests/<name>_baseline/metrics.json` — full performance metrics
- `backtests/<name>_baseline/trades.csv` — all trades with PnL
- `backtests/<name>_baseline/conversion_notes.md` — findings

**Minimum thresholds:** PF > 1.0 on at least one asset/mode combo with ≥30 trades

---

## Stage 4: Phase 10 Evaluation

**Tool:** `research/phase10_eval.py --strategy <name>`

**Process:**
1. Run backtest across 3 assets (MES, MNQ, MGC) × 3 modes (both, long, short)
2. Find best combo (highest PF with ≥30 trades)
3. Regime breakdown for best combo (18 composite cells + GRINDING analysis)
4. Portfolio correlation vs existing parents (daily PnL Pearson r)
5. Trade duration fingerprint (median/avg hold bars)

**Key gates:**
- At least one combo with PF > 1.2 and ≥30 trades
- Portfolio correlation r < 0.3 vs all parents
- If r > 0.4 vs any parent → REJECT (structural overlap)
- Median hold must match intended engine type

---

## Stage 5: Strategy Genome Mapping

**Tool:** `research/genome/strategy_genome.py --strategy <name>`

**Computes:**
1. Hold characteristics (median, avg, std, skew, class)
2. Trade structure (density, win rate, profit skew, tail dependency)
3. Market sensitivity (volatility, trend, RV — scored -1 to +1)
4. Regime performance (per-cell PnL, best/worst regime, dependence score)
5. Session profile (PnL by hour)
6. Year stability (PF by year)

**Engine type classification:** Auto-assigned from behavioral metrics (pullback_scalper, momentum_scalper, breakout, trend_continuation, trend_follower, mean_reversion, counter_trend, hybrid)

**Output:** `research/genome/strategy_genomes.json`

---

## Stage 6: Portfolio Fitness Test

**Tool:** `research/genome/portfolio_genome.py`

**Detects:**
- Engine type gaps (what's missing from portfolio)
- Behavioral similarity matrix (redundancy detection, threshold > 0.75)
- Regime concentration risk (cells with >25% of PnL)
- Asset diversification (coverage across MES/MNQ/MGC)
- Auto-generated research targets

**Output:** `research/genome/portfolio_genome_report.json`

---

## Stage 7: Validation Battery

**Tool:** `research/validation/run_validation_battery.py --strategy <name> --asset <ASSET> --mode <MODE>`

**10 Criteria:**
1. Walk-forward year splits (both periods PF > 1.0)
2. Walk-forward rolling windows (≥75% test windows PF > 1.0)
3. Regime stability (no catastrophic cells with PF < 0.5 and ≥10 trades)
4. Asset robustness (≥2 of 3 assets PF > 1.0)
5. Timeframe robustness (≥2 of 3 timeframes PF > 1.0)
6. Bootstrap PF CI lower bound > 1.0
7. Deflated Sharpe Ratio > 0.95
8. Monte Carlo P(ruin at $2K DD) < 5%
9. Top-trade removal PF > 1.0
10. Parameter stability ≥60% of combinations profitable

**LOW_SAMPLE handling:** Slices with <15 trades are flagged LOW_SAMPLE and not counted as hard failures.

**Stability Score (0-10):**
- ≥7.0 + 0 hard failures → PROMOTE TO PARENT
- 5.0-6.9 or 1-2 failures → CONDITIONAL (PROBATION)
- <5.0 or ≥3 failures → REJECT

**Output:** `research/validation/<strategy>_<asset>_<mode>_validation.json`

---

## Stage 8: Promotion Decision

| Decision | Criteria | Next Step |
|----------|----------|-----------|
| PARENT | Stability score ≥7.0, 0 hard failures | Deploy, add to portfolio |
| PROBATION | Score 5.0-6.9, or fixable failures | Refine (exit evolution, filters), re-validate |
| REJECTED | Score <5.0, or structural problem | Archive, extract components if useful |

---

## Stage 9: Continuous Refinement

**Exit Evolution:** `research/exit_evolution.py`
- Test 6+ exit variants on frozen entries (no entry changes)
- Variants: ATR trail, Chandelier, Time Stop, Trailing EMA, Profit Ladder, Vol-Contraction
- Gate: must not degenerate duration fingerprint

**Strategy Evolution:** `research/bb_eq_evolution.py` (example)
- Variant testing: volatility gates, trend filters, time-of-day, entry modifications
- Compare walk-forward stability across variants
- Goal: improve consistency while preserving PF

**Regime Gating:**
- Per-strategy regime profiles in `research/regime/strategy_regime_profiles.json`
- Activate/deactivate strategies based on daily regime classification
- GRINDING filter for trend-followers

---

## Stage 10: Deployment

**Prop Controller:** `controllers/prop_controller.py` + configs in `controllers/prop_configs/`
- Config-driven: trailing DD, daily limits, phase sizing
- Swap environment by changing config, never by changing strategy

**Execution:** `execution/tradovate_adapter.py` (skeleton)
- Paper trading → Live trading path
- Signal logger: `execution/signal_logger.py`

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Authoritative operating/state document |
| `docs/PROBATION_REVIEW_CRITERIA.md` | Non-XB-ORB probation governance |
| `docs/XB_ORB_PROBATION_FRAMEWORK.md` | XB-ORB probation governance |
| `docs/strategy_registry.md` | Every strategy's current status |
| `docs/research_pipeline.md` | This document — operating manual |
| `docs/research_log.md` | Chronological experiment record |
| `docs/LAB_STATE.md` | Historical snapshot only — not maintained |
| `engine/backtest.py` | Core backtest engine |
| `engine/statistics.py` | Bootstrap, DSR, statistical tests |
| `engine/regime_engine.py` | 4-factor regime classifier |
| `research/phase10_eval.py` | Strategy evaluation script |
| `research/genome/strategy_genome.py` | Behavioral fingerprint builder |
| `research/genome/portfolio_genome.py` | Portfolio gap analysis |
| `research/validation/run_validation_battery.py` | 10-criterion validation |
| `research/exit_evolution.py` | Exit variant testing |
| `backtests/run_baseline.py` | Extended metrics computation |

---

*Last updated: 2026-03-10*
