# Lever-B Ingestion Specs — 2026-06-16

> **Purpose (frontier #2):** turn "we need data" into actionable ingestion specs. For each feed: source requirement, schema, validation checks, and the first 10 tests it unlocks. **Report-only planning** — no ingestion runs here (`.gov` machine-fetch is blocked from this env; feeds require operator-supplied files or an authenticated path). No mutation.
> Priority is set by *independent-strategy-family unlock potential* (the mission: 3–5 independent prop-ready engines).

## Calendar grade ladder (target)
`MACHINE_FETCHED_OFFICIAL` or `USER_SUPPLIED_OFFICIAL` > `DETERMINISTIC` > `DATA_REQUIRED_recall`. Promotion-grade event work needs ≥ official/deterministic.

---
## WP-B1 — Treasury auction calendar (HIGHEST unlock: extends the proven rates-event vein)
- **Source:** TreasuryDirect auction announcements/results (auction query API or operator CSV). Fields per auction.
- **Schema:** `tenor` (2y/3y/5y/7y/10y/20y/30y), `auction_date`, `auction_time_et`, `settlement_date`, `type` (original-issue / reopen), `announcement_date`, `cusip`. 2019–2026.
- **Validation:** monotonic dates; tenor coverage complete; no dupes; cross-check count vs TreasuryDirect totals; rollover-adjacency flagged; clean-events (bar within window) on ZN/ZF/ZB.
- **First 10 tests unlocked:** (1) auction-week long ZN/ZF/ZB [replaces the dead 2nd-Wed proxy]; (2) pre-auction concession short (T-2→T0); (3) post-auction reversion long (T0→T+2); (4) by-tenor (10y-auction→ZN, 5y→ZF, 30y→ZB); (5) reopen-vs-original split; (6) auction × FOMC-week interaction; (7) auction-day-only intraday; (8) concession-then-reversion combo; (9) tenor-curve spread around auctions; (10) auction + stop-cap prop variant. **Why:** rates-event is the proven productive vein (FOMC-week sleeve); auctions are an independent rates-event family.

## WP-B2 — Official CPI / macro-release calendar (upgrades recall → official)
- **Source:** BLS CPI release schedule (+ PPP/PCE/retail-sales optional), operator-supplied official file or authenticated fetch. Critically include the **2025/2026 appropriations-lapse revised dates**.
- **Schema:** `release_date`, `time_et` (08:30), `ref_month`, `series` (CPI/PPP/PCE), `revised_flag`.
- **Validation:** diff vs current recall calendar (`forge_cpi_calendar_verified`) — list added/missing/shifted; confirm lapse revisions; bar-alignment on rates/gold.
- **First 10 tests:** (1) CPI-week rates re-run on OFFICIAL dates (recall KILLed — does official change it?); (2) CPI-day intraday MGC/MNQ; (3) CPI surprise-conditioned (needs print vs consensus — see WP-B5); (4) CPI × FOMC-week proximity; (5) PCE-week rates; (6) pre-CPI drift; (7) post-CPI continuation; (8) CPI-week on 6E/6J (USD); (9) recall-vs-official metric delta audit; (10) clean-events CPI on MGC (gap-prone). **Why:** validate/kill the CPI-week lane on trustworthy dates.

## WP-B3 — OPEC decision calendar (unlocks crude-native event family)
- **Source:** OPEC/OPEC+ meeting schedule + outcomes (operator file; few events/yr, ~50 over 2019-2026).
- **Schema:** `decision_date`, `time`, `type` (scheduled/extraordinary/JMMC), `outcome` (cut/hold/raise, optional).
- **Validation:** vs published OPEC calendar; flag emergency; MCL bar-alignment.
- **First 10 tests:** (1) OPEC-day MCL impulse-hold-through-settlement; (2) pre-OPEC drift; (3) post-OPEC continuation/reversal; (4) outcome-conditioned (cut→long); (5) OPEC × EIA proximity; (6) OPEC-week vol-expansion; (7) MCL intraday post-headline; (8) scheduled-vs-extraordinary; (9) stop-capped prop variant; (10) cross-asset OPEC→equity/FX spillover. **Why:** crude-native event is a fully independent (energy) family; no current calendar.

## WP-B4 — EIA calendar hardening (improve existing)
- **Source:** EIA petroleum status official release schedule (have a rule-based module; upgrade to official confirmation + holiday-shift table).
- **Schema:** `release_date`, `time_et` (10:30, holiday-shifted), `shifted_flag`, `shift_reason`.
- **Validation:** confirm rule-based vs official; the post-EIA-long lead (PF 1.43, conc 55%) re-run on hardened calendar.
- **First 10 tests:** mostly done in cycle-16 EIA screen; hardened calendar re-validates the post-EIA-long WATCH-LOW + adds EIA-surprise-conditioning, EIA×OPEC, by-product (RB/HO — needs data). **Why:** complete the crude-event lane; low marginal unlock.

## WP-B5 — Value / carry / curve / positioning inputs (largest backlog: 470 VALUE/CARRY harvest items)
- **Sources:** (a) **Databento multi-contract** (per-expiry, not just .c.0 continuous) → build term-structure/roll-yield/carry; (b) **CFTC COT** (large-trader positioning) weekly; (c) macro/fundamental (PPP/OECD, inventory: EIA stocks, USDA) per factor.
- **Schema:** curve = {instrument, contract_month, date, settle, OI, volume}; COT = {market, date, comm/noncomm long/short}; macro = {series, date, value}.
- **Validation:** curve continuity per contract; roll-yield sanity; COT weekly alignment; macro vintage/revision handling (point-in-time, no lookahead).
- **First 10 tests:** (1) commodity term-structure carry rank (backwardation long / contango short) — the #11 harvest note; (2) cross-asset carry (rates/FX/commodity); (3) COT-positioning filter on existing momentum; (4) commodity curve-value × inventory-state confirm; (5) FX carry (rate-diff); (6) value-momentum-everywhere cross-asset sleeve (AQR #12); (7) GTAA adjusted-yield rank (#08); (8) calendar-spread roll-down (rates/commodity); (9) inventory-conditioned crude; (10) COT extreme reversal. **Why:** unlocks the entire feed-blocked VALUE/CARRY supply — the path to genuinely independent (non-momentum, non-event) families. **Highest long-run unlock; highest data cost.**

---
## Priority order (independent-family unlock per cost)
1. **WP-B1 Treasury auctions** — cheap-ish (operator CSV), extends proven rates-event vein, independent rates family. **Do first when a feed arrives.**
2. **WP-B5 curve/carry/COT** — biggest unlock (470 items, non-momentum families) but highest data cost/effort.
3. **WP-B2 official CPI** — cheap, validates/kills CPI lane.
4. **WP-B3 OPEC** — independent crude family, small calendar.
5. **WP-B4 EIA hardening** — low marginal.

## Boundaries
Planning only. No ingestion, no `.gov` fetch (blocked), no mutation. When you supply a feed file (or authenticated source), I ingest per the matching WP spec, run its validation + first-10-tests report-only, and report PASS/WATCH/DEFER/KILL.
