# Lever-B Queue — Feed-Blocked Inputs, Ranked by Daily-WH2 Unlock Potential — 2026-06-16

> Feed-blocked ideas are **NOT kills.** Many of the best diversification ideas are feed-blocked. This is the prioritized queue of inputs to acquire, ranked by expected ability to unlock a **true daily/near-daily, non-MNQ, non-gold** workhorse on a genuinely different driver. Builds on `LEVER_B_INGESTION_SPECS_2026-06-16.md` (per-feed schema/validation/first-10-tests). Report-only; acquisition is an operator action.

| Rank | Feed family | Unlocks (daily-engine thesis) | Cadence reachable | Acquire-effort | Spec |
|--:|---|---|---|---|---|
| 1 | **Rates curve / carry / rolldown** (multi-contract per-expiry; ZN/ZF/ZB term structure) | Daily curve-state engine: steepening/flattening + rolldown carry as a continuous daily signal on rates — a non-equity, non-gold daily driver. The single most likely source of a true daily WH2. | daily | medium (Databento multi-contract) | WP-B5 (curve) |
| 2 | **Treasury auction calendar** (TreasuryDirect) | Auction-cycle daily/near-daily concession→reversion on ZN/ZF/ZB — extends the proven rates-EVENT vein toward higher cadence (40+/yr). | near-daily | low (operator CSV) | WP-B1 |
| 3 | **Dollar proxy / DXY or FX basket** | Gold/index daily confirmation + a dollar-trend daily engine; the regime driver behind gold and risk. | daily | low-medium (DXY or 6E/6J/6B basket — partly in-repo) | new (cross-confirm) |
| 4 | **Real-rate proxy for gold** (TIPS / breakevens, or ZN-real proxy) | Turns the gold sleeve from price-only into a real-rate-gated daily gold engine — diversifies the gold cluster by driver, not just mechanism. | daily | medium | new |
| 5 | **Crude inventory / OPEC / event inputs** (EIA stocks, OPEC calendar) | Inventory-state-gated daily crude engine (MCL) — a genuinely independent energy driver; current MCL intraday is cost-fragile + dead, but inventory-state may rescue it. | near-daily | medium | WP-B3/B4 |
| 6 | **COT / positioning** (CFTC weekly) | Positioning-extreme reversal filter applied to existing daily edges; commercial-vs-spec asymmetry. Weekly cadence but gates daily entries. | gates daily | low (CFTC public) | WP-B5 (COT) |
| 7 | **Cross-asset confirmation feeds** (aligned multi-series state) | Confirmation/divergence engines (gold↔dollar, crude↔risk, index dispersion). NOTE: a first cut is buildable NOW from in-repo data (no new feed) — that is pressure-cooker Cycle 2; richer versions need these feeds. | daily | low (in-repo first cut) | catalog F1–F5 |

## Reading
- **#1 rates curve/carry is the top unlock** — it's the most likely path to a true daily non-equity/non-gold workhorse on a new driver.
- **#7 cross-asset confirmation has a no-feed first cut** (Cycle 2) — pursue immediately in parallel; escalate to feeds if the in-repo version shows life.
- Acquisition priority should follow expected daily-WH2 unlock, not ease — but **#2 (auctions) and #6 (COT) are cheap/public**, so they're fast wins worth grabbing regardless.

## Feed delivery (2026-06-17 — sandbox constraint found)
Probed from this environment: **general internet works, but `.gov` hosts are blocked (HTTP 000)** — `api.fiscaldata.treasury.gov`, and almost certainly `bls.gov` / `eia.gov`. The `!`-in-prompt shell runs in the same sandbox, so it can't reach `.gov` either. **Therefore the official feeds must be downloaded on the operator's own machine and dropped into the repo as a file** (I then ingest report-only).

Easiest path for the #2 lever (Treasury auctions), run on YOUR terminal (not here):
```
curl -s "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query?fields=record_date,security_type,security_term,auction_date,issue_date,cusip,offering_amt,bid_to_cover_ratio,high_yield&filter=auction_date:gte:2019-01-01&page[size]=10000&format=csv" -o data/feeds/treasury_auctions.csv
```
Drop the CSV at `data/feeds/treasury_auctions.csv` (any superset of the WP-B1 columns is fine — `tenor`/`security_term`, `security_type`, `auction_date` are the minimum). The moment it's there I run WP-B1 validation + first-10-tests, report-only.

### Per-feed acquisition (drop files cleanly; run downloads on YOUR machine — `.gov` is sandbox-blocked)
Note: **FRED (`fred.stlouisfed.org`) is `.org`, likely sandbox-reachable** unlike `.gov` — I can probe/fetch FRED series if you want me to self-serve those (P1/P2 yields, P5 CPI level, P6 rates). Say the word; otherwise download and drop:

- **P1/P2 — rates curve/yields** → `data/feeds/treasury_yield_curve.csv`. FRED series DGS2,DGS5,DGS10,DGS30 (daily par yields). Min cols: `date, dgs2, dgs5, dgs10, dgs30`. (Or Databento multi-contract ZN/ZF/ZB per-expiry for roll-based carry → `data/feeds/rates_multicontract.csv`, cols `instrument, contract_month, date, settle`.)
- **P4 — EIA crude stocks** → `data/feeds/eia_crude_stocks.csv`. EIA Weekly Petroleum Status (crude ex-SPR stocks). Min cols: `release_date, period_end, stocks_kbbl` (+ `consensus_kbbl` if available; else I use 5-yr seasonal baseline). Release Wed 10:30 ET.
- **P5 — CPI** → `data/feeds/cpi_releases.csv`. Min cols: `release_date, ref_month, cpi_mom_pct` (+ `consensus_mom_pct` if available — consensus is the hard part; without it the "surprise" variant can't run, only the realized-acceleration variant). FRED CPIAUCSL gives the level (→ MoM); release dates from the in-house calendar.
- **P6 — policy rates** → `data/feeds/policy_rates.csv`. Min cols: `date, fed_funds, boj_rate` (FRED FEDFUNDS + BoJ policy rate). Monthly.
- **P3 — Treasury auctions** → `data/feeds/treasury_auctions.csv` (command above). **First to run.**

Each lands → structural validation (`research/lever_b1_feed_validator.py` pattern), then the locked screen sequence as a separate cycle. No screen runs before the real file.

## Boundaries
Queue only. No ingestion until a feed is supplied. No mutation/activation.
