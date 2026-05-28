# Phase 4b — High-fidelity backlog translation (26 SCREENABLE notes)

Re-reading of the 26 notes that Phase 4 keyword-mapped as `SCREENABLE_WITH_DEFAULT`,
with explicit parameter / pairing extraction. Routing per the 5-tier model:
EXACT_SCREEN / APPROX_SCREEN / NEEDS_NEW_PRIMITIVE / NEEDS_HOST / BACKLOG_ONLY.

Locked doctrine: backlog notes are NOT candidate specs until parameters extracted
(`feedback_backlog_translation_fidelity.md`). The Phase 5 wipeout (8/8 KILL)
proved that keyword-to-primitive default-param translation produces unrunnable
candidates. This document corrects that.

---

## Translation routing summary

| Routing | Count | Action |
|---|---|---|
| EXACT_SCREEN | **0** | None of the 26 notes have all parameters extractable + engine-primitive-exact |
| APPROX_SCREEN | 5 | Documented approximation; eligible for Phase 6 if approximation is small |
| NEEDS_NEW_PRIMITIVE | 11 | Roadmap items; require engine extension (Dual Thrust, anchored VWAP, RSI, session VWAP, etc.) |
| NEEDS_HOST | 7 | Exit-logic / overlay fragments needing host strategy pairing |
| BACKLOG_ONLY | 3 | Conceptual / falsification-baseline notes — keep but don't screen |

**Honest read:** the SCREENABLE pool is much smaller than Phase 4's keyword classification suggested. Most of these notes carry specific mechanics (Dual Thrust threshold formula, anchored VWAP, RSI, session VWAP bounce 2-candle confirmation, DXY proxy, dual-session state machines) that the engine does not currently implement. The real factory bottleneck is now **engine primitive coverage**, not candidate volume.

---

## Per-note translation table (all 26)

### APPROX_SCREEN (5 candidates — Phase 6 eligible)

| # | Source note | Approximation | Recommended P6 spec |
|---|---|---|---|
| A1 | 2026-05-07_13 — Donchian channel breakout fragment | Note specifies "lookback channel" but no explicit lookback; default to engine's 20-bar. Note explicitly pairs with "separate stop and hold framework" → use **no filter** (not ema_slope). | XB-Donchian-NoFilter-Ladder-MCL |
| A2 | 2026-05-14_09 — ATR stop + Donchian entry for commodity/rates | Donchian default lookback; pair atr_trail exit | XB-Donchian-NoFilter-ATRTrail-MCL |
| A3 | 2026-04-23_01 — Donchian breakout with ATR stop for non-equity | Pyramiding optional (skip in P6); default Donchian lookback | XB-Donchian-NoFilter-ATRTrail-6E (FX asset) |
| A4 | 2026-05-26_10 — Non-equity breakout requires BB bandwidth expansion | engine `bandwidth_squeeze` approximates "BB width in bottom decile of 60-session distribution"; default bw_threshold=50 | XB-ORB-BBSqueeze-Ladder-GC (gold, not yet tested) |
| A5 | 2026-04-16_05 — ORB with width filter | Width filter not in engine; APPROX = orb_breakout default (no width). Tested in Phase 3 already as ORB-Afternoon-Ladder; the width-filter idea unverifiable until built. | DEFERRED — already substantively covered by Phase 3 ORB family results; would re-test the same thing |

**Critical Phase 5 lesson driving the no-filter pick:** Phase 5's Donchian variants used `ema_slope` filter and produced 0 trades on MCL/MGC. The source notes (#4, #5, #12) do NOT specify ema_slope — they imply "Donchian + stop/hold framework," which translates closer to `filter=none`. The Phase 6 batch tests this corrected translation.

### NEEDS_NEW_PRIMITIVE (11 — roadmap items, not P6)

| # | Source note | Missing primitive |
|---|---|---|
| N1 | 2026-05-14_01 — Dual Thrust ORB for rates/commodities | Dual Thrust threshold (prior day OHLC formula, distinct from orb_breakout) |
| N2 | 2026-04-07_09 — Tokyo Open DXY Bias Session Effect | DXY proxy series + Tokyo open + first-pullback rule |
| N3 | 2026-04-17_03 — Afternoon VWAP Slope Confirmation | Anchored VWAP + cumulative delta proxy |
| N4 | 2026-05-06_12 — RSI MA Distance Cap for Intraday FX Reversion | RSI primitive + MA distance percentile gate |
| N5 | 2026-05-26_06 — London-to-NY FX value session alignment | Multi-session state machine + valuation anchor |
| N6 | 2026-04-16_03 — Dual-Thrust Afternoon Energy Release | Dual Thrust + range-compression filter + 12:30/14:00 ET windows |
| N7 | 2026-03-25_10 — Tokyo Session VWAP Bounce on JPY Futures | Session-anchored VWAP + 2-candle confirmation + opening-range marks |
| N8 | 2026-04-16_10 — Tokyo Open Failed-Drive Reversal | Failed-break detection + 2-bar reclaim confirmation |
| N9 | 2026-04-17_04 — Tokyo London Overlap Compression Break | Session-range compression + Tokyo-London overlap window |
| N10 | 2026-05-07_02 — Dual Thrust + Donchian + ATR risk frame | Dual Thrust threshold |
| N11 | 2026-05-14_05 — Fractional pyramid after Donchian breakout | Pyramiding / staged add bookkeeping |

**Critical pattern:** 5 of these (N1, N2, N5, N6, N7, N8, N9) require **session-specific primitives** that the engine does not have. Session targeting beyond morning/afternoon (Tokyo, London, NY, global commodity open) is a real gap. Dual Thrust is also a 3x-recurring missing primitive.

