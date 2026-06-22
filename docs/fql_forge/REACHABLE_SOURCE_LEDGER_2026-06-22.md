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

## NY-Fed / funding forced-flow — acquired + cheapest screen run (2026-06-22)
Acquired `data/feeds/funding.csv` from FRED (deep daily, reachable): SOFR(2018+), EFFR(2000+), DFF(1954+), RRPONTSYD(RRP volume, 2003+), WALCL(Fed balance sheet, weekly 2002+). Forced participants: repo/money-fund/Fed-balance-sheet mechanics.
- **Cheapest predeclared screen — SOFR-EFFR funding-stress → rates flight-to-quality (`forge_cycle_2026-06-22h`): KILL** (ZN/ZF, z>0.5 & z>1, clean-before-rolling, lag1d, OOS). PF 0.89-1.09; extreme-stress z>1 mildly positive recent-half only, not robust. The funding-stress directional hypothesis fails.
- **UNTESTED funding variants (open, lower-priority):** RRP-volume surge (liquidity-glut state), WALCL direction (QT/QE supply pressure), repo/RRP operation-size, SOMA holdings change. Operation-level NY-Fed API gives detail but check history depth; FRED state-series are the backtest-able versions.

## Notes
- `.gov` reachability is inconsistent: TreasuryDirect + CFTC-publicreporting work; BLS/EIA blocked. Re-probe periodically (TreasuryDirect flipped 000→200 between 2026-06-17 and 2026-06-22).
- **NY Fed Markets API is the most promising UNTESTED new source**: repo/RRP operations + SOMA changes are *literal* forced-flow (the Fed transacting), and SOFR/EFFR are reachable daily rate-state variables. Candidate next-vein for rates conditioning.
- All acquisitions structural-only (provenance + validation); screens are separate report-only steps.
