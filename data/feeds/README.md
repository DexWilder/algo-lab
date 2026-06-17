# data/feeds — external driver feeds (Lever-B)

## State: `LEVER_B1_FEED_GATED_NOT_IDLE` (2026-06-17)

The in-house OHLCV/session/prior-day/EMA/ATR ingredient set has been proven to its ceiling for a generic daily, non-MNQ, driver-diverse second workhorse (see `docs/fql_forge/WH2_CHECKPOINT_2026-06-17.md`). The next real unlock is an **external driver feed**, not another in-house mutation. We are **feed-gated, not idle**:
- WP-B1 (Treasury auctions) is blocked **only** on the real CSV.
- Claw continues harvesting report-only under the upgraded packet.
- Forge does **not** grind more exhausted in-house variants to look busy.
- No activation / registry / scheduler / portfolio / live / prop mutation.
- `.gov` is blocked from the sandbox (HTTP 000), so feeds must be downloaded on the operator's machine and dropped here.

## Expected file
`data/feeds/treasury_auctions.csv` — minimum columns (or accepted aliases): `tenor`/`security_term`, `security_type`, `auction_date`. (Download command in `docs/fql_forge/LEVER_B_QUEUE_2026-06-16.md`.)

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