### NEEDS_HOST (7 — exit/overlay fragments requiring host)

| # | Source note | Concept | Best host candidate |
|---|---|---|---|
| H1 | 2026-05-04_05 & 2026-05-03_05 (dup) — Partial profit ladder for non-equity trends | 3N/6N/9N partial scale-out exit | XB-ORB-EMA-Ladder family on non-equity assets |
| H2 | 2026-05-01_06 — Time stop for threshold reversal failures | Force exit if minimum follow-through not reached in N bars | XB-ORB-EMA-Ladder family on non-equity |
| H3 | 2026-04-19_12 — Support-bounce time-stop exit FX | Exit overlay on FX bounce entries | Needs FX bounce host (not in registry) |
| H4 | 2026-04-14_09 — GBPUSD Bounce Exit Template | 60% retracement + 8-bar time stop | Same as H3 — FX bounce host needed |
| H5 | 2026-05-07_03 — Multistage profit ladder for non-equity trend trades | 3N/6N/9N scale-out (duplicate of H1) | Same as H1 |
| H6 | 2026-05-11_03 — Multistage profit ladder for non-equity trend books | 3N/6N/9N scale-out (duplicate of H1/H5) | Same as H1 |

**Pattern:** profit-ladder variants H1/H5/H6 are essentially the same exit concept repeating. Once a 3N/6N/9N partial-exit primitive is built, all three notes test as the same exit-variant on existing host strategies.

### BACKLOG_ONLY (3)

| # | Source note | Reason for backlog-only |
|---|---|---|
| B1 | 2026-04-21_10 — Random entry time-stop baseline FX | Falsification baseline, not an edge-seeking strategy. Useful as benchmark when other FX edges are built — not a candidate. |
| B2 | 2026-04-22_12 — Random entry time-stop baseline for FX carry pairs | Same as B1 |
| B3 | 2026-04-16_04 — Global Commodity Open Buffer Breakout Levels | Session-anchor mapping (IST → CME) is non-trivial and would need an Asian-session primitive; closer to NEEDS_NEW_PRIMITIVE but value of the candidate alone is low |

---

## Phase 6 cheap-screen batch (5 candidates)

All 5 are APPROX_SCREEN per the table above. Selected to maximally test the
Phase 5 no-trade hypothesis (was `ema_slope` filter the cause?) and to extend
the asset dimension beyond Phase 5's MCL focus.

| # | Candidate | Asset | Entry | Filter | Exit | Hypothesis |
|---|---|---|---|---|---|---|
| P6-1 | XB-Donchian-NoFilter-Ladder-MCL | MCL | donchian_breakout | none | profit_ladder | Phase 5 Donchian+EMA-slope produced 0 trades; was the filter the cause? |
| P6-2 | XB-Donchian-NoFilter-Ladder-MGC | MGC | donchian_breakout | none | profit_ladder | Same hypothesis on gold |
| P6-3 | XB-Donchian-NoFilter-Ladder-6E | 6E | donchian_breakout | none | profit_ladder | Same hypothesis on FX |
| P6-4 | XB-Donchian-NoFilter-ATRTrail-MCL | MCL | donchian_breakout | none | atr_trail | Same hypothesis with the ATR-trail exit (note A2/A3) |
| P6-5 | XB-ORB-BBSqueeze-Ladder-GC | GC | orb_breakout | bandwidth_squeeze | profit_ladder | BB-squeeze on gold (not tested in Phase 5 — only MCL was) |

**Diversity check at sourcing:**
- non-MNQ: 5/5 ✓
- non-index: 5/5 ✓
- 4 Donchian + 1 ORB-BB (low entry diversity — but intentional, this batch is a **diagnostic** to resolve Phase 5's translation question)
- 3 asset classes: energy (MCL), gold (MGC, GC), FX (6E) ✓

**Correlation-guard pre-check:**
- P6-1 vs P6-4: same `(asset, entry, filter)` = MCL+donchian+none, different exits. Cluster will fire — pick at most 1 at promotion.
- Other pairs: each differs on ≥2 slots.

**Honest framing of this batch:**
This is a *diagnostic sprint*, not a wire-candidate-generation sprint. The primary objective is to confirm or refute the no-filter hypothesis from Phase 5. If P6-1/P6-2/P6-3 produce trades and PASS-or-MUTATE verdicts, then Phase 5's no-trade results were driven by filter mismatch, and the broader backlog Donchian family becomes screenable. If they still produce 0 trades or KILL on cost, then the Donchian primitive in this engine doesn't transfer to non-equity assets at default lookback, and Donchian-family notes route to NEEDS_NEW_PRIMITIVE (needs explicit lookback parameter extraction or different default).

---

## What this changes about the next-after-Phase-6 direction

If P6 confirms the no-filter hypothesis:
→ The backlog Donchian family becomes a real candidate-supply lane. Expand to more assets.

If P6 refutes the hypothesis:
→ The backlog is mostly NEEDS_NEW_PRIMITIVE; the next bottleneck is **building 2–3 new primitives** (Dual Thrust, anchored VWAP, RSI). Each primitive unlocks 2–5 backlog notes.

Either way, the days of "consume the backlog" as a Forge pattern are constrained by engine coverage, not by note volume.

---

## Pointers

- Phase 4 raw queue: `docs/reports/forge_sprint/2026-05-28_phase4_candidate_queue.json`
- Phase 5 results (the failure that triggered this re-parse): `docs/reports/2026-05-28_offensive_sprint_v3_phase5.json`
- Translation doctrine: `feedback_backlog_translation_fidelity.md` (memory)
- Three-track model: `feedback_three_track_candidate_model.md` (memory)
