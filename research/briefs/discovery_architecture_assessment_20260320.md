# Discovery Architecture Assessment — What's Missing, What's Premature

**Date:** 2026-03-20
**Context:** FQL has 113 strategies in registry, 8 source helpers active,
49 leads per weekly fetch, 7 launchd services running.

---

## Honest Assessment

The vision — full-spectrum intake, fragment capture, recombination engine,
strategy crossbreeding — is the right long-term target. But building all
of it now would be overengineering. Here's what actually earns its place
today vs what should wait.

### What's Genuinely Missing (Build Now)

**1. Component tagging in the harvest note format.**

The current note format captures whole strategies only. But the most
valuable things in the harvest backlog are often fragments — an entry
logic that works on a different asset, an exit method that could improve
an existing strategy, a regime filter that could gate an existing edge.

Missing: a `component_type` field in the note template that lets Claw
tag notes as one of:
- `full_strategy` — complete entry/exit/sizing logic
- `entry_logic` — testable entry condition only
- `exit_logic` — exit/target/stop method
- `filter` — regime/vol/time filter that gates an existing signal
- `sizing_overlay` — position sizing method (like VolManaged)
- `asset_behavior` — structural observation about a specific market
- `session_effect` — timing/session-specific pattern

This is a one-line addition to the note template. Zero engineering.
Claw tags it during synthesis. It makes the registry searchable by
component type when we later want to recombine.

**2. Source convergence tracking.**

When 3 independent sources describe the same mechanism, that's stronger
evidence than 1 source describing it once. The registry already has
`source_category` but no field for "this idea was also found in X."

Missing: a `convergent_sources` list field on registry entries. When
Claude reviews harvest notes and finds a duplicate that came from a
different source, instead of rejecting it, add the new source to the
existing entry's convergent_sources list. This turns duplicates into
signal strength.

**3. Cluster family relationships in registry.**

The registry has `family` and `genome_cluster` but no formal relationship
structure. The ZN-Afternoon-Reversion / Treasury-Cash-Close-Reversion
parent/child link was done via tags, which works but isn't queryable.

Missing: structured `relationships` field:
```json
"relationships": {
    "parent": "Treasury-Cash-Close-Reversion-Window",
    "children": [],
    "related": ["Treasury-Rolldown-Carry-Spread"],
    "salvaged_from": null,
    "components_used": ["afternoon_session_reversion", "impulse_threshold_filter"]
}
```

### What Should Wait (Premature Now)

**Strategy crossbreeding / evolution engine.** The idea of automatically
combining entry A with exit B with filter C is compelling but premature.
FQL has 113 strategies, ~25 rejected with documented failure modes, and
8 in probation. The catalog isn't deep enough for automated recombination
to beat manual hypothesis-driven design. Build this when the catalog
reaches 300+ entries and the component tagging has enough data to match
on.

**Automated fragment assembly.** Same reasoning. You need a critical
mass of tagged fragments before assembly logic adds value. Right now,
manual review during Friday sessions is sufficient.

**Multi-level strategy memory graph.** A graph database or knowledge
graph connecting strategies, components, factors, assets, and sources
would be powerful at scale but adds complexity FQL doesn't need yet.
The flat registry with tags and relationships fields handles the current
catalog size.

---

## What to Build Now

### Step 1: Extend note template with component_type

Add to `_note_template.md` and Claw's task instructions:

```markdown
- component_type: full_strategy | entry_logic | exit_logic | filter |
                  sizing_overlay | asset_behavior | session_effect
```

Claw tags this during note generation. Default: `full_strategy` for
backward compatibility.

### Step 2: Add convergent_sources to registry schema

When a harvest note describes a mechanism already in the registry from
a different source, add the new source to `convergent_sources` instead
of rejecting as duplicate:

```json
"convergent_sources": [
    {"source": "Quantpedia", "url": "...", "date": "2026-03-20"},
    {"source": "TradingView", "url": "...", "date": "2026-03-22"},
    {"source": "Alpha Architect blog", "url": "...", "date": "2026-03-25"}
]
```

Three independent sources = strong convergent evidence. Flag for
priority review.

### Step 3: Add relationships field to registry schema

```json
"relationships": {
    "parent": null,
    "children": [],
    "related": [],
    "salvaged_from": null,
    "components_used": []
}
```

This replaces ad-hoc tags like `parent_rejected:X` and `spawned_child:Y`
with a queryable structure.

### Step 4: Update harvest_engine.py to support component intake

When processing notes with `component_type != full_strategy`, stage them
differently — they don't need a full registry entry, they need a
component catalog entry that can be referenced by full strategies.

---

## Discovery Ranking Bias (Already Partially Implemented)

The harvest_config.yaml already has gap bonuses and noise penalties.
The additions needed:

| Bias | Current | Addition |
|------|---------|----------|
| Factor gap fill | +3 for HIGH gap | Already done |
| Source convergence | Not tracked | +2 when idea has convergent_sources >= 2 |
| Component reusability | Not tracked | +1 when component could improve existing parent |
| Short-bias | +2 | Already done |
| Non-equity / non-morning | +2 | Already done |

---

## Roadmap Summary

| Phase | What | When | Effort |
|-------|------|------|--------|
| **Now** | Component tagging in notes | Today | 10 min |
| **Now** | convergent_sources field in registry | Today | 30 min |
| **Now** | relationships field in registry | Today | 30 min |
| **Next month** | Component catalog (separate from strategy registry) | After 50+ fragments tagged | 2-3 hours |
| **3 months** | Cluster/recombination assistant (suggest component combos) | After 100+ fragments | 1 day |
| **6 months** | Strategy crossbreeding engine (automated assembly) | After 300+ registry entries | Multi-day |

The right pace: extend the schema now (cheap), let data accumulate,
build automation when the data justifies it.
