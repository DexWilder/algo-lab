# Strategy Discovery Pipeline

*Architecture for continuous strategy sourcing, validation, and portfolio integration.*
*Last updated: 2026-03-15*

---

## Overview

FQL's competitive advantage comes from volume of ideas combined with ruthless quality gates. The discovery pipeline is designed to continuously generate, evaluate, and integrate new strategies into the portfolio while preventing duplication and overfitting.

```
Harvest (external sources)
    |
Deduplicate (registry check)
    |
Cheap Validation (baseline backtest, minimum thresholds)
    |
Full Validation Battery (10 criteria)
    |
Portfolio Contribution Analysis (marginal Sharpe, overlap, gap fit)
    |
Promotion or Rejection (with full reason codes and salvage routing)
```

---

## Harvest Engine

### Sources

| Source | Type | Frequency | Tool |
|--------|------|-----------|------|
| TradingView public scripts | Pine scripts | Weekly | Manual + intake tools |
| GitHub quant repos | Python strategies | Weekly | Manual scan |
| Academic papers | Research ideas | Monthly | Manual review |
| Quant blogs and newsletters | Strategy concepts | Monthly | Manual review |
| Reddit / X discussions | Trade ideas | Weekly | Manual scan |
| YouTube strategy breakdowns | Video transcripts | Weekly | Manual review |
| Microstructure research | Market structure edges | Quarterly | Deep research |
| Internal crossbreeding | Component recombination | Automated | `research/crossbreeding/crossbreeding_engine.py` |
| Internal evolution | Parameter mutation | Automated | `research/evolution/evolution_scheduler.py` |

### Harvest Cadence

- **Weekly** -- TradingView, GitHub, social media scans
- **Monthly** -- Research sweep (papers, blogs, newsletters)
- **Quarterly** -- Discovery review (what worked, what gaps remain, priority adjustment)

### Harvest Output

Every harvested idea enters the registry with metadata:
- Source URL and attribution
- Strategy family classification
- Initial quality assessment
- Portfolio role hypothesis
- Similarity to existing strategies

---

## Deduplication

Before any validation work begins, check against the registry.

**Built module:** `research/strategy_registry.py`

**Checks:**
- Exact match on source URL
- Similarity match on strategy family + entry type + asset + session
- Genome overlap against existing strategies (>0.75 similarity = flagged)

If a near-duplicate exists:
- If the original was rejected: skip (unless the new variant addresses the rejection reason)
- If the original is active: evaluate as potential replacement only if it shows clear improvement
- Log the duplicate detection in the registry

---

## Cheap Validation

Fast, low-cost filtering to eliminate obviously non-viable candidates.

**Built module:** `research/batch_harvest_validation.py`

**Process:**
1. Run baseline backtest on primary asset (`backtests/run_baseline.py`)
2. Check minimum thresholds:
   - Profit factor > 1.0 on at least one asset/mode combo
   - Trade count >= 30
   - No obvious repainting
   - Session boundaries defined

**Reject immediately if:**
- No exits defined
- Martingale or grid logic
- Crypto-only (not adaptable to futures)
- Invite-only or obfuscated source
- Fewer than 10 trades across all assets

**Pass rate target:** 20-30% of harvested ideas should survive cheap validation.

---

## Full Validation Battery

10-criterion robustness assessment for candidates that pass cheap validation.

**Built module:** `research/validation/run_validation_battery.py`

**Criteria:**

| # | Test | Pass Condition |
|---|------|----------------|
| 1 | Walk-forward year splits | Both periods PF > 1.0 |
| 2 | Walk-forward rolling windows | >= 75% test windows PF > 1.0 |
| 3 | Regime stability | No catastrophic cells (PF < 0.5 with >= 10 trades) |
| 4 | Asset robustness | >= 2 of 3 assets PF > 1.0 |
| 5 | Timeframe robustness | >= 2 of 3 timeframes PF > 1.0 |
| 6 | Bootstrap PF confidence | Lower bound > 1.0 |
| 7 | Deflated Sharpe Ratio | DSR > 0.95 |
| 8 | Monte Carlo ruin probability | P(ruin at $2K DD) < 5% |
| 9 | Top-trade removal | PF > 1.0 without best trade |
| 10 | Parameter stability | >= 60% of parameter combinations profitable |

**Scoring:**
- Stability Score 0-10 (count of passed criteria)
- >= 7.0 with 0 hard failures: PROMOTE TO PARENT
- 5.0-6.9 or 1-2 failures: CONDITIONAL (PROBATION)
- < 5.0 or >= 3 failures: REJECT

**LOW_SAMPLE handling:** Slices with < 15 trades flagged but not counted as hard failures.

See `docs/research_pipeline.md` for full stage definitions.

---

## Portfolio Contribution Analysis

Candidates that pass validation are evaluated for portfolio fit.

