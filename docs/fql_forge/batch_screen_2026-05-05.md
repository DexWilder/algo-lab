# Batch Cheap-Screen — 2026-05-05

**Filed:** 2026-05-05 (Lane B / Forge throughput run — operator's batch-mode push)
**Authority:** T1, no Lane A surfaces touched. No registry mutation.
**Scope:** 3 candidates from `docs/fql_forge/hybrid_candidates_2026-05-05.md`. Cheap-screens via `research/scratch/batch_screen_2026-05-05.py`.

---

## Result table

| Candidate | Asset | Gap / family | Trades | PF | Net PnL | Max DD | Comparison baseline | Verdict | Next action |
|---|---|---|---:|---:|---:|---:|---|---|---|
| **XB-VWAP-EMA-Ladder-MNQ** | MNQ | Workhorse diversity (proven trio with VWAP entry) | 812 | **1.056** | +$2,511 | -$5,212 | XB-ORB-EMA-Ladder-MNQ baseline PF 1.62, 1183 trades | **KILL** | ORB is non-substitutable in proven trio; record learning, do not iterate |
| **XB-Donchian-EMA-Ladder-MCL** | MCL | Energy breadth (proven trio with Donchian entry) | 0 | n/a | $0 | $0 | n/a | **RETEST** | Engine `donchian_breakout` produces 0 trades on MNQ too — config issue, not candidate quality. Debug engine config separately. |
| **HYB-CashClose-A no-filter** | ZN | STRUCTURAL session-transition (rates, cash-close 14:45-15:25 ET fade) | 1,367 | **0.263** | **-$41,980** | **-$41,972** | n/a (new mechanism) | **KILL (hard)** | Cash-close fade logic catastrophically loses on ZN — wrong direction or wrong window for fade |
| **HYB-CashClose-B impulse-filtered** | ZN | Same | 98 | **0.552** | -$2,558 | -$3,471 | A above | **KILL** | Filter reduces losses but doesn't reverse direction; salvage attempt fails |

---

## Headline learnings (the durable evidence from this batch)

1. **ORB entry is NOT substitutable in the proven XB-ORB-EMA-Ladder trio.** Swapping to VWAP_continuation produces PF 1.056 (vs ORB's 1.62) and a NEGATIVE median trade despite positive aggregate. The entry mechanism is load-bearing — `ema_slope` filter and `profit_ladder` exit are NOT sufficient on their own. This is a high-information answer to one of Phase 0's core questions ("are proven_donors entry-agnostic?"). Answer: **no.** Donor catalog should mark ORB-derived donors as bundled with the assembly, not standalone-portable.

2. **Cash-close ZN does NOT extend ZN-Afternoon's edge.** The afternoon-reversion edge is window-specific (13:45-14:00 ET), not generalizable to the cash-close window (14:45-15:25 ET). The "fade the impulse" mechanism that works in the early-afternoon window FAILS in the cash-close window. Different microstructure, different participant behavior, different optimal direction.

3. **Donchian entry needs engine debug.** 0 trades on both MCL and MNQ across full data history. Either the entry threshold is too restrictive in the current engine config, or the entry function is broken. Out-of-batch fix.

4. **Item 2 cross-pollination criterion: still 0/2.** No candidate from this batch passed. The salvage thread (HYB-CashClose) was exercised — second attempt at populating `relationships.salvaged_from` after HYB-FX failed similarly. **Two salvage attempts, two failures.** Combined with HYB-FX's three calibration runs, today produced FIVE attempts at the salvage path with zero successes. That's becoming a real signal: salvages from rejected parents may be harder to make work than the donor-economy doctrine assumed.

---

## Updated donor catalog state (post-batch)

| Donor | Status update |
|---|---|
| `orb_breakout` (proven_donor) | Confirmed entry-load-bearing — substitutes fail. Strengthens proven status WITHIN the assembly |
| `ema_slope` (proven_donor) | Confirmed: necessary but not sufficient. Holds in proven tier but with note that paired entry matters |
| `profit_ladder` (proven_donor) | Same — necessary but not sufficient |
| `vwap_continuation` (engine entry) | Tested in proven trio: PF 1.056, weak. Available for other recipes but downweight expectations |
| `donchian_breakout` (engine entry) | Engine config issue — needs debug before any further use |
| `afternoon_session_reversion_timing` (Treasury-Cash-Close salvage) | Fails to transplant to cash-close window with naive fade logic. Mark as one-attempt-failed |
| `impulse_threshold` filter on cash-close window | Reduces blow-up but can't reverse direction; not a sufficient corrective on its own |

---

## Next batch queue (ranked by leverage; operator confirms scope)

| # | Candidate | Why next | Estimated cheap-test cost |
|---|---|---|---|
| 1 | **HYB-LunchComp-RatesAfternoon** (Candidate 3 from hybrid_candidates set) | Untested salvage from this set. Salvage path attempt #3. ZN/rates context. 3-component assembly (lunch_compression + high_vol_regime + impulse_threshold). | ~10s scratch run |
| 2 | **XB-PB-EMA-Ladder-MNQ** (proven trio with `pb_pullback` entry instead of ORB) | Tests another entry substitution; if also fails, confirms ORB is essential AND probably means the proven trio is "tightly coupled" rather than "donor catalog of swappable parts" | ~10s same harness as today |
| 3 | **HYB-VolMan-Sizing on a weaker baseline** (DailyTrend-MGC-Long or ZN-Afternoon-Reversion as parent) | Tests sizing overlay on parent with headroom (today's HYB-VolMan PASS-with-WARN was bounded by ceiling effect on XB-ORB-MNQ) | ~15s — needs DailyTrend strategy code (may not exist; would need re-implementation) |
| 4 | **HYB-BB-EMA-Ladder-MNQ** (`bb_reversion` entry in proven trio) | Same family as candidate 2; one more entry-substitution data point | ~10s |
| 5 | **Engine debug: `donchian_breakout` entry** | Out-of-batch — fix the engine config so future Donchian recipes can be tested. Lane B research/build (no Lane A change). | ~30 min investigation |

---

## What this batch did NOT do

- No registry append (any candidate)
- No Lane A surfaces touched
- No broad parameter optimization
- No promotion to live or to Phase 0 activation
- No iteration on KILL'd candidates beyond the one-bounded RETEST that confirmed Donchian is engine-config not asset-specific

---

## Files

- Scratch: `research/scratch/batch_screen_2026-05-05.py`
- This memo: `docs/fql_forge/batch_screen_2026-05-05.md`

---

*Filed 2026-05-05. Lane B / Forge batch-mode run. Per new operating rule: not standing by — surfacing next batch queue immediately.*
