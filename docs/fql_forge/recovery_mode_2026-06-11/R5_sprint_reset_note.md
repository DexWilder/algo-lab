# R5 — Sprint Reset Note (RED Recovery Mode)

> **Authority:** Operator #168 R5 (Recovery Mode 2026-06-11).
> **Sprint context:** 30-day Paper-Readiness Sprint, anchored 2026-06-02. Day 16/30 today.

## Honest sprint state

| Metric | Before recovery audit | After R1-R4 |
|---|---|---|
| Accepted packets | 1 (Packet #1) | **0** (Packet #1 → REVIEW pending operator) |
| Active Packet #2 candidates | 0 | 0 |
| Conditional portfolio_complement | 1 (BBKC-MNQ cost-required) | 1 (unchanged) |
| OBSERVATIONAL | 8 | 8 |
| Search bases saturated | 5 | 5 |
| Days remaining | 14 | 14 |

## What changed

The defensive hygiene audit (#162 OK A) discovered that the MGC data file has systematic multi-day gaps right after major release windows (NFP specifically). Packet #1's prior metrics were inflated by $4314.96 of fictitious PnL from 21 events where the backtest "held" through multi-day data outages and filled exits at arbitrary later prices.

This is **NOT** a Forge process failure — it is a data-integrity discovery that retroactively invalidates Packet #1's acceptance criteria. The discovery itself is hygiene-positive (the gate worked).

## Recommended Day 17-30 plan

Sprint deliverable remains "candidates closer to paper trading" per the original sprint reframing. The 30-day target of "1-3 paper packets" is at zero progress, but the recovery framework provides a path:

### Phase 1 (Day 17): Operator decisions on R1-R3
- #165 Packet #1 disposition
- #166 canonical filter doctrine
- #167 sprint scope-reset (recommend: keep 30-day plan, expectations reset)

### Phase 2 (Day 17-20): Foundation
- Apply ratified filter + gate set to ALL prior cycles' candidates (re-audit BBKC-MNQ, FOMC-MGC, NFP-MES/MNQ, etc.) with strict+hold-continuity
- Update doctrine docs: `event_window_clean_events_rule.md`, dual archetype gate set
- Flag all OBSERVATIONAL candidates for re-evaluation (some may pass under tail-engine gates that previously failed under workhorse gates)

### Phase 3 (Day 20-25): Source-mining reset
- Per #163 deferred OK D: harvest-intake review for genuinely new theses
- Output: ranked 15-25 candidate mechanisms with thesis / asset / data / labels (RUNNABLE_NOW, NEEDS_PRIMITIVE, NEEDS_DATA, NEEDS_RESEARCH)
- Filter for non-event mechanisms (since event-window family is saturated) AND for assets with clean data (MES/MNQ/ZN per strict 11i audit)

### Phase 4 (Day 25-30): Bounded testing of top-ranked source-mining mechanism
- One mechanism, bounded scope
- All audits use strict+hold-continuity + correctly-archetyped gate set
- Honest classification regardless of result

## Recommended sprint deliverable reframe

| Original | Recovery-mode reframe |
|---|---|
| 1-3 paper packets accepted | At least 1 packet meeting STRICT canonical filter + correct gate set |
| Plus 0 hidden process gaps | Plus full audit-hygiene canonical doctrine ratified |

The reframe acknowledges that **a candidate ratified under correct rules is worth more than 3 candidates accepted under wrong rules.** The current sprint has surfaced a critical doctrine gap; closing it is itself a major sprint deliverable.

## What MUST NOT happen

- Do NOT restore Packet #1 to ACCEPTED via discretion to preserve appearance of progress
- Do NOT lower canonical gates to make existing candidates pass
- Do NOT mark RED stage as "everything is broken" — the recovery process is working
- Do NOT skip the doctrine memos (R1, R2) just to chase new searches

## What MUST happen

- Operator decisions on #165-168
- Ratification of canonical filter + canonical gate set
- Re-evaluation of all prior candidates under canonical rules
- Honest sprint scoreboard update

## Strategic read

The campaign has produced:
- 1 doctrine update (event_window clean-events rule, 2026-06-10)
- 1 filter-sensitivity discovery (cycle 11e vs 11f)
- 1 critical data-integrity discovery (R4, $4314.96 of fictitious PnL)
- 5 saturation annotations (CPI, NFP-cross, FOMC-MGC, LHD, Gap)
- 8 OBSERVATIONAL candidates (honest near-misses)
- 0 surviving packets

**This is what RED Recovery Mode looks like done right: the discoveries are real, the gates are working, the next batch will be tested under correct rules.** Not what a "1 packet by Day 16" scoreboard looks like — but more durable.

The sprint can still produce a packet if the source-mining lane reveals a genuinely new mechanism. It just cannot produce one by pretending Packet #1 was packet-grade when the data underlying it was contaminated.
