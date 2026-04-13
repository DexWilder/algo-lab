# Crossbreeding Playbook

*Operational rules for the governed continuous recombination lane.*
*Established 2026-04-13 based on the XB-ORB genealogy.*

---

## What Counts as a Valid Donor

A strategy or idea qualifies as a component donor when:

1. It has identifiable entry, exit, or filter logic (tagged in registry)
2. The component can be described in one sentence
3. It has been tested at least once (first_pass result exists)
4. It is tagged with `reusable_as_component: true` in the registry

**High-value donors** (prioritize these):
- Components from validated strategies (xb_orb_ema_ladder's profit_ladder, ema_slope)
- Components from rejected strategies that had PF > 1.0 on at least one asset
- Components from archived ideas with convergent evidence

**Dead donors** (do not use):
- Components from closed families (ICT, gap-fade, overnight premium)
- Components that failed on ALL tested assets with PF < 0.8
- Components tagged `reusable_as_component: false`

---

## Hybrid Construction Rules

### Required
- At least one proven component (from a strategy that passed concentration gates)
- Maximum 3 components per hybrid (entry + filter + exit)
- Each component must come from a different parent strategy
- The hybrid must target a known portfolio gap (session, asset, regime, or mechanism)

### Forbidden
- No more than 3 components (entry + filter + exit is the max)
- No combining two entries, two exits, or two filters
- No hybrid that duplicates an existing workhorse's asset + session + mechanism
- No hybrid that requires data we don't have
- No hybrid that produces < 100 expected trades on 6 years of 5m data

### Strongly preferred
- Entry from one family + exit from xb_orb (profit_ladder is the only proven
  positive-median exit)
- Filter that addresses a specific regime or session gap
- Components that have been individually validated even if the parent failed

---

## How Hybrids Are Ranked

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Portfolio gap fit | 30% | Does it fill a real session/asset/regime gap? |
| Proven component count | 25% | How many components come from validated sources? |
| Expected trade density | 20% | Will it produce 500+ trades for workhorse evaluation? |
| Spec clarity | 15% | Can the hybrid be built without ambiguity? |
| Non-redundancy | 10% | Is it genuinely different from existing workhorses? |

### Ranking vs raw CONVERT_NEXT ideas

Hybrids can outrank raw ideas when:
- They use a proven exit (profit_ladder) with a new entry → higher survival chance
- They target a gap that no raw idea addresses
- They have simpler specs (component logic is already tested individually)

Raw ideas outrank hybrids when:
- The idea is from a fundamentally different mechanism family
- The idea has convergent evidence from multiple sources
- The idea has higher expected trade density

---

## Current Candidate Queue

| # | Hybrid | Gap | Proven Component |
|---|--------|-----|-----------------|
| 1 | Afternoon entry + EMA slope + profit ladder | Session (afternoon/close) | Filter + exit proven |
| 2 | VWAP pullback MR + vol filter + trailing stop | Regime (mean-reversion) | Entry partially validated |
| 3 | Vol squeeze breakout + session filter + profit ladder | Entry diversity | Exit proven |
| 4 | Commodity-specific entry + proven exit | Asset-native | Exit proven |

---

## Process: From Candidate to Probation

```
1. CANDIDATE GENERATION (continuous background)
   - Triggered by: new harvest, new archive, portfolio gap change
   - Constrained by: rules above (gap, proven donor, simplicity, density)
   - Output: ranked candidate list (max 5 active candidates)

2. CANDIDATE REVIEW (weekly)
   - Is any candidate stronger than the top CONVERT_NEXT idea?
   - Does any candidate address a gap that raw ideas don't?
   - Is the gap still real? (portfolio may have changed)

3. BUILD (when validation mode allows)
   - Build code using crossbreeding_engine.py component maps
   - First-pass through dual-archetype factory
   - Apply concentration-aware gates

4. VALIDATE (if first-pass survives)
   - Full deep validation battery
   - Year-by-year, concentration, cross-asset, drawdown

5. PROMOTE (if validation passes)
   - Add to forward runner as probation candidate
   - Follow XB_ORB_PROBATION_FRAMEWORK.md gates
```

---

## Anti-Chaos Rules

- Maximum 5 active hybrid candidates at any time
- Each candidate must have a written rationale tying it to a portfolio gap
- Candidates that sit unbuilt for > 60 days are auto-archived
- No candidate should be generated without checking redundancy against
  existing workhorses and the conversion queue
- "Interesting" is not a valid reason to generate a candidate.
  "Fills session gap X with proven component Y" is.
