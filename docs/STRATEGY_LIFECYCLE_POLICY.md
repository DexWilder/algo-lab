# FQL Strategy Lifecycle Policy

*Formal governance for every strategy from discovery to retirement.*
*Effective: 2026-03-18*

---

## Overview

Every strategy in FQL moves through a defined lifecycle. Each stage has
entry criteria, exit criteria, key metrics, and escalation triggers.
No strategy skips a stage. No strategy moves without evidence.

```
IDEA → TESTED → VALIDATION_PASS → PROBATION → CORE
                     ↓                 ↓          ↓
                  REJECTED          DOWNGRADE    KILL
                                       ↓          ↓
                                   ARCHIVED    ARCHIVED
```

---

## Stage 1: IDEA

*A cataloged strategy concept. Not yet coded or tested.*

### Entry Criteria
- Note exists in harvest manifest or registry with status=idea
- All mandatory tags applied (factor, asset_class, horizon, session,
  direction, testability, blocker)
- Passed dedupe check against registry (not a duplicate)
- Does not violate closed-family rules (or explicitly addresses the
  prior failure mode if it does)
- Does not violate momentum high-bar rule (or meets at least one
  acceptance criterion)

### Key Metrics
- **Testability score:** testable_now / needs_data / needs_engineering / needs_definition
- **Factor gap fill:** Does it address a HIGH or MEDIUM priority gap?
- **Cluster position:** Is it the best representative in its cluster?
- **Blocker clarity:** Is the blocker specific and potentially resolvable?

### Exit → TESTED
- You approve a conversion slot
- Spec is written and reviewed
- strategy.py is coded and passes import/signal smoke test
- Registry updated: status=testing, strategy_name set, spec_path set

### Exit → REJECTED
- Duplicate of existing idea (dedupe hit)
- Falls in closed family without addressing failure mode
- Untestable with no path to resolution
- Superseded by a better representative in the same cluster

### Caution Signals
- Blocker has no resolution path (may sit as idea indefinitely)
- Cluster already has 3+ ideas and none have been tested
- Idea is from a single source with no convergent evidence

---

## Stage 2: TESTED

*Strategy code exists. First-pass backtest results available.*

### Entry Criteria
- strategy.py exists and generates valid signals
- batch_first_pass has run (or manual first-pass backtest completed)
- Classification assigned: ADVANCE / SALVAGE / MONITOR / REJECT

### Key Metrics
- **Profit Factor** (primary): minimum 1.2 for ADVANCE
- **Trade count:** minimum 30 for statistical meaning (15 absolute floor
  for low-frequency strategies)
- **Walk-forward stability:** both halves show PF > 1.0
- **Cross-asset consistency:** edge appears on target asset, not random
- **Classification:** ADVANCE is the only path forward to validation

### Exit → VALIDATION_PASS
- Classification = ADVANCE (PF > 1.2, 30+ trades, WF stable)
- You approve proceeding to validation battery

### Exit → SALVAGE (one retry)
- Classification = SALVAGE (partial edge, identifiable fix)
- One controlled retry with exactly one variable changed
- Pre-declare the fix in registry before re-testing
- If salvage attempt also fails → REJECTED

### Exit → MONITOR
- Classification = MONITOR (signal exists but insufficient data)
- No active work. Wait for more data or market condition change.
- Re-test after 6 months or when blocker is resolved
- No expiration — can sit indefinitely

### Exit → REJECTED
- Classification = REJECT (PF < 1.0, structural loss, no viable edge)
- Log rejection_reason in registry with specific taxonomy code
- If 3+ strategies in same family rejected → family closed

### Escalation Triggers
- PF > 1.5 with 50+ trades → fast-track to validation
- PF between 1.0-1.2 but only in one direction → SALVAGE candidate
- Zero trades generated → implementation bug, fix before classifying

### Caution Signals
- High PF driven by 1-2 outlier trades
- Performance concentrated in a single crisis period
- Asset dominance (works on one asset, fails on all others)
- Carry/momentum conflation (proxy signal, not pure factor)

