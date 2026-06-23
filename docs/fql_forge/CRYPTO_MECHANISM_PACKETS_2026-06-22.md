# Crypto Mechanism Packets — 2026-06-22

> Build-before-test. NOT "BTC breakout grids." Crypto-NATIVE forced-flow only: each packet names the forced participant, the mechanism-IMPLIED direction+timing, data (reachable per source ledger), no-lookahead, cheap-screen, kill criteria. Same discipline as the rates mechanism packets. Report-only.

## C1 — Funding-rate mean-reversion (extreme funding → unwind)
- **Forced participant:** at extreme positive funding, crowded LONGS pay a large carry → marginal longs forced to close → price pressure DOWN; extreme negative funding → crowded shorts pay → squeeze UP.
- **Implied direction:** funding >> norm → SHORT perp (or fade longs); funding << norm → LONG. Hold ~1-3 funding periods.
- **Data:** OKX/Deribit funding history; perp price. **No-lookahead:** funding for period t is set at t-start (known). **Kill:** no edge at extremes / cost (perp fees+funding) eats it / not robust across funding-threshold band.

## C2 — Funding-time drift (pre-funding positioning)
- **Forced participant:** traders position into/around the 8h funding stamp (00/08/16 UTC) to receive/avoid payment → predictable drift in the bars around funding.
- **Implied direction:** depends on funding sign — when longs must pay (pos funding), pre-stamp selling to avoid payment → fade up into stamp. **Direction conditioned on funding sign.**
- **Data:** funding stamps + intraday perp bars. **No-lookahead:** funding sign known before stamp. **Kill:** no consistent stamp-window drift / cost.

## C3 — Perp-basis compression/expansion (leverage-demand state)
- **Forced participant:** high perp-spot basis = leveraged-long demand; basis spikes mean-revert as arbs (cash-and-carry) step in.
- **Implied direction:** basis >> norm → short perp / long spot (or fade perp); basis << norm → opposite. State/relative, not naive direction.
- **Data:** Deribit perp index vs Coinbase/Kraken spot. **Kill:** no reversion / arb cost.

## C4 — Liquidation-cascade reversal (DATA-LIMITED)
- **Forced participant:** forced liquidations cascade price beyond fair value → snapback as forced selling/buying exhausts.
- **Implied direction:** after a large down-liquidation spike → LONG snapback (and mirror).
- **Data:** liquidation feeds were on Binance/Bybit (BLOCKED). Proxy: large OI drop + price spike. **Status: DATA-LIMITED** until a reachable liquidation source / OI-flush proxy is built. Lower priority.

## C5 — Weekend liquidity regime (no futures equivalent)
- **Forced participant:** thin weekend liquidity (institutions out) → different vol/trend behavior; Monday repositioning.
- **Implied direction:** test weekend vs weekday regime (range/trend/gap into Monday). Calendar-mechanical, crypto-only.
- **Data:** Coinbase/Kraken spot (24/7). **No-lookahead:** calendar. **Kill:** no weekend/weekday separation that survives cost.

## C6 — OI-flush continuation/reversal
- **Forced participant:** sharp open-interest drop = mass position closing (delever) → exhaustion (reversal) or trend-confirmation (continuation).
- **Data:** OKX OI history. **Kill:** no edge / OI data too coarse.

## Priority to run (after acquisition)
1. **C1 funding mean-reversion** — cleanest forced-flow, direction mechanism-implied, OKX funding reachable, deep history.
2. **C3 perp-basis** — leverage-state, reachable (Deribit perp + spot).
3. **C5 weekend regime** — calendar-mechanical, crypto-unique, cheap.
4. C2 funding-time (intraday, needs fine bars), C6 OI-flush, C4 liquidation (data-limited).

## RESULTS / acquisition findings (2026-06-23)
- **C5 weekend-liquidity → KILL** (`forge_cycle_2026-06-23a`, BTC/ETH/SOL, deep Coinbase price). Predeclared weekend-FADE (Monday fades Fri→Sun move) PF 0.73-0.78 negative all coins, PF@40bps worse → mechanism direction WRONG (weekend moves CONTINUE, not revert). Did NOT flip to continuation (= long-crypto-beta-timing, no forced-flow story = fishing). Exploratory DoW map: consistent cross-coin Thu-weak / Mon-Wed-strong, but beta-timing category (like MES-Monday) — logged, not pursued.
- **C1/C3 UNBLOCKED via Deribit:** Deribit funding history is DEEP (BTC-PERPETUAL 2020+, hourly, ~744/call → paginate ~31-day windows). Fixes the OKX 3-mo cap that made C1 DATA-LIMITED. **C1 funding-mean-reversion is now properly retestable on deep Deribit funding** = highest-value next crypto step (flagship forced-flow mechanism, now has the data).

## Revised priority (2026-06-23)
1. **C1 via Deribit deep funding** (now unblocked) — flagship forced-flow, mechanism-implied direction, deep data. Acquire Deribit funding 2020+ + price, rerun C1 with full PnL decomposition.
2. **C3 perp-basis** (Deribit perp index vs spot) — also unblocked.
3. More crypto PRICE rungs (vol compression/expansion, post-large-range MR, Asia→US handoff) — but DoW/beta-timing rungs deprioritized (C5 showed they're beta).
4. C2/C6/C4 — fine-bar/OI/liquidation data checks.

## Boundaries
Report-only; mechanism-implied direction (no fishing/flipping — C5 honored this); no mutation.
