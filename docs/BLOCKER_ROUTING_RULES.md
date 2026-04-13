# Blocker Routing Rules

*Established 2026-04-13. Governs how blocked ideas and harvest notes are handled.*

## Blocker Classes and Default Actions

| Blocker Class | Examples | Default Action | Review Trigger |
|---------------|----------|----------------|----------------|
| **data_missing** | CFTC positioning, VIX intraday, options chain | DEFER | Data expansion phase decision |
| **multi_contract** | Curve slope, term structure, roll yield | DEFER | Multi-contract data source added |
| **vol_proxy_missing** | OVX, VVIX, implied vol surface | DEFER | Vol data feed added |
| **macro_data** | PPP, CPI series, GDP, OECD | DEFER | Macro data feed decision |
| **execution_ambiguity** | Unclear entry/exit, discretionary elements | SALVAGE (1 attempt) | Claw refinement task |
| **spec_incomplete** | Missing thresholds, undefined parameters | SALVAGE (1 attempt) | Claw refinement task |
| **asset_unavailable** | NG, SI, HG, agricultural futures | DEFER | Asset data onboarding |
| **sub_minute_data** | Tick data, 1s bars, order book | DEAD | Not planned for FQL |
| **closed_family** | ICT, gap-fade, overnight premium | DEAD | Only if new mechanism addresses prior failure |

## Salvage Rules

### What qualifies for salvage
- The mechanism is conceptually sound but specification is incomplete
- A single refinement pass (by Claw or operator) could make it testable
- The idea fills a genuine portfolio gap

### Maximum salvage attempts: 1
- One Claw refinement task to sharpen the spec
- If still untestable after refinement → ARCHIVE
- No second chances — either the mechanism can be specified or it can't

### Allowed mutation types
- Parameter specification (add missing thresholds)
- Session window definition (specify exact times)
- Proxy substitution (use ATR for VIX, price-based carry proxy)
- Asset mapping (specify which micro contract to use)

### NOT allowed
- Changing the core mechanism (that's a new idea, not a salvage)
- Adding complexity to work around data limitations
- Combining with another idea to make it work

## Staleness Rules

| Age | Status | Action |
|-----|--------|--------|
| 0-30d | Fresh | Normal processing |
| 31-45d | Aging | Flag in weekly audit, prioritize for triage |
| 46-60d | Stale | Force decision: convert, salvage, or archive |
| 60d+ | Expired | Auto-archive unless explicitly extended with reason |

### Extension rules
- An idea can be extended past 60d ONLY if:
  - It has convergent evidence from multiple sources
  - A specific data source is expected within 30 days
  - Operator explicitly approves with written reason
- Maximum extension: 30 additional days (90d total)
- No idea should exist in the registry past 90d without action

## Decision Flow

```
New idea enters registry
    ├── Testable now? → CONVERT_NEXT (build code, first-pass)
    ├── Needs spec work? → SALVAGE (1 Claw refinement attempt)
    │       ├── Still untestable → ARCHIVE
    │       └── Now testable → CONVERT_NEXT
    ├── Needs data we don't have? → DATA_BLOCKED (defer)
    │       └── Review at data expansion phase
    ├── Closed family? → DEAD (archive immediately)
    └── No viable path? → DEAD (archive immediately)
```

## Harvest Note Blocker Handling

Harvest notes follow the same rules. Additionally:
- Notes with `blocker: none` should be converted within 14 days
- Notes with soft blockers should be triaged within 30 days
- Notes with hard blockers (data-missing) are auto-deferred
- Duplicate notes are moved to `reviewed/` immediately
