# FQL Forge Daily Scorecard — 2026-06-02

**Generated:** 2026-06-02 ~20:45 PT (post-restart cycle)
**Mode:** Lane B / report-only / nonstop hunt
**Sprint day:** 30-day Paper-Readiness Sprint, day-of-30 unset (anchor to confirm). **Day-17 trigger:** unset.

---

## 1. Funnel state

| Stage | Count | Δ today | Target |
|---|---:|---:|---|
| Harvest backlog (Forge pending pickup) | 704 | +15 | drain to <100 over ~60 days |
| Refinement pending | 191 | — | — |
| Assessment pending | 28 | — | — |
| Specs generated today | **4** | +4 | 5–10 **qualified gap-aware** specs/day |
| Specs cheap-screened today | 6 (5 scheduled + 1 B2 mut) | +6 | match spec-generation rate |
| Mutation specs queued | 1 (B2 mut 1 done) | +1 | each WATCH → ≥1 mutation attempt |
| Candidates BLOCKED awaiting decision-grade | **6** (B2 mut 2-3, B3 A-D) | +6 | track until unblocked |
| Paper-readiness packets produced today | 0 | 0 | 1–3 over 30 days |

**Qualified-gap-aware specs generated today (4 of 4 qualified):**
- A: `EVT-Treasury-Auction-Drift-Snap-ZN` (gap: rates event/calendar)
- B: `EVT-EIA-Inventory-Crack-Gate-MCL` (gap: crude-native event)
- C: `CRY-Policy-Rate-Differential-6J` (gap: FX + carry)
- D: `EVT-OPEC-Cut-Drift-MCL` (gap: tail engine + crude-native + positive-skew)

All 4 specs target gaps not represented in current core/probation cohort.
**Vanity guard:** zero raw-volume specs added — only architecture-coverage moves.

---

## 2. Verdict counts (today's scheduled fire + B2 mut)

| Verdict | Scheduled (06-02 19:01) | B2 mut 1 | Total |
|---|---:|---:|---:|
| PASS | 3 | 0 | 3 |
| WATCH | 2 | 1 | 3 |
| RETEST | 0 | 0 | 0 |
| KILL | 0 | 0 | 0 |
| BLOCKED_WITH_DATA_REQUIREMENT | — | — | 2 |
| BLOCKED_WITH_PRIMITIVE_REQUIREMENT | — | — | 4 |

**Classifications applied to yesterday's + today's 5 PASS verdicts:** 0 ADVANCE_TO_DEEP_SCREEN / 4 WATCH / 1 RETEST. Detail in `research/data/fql_forge/kill_taxonomy.json`.

---

## 3. Top kill / WATCH reasons today

| Tag | Count | Closed-loop signal |
|---|---:|---|
| `concentration` | 6 | **Dominant failure mode** — cheap-screen over-samples a regime-dependent XB/MGC/MYM cluster |
| `implementation-blocked` | 6 | **Primitive coverage is bottleneck** — event-window + monthly-rebalance harness needed |
| `WF-split-fail` | 3 | H1/H2 asymmetry in BB candidates suggests regime carrying edge |
| `median-negative` | 3 | Edge doctrine signal #1 broken in 3 candidates incl. B2 mut 1 |
| `duplicate/overlap` | 3 | MYM/MGC already in cohort — additions concentrate, not diversify |
| `data-blocked` | 2 | EIA M2 spread + OPEC outcome list — per operator directive, surface not overbuild |
| `regime-dependent` | 2 | H2 >> H1 PF pattern; concentration is temporal not session |
| `cost-eats-edge` | 0 | Cost calibration stable — not the current bottleneck |
| `insufficient-n` | 1 | One borderline tail-engine sample |

---

## 4. Architecture gaps touched today

| Gap | Specs hunted today | Status |
|---|---:|---|
| VALUE | 0 (heavy in 30-note harvest backlog — next hunt cycle) | unfilled |
| CARRY | 1 (Spec C 6J) | BLOCKED_PRIMITIVE |
| VOL / vol-expansion | 0 | unfilled |
| STRUCTURAL / liquidity vacuum | 0 | unfilled |
| Non-equity index | 4 (A, B, C, D) | all BLOCKED |
| Afternoon / close / overnight | 1 (B2 mut 1 morning-only) | WATCH (degraded) |
| FX | 1 (Spec C) | BLOCKED_PRIMITIVE (data ✓) |
| Rates event/calendar | 1 (Spec A) | BLOCKED_PRIMITIVE (data ✓) |
| Crude-native event | 2 (B, D) | BLOCKED_DATA + PRIMITIVE |
| Metals | 0 | unfilled |
| Positive-skew tail engine | 1 (Spec D) | BLOCKED_DATA |
| Decorrelating | 4 of 4 specs | — |

