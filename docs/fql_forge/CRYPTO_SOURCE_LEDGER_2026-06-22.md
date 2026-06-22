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

## Boundaries
Ledger only this turn. Acquire structural + screen via mechanism packets next. Report-only; no mutation.
