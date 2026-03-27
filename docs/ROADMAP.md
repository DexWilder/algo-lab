# FQL Roadmap — Re-Ranked 2026-03-27

*Sorted by what the system actually needs next, not what sounds interesting.*
*Re-ranked based on: 14 components extracted, 73% fragment share, 40 forward*
*trades, 5 source lanes producing, 0 convergent sources, April 3 checkpoint ahead.*

---

## Tier 1: Build Soon (Before or Shortly After April 3)

These items have data to support them and directly improve the next phase.

### 1a. Component-Level Validation Memory

**Why now:** 14 strategies have extracted components. Fragments are flowing
(73% share). But there's no memory of which components have been tested in
which contexts. The impulse threshold filter was validated on ZN afternoon
but rejected on ZN close — that knowledge exists in notes but not in a
queryable structure.

**What it does:**
- Track per-component: which context it was tested in, what the result was
- Prevent retesting the same component in the same context
- Encourage retesting in different contexts
- Feed the future recombination assistant with validated/rejected data

**Data threshold:** Already met — 14 strategies with components, 2 rejected
strategies with salvageable components. Enough to be useful.

**Effort:** ~2 hours. Schema extension + backfill from existing test results.

### 1b. Energy / VALUE Targeted Discovery Plan

**Why now:** Both are HIGH-priority gaps in the target portfolio. Energy has
0 strategies and 0 testable ideas. VALUE has 0 strategies and 0 ideas.
The harvest system is producing notes but hasn't found ideas for these gaps.

**What it does:**
- Define specific search themes for Energy (crude oil microstructure,
  energy seasonal, MCL session effects, storage/contango strategies)
- Define specific search themes for VALUE (fundamental value, earnings
  yield, PPP-based, commodity fair value, real yield)
- Add targeted queries to helper search lists
- Add specific Claw directive emphasis for these gaps

**Data threshold:** N/A — this is a search configuration, not architecture.

**Effort:** ~1 hour. Config changes to harvest_config.yaml + helper queries.

### 1c. Walk-Forward Robustness Matrix

**Why now:** When challengers approach their promotion gates (VolManaged in
~5 weeks, ZN-Afternoon in ~7 months), the validation battery needs a clean
robustness grid. The battery exists (`run_validation_battery.py`) but the
results aren't surfaced in a matrix format showing regime × time × asset
robustness in one view.

**What it does:**
- Format validation battery results as a visual matrix
- Show which cells pass/fail across regimes, time periods, parameters
- Make the promotion decision data cleaner to read

**Data threshold:** Not needed until first promotion gate (~5 weeks).
Build before then.

**Effort:** ~2 hours. Visualization + formatting of existing battery output.

---

## Tier 2: Build After April 3 If Checkpoint Is Green

These depend on the checkpoint confirming that the current system is working.

### 2a. Convergence Scoring

**Gate:** ≥ 5 cross-source matches in the registry (currently 0).

**Why gated:** Convergence scoring is useless without convergent data.
The April 3 checkpoint will show whether the widened harvest + improved
attribution is producing cross-source matches. If yes, build it. If no,
wait another cycle.

**What it does:**
- Auto-boost priority when 2+ independent sources confirm the same mechanism
- Feed recombination scoring with confidence signals
- Make source diversity a quantitative input to candidate ranking

**Effort:** ~3 hours. Priority scoring function + registry integration.

### 2b. Source-Role-Based Lane Tuning

**Gate:** April 3 checkpoint confirms which lanes are primary/fragment/support.

**What it does:**
- Raise caps on confirmed primary sources (digest likely)
- Lower or maintain caps on confirmed support sources
- Expand feed lists for confirmed high-yield categories
- Possibly add more digest feeds if Quantpedia + ReSolve prove out

**Effort:** ~30 minutes. Config changes only.

### 2c. Strategy Contribution Operationalization

**Gate:** At least 1 challenger approaching promotion gate with forward data.

**What it does:**
- Run marginal Sharpe analysis on challengers with forward evidence
- Compute portfolio-with vs portfolio-without for each challenger
- Feed the promotion decision with quantitative contribution data
- Connect to the Elite Promotion Framework rubric

**Effort:** ~2 hours. Script that computes contribution from trade log data.

---

## Tier 3: Keep Later (Not Justified Yet)

These need significantly more data or catalog depth before they add value.

### 3a. Recombination Assistant

**Gate:** ≥ 100 tagged fragments in the catalog.
**Current:** ~20 fragments. Need 5x more.

**Why later:** The recombination assistant suggests component combinations
worth testing. With only 20 fragments, manual review during Friday sessions
is sufficient. Automation adds value when the fragment space is too large
to review manually.

### 3b. Crossbreeding Engine

**Gate:** ≥ 300 registry entries with component data.
**Current:** 14 with components. Need 20x more.

**Why later:** Automated assembly + batch testing. Premature at current scale.

### 3c. Strategy Genome Map (Visualization)

**Gate:** Component catalog has enough entries to visualize meaningfully.
**Current:** 14 strategies with components. Useful but not urgent.

**Why later:** The component search tool (`fql components`) serves the same
purpose as a genome map at current scale. When the catalog reaches ~50
strategies with components, a visual map adds real value.

### 3d. Exit Evolution Engine

**Gate:** ≥ 10 validated exit components across different contexts.
**Current:** ~5 exit components extracted (time exits, retracement, ATR).

**Why later:** Exit evolution tests whether swapping exit logic improves
existing strategies. Needs a critical mass of validated exit alternatives.

### 3e. Full Strategy Generation Engine

**Gate:** Recombination assistant proven + crossbreeding engine operational.

**Why later:** This is the endgame — automated strategy assembly from
validated components. Every prior phase must be working first.

---

## What Moved Up (vs Prior Roadmap)

| Item | Was | Now | Why |
|------|-----|-----|-----|
| Component validation memory | Phase 4 | **Tier 1a** | Fragments are flowing — need to track what works where |
| Energy/VALUE discovery | Mentioned as gap | **Tier 1b** | Target portfolio makes these explicit blind spots |
| Walk-forward matrix | Not explicit | **Tier 1c** | Needed before first promotion gate |

## What Moved Down

| Item | Was | Now | Why |
|------|-----|-----|-----|
| Convergence scoring | Phase 2 | **Tier 2a (gated)** | 0 convergent sources — no data to score |
| Genome map | Phase 3 | **Tier 3c** | Component search tool covers the need at current scale |

## What Stayed the Same

| Item | Position | Why |
|------|----------|-----|
| Recombination assistant | Later | Need 100+ fragments |
| Crossbreeding engine | Later | Need 300+ entries |
| Exit evolution | Later | Need 10+ validated exit components |

---

## Single Best Next Item Once Checkpoint Clears

**Component-level validation memory (1a).**

It's the foundation that makes every later module smarter:
- Convergence scoring uses it to weight validated components higher
- Recombination assistant uses it to prefer tested components
- Walk-forward matrix uses it to show which components survived
- Exit evolution uses it to compare exit methods across contexts

Building it now means every future build inherits better data.

---

## Post-Checkpoint Build Queue (if April 3 is green)

*Locked 2026-03-27. Execute in this order.*

1. **Component validation memory** — schema + backfill (~2h)
2. **Review Energy/VALUE harvest results** — did blind-spot queries produce ideas? (~30m)
3. **Walk-forward robustness matrix** — visualization for promotion gates (~2h)
4. **ATR vol regime filter validation** — test as reusable component across parents (~1h)

Then re-evaluate Tier 2 items based on checkpoint data.
