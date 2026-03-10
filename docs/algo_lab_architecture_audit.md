# Algo Lab Architecture Audit

*Canonical checkpoint — 2026-03-10, post-Phase 13*

---

## 1. Current System Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RESEARCH LAYER                               │
│                                                                     │
│  Intake ──→ Conversion ──→ Backtest ──→ Validation ──→ Promotion   │
│  (harvest)   (Pine→Py)     (engine)     (battery)      (gates)     │
│                                                                     │
│  Discovery ──→ Evolution ──→ Crossbreeding ──→ Regime Analysis     │
│  (phase10+)   (mutations)   (recombination)   (coverage map)       │
│                                                                     │
│  Genome ──→ DNA Clustering ──→ Triage ──→ Gap Detection            │
│  (behavioral)  (structural)    (routing)   (research targets)      │
├─────────────────────────────────────────────────────────────────────┤
│                        PORTFOLIO LAYER                              │
│                                                                     │
│  Correlation ──→ Weighting ──→ Stress Testing ──→ Monte Carlo      │
│  (pairwise)     (vol target)   (LOO/top-trade)   (5K-10K sims)    │
│                                                                     │
│  Regime Gate ──→ Portfolio Sim ──→ Prop Sim ──→ Income Projection  │
│  (per-strategy)  (equity curves)   (payout)     (scaling table)    │
├─────────────────────────────────────────────────────────────────────┤
│                        DEPLOYMENT LAYER                             │
│                                                                     │
│  Strategy Engine ──→ Prop Controller ──→ Execution Adapter         │
│  (pure signals)      (risk rules)        (broker API)              │
│                                                                     │
│  Signal Logger ──→ Tradovate Adapter ──→ Kill Switch ──→ Monitor   │
│  (paper trade)     (skeleton only)       (designed)      (designed)│
└─────────────────────────────────────────────────────────────────────┘
```

**Status:** Research layer = fully operational. Portfolio layer = fully operational. Deployment layer = designed + skeleton, not live.

---

## 2. Folder / Module Map

### Strategy Intake
| Module | Path | Status |
|--------|------|--------|
| Harvest CLI | `intake/manage.py` | Operational |
| Manifest | `intake/manifest.json` | 91 scripts indexed |
| TV scripts | `intake/tradingview/{family}/` | 8 family directories |
| Triage engine | `research/triage/run_triage.py` | Operational |
| Conversion runner | `backtests/run_conversion_baseline.py` | Operational |
| Pine→Python prompt | `prompts/pine_to_python_prompt.md` | Reference doc |

### Core Engine
| Module | Path | Status |
|--------|------|--------|
| Backtest engine | `engine/backtest.py` | Production (fill-at-next-open) |
| Regime engine | `engine/regime_engine.py` | Production (4-factor) |
| Indicators | `engine/indicators.py` | Utility library |
| Metrics | `engine/metrics.py` | Utility library |
| Statistics | `engine/statistics.py` | Utility library |
| Scoring | `engine/scoring.py` | Utility library |
| Prop eval | `engine/prop_eval.py` | Utility |

### Validation Battery
| Module | Path | Status |
|--------|------|--------|
| Generic battery | `research/validation/run_validation_battery.py` | Production (10-criterion) |
| Results (6 JSONs) | `research/validation/*.json` | PB, ORB, VWAP, Donch, XB variants |
| Legacy validation | `research/experiments/*/run_validation.py` | Deprecated (pre-generic) |
| Extended metrics | `backtests/run_baseline.py:compute_extended_metrics()` | Reused by all research scripts |

### Genome Engine
| Module | Path | Status |
|--------|------|--------|
| Strategy genome | `research/genome/strategy_genome.py` | 10 strategies profiled |
| Portfolio genome | `research/genome/portfolio_genome.py` | Gap detection operational |
| DNA clustering | `research/dna/build_dna_profiles.py` | 9 profiles, 8 clusters |
| DNA schema | `research/dna/dna_schema.json` | 20+ field structural fingerprint |

### Crossbreeding
| Module | Path | Status |
|--------|------|--------|
| Crossbreeding engine | `research/crossbreeding/crossbreeding_engine.py` | 20 recipes, 13 passed |
| Results | `research/crossbreeding/crossbreeding_results.json` | Stored |

### Evolution / Refinement
| Module | Path | Status |
|--------|------|--------|
| Evolution scheduler | `research/evolution/evolution_scheduler.py` | Batch 1+2 complete |
| Mutations library | `research/evolution/mutations.py` | 6 mutation types |
| Portfolio fitness | `research/evolution/portfolio_fitness.py` | 5-component scorer |
| Exit evolution | `research/exit_evolution.py` | 6 exit variants tested |
| BB Eq evolution | `research/bb_eq_evolution.py` | 4 BB variants tested |
| Generated candidates | `research/evolution/generated_candidates/` | 20 strategy directories |

### Portfolio Weighting
| Module | Path | Status |
|--------|------|--------|
| Weighting optimizer | `research/portfolio/portfolio_weighting.py` | 5 schemes tested |
| Portfolio simulation | `research/phase12_portfolio.py` | 5-strat equity curves |
| Overlap analysis | `research/portfolio/overlap_analysis.py` | Correlation + DD overlap |
| Sizing comparison | `research/portfolio/sizing_comparison.py` | ERC/vol target/Kelly |
| Regime portfolio | `research/portfolio/regime_portfolio_sim.py` | Regime-gated simulation |

### Prop Simulation
| Module | Path | Status |
|--------|------|--------|
| Prop controller | `controllers/prop_controller.py` | Platform-agnostic |
| Prop configs | `controllers/prop_configs/*.json` | 4 configs (Lucid, Apex, Generic, Cash) |
| Prop simulator | `research/portfolio/prop_account_simulation.py` | Multi-account + MC + payout |
| Monte Carlo | `research/monte_carlo/run_monte_carlo.py` | 10K-sim ruin analysis |
| Paper trade sim | `research/paper_trade_sim/run_paper_sim.py` | Signal-level simulation |

### Execution Infrastructure
| Module | Path | Status |
|--------|------|--------|
| Tradovate adapter | `execution/tradovate_adapter.py` | **Skeleton only** |
| Signal logger | `execution/signal_logger.py` | **Skeleton only** |
| Architecture doc | `docs/execution_architecture.md` | Fully designed |

### Range Discovery (Phase 13)
| Module | Path | Status |
|--------|------|--------|
| Evaluation script | `research/phase13_range_discovery.py` | Two-tier gate + RANGING_EDGE_SCORE |
| Strategy candidates | `strategies/{vwap_dev_mr,bb_range_mr,session_vwap_fade,orb_fade}/` | 4 MR strategies |

---

## 3. Product Split

### Product A: Eval-Stage Fast-Pass Engine

**Purpose:** Pass prop firm evaluations as fast as possible.

| Component | Status |
|-----------|--------|
| Strategy signals | 4 parents operational |
| Prop controller | Operational, 4 configs |
| Phase detection (P1→P2) | Implemented in prop_controller.py |
| Aggression scaling | P1 conservative, P2 aggressive (configurable) |
| Trailing DD management | Implemented |
| Daily loss limits | Implemented |

**How it works:** Run portfolio through prop controller → survive trailing DD → lock at profit target → advance to funded.

**Missing for live eval:**
- Live execution adapter (Tradovate skeleton exists, not connected)
- Real-time data feed integration
- Kill switch implementation

### Product B: Funded-Account Payout Engine

**Purpose:** Maximize monthly payouts from funded accounts after eval pass.

| Component | Status |
|-----------|--------|
| Payout cycle simulation | Operational (research/portfolio/prop_account_simulation.py) |
| Vol Target sizing | Operational (optimal weights computed) |
| Multi-account scaling | Modeled (3/5/10 accounts) |
| Income projections | Computed ($5K/yr per Apex 50K) |
| Stress testing | Operational (strategy failure, DD shock, vol spike) |

**Key insight:** Eval pass and payout are the same portfolio — the difference is P1 (conservative, survival-first) vs P2 (aggressive, growth-first). The prop controller handles this transition automatically via config.

**Bottleneck:** First payout takes ~400 days. Improving payout speed requires either:
- More aggressive P1 sizing (higher bust risk)
- Additional uncorrelated strategies (Phase 14 Gold MR)
- Higher-frequency strategies (currently not pursued)

---

## 4. Promotion Flow

```
harvested (91)
    ↓ intake/manage.py
converted (15)
    ↓ backtests/run_conversion_baseline.py
baselined
    ↓ research/validation/run_validation_battery.py
    │
    ├──→ rejected (12)          ← PF<1, no edge, structural overlap
    │     └─ research/postmortems/
    │
    ├──→ candidate (validation battery)
    │     ├─ Walk-forward year + rolling
    │     ├─ Regime stability
    │     ├─ Asset/timeframe robustness
    │     ├─ Bootstrap CI + DSR + MC
    │     └─ Parameter stability (81+ combos)
    │
    ├──→ probation (4)          ← Edge real, needs more data or refinement
    │     Donchian (48 trades)
    │     BB Equilibrium (gold-only WF)
    │     XB-ORB-EMA-Ladder (MC ruin $2K)
    │     Session VWAP Fade (Phase 14 refinement)
    │
    └──→ parent (4)             ← Full validation, 7+/10 stability
          PB-Trend (MGC-S)
          ORB-009 (MGC-L)
          VWAP Trend (MNQ-L)
          XB-PB-EMA-TimeStop (MES-S)
              ↓
          portfolio             ← Vol Target weights, correlation verified
              ↓
          deployment            ← Prop controller + execution adapter
```

**Lifecycle metrics:**
| Stage | Count | Pass Rate |
|-------|-------|-----------|
| Harvested | 91 | — |
| Converted | 15 | 16% of harvested |
| Parent | 4 | 27% of converted |
| Probation | 4 | 27% of converted |
| Rejected | 12 | 80% of converted (includes evolution candidates) |

**Gate criteria (current, post-Phase 11):**

| Gate | Metric | Threshold |
|------|--------|-----------|
| Discovery | PF | > 1.15 |
| Discovery | Trades | ≥ 30 |
| Discovery | Correlation vs parents | < 0.35 |
| Promotion (T2) | PF | > 1.4 |
| Promotion (T2) | Sharpe | > 1.8 |
| Promotion (T2) | Trades | ≥ 80 |
| Validation battery | Stability score | ≥ 7.0/10 |
| Validation battery | Hard failures | 0 |
| Portfolio entry | Correlation vs all parents | < 0.25 |
| Portfolio entry | Portfolio Sharpe delta | > 0 |

**Note:** `CANDIDATE_PROMOTION_STANDARD.md` is stale — written Phase 3, reflects 2-strategy state (PB + ORB only). The validation battery (`run_validation_battery.py`) is the actual source of truth for promotion criteria.

---

## 5. Missing Pieces for Live Deployment

### Critical (must have)

| Component | Current State | Effort |
|-----------|--------------|--------|
| Live data feed | None | Tradovate WebSocket or Databento live |
| Execution adapter | Skeleton | Connect Tradovate REST API |
| Kill switch | Designed | Implement auto-kill + manual |
| Real-time regime gate | Backtested only | Port to live data computation |
| Paper trade validation | Simulated only | 2-week live paper minimum |
| Order bracket management | Designed | Implement SL/TP placement |
| EOD flatten | In strategy signals | Needs execution-level enforcement |
| Daily reconciliation | Designed | Compare trade log vs broker fills |

### Important (should have)

| Component | Current State | Effort |
|-----------|--------------|--------|
| Monitoring dashboard | Designed | Real-time position + PnL display |
| Alert system | Designed | Email/SMS/Discord notifications |
| Heartbeat system | Designed | Connection health monitoring |
| Fill quality tracking | Not started | Compare backtest vs live fills |
| Multi-account orchestrator | Simulated | Route signals to N accounts |

### Nice to have (can wait)

| Component | Current State | Effort |
|-----------|--------------|--------|
| HMM regime detection | Not started | Alternative to rule-based regime |
| Alternative data (COT, GVZ) | Not started | Additional filters |
| Rithmic adapter | Not started | Backup broker |
| Auto-scaling | Modeled | Dynamic contract sizing |

---

## 6. Risks / Inconsistencies

### Structural Issues

**1. Duplicated indicator functions across strategies**
- `_atr()` defined in 20 files independently
- `_adx()` defined in 13 files
- `_rsi()` defined in 12 files
- `_compute_session_vwap()` defined in 4 files

**Risk:** Bug fix in one doesn't propagate. Indicators could diverge silently.
**Recommendation:** Extract to `engine/indicators.py` (already exists but not used by strategies). Strategies currently self-contain for platform-agnostic portability — this is by design but creates maintenance risk. **Low priority** — indicator logic is stable and simple.

**2. `compute_extended_metrics()` lives in `backtests/run_baseline.py`**
- Used by 17 files across research, evolution, crossbreeding, portfolio
- Should logically live in `engine/metrics.py`
- Current location works but is architecturally wrong

**Risk:** Import path is non-obvious. New scripts import from `backtests/` which feels wrong.
**Recommendation:** Move to `engine/metrics.py` and re-export from `backtests/run_baseline.py` for backwards compat. **Medium priority.**

**3. Stale promotion standard**
- `docs/CANDIDATE_PROMOTION_STANDARD.md` reflects Phase 3 state (PB + ORB, no validation battery)
- The actual promotion criteria are in `research/validation/run_validation_battery.py` and the two-tier gate in `research/phase13_range_discovery.py`
- `meta.json` status field (`converted`, `candidate_validated`, `candidate_deployable`) is not used by any automated system

**Risk:** New readers get confused about which criteria are current.
**Recommendation:** Update `CANDIDATE_PROMOTION_STANDARD.md` to reflect current battery, or replace with pointer to validation battery. **Medium priority.**

**4. Two validation systems exist**
- Legacy: `research/experiments/*/run_validation.py` (per-strategy, custom)
- Current: `research/validation/run_validation_battery.py` (generic, 10-criterion)

**Risk:** None functional — legacy is historical record. But folder structure is confusing.
**Recommendation:** No action needed. Legacy results are still valid reference data.

**5. `engine/regime.py` vs `engine/regime_engine.py`**
- Both exist. `regime.py` appears to be an older/simpler version.
- `regime_engine.py` is the production 4-factor engine.

**Risk:** Importing the wrong one.
**Recommendation:** Verify `regime.py` isn't imported anywhere; if dead code, remove it. **Low priority.**

### Naming / Organization

**6. Strategy wrapper pattern inconsistency**
- Crossbred strategies (`xb_pb_ema_timestop`, `xb_orb_ema_ladder`) are thin wrappers calling `crossbreeding_engine.py`
- All other strategies are self-contained `generate_signals()` implementations
- Both work but the wrapper pattern adds an import dependency

**Risk:** If `crossbreeding_engine.py` is refactored, wrapper strategies break.
**Recommendation:** Acceptable for now. If any wrapper strategy becomes a parent, inline the logic. XB-PB-EMA-TimeStop is already a parent — consider inlining. **Low priority.**

**7. Research script naming is inconsistent**
- Phase-based: `phase10_eval.py`, `phase12_portfolio.py`, `phase13_range_discovery.py`
- Function-based: `exit_evolution.py`, `bb_eq_evolution.py`, `grinding_deep_dive.py`
- Nested: `research/portfolio/`, `research/evolution/`, `research/genome/`

**Risk:** Hard to find things. No consistent pattern.
**Recommendation:** Acceptable — research scripts are write-once-run-once. The important outputs (JSONs, reports) are what matter.

### Data / Consistency

**8. `meta.json` files are stale**
- Only early strategies (orb_009, pb_trend, vwap_006, etc.) have `meta.json`
- Phase 10+ strategies have no meta files
- The `status` field in meta files is not updated after validation

**Risk:** Meta files are unreliable as status source. `strategy_registry.md` and `LAB_STATE.md` are the actual truth.
**Recommendation:** Stop creating meta.json for new strategies. Single source of truth = `strategy_registry.md`. **Low priority.**

**9. Gold-only MR concentration risk**
- All 4 MR candidates (BB Eq, Sess VWAP Fade, VWAP Dev MR, BB Range MR) are MGC-long
- If gold microstructure changes, entire MR engine family dies simultaneously
- Trend engine family spans 3 assets; MR family spans 1

**Risk:** Real concentration risk. Mitigated by: MR is portfolio enhancement, not core.
**Recommendation:** Accept for now. Monitor gold regime stability. Phase 14 refinement should include regime robustness testing.

---

## Summary Verdict

| Area | Grade | Notes |
|------|-------|-------|
| Research layer | **A** | Fully operational, 13 phases complete, automated pipelines |
| Portfolio layer | **A** | Vol Target, stress tests, prop sim, Monte Carlo all working |
| Strategy quality | **A** | 4 parents, 4 probation, near-zero correlations, 0% bust |
| Documentation | **B+** | Comprehensive but some stale docs (promotion standard, meta.json) |
| Code organization | **B** | Functional but duplicated indicators, misplaced metrics function |
| Deployment layer | **D** | Designed thoroughly but only skeleton code exists |
| Live readiness | **Not ready** | Need: data feed, execution adapter, kill switch, paper trade validation |

**Are we building the right lab?** Yes. The research and portfolio layers are professional-grade. The two-engine architecture (trend on indexes, MR on gold) is structurally sound. The promotion pipeline is rigorous. The gap is entirely in the deployment layer — taking signals from backtested to live.

---

*Created 2026-03-10. Update after each major phase.*
