# VALUE Hunt — Spec Catalog 2026-06-03

**Mode:** Lane B / report-only / Forge memory only.
**Source:** Triage of harvest backlog (~247 VALUE-tagged notes; 12 from last 30 inbound).
**Vanity-guard:** every spec below targets a gap not in core/probation cohort. No raw-volume specs included.

---

## Findings (executive)

The VALUE backlog is rich (~247 notes) but **bottlenecked at primitive coverage, not idea flow**. Three primitive classes are needed and only one (monthly_rebalance) exists:

| Primitive | Status | Specs it unlocks |
|---|---|---|
| Monthly rebalance | ✅ shipped 2026-06-02 | Gold real-rate value; Equity-Treasury yield-gap; Cross-asset adjusted-yield rotation; Term-premium rotation (also needs ACM data) |
| **Cross-asset spread/pairs harness** | ❌ not built | All pair specs: GC/SI, ZN/ZF, CL/RB, GC pairs, value books |
| **Fundamentals series ingest** (real yields, term premium, earnings yield, DXY, OIS spreads) | ❌ not built | Gold real-rate; Equity-Treasury yield-gap; Term-premium rotation; FX PPP |

→ Out of ~247 VALUE notes, **only 1 spec is runnable today using existing primitives + a self-contained synthetic fundamentals series**: Gold Real-Rate Value Dislocation (single-asset, monthly rebalance, fundamentals proxy-able from public sources).

---

## Catalog — 5 qualified gap-aware VALUE specs

### V1 — **GLD-RealRate-MGC-monthly** (RUNNABLE) ✅

- **Seed:** `2026-03-20_06_gold_real_rate_value_dislocation.md`
- **Thesis:** Gold has a mean-reverting relationship to 10y US real yields + DXY. When GC closes > 1.5σ below model fair value AND 10y real yields falling → LONG; > 1.5σ above + real yields rising → SHORT.
- **Asset / freq:** MGC, monthly rebalance.
- **Entry:** Month-end signal: LONG when (MGC residual vs 60-month rolling-regression fair value > 1.5σ negative) AND real-yield Δ < 0.
- **Exit:** Next month-end OR mispricing narrows inside 0.5σ.
- **Gap fit:** Single-asset gold value sleeve. **Zero current metals-value strategies.** Diversifies from intraday MGC workhorse (ORB).
- **Failure modes:** (i) DXY/real-yield series staleness, (ii) 60-month window includes regime changes, (iii) gold "fair value" is structurally non-stationary.
- **Primitive status:** ✅ monthly_rebalance shipped. Needs minimum-viable 10y real yield + DXY monthly series.
- **Recommendation:** WIRE NOW.

### V2 — **EQ-TY-YieldGap-MES-ZN-monthly** (BLOCKED: pairs harness)

- **Seed:** `2026-03-18_01_equity_treasury_yield_gap_value.md`
- **Thesis:** Earnings yield (S&P forward) minus 10y Treasury yield → cross-asset value pair. Long the cheaper, short the richer at monthly rebalance.
- **Asset / freq:** MES vs ZN paired, monthly.
- **Gap fit:** First cross-asset pair in factory. Decorrelates from index workhorse.
- **Primitive status:** ❌ **cross-asset pairs harness not built.** monthly_rebalance harness is single-asset only.
- **Recommendation:** Defer. Surfaces pair-harness as decision-grade ask.

### V3 — **XAY-Adjusted-Yield-Rotation** (BLOCKED: multi-asset rotation harness + fundamentals)

- **Seed:** `2026-03-17_04_cross_asset_adjusted_yield_value.md`
- **Thesis:** Rank ~4 asset classes (equity, rates, commodities, FX) on standardized yield proxies. Long top, short bottom. Monthly.
- **Primitive status:** ❌ rotation harness needs cross-asset signal alignment + yield-proxy ingest.
- **Recommendation:** Defer.

### V4 — **TPM-Term-Premium-Rotation-Rates** (BLOCKED: fundamentals)

