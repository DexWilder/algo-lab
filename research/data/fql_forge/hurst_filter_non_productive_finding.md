# Hurst-Filter Non-Productive Finding — 2026-06-09

> **Status:** Closed-loop research finding. Locked 2026-06-09 after both hurst filters tested.
> **Authority:** Lane B research-only. Does NOT remove primitives from FILTER_MAP — they remain available for future thesis-driven research.
> **Purpose:** Document the negative finding so future Forge sessions don't reinvest in the same dead end.

## Summary

Both `hurst_stable_mr` and `hurst_stable_trend` filters were built in cycle 06-03 (Hurst proxy via variance ratio, 256-bar window) and remained undeployed until 2026-06-08/09. Both have now been tested for the first time with existing entry primitives. **Both produce anti-edge results.**

## Test history

### hurst_stable_mr (deployed 2026-06-08 in cycle 08l)

Combined with `bb_reversion` entry on equity micros:

| Candidate | n | PF | Median | Verdict |
|---|---:|---:|---:|---|
| SM1-BB-MES-HurstMR-PL | 892 | 0.794 | -$14.99 | KILL ANTI-EDGE |
| SM1-BB-MNQ-HurstMR-PL | 816 | 0.885 | -$25.24 | KILL ANTI-EDGE |

Pattern: hurst_stable_mr filter, applied to mean-reversion entry (bb_reversion), produces uniformly losing signals across multiple equity micros. The filter and the entry are mechanism-mismatched.

### hurst_stable_trend (deployed 2026-06-09 in cycle 09a)

Combined with breakout entries (donchian_breakout, orb_breakout) on multiple assets:

| Candidate | n | PF | Median | Verdict |
|---|---:|---:|---:|---|
| SM2-DC-MES-HurstTrend-PL | 1141 | 0.997 | -$1.24 | KILL (essentially flat) |
| SM2-DC-MNQ-HurstTrend-PL | 1253 | 1.086 | -$4.24 | KILL |
| SM2-ORB-MGC-HurstTrend-PL | 501 | 1.097 | -$1.24 | KILL |

Pattern: hurst_stable_trend filter, applied to breakout entries on multiple assets, produces sub-edge results. PFs hover at 1.0 with negative median.

## Likely mechanism explanation

The Hurst proxy via variance ratio on log-returns over a 256-bar rolling window measures aggregate persistence/anti-persistence at a coarse timescale. The filters threshold:

- `hurst_stable_mr`: requires H ≤ ~0.45 (mean-reverting regime)
- `hurst_stable_trend`: requires H ≥ ~0.55 (trending regime)

**Why both fail with the obvious entry-mechanism pairings:**

1. **256-bar window is too smooth to resolve intraday regime switches.** Intraday entries (bb_reversion, donchian_breakout, orb_breakout) fire on bar-level conditions, but the Hurst measurement is integrated over multiple sessions. The filter's regime-state changes slowly, so it gates entries based on stale regime information.

2. **Mean-reversion entries naturally fire when the local regime is mean-reverting.** Adding a Hurst-MR filter on top is redundant in the productive cases and rejects entries during transient MR pockets in trending H regimes — losing the very signals that have edge.

3. **Breakout entries naturally fire when momentum is present.** A coarse Hurst-trend filter doesn't add discrimination at the bar level; it admits both productive breakouts and the noisy fake-breakouts that the bar-level entry would otherwise capture.

## Disposition

Both Hurst filters **remain in FILTER_MAP** but are now classified RESEARCH_ONLY for active hunt. They are NOT removed because:
- They may compose productively with NEW entry primitives whose mechanism complements coarse regime detection (e.g., daily-bar carry strategies, multi-session swing entries).
- They may compose productively with NEW filter combinations (e.g., hurst × session_morning).
- The cost of building them was already paid; archiving is wasteful.

**Saturated combinations (will not retest without thesis change):**
- hurst_stable_mr × bb_reversion × any equity micro
- hurst_stable_trend × donchian_breakout × MES/MNQ
- hurst_stable_trend × orb_breakout × MGC

**Future use cases that DO warrant testing if backlog supports them:**
- hurst_stable_trend × daily-bar carry/regime strategies
- hurst_stable_mr × prior_day_fade with longer hold windows
- hurst as a tail-engine event-filter (sparse signal, high concentration tolerance)

## Doctrine implication

Hurst-style coarse regime filters are not free productive primitives even after their build cost is sunk. **Filter primitives must be validated against entry mechanism timescale match, not just built and assumed to add value.** Tested as a single deployment, both filters confirmed non-productive at intraday timescales with the obvious entry pairings.

This argues against assuming "unused primitives" are hidden alpha. The SMP-1 catalog (2026-06-08) flagged hurst filters as a "critical primitive-coverage waste" — that framing was wrong. They were unused because the productive use case is narrower than the catalog assumed.

## Constraints

- No FILTER_MAP removal. Primitives remain available for future thesis-driven research.
- No registry mutation. No scheduler change. No portfolio change. No paper/live promotion.
- Lane B research-only finding.

## Source artifacts

- `research/forge_cycle_2026-06-08l_source_mining_batch1.py` (hurst_stable_mr deployment)
- `research/forge_cycle_2026-06-09a_smp2_tier1.py` (hurst_stable_trend deployment)
- `research/data/fql_forge/reports/forge_cycle_2026-06-08l.json`
- `research/data/fql_forge/reports/forge_cycle_2026-06-09a.json`
- `research/data/fql_forge/kill_taxonomy.json` keys `_HEADLINE_2026-06-08l_*` and `_HEADLINE_2026-06-09a_*`
- `research/crossbreeding/crossbreeding_engine.py` (`filter_hurst_stable_mr`, `filter_hurst_stable_trend`, `_hurst_window` proxy at compute_features:185)
