# MGC gap repair (#3) — ROOT CAUSE + STOP-and-surface — 2026-06-15

> **Mode:** truth-surface repair, AUTHORIZED — but **STOPPED before any write** per your cost-control clause ("if the repair requires a broader MGC rebuild, stop and surface scope/cost first").
> **Canonical `MGC_5m.csv` is UNTOUCHED** (backup `/tmp/MGC_5m_pre_repair_20260615.csv`; pre-repair sha256[:16] `90aa5c4e182a458b`, 256,341 rows — unchanged; I only read/tested).

## Root cause (diagnosed, not a simple re-fetch)
The narrow same-symbol re-fetch fails because the gaps are in the **source symbol**, not local processing:

| Date | in-file (`.c.0`) | Databento `MGC.c.0` | Databento `MGC.v.0` |
|---|---|---|---|
| control 2020-01-15 | 276 | **1356** ✓ | — |
| control 2021-03-10 | 276 | **1365** ✓ | — |
| gap 2020-02-13 | 0 | **0** ✗ | **1309** ✓ |
| gap 2020-04-10 | 0 | **0** ✗ | (has data) |
| gap 2019-08-13 | 0 | **0** ✗ | (has data) |

**The 29 MGC CPI-gap dates are a `MGC.c.0` (calendar-roll) continuous-symbol artifact.** On those dates the calendar-front contract had no trades, so `.c.0` returns nothing — but `MGC.v.0` (volume-roll) has full data. The canonical feed was built on `.c.0` and inherited the holes. This is a DSCL-grade roll-logic finding.

## Why I stopped (the naive fix is unsafe / broader than authorized)
- **Patching the 29 dates from `.v.0` into the `.c.0` file mixes roll methods** → price discontinuities at the seams (calendar-roll vs volume-roll pick different underlying contracts). That corrupts series consistency.
- **`MGC_5m.csv` is read by ACTIVE MGC books** — `ORB-MGC-Long`, `PB-MGC-Short` (core), `DailyTrend-MGC-Long` (probation), and the gated `XB-ORB-EMA-Ladder-MGC`. Mutating the canonical MGC feed would alter their backtest/forward basis — **out of scope** (do not touch unrelated/active Lane A state) and unsafe without explicit authorization.
- A clean fix = **rebuild the entire MGC series on `.v.0`** (consistent), but that is a **broad rebuild** that changes the feed for *all* MGC strategies → exactly the "stop and surface" trigger.

## Options (your call — nothing mutated)
1. **Leave MGC-CPI blocked.** Don't corrupt the canonical `.c.0` feed for one weak DEFER signal (clean PF 1.42, maxyr 53.6%). Mark MGC pre-CPI-drift `RESEARCH/WATCH — blocked_by_roll_artifact`. *(Cheapest, safest.)*
2. **Build a SEPARATE volume-roll event-research dataset** (e.g., `MGC_vroll_event.csv`) covering only the CPI event windows, fetched from `MGC.v.0`. Canonical `MGC_5m.csv` stays untouched; re-test MGC pre-CPI-drift on the complete `.v.0` data to get an honest verdict. Narrow fetch (~84 event-window days). *(My recommendation if you want a verdict.)*
3. **Full canonical MGC rebuild on `.v.0`.** Most consistent long-term, but a major truth-surface change affecting every MGC book (incl. active probation/core) — would itself need its own validation + re-baselining of those books. **Not recommended now** (large blast radius; touches frozen/active Lane A surfaces).

## Recommendation
**Option 2** — answers "does the signal survive complete data?" without touching the canonical feed or any active MGC book. If you'd rather not spend the fetch, **Option 1** (mark blocked) is fine; the signal is weak (DEFER) regardless. **Do NOT do a mixed-roll patch (the naive #3).**

This `.c.0` vs `.v.0` gap is a real DSCL roll-logic item worth logging for the eventual MGC data-source control work regardless of which option you pick.

## Boundaries
No data written. No promotion/wiring. No registry/scheduler/portfolio/live-prop change. Active MGC books untouched. Phase 1C frozen pending PHASE1C_24H_VERIFY.
