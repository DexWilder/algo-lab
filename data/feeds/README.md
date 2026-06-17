# data/feeds — external driver feeds (Lever-B)

## State: `FRED_YIELD_CURVE_BRANCH_CLOSED__FORGE_DISCOVERY_CONTINUES` (2026-06-17)
FRED yield-curve carry branch closed (mapped/dead: rotation, naïve spread, duration-balanced all KILL). Discovery continues. Batch-2 FRED daily DRIVERS acquired (structural only): `real_rates.csv` (DFII), `inflation_expectations.csv` (breakevens), `dollar_index.csv` (broad USD), `vix.csv`, `energy_spot.csv` (WTI/Brent/HenryHub), `credit_oas.csv` (HY OAS, short 2023+). These open new daily-driver packets P8–P13 (`FEED_DEPENDENT_CANDIDATE_PACKETS_BATCH2_2026-06-17.md`) — several attach to gold (live edge) via a genuinely new macro driver; all zero-evidence until screened (date-split OOS mandatory for gold-conditioning). Prior state line retained below.

## (prior) State: `LEVER_B1_FEED_GATED_NOT_IDLE` (2026-06-17) — FRED structural feeds acquired; WP-B1 auctions still first when CSV lands.

The in-house OHLCV/session/prior-day/EMA/ATR ingredient set has been proven to its ceiling for a generic daily, non-MNQ, driver-diverse second workhorse (see `docs/fql_forge/WH2_CHECKPOINT_2026-06-17.md`). The next real unlock is an **external driver feed**, not another in-house mutation. We are **feed-gated, not idle**:
- WP-B1 (Treasury auctions) is blocked **only** on the real CSV.
- Claw continues harvesting report-only under the upgraded packet.
- Forge does **not** grind more exhausted in-house variants to look busy.
- No activation / registry / scheduler / portfolio / live / prop mutation.
- `.gov` is blocked from the sandbox (HTTP 000), so feeds must be downloaded on the operator's machine and dropped here.

## Expected file (WP-B1, still the FIRST real validation cycle)
`data/feeds/treasury_auctions.csv` — minimum columns (or accepted aliases): `tenor`/`security_term`, `security_type`, `auction_date`. (Download command in `docs/fql_forge/LEVER_B_QUEUE_2026-06-16.md`.) **Not yet present.**

## FRED feeds ACQUIRED 2026-06-17 — `FRED_FEEDS_ACQUIRED_STRUCTURAL_ONLY` (NOT evidence of edge)
FRED (`.org`) is sandbox-reachable. Fetched + structurally validated only (no screens, no edge, no PASS/WATCH/KILL, no synthetic fill). Provenance: `research/data/fql_forge/reports/fred_feed_acquisition_2026-06-17.json`; script `research/fetch_fred_feeds.py`.
- `treasury_yield_curve.csv` (DGS2/5/10/30, 16,815 rows, 1962→2026-06-15) → **P1/P2 now FEED-READY** (curve/carry). Roll-based carry variant still wants multi-contract futures.
- `cpi_levels.csv` (CPIAUCSL, 953 rows) → **P5 partial**: realized CPI MoM only. **No pre-release consensus → the "CPI surprise" variant CANNOT run; only the realized-acceleration variant.** Do not call it surprise.
- `policy_rates.csv` (FEDFUNDS + BoJ IRSTCB01JPM156N, 863 rows) → **P6 FEED-READY** (Fed + BoJ).

**These are feed-ready, NOT screened.** Each P1/P2/P5/P6 screen is a SEPARATE, operator-APPROVED cycle. WP-B1 (auctions) remains the first real validation cycle once its CSV lands.

## The validator is NOT evidence of edge
`research/lever_b1_feed_validator.py` validates **feed structure/plumbing only** — existence, schema/alias resolution, date parsing, sort/dedup, normalization preview, future-date sanity, and `AWAITING_FEED` when absent. It deliberately produces **no** no-lookahead claim, **no** join-quality conclusion, **no** PASS/WATCH/KILL, **no** strategy screen, and **no** synthetic data. Passing structural validation means the file is *ingestible*, nothing about whether any auction mechanism has an edge.

## Locked run order — only after the REAL CSV lands (separate cycle)
1. Feed validation
2. Timestamp / no-lookahead audit
3. Join audit to ZN/ZF/ZB bars
4. Coverage by tenor and year
5. First-10 auction-mechanism cheap screen (only)
6. Brutal board classification
7. Archive kills; retain only evidence-clean survivors

No synthetic auction data, and no WP-B1 strategy logic, runs before the real file exists.
