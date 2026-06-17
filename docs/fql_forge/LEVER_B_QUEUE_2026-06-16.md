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

## Boundaries
Queue only. No ingestion until a feed is supplied. No mutation/activation.