- **Seed:** `2026-03-18_15_treasury_term_premium_value_rotation.md`
- **Thesis:** Use ACM term premium series; rank ZF/ZN/ZB/UB tenors; long most-negative dislocation, short most-positive.
- **Asset / freq:** ZF/ZN/ZB/UB rotation, weekly.
- **Primitive status:** ❌ pair/rotation harness; ACM term-premium series ingest.
- **Recommendation:** Defer.

### V5 — **MGC-MR-MeanRevert-Hurst-screen** (RUNNABLE via existing intraday primitives) ✅

- **Seed:** `2026-06-03_10_value_universe_selection_requires_hurst_below_one_half_*.md` + `2026-06-03_11_value_candidates_only_promote_when_their_mean_reversion_label_survives_three_time_interval_checks.md`
- **Thesis:** Run BB-reversion (existing `bb_reversion` entry primitive) on MGC and gate it through a Hurst-stability screen across 3 lookback windows. Multi-horizon stationarity check before signals fire.
- **Asset / freq:** MGC 5m, intraday MR with Hurst gate.
- **Gap fit:** Adds rigorous statistical-stationarity gating to an existing primitive. **Could become a new FILTER_MAP entry: `hurst_stable`.**
- **Primitive status:** ⚠️ Needs a new filter primitive: `hurst_stable` (rolling-Hurst computation as bar-level features). Smallest possible primitive build (~50 lines).
- **Recommendation:** Surface as small primitive ask: `OK hurst_stable filter`. Once built, immediately wire as `XB-BB-EMA-HurstGate-MGC`.

---

## Decision-grade asks (ranked by backlog-unlock count)

| # | Ask | Unlocks |
|---|---|---|
| 9 | **Build cross-asset spread/pairs harness** (2-leg time-aligned signal generation, common cost-aware metric output) | V2 + ~40-60% of VALUE backlog (all spread/pair specs) |
| 10 | **Stand up minimum-viable fundamentals series cache** (10y real yields, DXY, ACM term premium, S&P earnings yield, monthly) — can start with single-file hardcoded series like Spec C did | V1 (Gold real-rate) cleanly; V3/V4 partially |
| 11 | **Build `hurst_stable` rolling FILTER_MAP primitive** (~50 LOC) | V5 + all future mean-reversion candidates using Hurst gating |
| 12 | **Wire V1 (Gold Real-Rate) with hardcoded real-yield + DXY series, run cheap-screen via monthly_rebalance_run** | One immediate runnable VALUE spec; first metals-value sleeve in factory |

**Recommendation:** approve #12 immediately (uses existing primitives + minimum-viable hardcoded data analogous to Spec C). Approve #11 next (smallest build, unlocks Hurst-gated MR family). #9 and #10 are larger architectural lifts; defer until temporal-split + Donchian-mutation work clears.

---

## Architecture coverage delta if all 5 wire successfully

| Gap | Pre-cycle | Post-V1 | Post-all-5 |
|---|---|---|---|
| Metals VALUE | 0 strategies | 1 (V1) | 1 |
| Cross-asset VALUE pair | 0 | 0 | 1 (V2) |
| Cross-asset rotation | 0 | 0 | 1 (V3) |
| Rates VALUE (term premium) | 0 | 0 | 1 (V4) |
| MR + statistical gate | 0 | 0 | 1 (V5) |

**Bottom line:** even wiring just V1 would close the metals-VALUE gap and produce the first carry/value-shaped candidate in the cohort outside the existing carry probationer (Treasury-Rolldown).

---

## What we did NOT spec

- Single-leg spec from any of the ~12 sizing/exit/filter overlay notes from 2026-06-03 — those are *component* notes (entry_logic/exit_logic/filter/sizing_overlay), not full strategies. They become useful once we have a pairs/cross-asset harness.
- Anything requiring agricultural or weekly continuous-roll curves (ZC, ZS, LE, etc.) — separate data lift.

Vanity-guard confirmed: this catalog adds 0 specs that would land in the current XB/MGC/MYM cluster.
