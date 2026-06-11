# FOMC-MGC Event-Window — Narrow Saturation Annotation (2026-06-11)

> **Authority:** Operator decision #160 (2026-06-11).
> **Doctrine:** [[feedback_asset_family_saturation_rule]] — narrow saturation, REOPENABLE_WITH_NEW_THESIS.
> **Status:** Lane B research annotation only. No registry mutation.

## What is saturated

**Saturated:** FOMC-MGC simple single-direction event-window with time-based exits across 1h / 2h / 4h holding windows, both long and short.

Source cycles:
- Cycle 2026-06-11e (FOMC-MGC data-gap audit + first batch)
- Cycle 2026-06-11f (FOMC-MGC-Long-4h deep-screen + family review)

## What is NOT saturated

1. **FOMC with official surprise / dot-plot path data** — Fed.gov publishes Summary of Economic Projections at FOMC meetings; surprise-data thesis remains untested
2. **FOMC with pre-declared regime thesis** — e.g., hawkish-cycle vs dovish-cycle filter written BEFORE testing
3. **FOMC on other assets** — with new thesis + clean data
4. **FOMC basket / portfolio research** — multi-asset FOMC composite
5. **FOMC-MGC if reopened with a materially different thesis** — e.g., different exit architecture, regime-conditional direction, or volatility-stratified entry

## What is FORBIDDEN

- FOMC-MGC filter retest **now** (operator #160) — adding filters after concentration failure would be a rescue loop
- Single-direction FOMC sweeps on additional assets without thesis justification
- Lowering concentration or Era 3 gates to rescue the deep-screen result

## What the failure showed (the 252% concentration)

| Year | n | Net | Notes |
|---|---:|---:|---|
| 2019 | 2 | -$105 | losing |
| 2020 | 6 | +$247 | win |
| 2021 | 6 | -$487 | **losing** |
| 2022 | 7 | +$80 | tiny win |
| 2023 | 6 | -$453 | **losing** |
| 2024 | 7 | +$49 | tiny win |
| 2025 | 5 | -$427 | **losing** |
| **2026** | **3** | **+$1819** | **outlier** |
| Total | 42 | +$722 | net |

- **Era 3 PF 1.72** (strongest recent regime of any candidate this campaign — the edge IS emerging)
- BUT 2026's $1819 (3 events) drives 252% of total net
- 4/8 years losing — the alternating win/lose pattern across years is the failure mode

This is a **regime-emerging signal**, not a stable historical edge. Could become packet-grade with more 2026 data OR with a regime filter that explicitly captures the dovish-cycle subset.

## Family review (genuine independence confirmed)

| vs | Daily PnL corr | Day overlap |
|---|---:|---:|
| Packet #1 NFP-MGC-Long-2h | -0.005 | 0.0% |
| CPI-MGC-Long-1h archived | -0.000 | 0.0% |
| BBKC-MNQ portfolio complement | -0.015 | 57.1% |
| XB-ORB-MNQ probation | 0.035 | 73.8% |

INDEPENDENT (max corr 0.035). FOMC-MGC has zero event-day overlap with Packet #1 NFP-MGC (NFP=monthly 1st Fri 8:30am ET; FOMC=quarterly schedule 2pm ET — different days). Cross-asset comparisons also clean.

## REOPEN CRITERIA (any one)

- A written FOMC-specific thesis with mechanistic edge hypothesis (not parameter sweep)
- New primitive in the crossbreeding catalog that addresses concentration (e.g., regime filter, surprise-conditional entry)
- New data: FOMC surprise / SEP dot-plot path data joined to existing calendar
- New asset (e.g., FOMC-equity-index, FOMC-rates) with new thesis
- Operator override with documented rationale

## Cross-reference

- [[feedback_asset_family_saturation_rule]] — narrow saturation doctrine
- [[feedback_concentration_is_load_bearing]] — concentration is hard packet-readiness gate
- [[feedback_event_window_clean_events_rule]] — clean-events filter doctrine (updated 2026-06-11; see below)
- [[feedback_validation_gates]] — the 6 real concentration gates

## Calendar verification (Fed.gov OFFICIAL)

For audit history: official Fed.gov calendar fetched 2026-06-11:
- https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm (2021-2026)
- https://www.federalreserve.gov/monetarypolicy/fomchistorical2019.htm
- https://www.federalreserve.gov/monetarypolicy/fomchistorical2020.htm

58 scheduled meetings 2019-2026 through data cutoff 2026-06-08. Emergency/unscheduled meetings excluded (2019-10-04, 2020-03-03, 2020-03-15, 2025-08-22 notation vote).

Calendar source: `research/forge_fomc_calendar_official.py` — OFFICIAL_FED_GOV grade.

## Status

FOMC-MGC single-direction event-window: **NARROW SATURATION** (Long/Short × 1h/2h/4h all classified).

Best result: FOMC-MGC-Long-4h OBSERVATIONAL (PF 1.158 strict-filter / Era 3 PF 1.72 / concentration 252%).

Next FOMC-MGC work blocked pending one of the REOPEN CRITERIA above.

Workhorse pivot launched per #159: Last-hour drift on MES/MNQ.
