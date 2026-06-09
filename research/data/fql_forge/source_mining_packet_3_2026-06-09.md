# Source Mining Packet 3 — 2026-06-09 Day-12 Update

> **Status:** Extension of SMP-2 catalog. Incorporates closed-loop lessons from cycles 08l, 09a, 09b.
> **Authority:** Lane B research-only.
> **Method:** update + reorder Tier 2 NEEDS_PRIMITIVE with detailed specs; codify filter pre-flight lesson; surface concrete approval-ready options.

## Lessons absorbed since SMP-2 (2026-06-08)

### 1. Hurst filters are non-productive at intraday timescales (confirmed both directions)

Tested and falsified:
- `hurst_stable_mr × bb_reversion × MES/MNQ` (08l): anti-edge
- `hurst_stable_trend × DC/ORB × MES/MNQ/MGC` (09a): sub-edge

SMP-1 catalog framing of hurst as "critical primitive-coverage waste" was wrong. Both filters remain in FILTER_MAP for future thesis-driven research (e.g., daily-bar carry, multi-session swing). Full detail in `research/data/fql_forge/hurst_filter_non_productive_finding.md`.

### 2. Filter-entry direction-logic compatibility must be pre-flight verified

`gap_fill_trigger` (09b) revealed that `ema_slope` filter is structurally incompatible with FADE entries:
- Filter requires `ema20 > ema50` for LONG / `ema20 < ema50` for SHORT
- FADE mechanism requires SHORT after gap UP (typically in uptrend) and LONG after gap DOWN (typically in downtrend) — OPPOSITE direction logic

**Result:** n=0 on 4 of 6 assets in gap_fill first batch — primitive could not be fairly evaluated.

**Lesson:** before building a new entry primitive, validate filter-entry direction-logic compatibility on synthetic data. Test at least 2-3 sample bars where mechanism should fire + filter should pass. If filter blocks all setups, choose different filter for first batch.

## Updated Tier 2 NEEDS_PRIMITIVE specs (detailed)

### Spec: stop_run_reversal

**Mechanism:**
Detect liquidity sweeps: price spikes through a recent swing high/low, then reverses within N bars. Enter in the reversal direction.

**Detailed logic:**
1. Identify swing high/low: a bar where `high[i]` > all `high[i-N..i-1]` for `swing_lookback` (default 20) bars. Equivalent for swing lows.
2. Track recent swing-high/low value as `swing_h` / `swing_l`.
3. Detect sweep: `high[i] > swing_h * (1 + sweep_buffer)` (gap up through prior swing high) OR `low[i] < swing_l * (1 - sweep_buffer)`.
4. Detect reversal: within next `reversal_window_bars` (default 3) bars, close moves back below `swing_h` (for sweep-up) or above `swing_l` (for sweep-down).
5. Enter at reversal-confirmation bar in OPPOSITE direction of sweep: sweep-up → SHORT; sweep-down → LONG.

**Direction logic compatibility with filters:**
- `ema_slope` filter: PROBLEMATIC (sweeps often go WITH trend, so reversal entry is AGAINST trend → filter blocks). **Use filter=none for first batch.**
- `session_morning` filter: COMPATIBLE (most liquidity sweeps occur at session opens)
- `vol_regime` (high-vol band): COMPATIBLE (sweeps require high vol)

**Build estimate:** 4-6h (swing-detection logic + sweep/reversal state tracking + smoke tests)

**Expected first batch:** MGC, MCL, MES, MYM, MNQ (5 candidates with filter=none)

**Why this might unlock Packet #2:**
Sweeps are well-documented in market microstructure literature as repeatable mean-reversion events. Different from compression (RCB), squeeze (BBKC), and gap-fade (gap_fill). The mechanism specifically targets the "stop-hunting" pattern that intraday algorithms often exploit.

### Spec: opening_drive_continuation

**Mechanism:**
Detect sustained directional move in first 30-60 minutes of session (different from ORB which is breakout-of-range). Enter on continuation (momentum follow) once direction is confirmed.

**Detailed logic:**
1. Track session-open price (close at first session bar).
2. At each in-session bar within `drive_window_bars` (default 6 bars = 30min), compute `drive` = (close - open_price) / ATR.
3. Direction confirmed when `abs(drive) > min_drive_threshold` (default 1.5 ATR).
4. After confirmation, wait for `pullback_window_bars` (default 3) to find a pullback (counter-trend bar).
5. Enter at next bar in original drive direction (LONG if drive_up, SHORT if drive_down).

