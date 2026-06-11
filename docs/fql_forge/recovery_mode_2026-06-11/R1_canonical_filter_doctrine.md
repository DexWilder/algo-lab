# R1 — Canonical Filter Doctrine for Event-Window Hold Strategies

> **Authority:** Operator #168 R1 (Recovery Mode 2026-06-11).
> **Status:** RECOMMENDATION (operator decision pending ratification).
> **Doctrine reference:** [[feedback_event_window_clean_events_rule]] + #161-C update.

## Recommendation

**Canonical filter for event-window hold strategies: STRICT + HOLD-CONTINUITY.**

The filter has three components:
1. **Pre-data check:** event must occur AFTER data file start date
2. **Next-bar gap check:** the first bar AFTER the event timestamp (`df[df_dt > event].head(1)`) must be within `max_gap_minutes` (default 60)
3. **Hold-window continuity check:** all bars from entry through `entry + hold_bars` must be within `max_intra_hold_gap_minutes` of each other (default 60)

The permissive ("exact-match") variant is **DEPRECATED** for hold-window strategies (see Finding C below). It may remain valid for trigger-only / no-hold strategies.

## R4 evidence base

From cycle 11k anatomy of 21 events excluded by strict+hold-continuity vs strict alone:

| Classification | Count | % | Total PnL contribution |
|---|---:|---:|---:|
| **TRUE_DATA_GAP (multi-day outage)** | **21** | **100%** | **+$4314.96** |
| SESSION_BOUNDARY | 0 | 0% | — |
| EARLY_CLOSE_OR_HOLIDAY | 0 | 0% | — |
| ROLLOVER_ARTIFACT | 0 | 0% | — |
| RECOVERABLE | 0 | 0% | — |

ALL 21 events have intra-hold-window gaps ≥ 2960 minutes (49.3 hours). None are recoverable session-boundary artifacts.

**Concrete examples:**
- Event 1: 2019-12-06 NFP, entry 09:15, "intended exit" 2019-12-29 18:00 — 23 days of holding through a 112-hour data gap, filled at an arbitrary price → $553.76 fictitious PnL
- Event 16: 2024-10-04 NFP, entry 09:30, "intended exit" 2024-10-21 14:55 — 17 days held through a 79-hour gap → $1006.76 fictitious PnL
- Event 21: 2026-06-05 NFP (most recent), entry 09:10, "intended exit" 2026-06-09 03:15 — 4 days held through a 57-hour gap → -$523.24

## Why each version is correct/incorrect

| Filter | Hold-strategy validity | Trigger-only validity |
|---|---|---|
| Permissive (exact-match OR next-bar) | INVALID — includes events with intra-hold gaps | Valid (no hold) |
| Strict (next-bar only) | INVALID — checks entry but not exit continuity | Valid |
| **Strict + hold-continuity** | **CORRECT** | over-cautious but safe |

## Impact on prior decisions

- Packet #1 NFP-MGC-Long-2h's prior metrics (PF 2.26-2.39) included $4314.96 of PnL from 21 data-gap events. True PF on canonical filter: **1.250**.
- FOMC-MGC cycle 11e first-batch PF 1.403 was similarly inflated; cycle 11f strict filter showed 1.158; strict+hold would likely show further degradation (not re-tested but pattern is consistent).
- All other 06-10k audit clean-percent numbers should be re-validated on strict+hold filter for any hold-window candidate.

## Edge cases

- **For event-window strategies with hold ≤ 60 min:** strict alone is sufficient (no intra-hold check needed since hold fits in one gap interval)
- **For event-window strategies with hold > 60 min:** strict+hold-continuity is required
- **For trigger-only / immediate-exit strategies (e.g., gap detection without hold):** strict alone is sufficient

## Operator action

Ratify or amend per #165-167 response. If ratified:
- Update `docs/fql_forge/event_window_clean_events_rule.md` to specify strict+hold-continuity as canonical
- Re-flag all hold-window candidates' prior metrics as PROVISIONAL pending strict+hold re-audit
- Specifically: Packet #1 verdict matrix (R3) using strict+hold as canonical
