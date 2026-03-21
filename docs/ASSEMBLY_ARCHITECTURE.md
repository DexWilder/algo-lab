# FQL Elite Strategy Assembly Architecture

*From wide-net harvest to component-based strategy assembly.*
*Effective: 2026-03-20*

---

## Mission

FQL should not only find strategies. It should become better at finding,
preserving, connecting, recombining, and evolving the best components
into elite algos.

The endgame is not "find a bunch of scripts." It is: build a discovery
factory that can harvest, remember, connect, mutate, and validate ideas
better than a human browsing manually ever could.

---

## Architecture Layers

```
Layer 1: Wide-Net Intake (LIVE — 6 helpers, 8+ source classes)
    │
Layer 2: Component Tagging (LIVE — component_type in schema v3.1)
    │
Layer 3: Component Catalog + Search (BUILD NEXT)
    │
Layer 4: Convergence Scoring (BUILD NEXT)
    │
Layer 5: Recombination Assistant (BUILD AFTER 100+ FRAGMENTS)
    │
Layer 6: Crossbreeding Engine (BUILD AFTER 300+ ENTRIES)
```

---

## Build Order

### Phase 1: Component Catalog + Search (Next Build)

**What:** A queryable index of strategy components — entries, exits,
filters, overlays, behaviors, and effects — extractable from both new
harvest notes and existing rejected/archived strategies.

**Why now:** 113 strategies in registry. 25 rejected. Many contain
salvageable fragments (entry logic that worked on the wrong asset, exit
logic that could improve another strategy, filters that were validated
but the parent failed for other reasons). These fragments are invisible
today because the registry only stores whole strategies.

**Schema additions:**

```json
// On each strategy entry (extends existing component_type)
"components": {
    "entry": "Fade impulse > 1.5x 20d median at 14:00 ET",
    "exit": "Fixed time 14:25 ET or 60% retracement",
    "filter": "Impulse threshold 1.5x median",
    "sizing": null,
    "regime": "HIGH_VOL preferred (PF 1.64 vs 1.04 low-vol)",
    "timing": "13:45-14:25 ET afternoon window",
    "asset_scope": "ZN (rates)",
    "validation_status": "validated_in_parent"
}
```

Each component gets a `validation_status`:
- `validated` — tested and passed in a live strategy
- `validated_in_parent` — parent strategy validated this component
- `rejected_in_context` — failed in this context but may work elsewhere
- `untested` — harvested but not yet tested
- `salvaged` — extracted from a rejected strategy

**Query interface:**

```python
# scripts/component_search.py
def search_components(
    component_type=None,    # "entry", "exit", "filter", etc.
    asset_scope=None,       # "ZN", "MES", "rates", "energy"
    factor=None,            # "VOLATILITY", "CARRY", etc.
    validation_status=None, # "validated", "untested", etc.
    min_convergence=0,      # minimum convergent sources
):
    """Return matching components from the registry."""
```

Example queries this enables:
- "Show me all exit_logic components for rates" → finds time exits,
  retracement exits, stop methods used in ZN strategies
- "Show me all validated filters" → impulse threshold, vol regime,
  z-score — all tested in live strategies
- "Show me all rejected parents with salvageable components" →
  Treasury-Cash-Close-Reversion (salvageable: afternoon reversion timing)

### Phase 2: Convergence Scoring (Build Alongside Phase 1)

**What:** When a mechanism appears in multiple independent sources,
automatically boost its priority in the registry.

**Implementation:**

```python
# In harvest_engine.py or claw_control_loop.py
def check_convergence(new_note, registry):
    """Check if new_note's mechanism matches existing entries."""
    matches = find_similar_mechanisms(new_note.summary, registry)
    for match in matches:
        if new_note.source != match.source_category:
            # Different source confirms same mechanism
            match.convergent_sources.append({
                "source": new_note.source,
                "url": new_note.source_url,
                "date": today,
            })
            if len(match.convergent_sources) >= 2:
                match.review_priority = "HIGH"
                # Flag for priority review
```

**Scoring rules:**
- 1 source: baseline priority
- 2 independent sources: +1 priority level (e.g., MEDIUM → HIGH)
- 3+ independent sources: automatic priority review flag
- "Independent" = different source_category (academic vs TradingView
  vs practitioner blog vs Reddit counts as independent)

### Phase 3: Recombination Assistant (After 100+ Fragments)

**What:** A tool that suggests component combinations worth testing.

**When:** After enough fragments are tagged with component-level
validation status and context scope. ~100 fragments minimum.

**How it scores combinations:**

