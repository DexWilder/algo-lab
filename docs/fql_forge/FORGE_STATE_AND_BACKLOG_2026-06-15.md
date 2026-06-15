# Forge State, Exhausted-Lane Archive & Data-Infra Backlog — 2026-06-15

> **Mode:** Lane B / REPORT-ONLY hygiene + spec-prep. Generic non-MNQ cheap-screening is PAUSED (exhausted). No promotion/wiring/execution mutation. Phase 1C frozen at `PHASE1C_24H_VERIFY_PENDING`.
> **Purpose:** preserve this session's intelligence, set no-repeat rules, and stage the next *unblockable* data-infra work packages (prepared, NOT executed) — so the next push starts from truth, not a rabbit hole.

## 1. Exhausted lanes + NO-REPEAT rules (do not re-run without a new input)

| Lane | Verdict (2026-06-15) | NO-REPEAT unless… | Evidence |
|---|---|---|---|
| Lane A momentum cross-asset porting (stop_run / range_compression / first_impulse on MES/MGC/M2K/MYM/MCL) | **Exhausted — MNQ-specific.** Entries' edge is MNQ-microstructure-specific (unlike orb_breakout). | new mechanism, not a port | `forge_cycle_2026-06-15{,b}_*` |
| Structural/afternoon reversion (generic primitives, default params, rates/FX) | **Exhausted — no edge** (MNQ control also KILL; sanity-checked). | per-asset param calibration OR new primitive | `…structural_afternoon_rates_fx` |
| VOL non-equity (generic vol primitives, default params) | **Exhausted — no edge** (MNQ control 0.87–0.94). `volatility_regime_compound` under-fired (untested at defaults). | loosened params OR new primitive | `…vol_nonequity` |
| CPI / MGC pre-drift | **KILL on complete data.** Raw 3.24 → clean(.c.0) 1.42 → complete(v-roll) 1.20 @ 91.7% conc. | new event/asset thesis | `…cpi_clean_revalidation`, `…mgc_vroll_event_retest` |
| Treasury auction (2nd-Wed proxy) | **Not credible** — proxy meaningless; all KILL. | real TreasuryDirect calendar | `…event_window_harness` |
| VALUE / fundamental | **Not runnable** — no fundamental feed in OHLCV. | a fundamental data source | `inbox/_priorities.md` |

**Meta no-repeat rule:** generic crossbreeding primitives + default params are tuned to the MNQ-momentum regime. Cheap-screening them on non-MNQ assets/sessions is **saturated**. Do not repeat without a NEW data source, NEW calendar, or NEW (factor-specific or calibrated) mechanism.

## 2. DSCL / data-source backlog (findings from this session)

| # | Finding | Implication |
|---|---|---|
| D1 | **`.gov` machine-fetch is blocked from this environment** (bls.gov → HTTP 403; TreasuryDirect almost certainly same). | "Machine-fetch official calendar" is infeasible here. Needs **user-supplied official files** or an authenticated fetch path. |
| D2 | **CPI calendar is `DATA_REQUIRED` (recall)** with known **2025/2026 appropriations-lapse date revisions** → recent dates suspect. | Promotion-grade CPI work needs official dates. |
| D3 | **MGC `.c.0` (calendar-roll) has source gaps** on ~29 CPI dates; **`MGC.v.0` (volume-roll) has the data.** Canonical `MGC_5m.csv` built on `.c.0` inherited the holes. | Roll-methodology issue. `.v.0` more complete for MGC. Canonical rebuild = big blast radius (re-baselines active MGC books). |
| D4 | Roll-method mixing (`.c.0`+`.v.0`) creates price seams. | Never patch `.v.0` into the `.c.0` file. Use isolated research datasets (done for event research). |

This complements the locked DSCL policy (`data_source_control_layer_policy_2026-06-13.md` §8 build queue). These are data-source-control items, not strategy items.

## 3. Next data-infra work packages (PREPARED — not executed; each needs an explicit go + inputs)

**WP-1 — Official CPI calendar import (from user-supplied file).**
- Input needed: official BLS CPI release date+time file (CSV/JSON), 2019–2026, incl. 2025/2026 lapse-revised dates.
- Steps: parse → normalize tz (ET) → grade `MACHINE_FETCHED_OFFICIAL`/`USER_SUPPLIED_OFFICIAL` → diff vs recall calendar (added/missing/shifted) → re-run any CPI research on official dates.
- Output: official calendar module + diff report. *Blocked on user file.*

**WP-2 — TreasuryDirect auction calendar import (from user-supplied file).**
- Input needed: official auction schedule (2Y/3Y/5Y/7Y/10Y/30Y, original + reopen), with auction date/time, 2019–2026.
- Steps: parse → build multi-tenor calendar (grade official) → replace the 2nd-Wed proxy → re-screen ZN/ZF/ZB auction windows (report-only).
- Output: auction calendar module + screen. *Blocked on user file.*

**WP-3 — MGC roll-methodology review / `.v.0` rebuild impact analysis.**
- Steps (analysis only, no rebuild): quantify `.c.0` gap extent across full history; characterize price-seam magnitude `.c.0` vs `.v.0`; enumerate which active MGC books (ORB-MGC-Long, PB-MGC-Short, DailyTrend-MGC, gated Ladder-MGC) would be re-baselined by a `.v.0` switch; cost/benefit of full rebuild vs status quo.
- Output: decision memo. *Run before any canonical MGC change; touches active books → operator-gated.*

**WP-4 — VALUE / fundamental-feed requirements doc.**
- Steps: enumerate what data a futures "value/fundamental" factor needs (term structure, COT, macro surprise, carry), candidate sources, cost, integration shape.
- Output: requirements doc to decide if VALUE is worth funding. *Scoping only.*

## 4. Operating mode until unblock
Forge stays in report-only hygiene/spec-prep. It will NOT run more generic screens. It unblocks to real work when **either**:
- **Phase 1C verifier clears** (`PHASE1C_24H_VERIFY_OK`) → revisit activation sequencing (Wave 2/3), or
- **Official CPI/TreasuryDirect/fundamental data is supplied** → execute the relevant work package (WP-1/2/4).

Hard boundaries unchanged: no promotion, no paper/live wiring, no scheduler/registry/portfolio execution mutation, no live/prop routing; active MGC books, Ladder-MGC, Chandelier books, ATRTrail-MES, Phase 1D/FOMC, Wave 2/3 untouched. Phase 1C verifier verdict surfaced separately.

## Cross-reference
- Session screen artifacts: `research/data/fql_forge/reports/forge_cycle_2026-06-15*`
- Packets: `docs/fql_forge/reports/forge_queue/*_2026-06-15.md`
- `docs/fql_forge/data_source_control_layer_policy_2026-06-13.md`
- `docs/fql_forge/PHASE1C_ACTIVATION_stop_run_reversal_2026-06-15.md`