**Direction logic compatibility with filters:**
- `ema_slope` filter: COMPATIBLE (drive direction will typically align with longer-term trend)
- `session_morning` filter: REDUNDANT (mechanism is itself session-bound; would over-constrain)

**Build estimate:** 3-4h (drive tracking + pullback detection + state machine)

**Expected first batch:** MGC, MCL, MES, MYM, MNQ (5 candidates with ema_slope filter)

**Why this might unlock Packet #2:**
Opening drives are a different family than ORB breakouts. ORB triggers on range breaks; opening_drive triggers on sustained move regardless of whether range was broken. Different signal-construction may produce different cost-fragility profile.

## Reordered NEEDS_PRIMITIVE priority

Given filter-mismatch lesson + cost-fragility hypothesis:

| Priority | Spec | Build cost | Filter required | Notes |
|---:|---|---|---|---|
| 1 | stop_run_reversal | 4-6h | **filter=none** for first batch | Most novel mechanism; well-documented theoretical basis |
| 2 | opening_drive_continuation | 3-4h | ema_slope OK | Lower-novelty but cheaper; redundant overlap with ORB needs family review |
| 3 | (deferred) ICT liquidity sweep | 6-10h | TBD | Higher complexity overlaps with stop_run_reversal — skip if stop_run productive |

## DATA_REQUIRED queue (unchanged, priority order)

1. **Prop-firm cost rate sheet** (highest leverage per cumulative cost-fragility hypothesis)
2. Surprise-conditioned EIA crude data
3. Treasury auction calendar
4. WASDE / grain assets
5. COT-shift CFTC ingestion
6. OPEC curated outcomes

## Cumulative new-primitive scoreboard (4 mechanism families tested)

| Primitive | Final | Best near-miss |
|---|---|---|
| range_compression_break (RCB) | RESEARCH_ONLY | RCB15-MYM-Short PF 2.07 (71.6% concentration) |
| volatility_regime_compound (VRC) | ARCHIVED | mechanism anti-edge |
| bb_keltner_squeeze (BBKC) | RESEARCH_ONLY | **BBKC-MNQ PF 1.21 med $2.76 (cost-sensitive)** |
| gap_fill_trigger | RESEARCH_ONLY | filter-mismatch (untested fairly) |

**0 PAPER_PACKET from 4 mechanism-family explorations. 1 cost-sensitive near-miss. 1 filter-mismatch retry possible.**

## Approval-ready operator decision matrix

For when operator returns, the cleanest approval flow:

### Option A — Build stop_run_reversal next
- Approve: "OK build stop_run_reversal"
- Forge actions: build entry primitive + smoke tests + first batch (5 candidates, filter=none, PL-default)
- Time to result: ~6-8h elapsed (mostly batch runtime)

### Option B — Approve gap_fill filter-aligned retry
- Approve: "OK 118-A retry gap_fill with filter=none"
- Forge actions: rerun 6 candidates with `filter="none"`
- Time to result: ~10-15 min

### Option C — Operator submits filled prop-cost template (highest-leverage)
- Operator submits filled Blocks A/B/C with verified rate sheet
- Forge actions: re-run prop-stress for BBKC-MNQ + MCL Short PL/FR2 with verified costs; reclassify any newly-PASS_STRESS; family-review survivors
- Time to result: ~30-60 min after operator submission

### Option D — Combo: gap_fill retry + stop_run build in parallel
- Approve: "OK A + B parallel"
- Forge actions: run gap_fill retry while building stop_run_reversal
- Time to result: ~6-8h elapsed

## Constraints

- No registry mutation, no scheduler change, no portfolio change, no paper/live promotion.
- No cost-assumption changes without operator-verified data.
- Lane B research-only.

## Source artifacts

- `research/data/fql_forge/source_mining_packet_2_2026-06-08.md` (predecessor catalog)
- `research/data/fql_forge/hurst_filter_non_productive_finding.md` (lesson 1)
- `research/data/fql_forge/reports/forge_cycle_2026-06-09{a,b}.json` (lessons 1 + 2)
- `research/data/fql_forge/kill_taxonomy.json` (campaign trail)
