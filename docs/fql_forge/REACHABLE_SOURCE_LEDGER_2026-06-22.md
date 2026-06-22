# Reachable Data-Source Ledger — 2026-06-22

> New-source probe (operator-directed vein switch). Ledger of reachable sources, fields, quality, what each unlocks. Probing keeps finding sources after "exhausted" claims → reachable map expands.

| Source | Host | Reachable | Key fields | Quality | Unlocks |
|---|---|---|---|---|---|
| FRED series | fred.stlouisfed.org (.org) | ✓ (keyless csv) | DGS/DFII/T*IE/VIX/DTWEXBGS/FEDFUNDS/energy spot | clean, daily, deep history | macro/rates/vol/dollar/energy state (tested → no daily edge) |
| Yahoo Finance | query1.finance.yahoo.com | ✓ | OHLC daily futures (CL/BZ/GC/ES/HG…) | retail-grade, continuous front-month, research-only | fresh futures (vs stale FRED spot) |
| CFTC COT | publicreporting.cftc.gov (.gov public-reporting) | ✓ (Socrata) | comm/noncomm long/short, OI, weekly | clean, weekly | positioning (tested → no edge standalone/filter) |
| **TreasuryDirect auctions** | api.fiscaldata.treasury.gov (.gov) | ✓ **(was HTTP 000, now 200)** | auction_date, security_type, security_term, cusip, issue_date, offering_amt, **high_yield** | clean, 1979+, 799 Note/Bond 2019+ | **WP-B1 (tested this turn → core daily windows KILL; result-conditioned + intraday variants untested)** |
| **NY Fed Markets** | markets.newyorkfed.org (.org) | ✓ **(NEW)** | SOFR/EFFR ref rates, **repo/RRP operations, SOMA holdings (2003+), Treasury ops** | clean, official | genuine forced-flow (repo/SOMA/Fed ops) — UNTESTED, live lane |
| BLS / EIA | .gov | ✗ HTTP 000 | — | — | CPI values, EIA inventory (still operator-supplied) |

## Notes
- `.gov` reachability is inconsistent: TreasuryDirect + CFTC-publicreporting work; BLS/EIA blocked. Re-probe periodically (TreasuryDirect flipped 000→200 between 2026-06-17 and 2026-06-22).
- **NY Fed Markets API is the most promising UNTESTED new source**: repo/RRP operations + SOMA changes are *literal* forced-flow (the Fed transacting), and SOFR/EFFR are reachable daily rate-state variables. Candidate next-vein for rates conditioning.
- All acquisitions structural-only (provenance + validation); screens are separate report-only steps.
