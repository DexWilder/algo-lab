# Filter Pre-Flight Compatibility Rule — Forge Pre-Build Doctrine

> **Status:** CODIFIED FQL doctrine. Locked 2026-06-09 per operator decision #120.
> **Authority:** Pre-build check for any new entry primitive. Lane B research-only; applied during primitive design.
> **Trigger to codify:** gap_fill_trigger first batch (09b) wasted compute on `n=0` outcomes for 4 of 6 assets because `ema_slope` filter is structurally opposite to FADE mechanism direction.

## Rule

**Before running the first real-data batch for a new entry primitive, validate filter-entry direction-logic compatibility on synthetic data.**

## Required pre-flight checklist

1. **What is the entry thesis?**
   - momentum-follow (e.g., breakout continuation, ORB)
   - fade / mean-reversion (e.g., gap-fill, BB reversion)
   - breakout / regime-shift (e.g., donchian, range compression)
   - reversal (e.g., stop_run_reversal, RSI extremes)
   - event / tail (e.g., NFP, EIA, FOMC)
   - carry / spread (e.g., curve trades, treasury rolldown)

2. **Does the selected filter AGREE with or CONTRADICT that thesis?**
   - momentum-follow + ema_slope → AGREES (trend filter passes trend-direction setups)
   - **fade + ema_slope → CONTRADICTS** (filter rejects against-trend trades; fade entries are against-trend by construction)
   - breakout + session_morning → AGREES (open breakouts are common)
   - MR + hurst_stable_mr → REDUNDANT or AGREES (regime-conditioned MR — but may over-restrict)
   - Event + naive-direction → DEPENDS on event's expected directional response

3. **Does the filter BLOCK the natural side of the trade?**
   - Run a synthetic mental test: in the typical setup the mechanism targets, would the filter pass or reject?
   - If filter rejects > 80% of natural setups → filter is mismatched

4. **Synthetic sanity test (mandatory before real data):**
   - Build 5-10 bars of synthetic data containing the SHOULD-FIRE pattern (e.g., gap up at session open)
   - Compute features
   - Step through entry+filter logic for the candidate bar
   - **Verify the entry mechanism alone would fire** (direction, stop, target produced)
   - **Verify the filter does NOT block** the natural setup
   - If filter blocks → filter is mismatched

5. **If filter conflicts with thesis:**
   - **First real batch must use `filter="none"` or a thesis-aligned filter.**
   - Do NOT use the standard `ema_slope` default just because other primitives use it.

## Filter-thesis compatibility quick reference

| Thesis | Compatible filters | Incompatible filters |
|---|---|---|
| Momentum-follow | ema_slope, ema_slope_vol_high, session_morning, hurst_stable_trend | hurst_stable_mr (MR-only), vol_regime low (anti-momentum) |
| Fade / MR | vol_regime, session_morning, none, hurst_stable_mr (with caveat) | ema_slope (trend filter rejects against-trend), ema_slope_vol_high |
| Breakout (regime-shift) | vol_regime, none, session_morning, ema_slope (mild) | hurst_stable_mr, session_close (may miss morning breaks) |
| Reversal | vol_regime high, session_morning, none | ema_slope (trend filter rejects reversal), hurst_stable_trend |
| Event / tail | event-conditioned filter (custom), session-specific, none | trend filters generally redundant or contradictory |
| Carry / spread | hurst_stable_trend (daily-bar), none, regime-specific custom | intraday filters generally irrelevant |

## When to apply this rule

**Applies to:** every NEW entry primitive build, immediately after smoke tests, BEFORE the first real-data batch.

**Does NOT apply to:** filter swaps on existing primitive batches (operator-directed retries are explicit choices, not mistakes to prevent).

## Documentation requirement

When building a new entry primitive, the build PR / commit must include:
- One-line statement of the entry thesis (per the 6 categories in §1)
- Filter selection rationale referencing this rule
- Synthetic sanity test result (PASS / FAIL on the mandatory check)

## Lesson archived from cycle 09b (gap_fill_trigger)

The first gap_fill batch consumed ~8 min of compute and produced `n=0` outcomes for 4 of 6 assets because `ema_slope` was selected by reflex rather than by thesis-alignment. The FADE mechanism by construction wants to trade AGAINST the trend — exactly what `ema_slope` is designed to reject.

**Cost of mistake:** ~8 min compute + one cycle of operator-decision overhead.

**Cost of pre-flight check:** ~5 minutes of synthetic validation.

**Lesson:** the pre-flight check is cheap insurance against expensive real-data wipeouts.

## Counter-example revoke clause

If a future build follows this rule strictly and the pre-flight check fails to predict a real-data wipeout, this rule is reviewed for refinement. Until then, the rule stands.

## Constraints

- This rule does NOT prevent operator-approved filter retries (e.g., #118 gap_fill retry with filter=none).
- This rule does NOT remove any primitive from FILTER_MAP or ENTRY_MAP.
- This rule does NOT mutate registry, scheduler, portfolio, or runtime.
- Lane B research heuristic.

## Source artifacts

- `research/forge_cycle_2026-06-09b_gap_fill_first_batch.py` (originating mistake)
- `research/data/fql_forge/reports/forge_cycle_2026-06-09b.json` (mistake evidence)
- `research/data/fql_forge/kill_taxonomy.json` key `_HEADLINE_2026-06-09b_gap_fill_filter_mismatch`
- `research/crossbreeding/crossbreeding_engine.py` (FILTER_MAP / ENTRY_MAP for cross-reference)
