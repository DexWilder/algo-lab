# Data-Infra #1 — Official CPI fetch + MGC pre-CPI re-test — 2026-06-15

> **Mode:** Lane B / REPORT-ONLY. No promotion, no wiring, no data mutation performed.
> **Outcome:** (1a) official machine-fetch **BLOCKED from this environment**; (1b) MGC pre-CPI-drift is **confirmed data-gap-limited** — gaps are THE blocker. Both unblock paths are operator-gated.

## 1a — Machine-fetch official CPI calendar: BLOCKED
- `WebFetch` of `bls.gov/schedule/news_release/cpi.htm` and the archive → **HTTP 403** (BLS hard-blocks automated fetches from this environment).
- `WebSearch` returns only fragments — **cannot** assemble a verifiable full historical calendar. I will **not** fabricate an "official" calendar from snippets.
- **Concrete data-integrity finding:** WebSearch surfaced a BLS notice — *"Revised news release dates following the 2025 and 2026 lapses in appropriations"* ([bls.gov/bls/2025-lapse-revised-release-dates.htm](https://www.bls.gov/bls/2025-lapse-revised-release-dates.htm)). This **confirms the recall calendar's 2025/2026 dates are suspect** (matching its own "2026 lower confidence" caveat). Calendar grade stays `DATA_REQUIRED` and now carries a **known recent-date risk**.
- ⚠️ **Meta:** official `.gov` machine-fetch is not available from this environment. This almost certainly affects data-infra **#2 (TreasuryDirect auctions)** too. The "machine-fetch official" approach needs a different path: **operator-provided official data files**, an authenticated fetch tool, or manual download.

## 1b — MGC pre-CPI-drift re-test + "are MGC gaps the blocker?" → YES
From the clean-events validation (15f) + gap diagnosis:
- Clean signal: **PF 1.42, clean n=42, maxyr 53.6%, ON=0 → DEFER** (not a candidate).
- **MGC data gaps are the dominant limiter:** only **55/84** CPI events have an MGC bar within 10 min of 08:30 ET; **29/84 are unusable** due to missing MGC data — full-day gaps (e.g., 2019-08-13, 2020-02-13, 2020-04-10 have *no* MGC bars) or near-empty days (2019-12-11: 2 bars all day). Gold trades ~24h, so this is **missing data, not non-trading**.
- Gap-affected events span **all years**: 2019:2 / 2020:5 / 2021:6 / 2022:3 / 2023:3 / 2024:5 / 2025:2 / 2026:3. Persistent MGC feed-quality issue.

**Answer to scope output #5:** MGC data gaps **remain the blocker.** The signal can't be trusted/promoted until they're remediated.

## Disposition
- **MGC pre-CPI-drift = DEFER / RESEARCH-WATCH**, data-gap-limited. Not promoted, not wired.
- Calendar grade unchanged (`DATA_REQUIRED`, recent-date risk). No official upgrade possible from here.

## Two unblock paths (operator-gated)
1. **#3 MGC gap remediation (executable here — `DATABENTO_API_KEY` is set):** re-fetch the 29 gap dates' MGC 1m bars from Databento, resample, repair `MGC_5m.csv` (with backup + verification + no clobber of good bars), then re-test. *This is a truth-surface data mutation → needs your explicit go.*
2. **#1a official CPI calendar via operator-provided data:** since `.gov` fetch is blocked, you'd supply the official BLS release-date file (or an authenticated source), then I diff vs recall + re-test.

## Recommendation
Authorize **#3** (scoped MGC re-fetch for the 29 gap dates) — the Databento key is available and gaps are the concrete blocker; it's the shortest path to either a real MGC-CPI candidate or a clean kill. Handle the official-CPI-calendar grade separately via operator-provided data (since machine-fetch is blocked).

**I did not run the re-fetch** (data mutation, API cost, truth-surface) — awaiting your go. Phase 1C remains frozen pending PHASE1C_24H_VERIFY; nothing promoted/wired.

## Sources
- [BLS CPI schedule](https://www.bls.gov/schedule/news_release/cpi.htm) (403 to automated fetch) · [BLS 2025/2026 lapse revised dates](https://www.bls.gov/bls/2025-lapse-revised-release-dates.htm)
