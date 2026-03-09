# Strategy Evolution Engine — Design Specification

*Architecture document only. No code to be built until Phase 7 paper trading completes.*

---

## Purpose

Automate the strategy research pipeline: harvest → convert → backtest → validate → combine. Currently this is manual with Claude orchestration. The evolution engine turns it into a scheduled, systematic process.

## Design Principles

1. **Components over strategies** — decompose strategies into entries, exits, filters, risk models. Recombine them.
2. **Statistical gates at every stage** — no strategy advances without passing DSR, bootstrap CI, robustness battery.
3. **Platform-agnostic** — strategies produce pure signals. Prop rules applied separately.
4. **No optimization without validation** — parameter search always uses walk-forward or cross-validation.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Evolution Engine                       │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐           │
│  │ Component │    │ Combiner │    │ Evaluator│           │
│  │ Registry  │───▸│          │───▸│          │           │
│  └──────────┘    └──────────┘    └──────────┘           │
│       │                              │                    │
│       │                              ▼                    │
│  ┌──────────┐              ┌──────────────┐             │
│  │ Harvester │              │ Promotion    │             │
│  │ (intake)  │              │ Pipeline     │             │
│  └──────────┘              └──────────────┘             │
│                                    │                      │
│                                    ▼                      │
│                           ┌──────────────┐               │
│                           │ Portfolio    │               │
│                           │ Optimizer   │               │
│                           └──────────────┘               │
└─────────────────────────────────────────────────────────┘
```

---

## 1. Component Registry

**Purpose:** Store reusable strategy building blocks.

### Component Types

| Type | Description | Examples |
|------|-------------|----------|
| Entry | Signal generation logic | ORB breakout, VWAP crossover, pullback, sweep reversal |
| Exit | Position closing logic | Fixed R:R, trailing stop, VWAP cross, time-based |
| Filter | Trade filtering | Regime gate, volume filter, time-of-day, trend alignment |
| Risk | Position sizing / stops | ATR-based stop, fixed dollar, percentage risk |
| Session | Time window definition | RTH only, pre-market, London overlap |

### Registry Schema

```json
{
  "id": "ENTRY-ORB-BREAKOUT-001",
  "type": "entry",
  "name": "Opening Range Breakout",
  "parameters": {
    "or_minutes": {"type": "int", "default": 30, "range": [15, 60]},
    "breakout_filter": {"type": "string", "default": "close", "options": ["close", "high_low"]}
  },
  "inputs": ["open", "high", "low", "close", "volume", "datetime"],
  "outputs": ["signal", "reference_price"],
  "source_strategies": ["orb_009"],
  "performance_notes": "Works best on MGC-Long, medium-vol regime"
}
```

### Interface Contract

Every component implements:
```python
def compute(df: pd.DataFrame, **params) -> pd.DataFrame:
    """Returns df with component-specific output columns."""
```

---

## 2. Combiner

**Purpose:** Generate candidate strategies by combining components.

### Combination Rules

1. Every strategy must have: 1 entry + 1 exit + 1 risk model
2. Filters and session constraints are optional (0 or more)
3. Invalid combinations are pruned before backtesting:
   - Long-only entry + short-only filter → skip
   - Incompatible timeframes → skip
   - Duplicate of existing strategy (by component hash) → skip

### Combination Modes

| Mode | Description |
|------|-------------|
| Exhaustive | All valid combinations (small registries) |
| Guided | User-specified entry + vary exits/filters |
| Mutation | Take existing strategy, swap one component |
| Crossover | Combine components from two successful strategies |

### Output

Each combination produces a `CandidateStrategy` object:
```python
@dataclass
class CandidateStrategy:
    entry: Component
    exit: Component
    filters: list[Component]
    risk: Component
    session: Component | None
    id: str  # hash of component combination
```

---

## 3. Evaluator

**Purpose:** Backtest and score candidates against promotion criteria.

### Evaluation Pipeline

```
Candidate Strategy
    ↓
[1] Baseline Backtest (all assets × modes)
    ↓ Filter: PF > 1.0
[2] Transaction Cost Adjustment
    ↓ Filter: Net PF > 1.2
[3] Top-Trade Removal
    ↓ Filter: PF stays > 1.0
[4] Walk-Forward Split (2024 vs 2025)
    ↓ Filter: Both periods PF > 0.8
[5] Parameter Stability (if parameterized)
    ↓ Filter: >75% of variations profitable
[6] Bootstrap CI (10K resamples)
    ↓ Filter: Lower CI bound > 0.9
[7] Deflated Sharpe Ratio
    ↓ Filter: DSR > 0.90
    ↓
