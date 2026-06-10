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
   - **Verify `entry_ok` is True at the candidate bar** (else the signal generator will silently filter it out)
   - If filter blocks OR entry_ok is False → mismatch detected

5. **`entry_ok` compatibility (added 2026-06-10):**
   - `entry_ok = in_session & (times >= "09:45") & (times < "14:45")`
   - Any primitive that intends to fire in the FIRST 3 bars of session (09:30-09:40) will be silently blocked because `entry_ok=False` until 09:45
   - If thesis requires session-open behavior:
     - Either: count session bars starting from `entry_ok=True` (i.e., from 09:45)
     - Or: explicitly check `entry_ok[i]` instead of `in_session[i]`
   - Synthetic test must assert entry fires when `entry_ok=True`, not just when `in_session=True`

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

## Lesson archived from cycle 10a (abnormal_range_followup + retroactive gap_fill cycles)

Discovered 2026-06-10 after the 3rd primitive (abnormal_range_followup) showed the same `n=0 on equity micros + MCL` pattern as gap_fill 09b/09c.

**Root cause:** `generate_crossbred_signals` (line 1470) only calls entry function when `f["entry_ok"][i]` is True. `entry_ok = in_session & (times >= "09:45") & (times < "14:45")`. Any primitive that designs to fire in the **first 3-5 bars of session** (09:30-09:40) has its entry function NEVER called — `entry_ok` is False during those bars.

**Affected primitives:** gap_fill_trigger (cycles 09b, 09c), abnormal_range_followup (cycle 10a). MGC and ZN partially fire only due to session-structure quirks (in_session gaps mid-session reset the `session_open_bars` counter, allowing mid-session fires).

**Pre-flight check addition:** When entry primitive uses `session_open_bars` or any "fire only at session start" logic, verify it triggers AT OR AFTER 09:45 ET (when `entry_ok = True`). Two options:

1. Adjust the primitive to count session bars STARTING from 09:45 (skip the first 3 bars of RTH):
   ```python
   # Count from first entry_ok bar, not first in_session bar
   if not f["entry_ok"][i]: return 0, 0, 0
   ```

2. Adjust the session-detection logic to use `entry_ok` instead of `in_session`:
   ```python
   # Use entry_ok as session-start detector
   if i == 0 or not f["entry_ok"][i-1]:
       # We're at the first entry_ok bar of the day
   ```

**Cost of mistake:** ~25 min compute across 3 cycles (gap_fill + retry + abnormal_range) + operator-decision overhead on archived primitives.

**Cost of pre-flight check:** ~3 minutes — synthetic test asserts entry fires when `entry_ok=True` (≥09:45), not just when `in_session=True`.

**Lesson generalized:** the entry primitive's intended firing window MUST be inside `entry_ok` window. Any "fire at session open" logic that operates before 09:45 ET will be silently filtered out by the signal generator.

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
