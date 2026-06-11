# Packet Standard V1 — 2026-06-11

> **Status:** FROZEN for the duration of the Paper-Readiness Sprint (2026-06-02 → 2026-07-02).
> **Authority:** Operator ratification this turn after Recovery Mode R1-R5.
> **Change control:** [[packet_standard_v1_change_control]]. Any change goes through change-control — no ad-hoc reclassification.

## Purpose

Replace ad-hoc rule churn ("candidate found → audit issue discovered → rule changed → reclassified → scoreboard reverses") with a frozen versioned standard. Re-score once under V1, then resume nonstop hunting under stable rules.

## Archetypes

A candidate is classified by archetype based on shape, then evaluated under archetype-specific gates.

### WORKHORSE
High-frequency continuous-intraday strategies (n ≥ 500 trades).
Examples: XB-ORB-EMA-Ladder family, BBKC-MNQ, last-hour drift.

### TAIL_ENGINE
Low-sample event-driven strategies (n < 500 trades).
Examples: NFP-MGC, CPI-event-window, FOMC event-window.

### PORTFOLIO_COMPLEMENT
A strategy that improves portfolio behavior (low daily correlation to existing accepted strategies) but is NOT independently a paper-readiness packet. Must NOT be counted as accepted packet progress.

### OBSERVATIONAL
A near-miss with useful signal information but fails one or more hard gates. Preserved as research memory; NOT counted as candidate.

### ARCHIVED / REOPENABLE
Failed candidates kept reopenable under specific conditions:
- REOPENABLE_WITH_NEW_THESIS
- REOPENABLE_WITH_NEW_DATA
- REOPENABLE_WITH_NEW_EXIT_ARCHITECTURE
- REOPENABLE_WITH_PORTFOLIO_PURPOSE

## Canonical filter doctrine (ratified per R1)

For HOLD-WINDOW event strategies (hold > 60min): **strict + hold-continuity**:
1. Pre-data check (event after data file start)
2. Next-bar gap ≤ 60 min
3. Hold-window continuity — all bars from entry through `entry + hold_bars` within 60 min of each other
4. NO multi-day fallback fills
5. Excluded-event reason table mandatory

For trigger-only or hold ≤ 60min strategies: **strict next-bar** sufficient.

Permissive (exact-match override) is **DEPRECATED** for hold > 60min strategies.

See: [[feedback_hold_continuity_canonical_filter]], `docs/fql_forge/recovery_mode_2026-06-11/R1_canonical_filter_doctrine.md`, `docs/fql_forge/event_window_clean_events_rule.md` (updated 2026-06-11).

## Workhorse hard gates

| # | Gate | Threshold |
|---|---|---|
| 1 | n ≥ 500 | Hard |
| 2 | PF ≥ 1.20 | Hard |
| 3 | Positive median trade | Hard |
| 4 | PASS_STRESS at 2× cost + 2 ticks slip | Hard |
| 5 | Max-year concentration ≤ 50% | Hard |
| 6 | Years positive ≥ 50% | Hard |
| 7 | Era 3 PF ≥ 1.0 | Hard |
| 8 | Era 3 median ≥ 0 | Hard |
| 9 | Cross-asset family review | Hard |

## Tail-engine hard gates (ratified per R2)

| # | Gate | Threshold |
|---|---|---|
| 1 | n ≥ 20 | Hard |
| 2 | PF ≥ 1.30 (STRONG) | Hard |
| 3 | PASS_STRESS at 2× cost + 2 ticks slip (stress PF ≥ 1.30 floor) | Hard |
| 4 | Max single instance ≤ 35% | Hard |
| 5 | Positive instance fraction ≥ 60% | Hard |
| 6 | Instance CV ≤ 3.0 | Hard |
| 7 | Era 3 PF ≥ 1.0 | Hard |
| 8 | Max DD duration ≤ 900d | Hard |
| 9 | Cross-asset family review | Hard |
| 10 | Canonical clean-data filter (R1) | Hard |
| 11 | Calendar grade ≥ OPERATOR_VERIFIED | Hard |

