# FQL Forge Daily Scorecard — 2026-06-03

**Generated:** 2026-06-03 (post-build cycle)
**Mode:** Lane B / report-only / nonstop autonomous
**Sprint:** Paper-Readiness Sprint anchored **2026-06-02**. Day-17 checkpoint **2026-06-19**. 30-day deliverable **2026-07-02**.
**Day of sprint:** 2 / 30

---

## 1. Cycle deliverables

| Build | File(s) | Status | Smoke |
|---|---|---|---|
| Event-window Forge primitive | `research/event_window_engine.py` | ✅ shipped | 8/8 tests + end-to-end MCL: n=20, PF=1.261, archetype=TAIL_ENGINE, gate=KILL (random events; expected) |
| FX-carry monthly harness | `research/monthly_rebalance_engine.py` | ✅ shipped | 5/5 tests + end-to-end 6J: n=14, PF=0.739, gate=KILL (alternating sig; expected) |
| Vol-regime FILTER_MAP primitive | `research/crossbreeding/crossbreeding_engine.py` (`atr_pctrank`, `vol_regime`, `ema_slope_vol_high`, `ema_slope_vol_low`) | ✅ shipped | 4/4 tests + concentration-mutation comparison on XB-BB-MGC |

**All three approved unlock builds shipped this cycle.** Each ships with a self-contained smoke test script under `research/tests/`. No registry mutation, no Lane A touch.

---

## 2. Empirical finding — concentration-mutation Plan B failed

| Variant | Filter | n | PF | Median | Max-Year | Top-3 | Top-10 | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Baseline | `ema_slope` | 298 | 1.611 | $1.76 | **95.7%** | 74.0% | 127.6% | PASS |
| Vol-high(70) | `ema_slope_vol_high` | 17 | 0.595 | $0.76 | 0.0% | 0.0% | 0.0% | **KILL** (sample) |
| Vol-low(30) | `ema_slope_vol_low` | 247 | 1.609 | $1.76 | **94.3%** | 80.4% | 138.6% | WATCH |

**Diagnosis:** vol-regime overlay does NOT repair XB-BB-MGC concentration. High-vol filter destroys sample size; low-vol filter preserves PF (1.611 → 1.609) but keeps max-year at 94.3% (was 95.7%).

**Cumulative concentration-mutation evidence on XB-BB-MGC:**
- Session-morning filter (2026-06-02): degrades PF 1.502 → 1.042, median +0.26 → -20.24 → wrong axis
- Vol-high filter (2026-06-03): destroys sample → unusable
- Vol-low filter (2026-06-03): preserves PF, preserves concentration → wrong axis

**Closed-loop pivot:** concentration is **calendar-year / regime-dominance**, not session or vol. Next mutation = explicit temporal split (train vs test on year axis) OR year-by-year robustness gate. Both intraday filter axes are exhausted for this candidate.

---

## 3. Funnel state

| Stage | 2026-06-02 | 2026-06-03 | Δ | Target |
|---|---:|---:|---:|---|
| Harvest backlog | 704 | ~704 | — | drain to <100 over ~60 days |
| Specs generated this cycle | 4 (A/B/C/D) | 0 (built primitives instead) | — | 5–10 qualified gap-aware/day |
| Specs cheap-screened this cycle | 6 | 2 (vol-regime mut) | -4 | match generation rate |
| Mutation specs tested | 1 | 2 | +2 | each WATCH → ≥1 mutation attempt |
| Candidates BLOCKED awaiting decision-grade | 6 | 2 (Spec B data, Spec D data) | -4 | unblock via builds |
| Paper-readiness packets produced | 0 | 0 | 0 | 1–3 over 30 days |

**Vanity-guard:** zero raw-volume specs added this cycle; all work was approved primitive unlocks + concentration-mutation Plan B test.

---

## 4. Verdict counts cumulative

| Verdict | Cumulative through 2026-06-03 |
|---|---:|
| PASS (cheap-screen) | 5 (yesterday's + today's scheduled) |
| WATCH | 6 (4 classified + B2-mut1 + vol-low-30) |
| RETEST | 1 (XB-BB-EMA-Ladder-MYM) |
| KILL | 1 (vol-high-70 sample failure) |
| BLOCKED_WITH_DATA_REQUIREMENT | 2 (Spec B, Spec D) |
| BLOCKED_WITH_PRIMITIVE_REQUIREMENT | 0 (was 4 → all unlocked this cycle) |

---

## 5. Top kill / WATCH reasons updated

| Tag | Through 06-03 | Trend |
|---|---:|---|
| `concentration` | 7 | dominant; XB cluster over-sampled |
| `implementation-blocked` | 6 | unlocking — 3 new primitives shipped |
| `WF-split-fail` | 4 | +1 vol-high sample fail |
| `median-negative` | 3 | session/regime mutations producing this |
| `duplicate/overlap` | 3 | MYM/MGC saturation |
| `data-blocked` | 2 | EIA M2 spread, OPEC outcome list — still deferred per operator |
| `regime-dependent` | 3 | +1 vol-low result confirms calendar-year dominance |
| `cost-eats-edge` | 0 | not the current bottleneck |
| `insufficient-n` | 2 | +1 vol-high oversampling regime |