**Coverage scorecard:** 4 gap categories touched (CARRY, FX, rates-event, crude-event). 6 gap categories still unaddressed today. Next cycle priorities: VALUE (heavy harvest backlog), VOL, STRUCTURAL, metals.

---

## 5. Candidate closest to paper packet

**None today.** Closest existing probation candidate per yesterday's brief: `Treasury-Rolldown-Carry-Spread` (eff. 20, displacing MomIgn at June 1) and `VolManaged-EquityIndex-Futures` (CONVICTION-READY). Both governed by Lane A controller; no Lane B Forge action available.

**Forge-side paper-packet pipeline is empty.** 0 candidates have cleared cheap-screen → deep-screen → forward evidence. All today's 5 cheap-screen PASSes failed concentration gates at the WATCH classification.

**Implication for sprint:** Day-of-30 needs to be set so day-17 trigger fires correctly. If sprint starts today (2026-06-02), day-17 = 2026-06-19.

---

## 6. Next task in chain

**Immediate next Forge tasks (autonomous, gap-aware, existing-primitive-compatible):**

1. **VALUE-hunt batch** — backlog is heavy with cross-asset value notes (12 of last 30 harvest). Generate 3–5 specs targeting cross-sectional value on equity-index spreads OR commodity value (pairs of liquid micro futures). Primitives needed: ranking + spread harness. Check existing portfolio_correlation_matrix.py for re-use.
2. **DC-EMA Donchian extension** — `donchian_breakout` entry primitive exists but ZERO candidates use it. Add 2–3 specs: `XB-DC-EMA-Ladder-MCL`, `XB-DC-EMA-Ladder-MGC`, `XB-DC-EMA-Ladder-ZN`. All existing primitives. Pure gap-aware. Run via existing harness.
3. **Rates extension** — ZN/ZF/ZB last_bar current. Existing ZN strategies = 2. Cross-asset extension of XB-ORB-EMA-Ladder to rates. All existing primitives.
4. **Volatility-regime overlay mutation primitive** — needed to actually repair the high max-year on XB-BB-MGC; small primitive (FILTER_MAP entry that uses ATR-percentile or rolling-vol gate). Unlocks the concentration-mutation lane Plan B after B2 mut 1's session-filter failure.

**Chain rule:** finish one → start next → no idle gap → surface only decision-grade.

---

## 7. Open decision-grade asks for operator

| # | Ask | Why | Backlog-unlock count |
|---|---|---|---:|
| 1 | **Build event-window Forge primitive** | Unlocks Spec A + B + D (+ ~7 of last 30 harvest notes auction/EIA/CPI/OPEC/FOMC-drift) | ~10 candidates |
| 2 | **Template monthly-rebalance harness from `run_treasury_rolldown_spread.py` for 6J/FX carry** | Unlocks Spec C (+ all future FX/policy carry candidates) | ~3–5 candidates |
| 3 | **Build volatility-regime overlay FILTER_MAP primitive** | Unlocks concentration-mutation lane Plan B after B2 mut 1 failure | ~5 WATCH candidates (today's batch) |
| 4 | **Add EIA M2 crude curve data to ingest** | Unlocks Spec B + future crude curve candidates | ~2–3 candidates |
| 5 | **Compile OPEC conference outcome list (manual classification)** | Unlocks Spec D | 1 candidate |

**Recommended ranking by leverage:** #1 > #3 > #2 > #4 > #5.

---

## 8. Sprint scoreboard

- **Sprint deliverable:** 1–3 paper-readiness packets over 30 days
- **Day count to day-17 trigger:** depends on sprint anchor date (TBD by operator)
- **Current paper-packet progress:** 0
- **Health:** sprint scoreboard is empty — primitive coverage is gating throughput from cheap-screen → deep-screen → paper packet. Without unlock #1 (event-window) and #3 (vol-regime overlay), the next 5-10 cheap-screen days will repeat today's WATCH pattern.

---

## 9. Boundaries held (verification)

- ✅ No Lane A change
- ✅ No registry truth mutation (kill_taxonomy.json is report-only, not consumed by runner)
- ✅ No scheduler/cadence change
- ✅ No portfolio allocation change
- ✅ No promotion / paper / live change
- ✅ No OpenClaw upgrade
- ⚠️ Code change made: 1 candidate added to `research/fql_forge_batch_runner.py` CANDIDATES dict (`XB-BB-EMA-MorningOnly-MGC-v2`, batch B2 mut 1). This is the Forge research catalog; Lane B research source code, not Lane A runtime. Per operator approval of "OK Batch B2."
