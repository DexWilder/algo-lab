# Closed-Loop Finding — Non-ORB MCL/MGC Hunt Wipeout

> **Status:** Closed-loop research finding. Updates Forge's primitive-coverage hypothesis.
> **Recorded:** 2026-06-08 after cycle 08c (non-ORB Packet #2 hunt) wipeout.
> **Authority:** Lane B research-only; informs next-hunt prioritization, not registry mutation.

## Finding

Cycle 08c ran 18 non-ORB candidates on MCL/MGC across 5 entry/exit/filter combinations:

| Family | n candidates | KILL | OBSERVATIONAL | PAPER_PACKET |
|---|---:|---:|---:|---:|
| pb_pullback (mean-reversion) | 4 | 4 | 0 | 0 |
| bb_reversion (Bollinger MR) | 4 | 4 (incl. 1 ARCHITECTURAL_REJECT) | 0 | 0 |
| vwap_continuation (momentum-derivative) | 4 | 4 (incl. 1 ARCHITECTURAL_REJECT) | 0 | 0 |
| prior_day_fade (anti-PDB MR) | 2 | 1 | 1 (FAIL_STRESS) | 0 |
| donchian + session_close (last-hour) | 4 | 4 | 0 | 0 |
| **TOTAL** | **18** | **17** | **1** | **0** |

**Net result: 0 PAPER_PACKET / 1 OBSERVATIONAL (FAIL_STRESS) / 17 KILL.**

## Mechanism explanation

- **Mean-reversion entries (pb_pullback, bb_reversion) on commodity micros:** consistently median-negative. Commodities trend and consolidate; MR entries get whipsawed.
- **vwap_continuation:** marginal PFs (1.02-1.37) but all median-negative or losing-era ARCHITECTURAL_REJECT.
- **prior_day_fade:** sparse signal (72-115 trades over 8 yrs); only PDF-MGC-Short had positive median but FAIL_STRESS + CURRENT_REGIME_WARNING.
- **donchian + session_close (last-hour breakouts on MCL/MGC):** all 4 KILL on median. Last-hour breakouts on commodities don't work — possibly due to position-management close-the-day behavior.

## Architectural-reject insights

Two candidates were ARCHITECTURAL_REJECT (PF ≥ 1.3 + median > 0 but losing-era in middle of sample):
- **BB-MGC-Short** (PF 1.697, median $6.26, Era3 PF 2.57 — passes Era-3 but losing era in middle)
- **VWAP-MGC-Short** (PF 1.374, median $2.76, Era3 PF 1.50 — same architecture)

These are interesting because they look strong on headline metrics but fail the temporal-distribution gate. The temporal_split + losing-era guardrail (locked earlier in campaign) caught them. **Doctrine working as designed.**

## What this tells us about the MCL/MGC edge structure

The XB-ORB-EMA-Ladder family captures the dominant edge structure on commodity micros. Alternative mechanisms (MR, VWAP, MR-against-PDB, last-hour breakout) do NOT produce viable competing edges. **Commodity micros are ORB-family monocultures within our current primitive set.**

This is a constraint, not a defect. It implies:
1. Future commodity-micro hunts should target NEW entry types not currently in `ENTRY_MAP` (event-conditioned, gap-based, microstructure-based).
2. Packet #2 should NOT come from MCL/MGC under current primitive coverage.
3. Resources should pivot to:
   - **Rates** (different asset class, different mechanism family)
   - **FX** (different timezone, session-transition structure)
   - **Equity index sessions** (afternoon/close strategies on MNQ/MES that don't compete with morning ORB)
   - **New entry primitives** (vol-of-vol, microstructure, event-conditioned) if backlog supports it

## Implication for primitive-coverage bottleneck doctrine

Per memory `feedback_primitive_coverage_bottleneck`: "Primitive coverage is now the bottleneck. Diagnose existing first, build new ranked by backlog-unlock count."

This cycle proved existing non-ORB entries are diagnosed and exhausted on commodities. Primitive expansion is now warranted IF a backlog gap correlates with multiple thesis families. Else continue with existing primitives on untested asset/session/regime combinations.

## Doctrine: "Asset-Family Saturation" (proposed, not yet codified)

Tentative rule for consideration after pattern repeats:

> When 5+ non-overlapping entry-family combinations on a single asset all KILL under the same gates, the asset is **saturated** by the existing probation strategy on that asset. Future hunts on that asset require either (a) new primitive types, or (b) new asset/session/regime mutations that the existing family does NOT cover.

Test pattern with one more wipeout cycle before codifying.

## Constraints

- **No registry mutation.** No probation strategy change.
- **No portfolio allocation change.**
- Research-only Lane B finding.
- Saturation hypothesis is tentative; do NOT auto-skip future MCL/MGC hunts based on this alone.

## Source artifacts

- `research/forge_cycle_2026-06-08c.py`
- `research/data/fql_forge/reports/forge_cycle_2026-06-08c.json`
- `research/data/fql_forge/kill_taxonomy.json` key `_HEADLINE_2026-06-08c_NON_ORB_MCL_MGC_WIPEOUT`