---

## 6. Architecture gaps touched

| Gap | Capacity status (post-build) | Hunts this cycle |
|---|---|---|
| VALUE | existing primitives (intraday) + monthly harness now available | 0 (build cycle) |
| CARRY | monthly harness shipped → Spec C runnable when FRED data pulled | 0 |
| VOL / vol-expansion | vol-regime filter shipped → directly usable | 1 (XB-BB-MGC test) |
| STRUCTURAL / liquidity vacuum | event-window primitive shipped → runnable when calendars supplied | 0 |
| Non-equity index | event-window + monthly both apply | 0 |
| FX | monthly harness shipped + 6J data current | 0 |
| Rates event/calendar | event-window primitive shipped + ZN data current | 0 |
| Crude-native event | event-window primitive shipped + MCL data current | 0 |
| Metals | no specific build needed; existing primitives | 0 |
| Afternoon / close / overnight | existing primitives (session_afternoon) | 0 |
| Positive-skew tail engine | event-window primitive is the natural fit | 0 |

**Next cycle priorities (autonomous):**
1. Wire Spec A (Treasury auction ZN) — calendar is free at treasurydirect.gov; one-time pull → smoke-screen
2. Wire Spec C (BoJ-Fed 6J carry) — FRED Fed Funds + BoJ rate series; one-time pull → smoke-screen
3. Donchian extension: `XB-DC-EMA-Ladder-MCL/MGC/ZN` — existing primitives, zero blockers
4. Generate VALUE specs from harvest backlog (12 of last 30 notes value-themed)

---

## 7. Candidate closest to paper packet

**None.** Lane B Forge pipeline still has 0 candidates past deep-screen. The probation cohort governed by Lane A controller remains the only path to paper readiness, and is operator-gated.

**Sprint day-17 trigger watch (2026-06-19):** if zero credible paper-readiness packets visible by then, re-plan the funnel per [[feedback_drift_prevention_patterns]].

---

## 8. Next task in chain

Continuing autonomously per standing rule (no permission needed for normal Forge work):

1. **Wire Spec A first** — treasury_auction_calendar.csv from treasurydirect.gov; build minimal candidate that uses `event_window_run` with the calendar; run smoke; classify with kill taxonomy.
2. **Wire Spec C** — pull Fed Funds + BoJ rate monthly series from FRED; build `build_policy_differential_signal` → run on 6J via `monthly_rebalance_run`; classify.
3. **Generate VALUE specs** — triage harvest backlog by VALUE keyword cluster (~12 notes); convert top 3-5 to qualified gap-aware specs.
4. **Donchian extension** — add `XB-DC-EMA-Ladder-{MCL,MGC,ZN}` to CANDIDATES; run via rotation or one-off; classify.

Continuing without ask.

---

## 9. Open decision-grade asks for operator

| # | Ask | Why | Status |
|---|---|---|---|
| 4 | Add EIA M2 crude curve data to ingest | Unlocks Spec B + future crude curve | DEFERRED 2026-06-02 |
| 5 | Compile OPEC outcome list | Unlocks Spec D | DEFERRED 2026-06-02 |
| 6 | Concentration-mutation pivot to **temporal split** for XB-BB-MGC | Both filter axes (session, vol-regime) empirically failed today and yesterday. Next axis is calendar-year robustness. | **NEW** — `OK temporal-split mutation` to authorize |

---

## 10. Sprint scoreboard

- **Sprint anchor:** 2026-06-02 ✅
- **Day:** 2 of 30
- **Day-17 trigger date:** 2026-06-19
- **30-day deliverable date:** 2026-07-02
- **Paper-readiness packet progress:** 0 of 1–3
- **Capacity delta this cycle:** 3 new primitives unlock ~10-15 candidate slots; backlog draining starts next cycle.

---

## 11. Boundaries held

- ✅ No Lane A change
- ✅ No registry truth mutation
- ✅ No scheduler/cadence change
- ✅ No portfolio allocation change
- ✅ No promotion / paper / live change
- ✅ No OpenClaw upgrade
- ⚠️ Code changes (Lane B research only): `research/event_window_engine.py` (new), `research/monthly_rebalance_engine.py` (new), `research/crossbreeding/crossbreeding_engine.py` (filter additions), `research/tests/test_event_window_smoke.py`, `research/tests/test_monthly_rebalance_smoke.py`, `research/tests/test_vol_regime_smoke.py` (new tests). Per operator approval of "OK build event-window primitive", "OK build FX-carry monthly harness", "OK build vol-regime filter".