**Soft flags** (surface but do not auto-fail):
- Era 3 median sign — tail engines may have negative median + positive PF legitimately
- Year-exclusion PF robustness
- Recent-regime deterioration

See: [[feedback_dual_archetype_factory]], `docs/fql_forge/recovery_mode_2026-06-11/R2_tail_engine_gate_doctrine.md`.

## Portfolio-complement gates

A candidate may be classified PORTFOLIO_COMPLEMENT if:
- It passes its archetype hard gates AT LEAST under a non-canonical interpretation, AND
- Family review shows moderate correlation to an existing accepted strategy (corr 0.3-0.7 with substantial day overlap), AND
- Operator portfolio review authorizes inclusion as sleeve.

PORTFOLIO_COMPLEMENT does NOT count as accepted paper-readiness packet.

## Calendar grade ladder

| Grade | Definition |
|---|---|
| OFFICIAL_SOURCE_VERIFIED | Direct source verification (e.g., Fed.gov, BLS.gov) by operator |
| OPERATOR_VERIFIED | Operator-submitted calendar from official source |
| MACHINE_FETCHED_OFFICIAL | Forge fetched from official URL (e.g., federalreserve.gov FOMC page) |
| FORGE_COMPILED_DATA_REQUIRED | Forge-recall calendar (not promotion-grade per #140) |
| UNVERIFIED | Inferred from other sources |

Acceptance requires ≥ MACHINE_FETCHED_OFFICIAL for tail-engine event-window candidates.
Exploratory screens may use FORGE_COMPILED_DATA_REQUIRED if explicitly labeled.

## Status definitions

| Status | Meaning |
|---|---|
| ACCEPTED_PAPER_READINESS_PACKET | Passed full V1 audit; eligible for paper-trading decision |
| PAPER_PACKET_CANDIDATE | Passed cheap screen + stress; pending 8-dim audit + family review |
| REVIEW | Material change to inputs/rules required reassessment; not accepted |
| PORTFOLIO_COMPLEMENT | Independent of accepted strategies, useful for portfolio behavior |
| OBSERVATIONAL | Near-miss; useful research memory |
| ARCHIVED | Failed canonical V1 audit; closed unless reopen-criteria met |

## Cross-references (DO NOT DUPLICATE)

V1 references these existing doctrines rather than restating them:

- [[feedback_evidence_integrity_failsafe]] — fail-closed plumbing rule
- [[feedback_proactive_plumbing_inspection]] — inspect-don't-infer
- [[feedback_event_window_clean_events_rule]] — event-window clean filter (updated 2026-06-11 per #161-C)
- [[feedback_hold_continuity_canonical_filter]] — strict+hold-continuity locked 2026-06-11
- [[feedback_asset_family_saturation_rule]] — narrow saturation, REOPENABLE
- [[feedback_concentration_is_load_bearing]] — concentration gate primacy
- [[feedback_dual_archetype_factory]] — workhorse vs tail-engine
- [[feedback_pl_workhorse_default_exit]] — profit_ladder default for workhorse
- [[feedback_red_recovery_mode]] — what RED triggers
- [[feedback_continuous_forge_execution]] — always-on Forge
- [[feedback_forge_autonomous_mode]] — Lane B autonomous

`docs/fql_forge/recovery_mode_2026-06-11/R5_sprint_reset_note.md` — sprint state, NOT re-stated here.

## What V1 does NOT do

- V1 does not mutate registry / scheduler / portfolio
- V1 does not authorize paper / live promotion
- V1 does not change asset_config or cost models
- V1 does not retroactively change non-affected prior decisions
- V1 does not eliminate any of the existing doctrines listed above

V1 is the FRAMEWORK for classification under correct rules. Existing doctrines remain in force.
