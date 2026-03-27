# Energy & VALUE Idea Map — What FQL Is Missing

*Research note. Not architecture. Defines what to look for.*
*Date: 2026-03-27*

---

## Energy (MCL) — 0 Strategies, 0 Testable Ideas

### Why It's Hard

Energy futures have different microstructure than equity/metal:
- Highly seasonal (heating/cooling demand, refinery cycles)
- Supply-driven shocks (OPEC, geopolitical, weather)
- Storage economics drive term structure (contango/backwardation)
- Higher tick volatility relative to margin
- Settlement mechanics differ from equity index futures

FQL's existing edge families (momentum, breakout, mean reversion) were
developed on equity/metal. They may not translate directly to crude.

### Strategy Families That Usually Work in Energy

| Family | Mechanism | Testability with MCL | Notes |
|--------|-----------|---------------------|-------|
| **Term structure carry** | Long backwardation, short contango. Roll yield capture. | Needs front/back data (v2 carry lookup) | Same family as commodity carry (Family 42). Blocked by data. |
| **Seasonal patterns** | Crude has documented seasonal tendencies (winter builds, spring refinery maintenance, summer driving season) | Testable now — calendar rules on existing MCL data | Requires seasonal calendar. |
| **Inventory-driven** | Trade based on EIA weekly inventory reports (Wed 10:30 ET). Surprise vs consensus. | Event strategy. Needs inventory expectations data. | TV-related ideas exist in harvest. |
| **Session microstructure** | Settlement mechanics at 14:30 ET. Nymex close patterns. | Testable now — similar to ZN afternoon reversion. | The MCL settlement window may have structural reversion. |
| **OPEC event** | Pre/post OPEC announcement positioning | Sparse events (~6/year). Exists as idea in registry (BLOCKED). | Low sample, needs longer history. |
| **Volatility regime** | Crude vol is mean-reverting. ATR-based regime gating. | Filter/overlay, not standalone. Testable now. | Could gate existing or new MCL strategies. |
| **Crude-gold spread** | Crude/gold ratio as a value signal. Mean reversion of the ratio. | Testable now — both MCL and MGC in data. | Cross-asset, unusual for FQL. |

### Most Promising Entry Points

1. **MCL session microstructure** — closest to what FQL already does well
   (ZN afternoon reversion was a session timing discovery). Look for
   settlement window effects around 14:30 ET on MCL.

2. **MCL seasonal carry proxy** — monthly rebalance based on calendar
   (e.g., long Oct-Mar, short Apr-Sep). Simple, testable now, documents
   whether crude seasonality is real on MCL.

3. **MCL ATR regime filter** — not a standalone strategy but a component
   that could gate future MCL strategies. Fragment, not full strategy.

### Best Source Ecosystems for Energy Ideas

- CME Group energy education pages
- EIA (Energy Information Administration) reports
- Commodity-specific blogs (Goehring & Rozencwajg)
- Quantpedia commodity carry / term structure articles
- GitHub: crude oil trading repos
- Reddit: r/FuturesTrading crude oil discussions

---

## VALUE — 0 Strategies, 0 Ideas

### Why It's Hard

"Value" in futures is fundamentally different from equity value investing:
- No P/E ratio for a futures contract
- No book value for crude oil
- "Value" must be translated into a futures-tradable signal

### What VALUE Means in Systematic Futures

| Approach | Signal | Applicability | Notes |
|----------|--------|--------------|-------|
| **Yield gap** | Equity earnings yield minus bond yield. Long equities when gap is wide (equities cheap vs bonds). | MES vs ZN/ZB spread trade | Requires yield data or price-derived approximation. |
| **PPP-based FX value** | FX fair value from purchasing power parity. Long undervalued, short overvalued currencies. | 6J/6E/6B | Requires PPP data (OECD). Blocked by external data. |
| **Commodity fair value** | Mean reversion of real commodity prices to long-term averages (adjusted for inflation). | MCL/MGC | Requires CPI-adjusted historical prices. |
| **Gold real rate** | Gold should fall when real yields rise. Trade gold vs real yield direction. | MGC vs ZN | Requires TIPS yield or proxy. Blocked by data. |
| **Term premium** | Trade Treasury futures based on estimated term premium (compensation for duration risk). | ZN/ZB | Requires term premium model. Academic, complex. |
| **Cross-asset relative value** | Rank assets by "cheapness" relative to own history. Long cheapest, short richest. | Multi-asset | The academic approach. Needs carry_lookup v2 for full implementation. |

### Most Promising Entry Points

1. **Equity-Treasury yield gap** — simplest VALUE signal with existing data.
   Compute earnings yield proxy from MES price, compare to ZN yield proxy
   from carry_lookup. Monthly rebalance. Testable with v1 carry lookup.

2. **Commodity real price reversion** — MGC and MCL have ~6 years of data.
   Compare current price to 2-year trailing average. Long when price is
   well below average, flat or short when well above. Simple, testable,
   but may conflate with momentum.

3. **Cross-asset cheapness rank** — rank MCL, MGC, ZN, 6J by deviation
   from 1-year mean. Long the most undervalued, short the most overvalued.
   Monthly rebalance. Cross-sectional value factor, testable now.

### Best Source Ecosystems for VALUE Ideas

- AQR factor research (Asness, Moskowitz, Pedersen)
- Quantpedia "value" category
- Alpha Architect value research
- Philosophical Economics (already in blog feeds)
- Verdad Capital research (no RSS but Claw searches)
- Academic: "Value Everywhere" (Asness et al. 2013)

---

## Priority Actions for Harvest System

| Gap | Action | Where |
|-----|--------|-------|
| Energy session micro | Add MCL session/settlement queries to Reddit + GitHub helpers | Helper query lists |
| Energy seasonal | Add "crude oil seasonality" to blog/digest search | harvest_config.yaml |
| VALUE yield gap | Add "equity yield gap" + "earnings yield systematic" to searches | Helper queries |
| VALUE cross-asset | Already partially covered by digest feeds (Quantpedia) | Monitor |
| VALUE commodity | Add "commodity fair value" + "real price reversion" | Helper queries |
