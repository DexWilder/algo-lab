# MGC pre-CPI-drift — v-roll complete-data verdict (option 2) — 2026-06-15

> **Mode:** Lane B / REPORT-ONLY. Canonical `.c.0` feed UNTOUCHED. No promotion/wiring/active-MGC-book change.
> **Verdict:** **KILL.** On complete (v-roll) event data the signal collapses; the `.c.0` DEFER was a partial-data artifact.
> **Artifacts:** `research/forge_cycle_2026-06-15g_*` + `.json`; research dataset `research/data/fql_forge/MGC_vroll_event.csv`.

## What was built (option 2 — isolated research dataset)
- Separate research file `research/data/fql_forge/MGC_vroll_event.csv` from **Databento `MGC.v.0`** (volume-roll), CPI event windows only. **18,479 bars over 83/84 event dates** (only 2020-04-10 still missing even on `.v.0`). 1m→5m via canonical `resample_5m`. Full provenance in the JSON (symbol/dataset/schema/fetch-ts/rows-per-date/hash).
- **Canonical integrity confirmed:** `MGC_5m.csv` sha256[:16] `90aa5c4e` **identical before and after**; active MGC books unaffected.

## Re-test (MGC pre-CPI-drift, clean-events + hold-continuity)
| Metric | canonical `.c.0` (partial) | **v-roll (complete)** |
|---|---|---|
| clean n | 42 | **83** |
| clean PF | 1.422 | **1.201** |
| median | $5.76 | $11.76 |
| H1/H2 PF | 1.21 / 1.61 | 1.34 / 1.12 |
| max-year concentration | 53.6% | **91.7%** |
| overnight holds | 0 | 0 |
| verdict | DEFER | **KILL / weak** |

## Finding
The `.c.0` clean PF 1.42 was **inflated by missing data** — the `.c.0` gaps dropped 42 of 84 events, and those happened to be the worse ones. With the 41 recovered events added (complete v-roll data), PF falls to **1.201** (below the 1.3 bar) and year-concentration jumps to **91.7%** (one year carries the whole edge). **No real, robust edge.**

Per the decision rule ("if it collapses, mark MGC CPI drift KILL"): **MGC pre-CPI-drift = KILL.**

## Broader synthesis — non-MNQ diversification sweep complete
Every report-only avenue this session is now exhausted with **no surviving candidate**, but each was honestly validated and no false candidate was promoted:
- Lane A momentum cross-asset → MNQ-specific
- Structural/afternoon reversion → no edge (control-confirmed)
- VOL non-equity → no edge (control-confirmed)
- EVENT/CPI → collapses under clean-events + complete-data (this packet)
- Auctions → no real calendar (`.gov` fetch blocked)
- VALUE → no fundamental feed

The data-integrity discipline repeatedly caught inflated results (raw 3.24→clean 1.42→complete-data KILL). That is the system working.

## Recommendation (strategic decision point)
Cheap report-only Forge is exhausted; the MGC-CPI thread is closed (KILL). Near-term portfolio value now lives in:
1. **Phase 1C paper observation** — let `stop_run_reversal` prove out live (verifier pending), then consider Wave 2/3.
2. **Real data infra (DSCL §8)** if non-MNQ diversification is still the priority — but `.gov` machine-fetch is blocked here, so that needs operator-provided official data (CPI/TreasuryDirect) or an authenticated path. Until then, event/auction diversification is data-blocked.

I recommend **pausing autonomous Forge** here and treating "non-MNQ diversification" as gated on a data-infra decision, while Phase 1C paper evidence accrues. Nothing promoted/wired; Phase 1C frozen pending PHASE1C_24H_VERIFY.

## Cleanup note
The MGC `.c.0` vs `.v.0` roll-gap remains a real DSCL roll-logic item for whenever MGC data-source control is taken up (option 3 full rebuild) — logged, not actioned.