CANDIDATE VALIDATED
```

### Scoring Function

```
score = (
    0.30 * normalize(net_sharpe) +
    0.25 * normalize(net_pf) +
    0.20 * normalize(1 / max_drawdown) +
    0.15 * normalize(dsr) +
    0.10 * normalize(trade_count / 50)  # penalize <50 trades
)
```

### Batch Processing

- Run candidates in parallel (multiprocessing)
- Cache intermediate results (avoid re-backtesting identical signals)
- Track all trials for DSR correction (total trials count matters)

---

## 4. Promotion Pipeline

**Purpose:** Move validated candidates through status stages.

### Status Flow

```
generated → baseline_tested → cost_adjusted → robustness_tested →
candidate_validated → correlation_checked → deployment_ready
```

### Promotion Rules

| Gate | Criteria |
|------|----------|
| baseline_tested | PF > 1.0 on at least one asset/mode |
| cost_adjusted | Net PF > 1.2 after commission + slippage |
| robustness_tested | Passes top-trade, walk-forward, parameter stability |
| candidate_validated | DSR > 0.90, bootstrap CI lower bound > 0.9 |
| correlation_checked | Daily PnL r < 0.15 vs all existing portfolio strategies |
| deployment_ready | Improves portfolio Sharpe OR reduces drawdown overlap |

---

## 5. Portfolio Optimizer

**Purpose:** Evaluate whether a validated candidate improves the live portfolio.

### Optimization Steps

1. Add candidate to existing portfolio
2. Compute portfolio metrics (Sharpe, MaxDD, Calmar, correlation matrix)
3. Run Monte Carlo (10K reshuffles) on expanded portfolio
4. Compare to current portfolio:
   - Does Sharpe improve?
   - Does MaxDD decrease?
   - Does drawdown overlap decrease?
   - Does the candidate survive prop rules?

### Sizing

- Default: equal weight (1 contract)
- Advanced: ERC weights from inverse vol
- Constraint: total contracts ≤ prop cap

---

## 6. Harvester Integration

**Purpose:** Feed new raw strategies into the pipeline automatically.

### Current State
- Manual: Claude-assisted TradingView script discovery
- 76 scripts harvested across 8 families
- Clawbot/OpenClaw integration planned but not built

### Target State
- Scheduled harvest (2x weekly) from TradingView trending scripts
- Auto-categorize into families using keyword matching
- Auto-score using existing triage criteria
- Feed convert_now candidates directly to Combiner

---

## 7. Automation Roadmap

### Phase A: Semi-Automated (target: after paper trading)

| Task | Frequency | Implementation |
|------|-----------|---------------|
| Component extraction | Manual | Extract entries/exits from validated strategies |
| Combination testing | On-demand | CLI: `python3 evolve.py --mode guided --entry orb_breakout` |
| Evaluation pipeline | Automated | Full 7-step pipeline runs without intervention |
| Promotion tracking | Automated | Status updates in strategy meta.json |

### Phase B: Fully Automated (target: 3-6 months)

| Task | Frequency | Implementation |
|------|-----------|---------------|
| Harvest new scripts | 2x weekly | Scheduled job, auto-categorize |
| Exhaustive combination | Weekly | Full registry × registry sweep |
| Portfolio reoptimization | Monthly | Re-run portfolio optimizer with new candidates |
| Performance monitoring | Daily | Live vs backtest drift detection |

### Phase C: Adaptive (target: 6-12 months)

| Task | Frequency | Implementation |
|------|-----------|---------------|
| Dynamic component weighting | Monthly | Weight components by recent performance |
| Regime-adaptive selection | Real-time | Switch active strategies by detected regime |
| Parameter adaptation | Monthly | Walk-forward parameter refresh |
| Auto-decommission | Monthly | Retire strategies with decaying edge |

---

## Implementation Notes

### Technology Stack
- **Language:** Python 3.14 (current lab environment)
- **Parallel execution:** multiprocessing (no external dependencies)
- **Data:** Databento CME 5m bars (existing pipeline)
- **Storage:** JSON + CSV (existing pattern), SQLite for large-scale tracking
- **No external ML dependencies** — pure numpy/pandas (lab constraint: no scipy)

### File Structure (Proposed)

```
evolution/
  engine.py           # Main orchestrator
  registry.py         # Component registry
  combiner.py         # Strategy combination logic
  evaluator.py        # Backtest + scoring pipeline
  promoter.py         # Status management
  portfolio_opt.py    # Portfolio-level optimization
  config.json         # Engine configuration
  components/
    entries/          # Entry component implementations
    exits/            # Exit component implementations
    filters/          # Filter component implementations
    risk/             # Risk model implementations
```

### Key Constraints
- Must work without scipy (pure numpy implementations for stats)
- Must track total trials for DSR correction
- Must preserve existing engine interface (`generate_signals(df) -> df`)
- Component combinations must output the same interface as hand-coded strategies

---

## Open Questions (for future resolution)

1. **Parameter search:** Grid search vs Bayesian optimization vs random search?
2. **Lookback window:** How much data is "enough" for validation? (Current: ~2 years)
3. **Auto-harvest scope:** TradingView only, or expand to GitHub/academic papers?
4. **Regime adaptation:** Per-component or per-strategy regime switching?
5. **Multi-asset correlation:** How to handle correlation when adding 5+ strategies?

---
*Design specification created 2026-03-08*
*Status: Architecture only — no code until Phase 7 paper trading completes*
