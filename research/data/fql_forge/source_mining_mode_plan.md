# Source Mining Mode — Contingency Plan

> **Status:** Contingency plan. Activate IF VRC retry (cycle 08k) fails per #110.
> **Recorded:** 2026-06-08.
> **Authority:** Lane B research; report-only.

## Activation criteria

Activate Source Mining Mode ONLY IF VRC retry produces:
- n still near-zero (PRIMITIVE_BUILD_FAILED), OR
- fires but all KILL (no productive signal)

If VRC retry produces ANY OBSERVATIONAL or PASS_STRESS candidate, do NOT activate Source Mining — proceed with family review on the VRC survivor instead.

## Goal

Produce one of:
- **5 RUNNABLE_NOW candidate specs** using existing primitives + existing data, OR
- **1 high-leverage primitive/data unlock** spec with explicit expected-unlock-count

## Sources to mine

| Source | Location | Mechanism types likely |
|---|---|---|
| 1. kill_taxonomy headlines | `research/data/fql_forge/kill_taxonomy.json` (~72 keys) | Mechanism-specific lessons, asymmetry patterns, failed templates with reasoning |
| 2. Harvest results (06-04) | `research/data/harvest_results.json` (10 mass-screen candidates) | Pre-doctrine candidates worth re-examining |
| 3. Intake folders | `intake/tradingview/{breakout,ict,mean_reversion,opening_drive,orb,session,trend,vwap}` | TradingView source leads (mostly empty pending Claw output) |
| 4. Insight docs | `research/data/fql_forge/*_insight.md` | 5 directional/structural insight docs |
| 5. Existing primitive inventory | crossbreeding_engine.py | Untested combinations within existing primitives |
| 6. Memory project notes | `~/.claude/projects/-Users-chasefisher/memory/` | Multi-session learnings |

## Mining workflow (one bounded cycle)

1. **Catalog** all candidate mechanisms from sources 1-6 into a single inventory
2. **Cross-reference** each against existing primitives — what already covers this?
3. **Classify** each mechanism:
   - **RUNNABLE_NOW**: existing primitive + existing data; just needs spec wiring
   - **NEEDS_PRIMITIVE**: requires new entry/exit/filter primitive build
   - **NEEDS_DATA**: requires new data source not in tree (calendar, expectations, COT)
   - **NEEDS_RESEARCH**: requires literature/theory work before implementation
   - **ALREADY_TESTED**: appears in kill_taxonomy with reasoning — skip unless doctrine has changed substantively
4. **Filter** to RUNNABLE_NOW only for active hunt; queue NEEDS_PRIMITIVE / NEEDS_DATA for operator decisions
5. **Score** RUNNABLE_NOW candidates by:
   - Novelty (distance from existing primitive patterns)
   - Mechanism plausibility (does it have a real theoretical basis?)
   - Asset-applicability (works on >1 asset class?)
   - Cost-robustness expectation (is the typical move-size large enough to survive stress?)
6. **Select top 5 RUNNABLE_NOW** for first batch
7. **Surface to operator** for approval before running

## Hard rules during Source Mining

- **No new primitive builds** — Source Mining is for combining existing primitives in new ways
- **No data unlocks** — those queue separately
- **No bypass of standard gates** — same prop-stress, family-review, concentration rules apply
- **No rescue of already-killed mechanisms** — only re-examine if doctrine has materially changed
- **No broad parameter mining** — one spec per mechanism, default params

## Pre-mining inventory hints

Based on cursory scan of sources, candidate mechanisms NOT yet exhaustively tested in current primitive set:

| Mechanism | Source | Estimated classification |
|---|---|---|
| Opening drive continuation (different from ORB) | intake/tradingview/opening_drive (empty README) | NEEDS_PRIMITIVE or RUNNABLE_NOW via vwap_continuation+session_morning |
| ICT-style liquidity sweep | intake/tradingview/ict (README only) | NEEDS_PRIMITIVE (custom triggers) |
| Range expansion after consolidation | harvest_results | Similar to range_compression_break — partial overlap |
| Bollinger-Keltner squeeze | harvest_results (BBKC-Squeeze) | NEEDS_PRIMITIVE (Keltner channels not in features) |
| Close momentum (last 30 min directional) | harvest_results (CloseMomentum) | RUNNABLE_NOW via session_close filter + ORB-style trigger |
| Gap momentum (overnight gap → direction) | harvest_results (GapMom) | RUNNABLE_NOW partially — prior_day_close exists; needs gap-specific trigger |
| Session VWAP fade | harvest_results (SessionVWAPFade — already KILL) | ALREADY_TESTED |
| Half-life gated MR (rates curves) | feedback_event_strategy_doctrine | Cross-checked: HL-filter exists |
| Mean-revert toward prior-day VWAP | not in current set | NEEDS_PRIMITIVE (prior-day-VWAP not computed) |
| Volume-weighted close break | not in current set | RUNNABLE_NOW via VWAP-distance signals (vwap_continuation) |

## After Source Mining cycle

**If 5 RUNNABLE_NOW candidates surface and at least 1 reaches PASS_STRESS in cheap-screen:** continue Hybrid D path.

**If 0 RUNNABLE_NOW survive cheap-screen:** Source Mining has confirmed existing primitive set is structurally exhausted. Next operator decision: build NEEDS_PRIMITIVE candidate, open NEEDS_DATA queue item, or revise sprint scope.

## Constraints

- Lane B research-only.
- No registry mutation. No scheduler change. No portfolio allocation change. No paper/live promotion.
- One bounded Source Mining cycle. If unproductive, surface for operator direction; do NOT auto-iterate.

## Source artifacts

- `research/data/fql_forge/kill_taxonomy.json` (mining source 1)
- `research/data/harvest_results.json` (mining source 2)
- `intake/tradingview/*` (mining source 3)
- `research/data/fql_forge/*_insight.md` (mining source 4)
- `research/crossbreeding/crossbreeding_engine.py` (primitive inventory)
