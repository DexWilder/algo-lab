# Crypto Source Ledger — 2026-06-22

> New-ore vein (#1 strategic priority, $0). Probed reachability from sandbox. Crypto = 24/7, retail-heavy, less institutionally efficient, crypto-NATIVE forced-flow (funding/basis/liquidations). Source-ledger-first; mechanism packets before testing; same hardened discipline (no-lookahead, contamination, cost, overfit, mechanism-implied direction).

## Reachability (probed 2026-06-22)
| Exchange | Reachable | Data | Notes |
|---|---|---|---|
| **OKX** | ✓ HTTP 200 | perp **funding-rate history**, candles, OI | best for funding; `/api/v5/public/funding-rate-history?instId=BTC-USD-SWAP` |
| **Coinbase** | ✓ HTTP 200 | **spot candles** (BTC-USD etc) | 300 candles/req → paginate; clean spot |
| **Kraken** | ✓ HTTP 200 | spot OHLC | alt spot source / cross-check |
| **Deribit** | ✓ HTTP 200 | perp **funding history** (index_price+funding), **OPTIONS** (IV/greeks) | THE options venue → partial vol-surface (#2 area) reachable here |
| Binance | ✗ HTTP 451 | — | geo-restricted from sandbox |
| Bybit | ✗ HTTP 403 | — | CloudFront blocked |

## What's unlocked
- **Funding rate** (OKX, Deribit): the canonical crypto forced-flow — longs pay shorts (or vice versa) every 8h; extreme funding = crowded positioning forced to pay → mean-reversion / unwind pressure.
- **Perp–spot basis** (Deribit perp index vs Coinbase/Kraken spot): basis compression/expansion = leverage demand state.
- **Spot** (Coinbase/Kraken): clean price for spot mechanisms + basis denominator.
- **Options/IV** (Deribit): dealer gamma/skew — bonus toward the #2 vol-surface area.
- Liquidation data: NOT directly in these public endpoints (Binance/Bybit had it, blocked) → liquidation-cascade packet is data-limited unless a reachable mirror is found; OI-change is a partial proxy.

## History-depth / acquisition caveats (resolve at acquisition)
- OKX funding-history & Coinbase candles paginate (limited per request) → need looped acquisition; confirm depth (BTC perp funding ~2019+, Coinbase BTC spot 2015+).
- Funding is 8h cadence (00/08/16 UTC) → funding-TIME effects testable; align carefully (UTC, no-lookahead: funding known before the period it applies).
- Crypto trades 24/7 incl weekends → enables weekend-liquidity packet (no equiv in futures).

## ACQUISITION FINDING (2026-06-22) — funding-history DEPTH is the constraint, not reachability
- **OKX public funding-rate-history is HARD-CAPPED ~3 months** (confirmed: 296 records, oldest 2026-03-16, page-4 empty w/ success code — not rate-limit). → **C1 funding-mean-reversion is DATA-LIMITED (~99 days, ~15 extreme events), NOT a KILL** (`forge_cycle_2026-06-22k`). Cannot validate on free OKX funding.
- **Crypto PRICE is deep & free** (Coinbase BTC-USD daily paginates years; Kraken too). So PRICE-based crypto packets are immediately testable; FUNDING/basis packets need a deeper funding source.
- **Deeper-funding paths to retry C1/C3:** Deribit funding (start/end-timestamp pagination — earlier probe returned a custom range, may go deeper); or a public funding dataset; or accept paid. **CHECK DERIBIT FUNDING DEPTH NEXT.**
- **Immediately runnable now (price-only, deep history):** C5 weekend-liquidity regime (crypto-unique, calendar-mechanical), and price-based MR/momentum — these don't need funding depth.

## Revised priority (post-acquisition-finding)
1. **C5 weekend-liquidity** (price-only, deep, immediately runnable) — next crypto screen.
2. **Deribit funding-depth probe** → if deep, retry C1 (funding-mean-reversion) + C3 (perp-basis) properly.
3. C2/C6 need fine bars / OI depth (check).

## Boundaries
Report-only; mechanism-implied direction (no fishing); no mutation. C1 left DATA-LIMITED (not KILL) pending deeper funding source.