---

## Stage 3: VALIDATION_PASS

*Full validation battery completed. Strategy meets all quality gates.*

### Entry Criteria
- ADVANCE classification from first-pass
- Validation battery completed:
  - Walk-forward matrix (PF > 1.0 in both halves)
  - Parameter stability (no cliff edges, smooth PF surface)
  - Cross-asset test (works on intended asset, behavior on others documented)
  - Contribution simulation (positive or neutral marginal Sharpe)
- No kill criteria triggered on backtest data
- Drift baseline established

### Key Metrics
- **Walk-forward PF:** > 1.0 in both halves (ideally > 1.15)
- **Parameter stability:** PF varies < 30% across ±20% parameter range
- **Contribution:** Marginal Sharpe ≥ 0 (doesn't dilute portfolio)
- **Correlation to existing portfolio:** < 0.35 preferred, < 0.50 acceptable
- **Drawdown profile:** Max DD within 2x of backtest expectation

### Exit → PROBATION
- All validation checks pass
- You approve probation entry
- Allocation tier assigned (typically MICRO for new entrants)
- Forward runner updated to include strategy
- Probation start date and target trade count set

### Exit → REJECTED
- Walk-forward fails (one half PF < 0.8)
- Parameter stability fails (cliff edge found)
- Contribution is dilutive (marginal Sharpe < -0.5)
- Correlation > 0.50 with existing strategy that performs better

### Exit → MONITOR
- Validation mostly passes but insufficient data depth
- Wait for more history before committing a probation slot

### Escalation Triggers
- Contribution is strongly positive (marginal Sharpe > 1.0) → prioritize
  for probation entry
- Fills a factor gap with zero existing coverage → high-value candidate

### Caution Signals
- PF degrades from first-pass to walk-forward (overfitting risk)
- Works only with stop, fails without (edge may be fragile)
- Tight parameter sensitivity (PF collapses with small changes)

---

## Stage 4: PROBATION

*Strategy running in forward paper trading. Accumulating live evidence.*

### Entry Criteria
- Validation battery passed
- Probation slot approved by you
- Forward runner configured with strategy
- Allocation tier set (MICRO or REDUCED)
- Probation journal entry created with start date
- Target trade count and promotion PF threshold defined per strategy

### Key Metrics (in priority order)
1. **Forward PF** — single most important metric
2. **Forward trade count** — enough evidence to decide?
3. **Drawdown behavior** — within expected range?
4. **Walk-forward consistency** — forward matches backtest?
5. **Contribution** — adding value or taking space?
6. **Drift alerts** — edge structurally changed?
7. **Overlap/redundancy** — duplicating another strategy's returns?

### Review Schedule
- **Week 2:** Sanity check. Trades happening? No action needed.
- **Week 4:** Early signal. Downgrade possible if PF < 0.5 after 10+ trades.
- **Week 8:** Formal review. Apply full criteria matrix.
- **Week 12:** Final decision. Promote, extend (max 16 weeks), or remove.

### Strategy-Specific Thresholds

| Strategy | Target Trades | Promote PF | Continue PF | Downgrade PF | Remove PF |
|----------|--------------|------------|-------------|--------------|-----------|
| DailyTrend-MGC-Long | 15 | > 1.2 | 1.0-1.2 | < 1.0 | < 0.7 after 20 |
| MomPB-6J-Long-US | 30 | > 1.2 | 1.0-1.2 | < 1.0 | < 0.8 after 40 |
| FXBreak-6J-Short-London | 50 | > 1.1 | 1.0-1.1 | < 0.95 | < 0.85 after 60 |
| PreFOMC-Drift-Equity | 8 | > 1.2 | 1.0-1.2 | < 0.9 | < 0.7 after 12 |
| TV-NFP-High-Low-Levels | 8 | > 1.1 | 1.0-1.1 | < 0.9 | < 0.7 after 12 |

### Exit → CORE (Promotion)
- Forward trades meet target threshold
- Forward PF meets promote threshold
- No active ALARM drift alerts
- Contribution report shows positive or neutral
- No kill switch events
- You approve promotion

### Exit → DOWNGRADE
- Forward PF below downgrade threshold after sufficient trades
- Drift ALARM on primary session
- Edge disappeared (session or directional edge gone)
- Moved to status=testing, controller_action=OFF

### Exit → KILL (Removal)
- Forward PF below remove threshold after extended sample
- Kill switch fires
- Max single drawdown exceeds threshold ($2K warning, $5K remove)
- 3 probation strategies losing on the same day (correlation alarm)
- Moved to status=rejected with rejection_reason

### Escalation Triggers
- Week 4 PF > promote threshold with sufficient trades → consider
  early promotion at Week 6 (rare, needs strong evidence)
- No trades for 2+ consecutive weeks → investigate signal generation

### Caution Signals
- Forward PF between continue and downgrade range → watch closely
- All wins concentrated in a single week → regime-dependent
- Drift monitor showing DRIFT (not ALARM) → monitor, don't act yet

---

## Stage 5: CORE (Promotion)

*Strategy is a full member of the live portfolio.*

### Entry Criteria
- Probation review passed with promote decision
- Registry updated: status=core, controller_state=ACTIVE
- Allocation tier upgraded (MICRO→REDUCED or REDUCED→BASE)
- Post-promotion monitoring period: 4 weeks

### Key Metrics
- **Ongoing PF:** monitored via daily pipeline
- **Contribution:** marginal Sharpe tracked weekly
- **Half-life:** decay score monitored daily
- **Drift:** forward vs backtest comparison
- **Kill criteria:** evaluated weekly

### Tier Progression
- Promotion entry: MICRO → REDUCED, or REDUCED → BASE
- Tier-up criteria: 3 consecutive positive months, PF > 1.3, contribution positive
- Tier-down criteria: 2 consecutive negative months, PF < 1.0, or kill flag raised
- Maximum tier: BASE for most strategies. BOOST requires explicit approval
  and exceptional forward evidence (PF > 1.5, 100+ trades, strong contribution)

### Exit → DOWNGRADE
- Kill criteria flagged (dilution, redundancy, decay, or regime failure)
- Forward PF drops below 0.8 within 4 weeks of promotion (rollback)
- Contribution becomes dilutive + redundant simultaneously
- Tier reduced first; if problems persist, moved to testing/archived

### Exit → KILL
- Multi-flag kill (2+ kill criteria triggered simultaneously)
- Kill switch fires (emergency)
- Structural market change invalidates the strategy's mechanism

### Ongoing Monitoring
- Daily: health check, half-life, contribution, controller, drift
- Weekly: kill criteria review, integrity monitor
- Monthly: genome map position, factor concentration check

### Caution Signals
- Half-life status moves from HEALTHY to DECAYING
- Contribution drops from positive to neutral
- Regime controller assigns REDUCED or OFF action
- Correlation with another core strategy exceeds 0.35

---

## Stage 6: DOWNGRADE

*Strategy removed from active portfolio. May be recoverable.*

### Entry Criteria
- Kill criteria flagged OR probation review failed OR post-promotion
  rollback triggered
- Registry updated: status=testing or status=archived
- Controller action set to OFF
- Allocation tier set to OFF
- Forward runner updated to exclude strategy

### Key Metrics
- **Root cause:** Which kill criterion triggered? Is it fixable?
- **Backtest re-run:** Does the edge still exist in updated data?
- **Family health:** Are other strategies in the same family also degrading?

### Resolution Paths

| Root Cause | Action | Timeline |
|------------|--------|----------|
| Dilution (marginal Sharpe < 0) | Remove from portfolio. Re-test only if portfolio composition changes materially. | Archive unless portfolio changes |
| Redundancy (corr > 0.35) | Keep the stronger strategy, archive the weaker. | Immediate |
| Decay (recent Sharpe < 0.5) | Reduce tier → OFF. Monitor for 4 weeks. If recovery, re-enter probation. | 4-week watch |
| Regime failure | Review regime gates. If fixable, add/tighten gates and re-enter testing. | Spec fix + re-test |
| Post-promotion rollback (PF < 0.8) | Return to testing. Re-enter probation only with new evidence. | Back to testing |

### Exit → ARCHIVED
- No recovery path identified
- Root cause is structural (not regime or parameter)
- Family has 3+ failures → family closed

### Exit → TESTING (Re-entry)
- Root cause identified and fixed (specific, documented change)
- Counts as a salvage attempt (max 1 per strategy)
- Must pass validation battery again before probation

---

## Stage 7: KILL

*Permanent removal. Strategy is archived with full documentation.*

### Entry Criteria (any one sufficient)
- Multi-flag kill (2+ simultaneous kill criteria)
- Kill switch fires
- Forward PF < remove threshold after extended sample
- Max drawdown exceeds hard limit
- Structural market change invalidates mechanism
- You approve removal

### Required Documentation
- `rejection_reason`: specific taxonomy code from registry v3.0
  (STRUCTURAL_LOSS, SAMPLE_INSUFFICIENT, WALK_FORWARD_UNSTABLE,
  REGIME_DEPENDENT, REDUNDANT, IMPLEMENTATION_BUG, EDGE_DECAYED)
- `rejection_details`: what specifically failed and why
- `kill_flag`: which kill criterion triggered
- `kill_details`: numeric evidence
- State history preserved (all prior statuses with dates)

### Post-Kill Actions
- Registry: status=rejected, full rejection metadata
- Forward runner: strategy removed
- Allocation: tier=OFF
- Family check: if 3+ in same family now rejected → close family
- Genome map: flag as AVOID if family closed
- Harvest config: add to high_bar_families if applicable

### Reopening Criteria (Exceptional)
A killed strategy may be reconsidered ONLY if:
1. Material market structure change (documented, not speculative)
2. Fundamentally different approach within the same family
3. New data source that resolves the original failure mode
4. Explicit approval from you with written thesis

This is a HIGH BAR. Most killed strategies stay dead.

---

## Cross-Stage Rules

### Family-Level Governance
- 3+ rejections in the same family → family closed
- Closed families are added to `harvest_config.yaml` high_bar_families
- New ideas in closed families require explicit thesis addressing prior
  failure mode
- Family closure is logged in genome map as AVOID

### Factor Concentration
- Portfolio momentum concentration monitored (currently 54%)
- New momentum strategies require high-bar rule clearance
- Factor decomposition refreshed monthly or after portfolio changes

### Session Restrictions
- Session-specific strategies keep their session gates through all stages
- 6J strategies: US/London session restrictions preserved even after promotion
- Session drift ALARM on a probation strategy is an immediate review trigger

### One-Retry Rule
- Every strategy gets exactly one salvage attempt
- The fix must be pre-declared and singular (one variable changed)
- Salvage attempt expires after 30 days if not executed
- Failed salvage → permanent rejection

### Evidence Hierarchy (Applies at Every Stage)
1. Forward PF (most important — real market evidence)
2. Forward trade count (is the sample large enough?)
3. Drawdown behavior (within expected range?)
4. Walk-forward consistency (does forward match backtest?)
5. Contribution (adding or diluting portfolio?)
6. Drift alerts (structural change in edge?)
7. Overlap/redundancy (duplicating returns?)

---

## Quick Reference: Status Transitions

```
IDEA ──→ TESTED ──→ VALIDATION_PASS ──→ PROBATION ──→ CORE
  │         │              │                │            │
  │         ├→ SALVAGE     ├→ MONITOR       ├→ DOWNGRADE ├→ DOWNGRADE
  │         │   (1 retry)  │                │            │
  │         ├→ MONITOR     └→ REJECTED      ├→ KILL      └→ KILL
  │         │                               │
  └→ REJECTED └→ REJECTED                   └→ KILL

DOWNGRADE ──→ TESTING (re-entry, counts as salvage)
           ──→ ARCHIVED (no recovery path)

KILL ──→ ARCHIVED (permanent, requires exceptional criteria to reopen)
```