```python
def score_combination(entry, exit, filter, asset, session):
    score = 0

    # Portfolio gap fill
    score += gap_bonus(entry.factor)           # +3 for HIGH gap

    # Source convergence
    score += convergence_bonus(entry, exit)     # +2 if both validated independently

    # Context compatibility
    if entry.asset_scope == exit.asset_scope:
        score += 2                              # Compatible context
    if entry.timing overlaps exit.timing:
        score += 1                              # Session-compatible

    # Validated components
    if entry.validation_status == "validated":
        score += 2
    if exit.validation_status == "validated":
        score += 2

    # Portfolio diversification
    score += direction_bonus(entry)             # +1 for short-biased
    score += session_bonus(entry.timing)        # +1 for non-morning
    score += asset_bonus(entry.asset_scope)     # +1 for non-equity

    # Closed-family check (BLOCKS, not just penalizes)
    if is_closed_family(entry, exit):
        return -999                             # Do not resurrect dead mechanisms

    return score
```

**Rejection rules for combinations:**
- BLOCK if combination recreates a closed family
- BLOCK if both components failed in same context
- PENALIZE if combination adds to crowded factor/asset/session
- PENALIZE if no component has been validated in any context

### Phase 4: Component-Level Validation Memory (After Phase 3)

**What:** Track which components have been tested in which contexts,
and what the results were.

**Why:** A filter that failed on MES morning may work on ZN afternoon.
An exit that degraded one strategy may improve another. Component-level
validation memory prevents re-testing the same component in the same
context while encouraging testing in new contexts.

**Schema:**

```json
"component_validation_history": [
    {
        "component": "impulse_threshold_1.5x",
        "context": "ZN_afternoon_14:00-14:25",
        "result": "validated",
        "pf_contribution": "+0.34 vs unconditional",
        "date": "2026-03-20"
    },
    {
        "component": "impulse_threshold_1.5x",
        "context": "ZN_close_15:00-15:25",
        "result": "rejected",
        "pf_contribution": "-0.09 vs unconditional",
        "date": "2026-03-20"
    }
]
```

### Phase 5: Portfolio Contribution / Replacement Logic (Ongoing)

This already exists in the probation scoreboard and portfolio gap
dashboard. The assembly architecture connects to it by:

- Using gap scores to prioritize which combinations to test first
- Using contribution analysis to decide whether an assembled strategy
  replaces an incumbent or adds alongside
- Using overlap analysis to reject combinations that are redundant
  with existing strategies

### Phase 6: Crossbreeding Engine (After 300+ Entries)

**What:** Automated system that generates, scores, and queues component
combinations for batch testing.

**When:** When the component catalog has enough validated fragments to
make automated search more efficient than manual hypothesis-driven design.

**This is explicitly premature today.** 113 entries, 112 full_strategy,
1 sizing_overlay. The fragment data doesn't exist yet. Build schema,
accumulate data, automate when data justifies it.

---

## Schema Changes Still Needed

### Immediate (Phase 1)

Add `components` dict to registry entries:

```json
"components": {
    "entry": "<description or null>",
    "exit": "<description or null>",
    "filter": "<description or null>",
    "sizing": "<description or null>",
    "regime": "<description or null>",
    "timing": "<description or null>",
    "asset_scope": "<asset or class>",
    "validation_status": "validated | rejected_in_context | untested | salvaged"
}
```

### Near-Term (Phase 2)

Add convergence-aware priority boosting to `compute_priorities()`.

### Future (Phase 3+)

Add `component_validation_history` list. Add `crossbreed_candidate` bool.
Add `implementation_difficulty` enum (low/medium/high). Add
`salvageability` enum (none/partial/full).

---

## How Source Convergence Influences Ranking

| Convergence Level | Priority Effect | Action |
|-------------------|----------------|--------|
| 1 source | Baseline | Normal review |
| 2 independent sources | +1 level | Elevated review |
| 3+ independent sources | Auto-flag HIGH | Priority conversion candidate |
| Curated digest source confirms | +1 bonus | Higher-signal confirmation |
| Academic + practitioner confirms | +2 bonus | Strongest possible convergence |

"Independent" means different source_category. Two TradingView scripts
saying the same thing = 1 source. TradingView + Quantpedia + Alpha
Architect blog = 3 independent sources.

---

## How Closed-Family Memory Works in Assembly

The recombination assistant must check every proposed combination against
the closed-family list in `harvest_config.yaml`. A combination is BLOCKED if:

1. It recreates a known-dead mechanism (e.g., overnight equity
   continuation + any vol filter = still dead, filter was proven
   counterproductive)
2. Both components were rejected in the same context
3. The proposed combination is a cosmetic variation of a prior rejection

A combination is ALLOWED despite closed-family overlap if:
1. The asset/session/regime is materially different
2. The new hypothesis explicitly addresses the prior failure mode
3. The combination introduces a genuinely new component not present
   in the prior test

---

## Governance

This architecture is governed by the same principles as the rest of FQL:

- **Broad intake first, ruthless filtering later.** The component catalog
  should capture everything. The recombination assistant should be strict.
- **Forward evidence outranks backtest fantasy.** Assembled strategies
  must survive the same validation battery as discovered strategies.
- **No free passes for assembled strategies.** A combination of two
  validated components is not automatically validated itself. It must
  prove its portfolio contribution through forward evidence.
- **Elite standard at every layer.** A mediocre combination is worse
  than no combination. The assembly engine exists to find elite outliers,
  not to generate volume.
