# Inbound Feed Staging Manifest — 2026-06-17

> Lane 2 of the two-lane refresh. Feed-gated items are **queues, not blockers** — Lane 1 (reachable Yahoo/FRED discovery) runs in parallel. Drop a file at its path → its validator/screen runs report-only. `.gov` is sandbox-blocked, so these are operator-downloaded on your machine. Nothing here mutates anything.

## Priority queue (by expected structural-flow WH2 edge)

### #1 — Treasury auctions  → `data/feeds/treasury_auctions.csv`  [HIGHEST]
- Why: structural issuance flow (concession→reversion, bidder composition) — a forced-flow edge no liquid-futures price screen can find. Directly = WP-B1.
- Acquire (your terminal): `curl` in `LEVER_B_QUEUE_2026-06-16.md` (TreasuryDirect Fiscal Data API, public).
- Min cols: `security_term`/tenor, `security_type`, `auction_date` (+ bid_to_cover, high_yield enrich).
- Readiness: `research/lever_b1_feed_validator.py` (structure-only) ✓. Then locked WP-B1 sequence.

### #2 — Rates F2 / multi-contract roll  → `data/feeds/rates_multicontract.csv`
- Why: the TRUE roll-yield/carry form (front-vs-deferred), distinct from the KILLED FRED yield-curve proxy. The yield-curve branch is dead; this is a different mechanism.
- Acquire: Databento/CME per-expiry ZN/ZF/ZB settles, OR Yahoo continuous + a deferred series if obtainable.
- Min cols: `instrument, contract_month, date, settle` (front + 2nd deferred per tenor).
- Readiness: WP-B5(curve) spec; new validator stub on arrival (structure-only).

### #3 — EIA inventory surprise  → `data/feeds/eia_crude_stocks.csv`
- Why: energy-EVENT driver (draw/build vs consensus) — distinct from the KILLED WTI-Brent price reversion. (FRED EIA series IDs 404'd; needs EIA-direct download.)
- Acquire: EIA Weekly Petroleum Status (crude ex-SPR) on your machine.
- Min cols: `release_date, period_end, stocks_kbbl` (+ `consensus_kbbl` if available; else 5-yr seasonal baseline).
- Readiness: structure-only validator on arrival.

### #4 — CPI/BLS surprise (consensus)  → `data/feeds/cpi_releases.csv`
- Why: revives the inflation-SURPRISE variant (realized CPI level already on FRED; consensus is the missing piece). Lower priority — monthly cadence.
- Min cols: `release_date, ref_month, cpi_mom_pct, consensus_mom_pct`.

### #5 — OPEC dates/outcomes  → `data/feeds/opec_calendar.csv`  [LOWEST — sparse/messy]
- Why: crude-event; but sparse (~8-10/yr) and messy → ranked below auctions/EIA.

## Prep ready (feed-gated ≠ idle — done 2026-06-18)
- **WP-B1 auction harness** `research/wp_b1_auction_harness.py` — READY-BUT-UNRUN. On the real `treasury_auctions.csv` it runs the full locked sequence (validate → no-lookahead → join → coverage → predeclared mechanisms → tail board w/ FOMC-contamination split). Absent file → AWAITING_FEED, runs nothing (no synthetic data, no labels). All session lessons baked in.
- **F2 / multi-contract month-end RE-GRADE protocol** (for `rates_multicontract.csv`): re-run month-end-rates (currently WATCH-marginal/contaminated) on PROPERLY-ROLLED front+deferred series (not continuous), to confirm-or-kill the roll-adjacency-inflated edge. Decompose clean-of-FOMC up front; require non-roll, non-FOMC clean PF ≥1.3 with max-year <50% to upgrade off WATCH-marginal. Also enables true roll-yield P1 (front-vs-deferred carry).
- **Claw structural-harvest config** — recommendation in `CLAW_HARVEST_REQUEST` NOT yet applied (Claw automation-owned); 2026-06-18 harvest still saturated/dead families. Operator to apply so harvest stops recycling dead ideas.

## Status
All slots **empty / awaiting operator file**. `data/feeds/` already holds reachable feeds (FRED macro/rates/vol/energy-spot; Yahoo fresh energy futures) — those are Lane-1 research-grade, NOT capital-grade. The structural feeds above are the high-EV WH2 frontier. No activation/mutation; staging only.
