# Failed Daily Breakout — Narrow Saturation Annotation (2026-06-12)

> **Authority:** Operator decision #206 A (2026-06-12).
> **Doctrine:** [[feedback_asset_family_saturation_rule]] — narrow saturation, REOPENABLE_WITH_NEW_THESIS.
> **Disposition language (operator):** "Daily failed breakout direct port is archived. Reopen only with a new thesis, not exit tuning, asset shopping, or threshold rescue."

## What is saturated

**Saturated:** failed_daily_breakout direct port on MNQ with 3 pre-declared exit variants (fixed 3-day hold, fixed 5-day hold, daily invalidation).

Evidence (cycle 12k):

| Variant | n | PF | Median | Largest single-day loss | Tradeify $2K DD |
|---|---:|---:|---:|---:|---|
| A_fixed_3_day | 295 | **1.143** | **+$92.76** | $2,960 | FAIL |
| B_fixed_5_day | 295 | 1.089 | +$10.76 | $5,178 | FAIL |
| C_daily_invalidation | 295 | 0.957 | -$124.24 | $5,178 | FAIL |

All 3 fail packet gates (PF below 1.15 floor for A/B; C hard fails on median).

## Why the harness mattered (lesson preserved)

The risk-accounting findings are the *real* takeaway:

1. **All 3 variants breach Tradeify $2K daily DD** — largest single-day loss $2,960-$5,178
2. **Top-3 trade concentration is severe** (variant B: 91% of net from 3 trades)
3. **100% overnight exposure** (true multi-day positions confirmed working in harness)
4. **FOMC exposure 14.9-21% of trades** — non-trivial macro hold-through risk
5. **Variant A has positive median ($92.76)** — mechanism produces small wins on average but PF can't survive cost model

This is *structural* information about daily-timeframe candidates: **the largest-single-day-loss constraint binds for prop-firm deployment, not PF alone.** Future daily candidates need to clear this bar by mechanism design, not just gate tuning.

## What is NOT saturated

The DAILY-TIMEFRAME LANE itself remains open. Specifically still open with NEW thesis:

1. **New entry primitives** — inside_day_expansion, weekly_range_compression, 3_day_momentum (operator-listed alternatives from #202)
2. **Volatility-conditioned daily breakouts** — entry only in specific vol regimes
3. **Smaller-size variants** — quarter-sized contracts on MGC or smaller-vol products to keep single-day loss within prop limits
4. **Hybrid mechanisms** — daily-level signal + intraday execution (different from "5-min exit on daily signal" Test 1 failure)

These are NEW theses, not rescues. Per operator #206 language:
> "Daily failed breakout direct port is archived. Reopen only with a new thesis, not exit tuning, asset shopping, or threshold rescue."

## What is FORBIDDEN

- Threshold tuning on existing variants (e.g., 2-day hold, 4-day hold)
- MES port of failed_daily_breakout (per "no MES port" + "no asset shopping")
- Exit rescue loops (per "no exit tuning")
- Vol filter additions specifically to save failed_daily_breakout (would be threshold rescue)

## REOPEN CRITERIA

- A written new entry-mechanism thesis (NOT failed_daily_breakout)
- New data source (e.g., options skew, volume profile) tied to thesis
- New session/asset combination with theoretical basis specific to that combination
- Operator override with documented rationale

## Observational evidence preserved

Variant A (3-day hold) results are observational evidence ONLY:
- 295 events, positive median $92.76, PF 1.143
- Mechanism may have structural behavior
- Insufficient to clear V1 floor under cost model
- Daily DD profile (largest single-day loss $2,960) makes it incompatible with current Tradeify-style $2K daily DD account

Per operator: "no candidate, only observational reference."

## Cross-reference

- `docs/fql_forge/daily_test2_harness_methodology_2026-06-12.md` — harness spec (built, reused for future)
- `engine/multi_day_exit.py` — permanent infrastructure
- `engine/multi_day_risk_accounting.py` — permanent infrastructure
- [[feedback_asset_family_saturation_rule]] — narrow saturation doctrine
- [[feedback_concentration_is_load_bearing]] — concentration primacy

## Status

failed_daily_breakout direct port: **NARROW SATURATION** (MNQ × 3 exit variants).

The multi-day harness remains as **permanent reusable Lane B infrastructure** for any future daily candidate with a genuinely new entry thesis.

Sprint state Day 18/30 unchanged at Lane A (4 packaged candidates).
