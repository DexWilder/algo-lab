# FQL Harvest Expansion Plan — Hedge-Fund-Level Strategy Memory

*Aggressive discovery, selective conversion. Build the catalog first.*
*Effective: 2026-03-17*

---

## Philosophy

Most hedge funds maintain strategy catalogs of 500-2,000+ ideas. FQL has 103.
The goal is to build a much larger idea base while keeping conversion
discipline tight. Store aggressively, test selectively.

**The catalog IS the competitive advantage.** Having 500 tagged, clustered,
deduplicated ideas means future research sprints can immediately access
the best candidates for any factor gap, asset class, or market regime.

---

## Source Priority (6 lanes, ranked)

### Tier 1 — High volume, high quality

| Lane | Cadence | Cap/Run | Status |
|------|---------|---------|--------|
| **OpenClaw tactical** | Weekly | 10 | ACTIVE |
| **OpenClaw strategic** | Weekly | 15 | ACTIVE — increase cap |
| **TradingView scan** | Weekly | 10 | ACTIVE — increase to weekly |

### Tier 2 — Medium volume, curated

| Lane | Cadence | Cap/Run | Status |
|------|---------|---------|--------|
| **Academic review** | Biweekly | 8 | ACTIVATE |
| **YouTube/practitioner extraction** | Biweekly | 5 | ACTIVATE |

### Tier 3 — Low volume, periodic

| Lane | Cadence | Cap/Run | Status |
|------|---------|---------|--------|
| **Legacy revival** | Monthly | 3 | ACTIVATE |

### Weekly intake target: 30-50 ideas staged, 10-20 accepted to registry

---

## Tagging Schema (mandatory for every idea)

Every idea entering the registry MUST have these tags:

### Required Tags

```
factor:        EVENT | CARRY | STRUCTURAL | VOLATILITY | MOMENTUM | VALUE
asset_class:   equity_index | metal | energy | rate | fx | multi
horizon:       intraday | daily | swing | weekly | monthly
session:       morning | midday | afternoon | close | overnight | london |
               tokyo | all_day | daily_close | event_window
direction:     long | short | both
source_type:   academic | tradingview | practitioner | openclaw | internal |
               youtube | legacy
testability:   testable_now | needs_data | needs_engineering | needs_definition
blocker:       none | blocked_by_data | blocked_by_execution |
               blocked_by_engineering | blocked_by_ambiguity
```

### Optional Tags

```
family_closed:     true/false (is this in a closed family?)
momentum_highbar:  true/false (momentum that passes the high-bar rule)
salvage_eligible:  true/false
convergent_with:   [strategy_id] (confirms an existing idea)
overlaps_with:     [strategy_id] (potentially redundant)
regime_dependent:  true/false
```

---

## Dedupe and Clustering Rules

### Before accepting any idea:

1. **Hash check:** content hash against manifest (automatic)
2. **Name similarity:** check registry for similar strategy names
3. **Concept match:** same family + same asset + same session = potential duplicate
4. **Cluster assignment:** group into concept clusters:
   - Gap-fade cluster (CLOSED — 3 failures)
   - Overnight premium cluster (CLOSED — 2 tests)
   - Session breakout cluster
   - Event-day reaction cluster
   - Trend/momentum cluster
   - Vol compression cluster
   - Carry/macro cluster

### Clustering action:

- If idea falls in a CLOSED cluster → reject unless materially different mechanism
- If idea falls in an existing cluster with 3+ ideas → flag as low-priority unless it's clearly the best representative
- If idea opens a NEW cluster → flag as high-priority

---

## Weekly Review Flow

### Monday (30 min): Harvest + Stage

```bash
# Run all active harvest lanes
python3 research/harvest_engine.py --run

# Check what was staged
python3 research/harvest_engine.py --status
```

### Tuesday (45 min): Review + Tag + Accept/Reject

For each staged note:
1. Read the note
2. Apply mandatory tags
3. Check dedupe/clustering
4. Decision: ACCEPT / REJECT / MERGE with existing idea
5. If ACCEPT: add to registry with full tags
6. If REJECT: log reason in manifest

### Wednesday (15 min): Conversion check

```bash
# Is anything in the queue ready and worth converting?
python3 research/operating_dashboard.py
```

Only convert if:
- The candidate fills a factor/asset gap
- It's clearly the best representative in its cluster
- Current probation strategies don't need attention first

### Friday (20 min): Scorecard + Digest

```bash
python3 research/weekly_scorecard.py
python3 research/weekly_intake_digest.py
python3 research/operating_dashboard.py
```

---

## Quality Gates

### What keeps quality high at higher volume:

1. **Mandatory tagging** — forces structured thinking about every idea
2. **Cluster assignment** — prevents accepting the 5th variant of a tested concept
3. **Closed family enforcement** — automatic rejection of ideas in dead families
4. **Factor-aware prioritization** — gaps get priority, overcrowded factors get deprioritized
5. **Conversion bottleneck is intentional** — accept 20 ideas/week, convert 1-2 max
6. **Best-representative rule** — each cluster should have ONE clear best candidate, not 5 mediocre ones

### Red flags that mean quality is dropping:

- More than 50% of staged notes are rejected → tighten search terms
- Registry growing but no new clusters forming → harvesting redundant ideas
- Conversion queue backed up with > 10 items → slow down intake
- Same concept appearing from multiple sources → it's already captured, stop harvesting it

---

## Activation Sequence

### Phase 1 (immediate): Increase existing lane caps

```yaml
openclaw_tactical: max_per_run: 10 (was 5)
openclaw_strategic: max_per_run: 15 (was 10)
tradingview_scan: cadence: weekly (was biweekly), max_per_run: 10 (was 8)
```

### Phase 2 (this week): Activate academic + practitioner lanes

```yaml
academic_review:
  enabled: true
  cadence: biweekly
  max_per_run: 8
  sources: [SSRN, Quantpedia, QuantifiedStrategies, AlphaArchitect]

youtube_practitioner:
  enabled: true
  cadence: biweekly
  max_per_run: 5
  notes: "Extract mechanical rules only. No discretionary methods."
```

### Phase 3 (next month): Activate legacy revival

```yaml
legacy_revival:
  enabled: true
  cadence: monthly
  max_per_run: 3
  filters: [IMPLEMENTATION_BUG, SAMPLE_INSUFFICIENT, WALK_FORWARD_UNSTABLE]
```

---

## Catalog Milestones

| Milestone | Target | Timeline |
|-----------|--------|----------|
| 150 strategies | Registry growth | 2-3 weeks |
| 200 strategies | Catalog depth | 4-6 weeks |
| 300 strategies | Hedge-fund-level base | 8-12 weeks |
| 500 strategies | Full institutional memory | 6 months |

At each milestone, run genome classifier and factor decomposition
to verify the catalog is growing in the RIGHT dimensions, not just
getting bigger.

---

## What Does NOT Change

- Probation strategies still accumulate forward evidence undisturbed
- Conversion remains selective (1-2 per week max)
- Closed families stay closed
- Momentum high-bar rule stays enforced
- FISH security policy stays enforced
- Forward runner logic stays unchanged
- No new probation strategies without validation battery
