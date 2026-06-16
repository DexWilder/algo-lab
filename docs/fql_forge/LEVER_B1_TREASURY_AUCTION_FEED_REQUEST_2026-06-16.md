# Lever-B1 — Treasury Auction Calendar — Exact Feed Request — 2026-06-16

> **Purpose:** WP-B1 is the highest-priority Lever-B feed (extends the proven rates-event vein — the ZN-FOMC sleeve — into an *independent* rates-event family). This document tells you EXACTLY what to supply so I can ingest + run the first-10 tests with zero back-and-forth. **Report-only; no ingestion runs until the file lands.**

## What I need from you (pick the easiest path)

**Path A — operator CSV (preferred, fastest).** One CSV, 2019-01-01 → present, one row per auction.
**Path B — TreasuryDirect API dump.** The auction-query JSON (`/services/api/fiscal_service/v1/accounting/od/auctions_query` or the Securities `/v1/debt/...auctions`); I'll normalize it to the schema below. Just drop the raw file.
**Path C — point me at an authenticated/whitelisted URL** I'm allowed to fetch (the `.gov` machine-fetch path is blocked from this env, so a local file is the reliable route).

## Exact CSV schema (Path A)

| column | type | example | notes |
|---|---|---|---|
| `tenor` | string | `10Y` | 2Y/3Y/5Y/7Y/10Y/20Y/30Y (FRN/TIPS optional, tag separately) |
| `security_type` | string | `Note` | Bill/Note/Bond/TIPS/FRN |
| `auction_date` | date | `2026-06-11` | the auction day (ET) |
| `auction_time_et` | time | `13:00` | usually 13:00 ET; needed for any intraday test |
| `announcement_date` | date | `2026-06-05` | for pre-announcement vs pre-auction split |
| `settlement_date` | date | `2026-06-16` | |
| `offering_type` | string | `Reopening` | `Original` or `Reopening` |
| `cusip` | string | `91282CKZ9` | dedupe key + audit |

Minimum viable if some columns are hard: **`tenor`, `security_type`, `auction_date`** are required; the rest enrich the tests but aren't blocking.

## Coverage I need
- **Span:** 2019-01-01 → present (overlaps the ZN/ZF/ZB price history I already hold).
- **Tenors:** at minimum the coupon tenors that move ZN/ZF/ZB — **2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y**. Bills optional (less price impact).
- Reopenings included and flagged (different concession behavior than originals).

## What I do the moment it lands (no further approval needed — report-only)
1. **Validate** (per WP-B1): monotonic dates, complete tenor coverage, no CUSIP dupes, count cross-check vs TreasuryDirect totals, **rollover-adjacency flag**, clean-events bar-alignment on ZN/ZF/ZB (no data-gap fictitious PnL).
2. **Run the first-10 tests report-only**, mapped to the proven executor where possible:
   - auction-week long ZN/ZF/ZB (replaces the dead 2nd-Wed proxy)
   - pre-auction concession short (T−2→T0); post-auction reversion long (T0→T+2)
   - by-tenor routing (10Y→ZN, 5Y→ZF, 30Y→ZB)
   - reopening-vs-original split; auction × FOMC-week interaction; auction-day intraday; concession-then-reversion combo; tenor-curve spread; stop-capped prop variant
3. **Report** PASS / WATCH / DEFER / KILL per test with the standard gates (PF tier, median, concentration top-3/top-10/max-year, clean-events, prop-DD, cost ratio) + taxonomy tags. Survivors route to the **shared event executor** (same scaffold as ZN-FOMC) for fidelity check before any packet.

## Why this one first
The ZN-FOMC sleeve proved the rates-event vein is real. Auctions are ~40+ events/yr (vs 8 FOMC) — far more sample, **independent** of FOMC, and reuse the entire executor + clean-events + regime-gate machinery already built. Highest independent-family unlock per unit of operator effort. Boundaries: no ingestion, no mutation, no fetch until you supply the file.