**Built modules:**
- `research/strategy_contribution_analysis.py` -- Marginal Sharpe contribution
- `research/counterfactual_engine.py` -- Opportunity-cost analysis
- `research/portfolio_correlation_matrix.py` -- Correlation analysis

**Checks:**
- Marginal Sharpe: does adding this strategy improve portfolio Sharpe?
- Correlation: r < 0.3 vs all existing core strategies (r > 0.4 = REJECT)
- Overlap: genome similarity < 0.75 vs all active strategies
- Gap fit: does it address an identified portfolio gap?
- Session diversification: does it trade in underrepresented sessions?
- Asset diversification: does it add exposure to underrepresented assets?

---

## Salvage Lane

If a candidate fails validation, classify the failure mode and route salvageable ideas to controlled mutation tests.

### Salvageable Failure Modes

| Failure Mode | Salvage Approach |
|-------------|-----------------|
| Good edge, wrong session | Apply session restrictions |
| Good edge, wrong regime | Apply regime filters |
| Good entry, poor exit | Exit evolution testing |
| Marginal edge, high variance | Risk model adjustment |
| Good concept, wrong parameters | Parameter stability sweep |
| Regime-specific strength | Deploy as regime specialist |

### Salvage Rules

- **Maximum 3 salvage attempts** per candidate (prevent overfitting through iteration)
- Each salvage attempt must change exactly one variable (single-variable testing)
- Salvaged candidates must pass the full validation battery, not a reduced version
- If all salvage attempts fail: REJECT with full documentation

### Built Tools

- `research/exit_evolution.py` -- Exit variant testing (6+ variants on frozen entries)
- `research/bb_eq_evolution.py` -- Strategy-specific variant testing
- Session restriction testing via controller config
- Regime gating via `engine/regime_engine.py`

---

## Strategy Memory and Registry

Every strategy ever evaluated is stored in the registry with full metadata.

**Built module:** `research/strategy_registry.py`
**Data store:** `research/data/strategy_registry.json`

### Registry Fields

| Field | Purpose |
|-------|---------|
| ID | Unique identifier |
| Name | Human-readable name |
| Family | Strategy family (trend, momentum, reversion, etc.) |
| Asset | Primary trading asset |
| Session | Preferred trading session |
| Direction | Long, short, or both |
| Status | core, probation, testing, idea, rejected |
| Validation score | 0-10 from validation battery |
| Rejection reason | Why it was rejected (if applicable) |
| Source | Where the idea came from |
| Similarity cluster | Genome cluster assignment |
| Half-life status | Current edge decay status |
| Contribution status | Current portfolio contribution |
| Last review date | When last evaluated |

### Registry Integrity Rules

- No strategy ID reuse (ever)
- Rejected strategies are never deleted (institutional memory)
- Status changes require reason codes
- Registry is the single source of truth for strategy status

---

## Strategy Genome Map

Behavioral fingerprinting for diversity management and gap identification.

**Built module:** `research/strategy_genome_map.py`
**Output:** `research/genome/`

### Genome Dimensions

| Trait | Description |
|-------|-------------|
| Family | Strategy family classification |
| Entry type | Breakout, pullback, reversion, momentum, etc. |
| Exit type | ATR trail, time stop, target, signal-based |
| Regime specialization | Which regimes the strategy performs best in |
| Session behavior | Morning, midday, afternoon, close |
| Asset exposure | MES, MNQ, MGC, MCL, M2K |
| Portfolio role | Core earner, diversifier, hedge, regime specialist |
| Structural overlap | Similarity score vs other strategies |

### Gap Detection

The genome map enables identification of:
- Missing strategy families (what types of edges are absent?)
- Underrepresented sessions (are we concentrated in morning trades?)
- Asset gaps (which assets lack coverage?)
- Regime gaps (which regimes have no specialist?)
- Direction imbalance (too many longs vs shorts?)

**Built tools:**
- `research/opportunity_scanner.py` -- Portfolio gap identification
- `research/harvest_scheduler.py` -- Gap-targeted candidate surfacing
- `research/portfolio_opportunity_map.py` -- Opportunity visualization

---

## Discovery Metrics

Track discovery pipeline effectiveness over time:

| Metric | Target |
|--------|--------|
| Ideas harvested per month | 10-20 |
| Cheap validation pass rate | 20-30% |
| Full validation pass rate | 10-20% of cheap validation survivors |
| Portfolio integration rate | 1-2 new strategies per quarter |
| Time from harvest to decision | < 2 weeks |
| Registry completeness | 100% of evaluated ideas recorded |
| Duplicate detection rate | > 95% |

---

## Maintenance

This document should be updated when:
- New harvest sources are added
- Validation criteria change
- Salvage rules are adjusted
- New genome dimensions are defined
- Discovery metrics targets are revised

These documents must be periodically updated as the platform evolves. Any major module added to FQL must be reflected in the architecture documentation.
