# Data-Acquisition Roadmap (2026-07-07) — ranked by DISCOVERY-RATE ROI, not "acquire richer data"

> Each dataset ranked by (mechanisms unlocked × payoff) / effort. Specific, not aspirational. Payoff/effort = L/M/H.
> The metric that matters: does this dataset increase our mechanism-discovery rate?

| Rank | Dataset | Effort | Payoff | Mechanisms unlocked | Cost | Why this rank |
|---|---|---|---|---|---|---|
| 1 | **Index reconstitution calendar** (S&P/Russell rebal dates) | L (scrape) | **H** | M15 index-rebalance | free | cheap + WH1 forced-flow (funds must buy adds at close) — best ROI |
| 2 | **NG 1m** (Databento) | L | M | M28 commodity-seasonal | ~$3 | trivial pull; unlocks an untapped market+mechanism (NG winter seasonality) |
| 3 | **EIA inventory** (free API key) | L (register) | M | M20 inventory-surprise | free | free; crude/energy regime input |
| 4 | **CPI/NFP consensus** (macro surprise) | M (vendor/scrape) | **H** | M29 macro-surprise | low-$ | WH1 index-reaction path; biggest missing index-event mechanism |
| 5 | **Full options OI history** (Databento ES.OPT+weeklies) | M (chunked) | M | deepens M08 gamma, M19 OPEX | ~$15/yr | GEX ingredient already validated; more coverage + OPEX pin |
| 6 | **MOC imbalance feed** (closing auction) | H | **H** | M17 closing-auction | $$ | WH1 microstructure but paid/harder |
| 7 | **ETF create/redeem flows** | H (paid vendor) | **H** | M16 ETF-flow | $$$ | strong WH1 forced-flow but expensive/gated |
| 8 | **Crypto liquidation feed** (exchange APIs) | M | M | M26 liquidation-cascade | free-ish | crypto diversifier |
| 9 | **Earnings/buyback calendar** | M | L-M | M24 buyback-blackout | low | seasonal index effect |
| 10 | **Ex-dividend calendar** | L | L | M27 dividend-reinvest | free | minor seasonal |

## Immediate (free/cheap, this week): #1 index-rebalance calendar, #2 NG 1m, #3 EIA key. These unlock 3 new mechanisms at ~$3 total.
## The point: growth in the mechanism library comes from DATA that unlocks forced-flow mechanisms, ranked by ROI — plus external harvesting for genuinely new mechanism ideas.
