# Data-Blocked Strategy Rule

**Established:** 2026-04-14 after the MYM pipeline-omission incident.

**Purpose:** Formalize the distinction between a strategy that is
**quiet** (producing no signals because market conditions don't trigger
its entry logic) and a strategy that is **data-blocked** (producing no
signals because the data pipeline upstream of the strategy is broken,
missing, or frozen). The two look identical to naive drift monitoring
but mean opposite things. This rule ensures the registry carries the
evidence to disambiguate.

---

## Core rule

**A strategy may be marked data-blocked when its expected data feed is
missing, frozen, or degraded in a way that prevents it from evaluating
entry logic against fresh bars.**

A data-blocked strategy is **not** producing forward evidence. Any zero-
trade or below-expected-frequency period during a data-blocked window
is **not valid evidence of edge degradation, edge stability, or any
other strategy property.** The window is evidentially null.

---

## Backfill completion does not start the review clock

**The review clock starts from the first verified fresh live bar after
backfill, not from:**
- the strategy's `promoted_date` in the registry
- the date the backfill was performed
- the date the data pipeline was fixed
- the last bar timestamp written by backfill (if that bar is older than the fix date)

**Rationale:** a backfilled bar is historical data written retroactively.
It is not a forward observation. The strategy has not had the
opportunity to trade live against it. Counting backfilled days toward
probation-review thresholds would inflate evidence count against frozen
or degraded data.

---

## Required registry fields

When a strategy is marked data-blocked, the registry entry must carry:

### `data_pipeline_gap` (structured object)

```json
{
  "start": "YYYY-MM-DD",
  "end": "YYYY-MM-DD | null (if unresolved)",
  "last_bar_before_fix": "YYYY-MM-DD HH:MM",
  "last_bar_after_fix": "YYYY-MM-DD HH:MM | null",
  "backfill_bars": <int | null>,
  "root_cause": "<short description>",
  "review_clock_adjustment": "review gates count forward trades from first live bar post-backfill, not from promoted_date"
}
```

### `review_clock_start_source` (string enum)

One of:
- `"promoted_date"` — default, used for strategies that have never been data-blocked
- `"first_fresh_bar_post_backfill"` — used for any strategy whose registry has a non-null `data_pipeline_gap`
- `"manually_set:<ISO date>"` — used when a human reviewer overrides the default (record the date the clock is being treated as starting from)

When `data_pipeline_gap` is present and resolved, `review_clock_start_source` must be set to one of the latter two values.

---

## Lifecycle states

A strategy can move through these data states independently of its lifecycle state (core/probation/archived):

| Data state | Meaning | Review clock behavior |
|---|---|---|
| **normal** | Data feed fresh, expected cadence met | Clock ticks normally |
| **data-blocked (open)** | Pipeline gap exists; `data_pipeline_gap.end` is null | Clock paused — window is evidentially null |
| **data-blocked (resolved)** | Pipeline fixed; `data_pipeline_gap.end` set | Clock resumes from first fresh post-backfill live bar |
| **degraded** | Data present but upstream flagged as reduced quality (e.g., databento "degraded" day) | Clock ticks, but evidence from those specific days flagged in review notes |

The data state lives alongside `status` and `controller_action`. A probation strategy can be data-blocked without being rejected/archived, and vice versa.

---

## When to apply this rule

Mark a strategy data-blocked when any of these are true:

1. **Symbol-list omission:** the strategy's required asset is missing from the data-refresh pipeline's symbol list (e.g., `data/databento_loader.py` SYMBOLS dict).
2. **Pipeline failure:** the data-refresh script has been failing for this symbol for more than 2 consecutive expected-refresh fires, with no transient infrastructure explanation.
3. **Frozen file:** `data/processed/<ASSET>_5m.csv` has an mtime older than 2× the normal refresh cadence (i.e., > 2 trading days old for a daily-refresh feed).
4. **Manual investigation finding:** a human reviewer determines the strategy's zero-trade period is due to data inputs, not market conditions.

Do NOT mark a strategy data-blocked when:

- The strategy is in a legitimately quiet market regime (e.g., low vol, no setups).
- The strategy is sparse by design (event-driven, monthly-rebalance) and the silence is within its expected inter-event interval.
- The strategy just entered probation and has not yet had time to produce signals in its own window (the drift monitor's `entered_forward_date` window-aware severity handles this case).

---

## Automation expectations

This document describes the **convention**, not the **automation.** As of 2026-04-14, no tool automatically detects a data-pipeline-gap condition or auto-sets the `review_clock_start_source` field. Human reviewers must:

1. Recognize the condition (e.g., during a verification pass like the one that caught MYM on 2026-04-14).
2. Write the `data_pipeline_gap` field to the registry manually (or via a one-off script).
3. Apply the review clock adjustment when evaluating the strategy against its probation gates.

When the hardening queue opens post-May 1, a daily data-freshness check that auto-flags data-blocked conditions would be a natural addition. Queue it under "authority-consistency validator."

---

## Worked example — XB-ORB-EMA-Ladder-MYM (2026-04-14)

**Situation:** MYM was promoted 2026-04-13 as the third XB-ORB workhorse. The next day, a systematic check showed MYM_5m.csv had not updated since 2026-03-11 — 33 days stale.

**Root cause:** `data/databento_loader.py` SYMBOLS dict did not include MYM. The strategy code, asset config, and launchd agents all knew about MYM, but the data pipeline piece was omitted when MYM was added.

**Resolution:**
- SYMBOLS dict patched (one-line add).
- Manual backfill ran: `python3 scripts/update_daily_data.py --symbol MYM` — fetched +6,134 bars, last bar 2026-04-13 19:55.
- Registry entry updated with `data_pipeline_gap` field:
  ```json
  {
    "start": "2026-04-13",
    "end": "2026-04-14",
    "last_bar_before_fix": "2026-03-11 19:55",
    "last_bar_after_fix": "2026-04-13 19:55",
    "backfill_bars": 6134,
    "root_cause": "symbol_list_omission in data/databento_loader.py SYMBOLS",
    "review_clock_adjustment": "review gates count forward trades from first live bar post-backfill, not from promoted_date"
  }
  ```
- Review clock: 20-trade first-formal-review gate per `XB_ORB_PROBATION_FRAMEWORK.md` counts trades from the first live bar the strategy sees post-backfill. As of 2026-04-14, that first live bar has not yet been produced (next forward-day fire is the gate-eligibility start).

**What the rule prevents:** without this formalization, a future reviewer on (say) 2026-04-27 could look at MYM's probation status and see "14 days since promotion, 0 trades, missing-signal severity = DRIFT per expected cadence." That reviewer might conclude the strategy is weakening. The rule ensures they instead see "14 days since promotion but only [N] days of live data; review clock starts from first fresh bar" and interpret the silence correctly.

---

## Related documents

- `docs/PROBATION_REVIEW_CRITERIA.md` — where individual non-XB-ORB thresholds live
- `docs/XB_ORB_PROBATION_FRAMEWORK.md` — where XB-ORB thresholds live
- `docs/ELITE_PROMOTION_STANDARDS.md` — where strategy-shape frameworks live
- `docs/PORTFOLIO_TRUTH_TABLE.md` — operator-facing view; lists any strategies currently in data-blocked state

---

*This rule applies retroactively. Any strategy whose zero-trade history coincides with a known data-pipeline gap should have its registry entry updated to reflect the gap and adjust its review clock. Do not silently count evidentially-null windows toward promotion decisions.*
