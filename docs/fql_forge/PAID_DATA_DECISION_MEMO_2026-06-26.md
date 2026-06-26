# Paid-Data Decision Memo (2026-06-26) — report-only; an OPERATOR spending decision

> ⚠️ **PROVISIONAL / SUSPENDED (2026-06-26): do not act on this yet.** It was written off an overbroad "free data
> exhausted" claim. DATA_INVENTORY_RESET found we hold **Databento 1-minute OHLCV + VOLUME (11 instruments)** that is
> entirely unexplored (all prior tests used close-only). The volume/1m-microstructure vein must be worked BEFORE any
> paid-data spend is justified. See `DATABENTO_INVENTORY_AND_UNLOCKS_2026-06-26.md`. The items below that are genuinely
> absent from `ohlcv-1m` (bid/ask, trades, MBP/L2, gamma, VIX-curve) remain valid candidates — but the spend is on hold
> until the free volume/1m vein is exhausted.

> Context: the funnel has established (with discipline) that free/cheap-data liquid-futures edges are real-but-
> sub-threshold or dead (5 mechanisms + 2 baskets + naive COT, all killed/shelved at cost + full-N DSR). The
> strong-prior unexplored edges live in data we'd have to buy. This memo frames that decision. **I cannot and will
> not spend money or commit to a vendor — this is yours to decide.** Nothing here is a capital action.

## Ranking (mechanism prior × feasibility) — buy in this order if at all
| Rank | Data | Unlocks (packets) | Instruments | Min viable feed | ~Cost (indicative, verify) | Impl. complexity | Prop-tradable-daily relevance |
|---|---|---|---|---|---|---|---|
| 1 | **Dealer gamma / options OI surface** | P07 OPEX/quad-witch pin, gamma-flip regime, dealer-hedging flow | MES/MNQ/SPX (index options) | ORATS / CBOE DataShop / SqueezeMetrics-style GEX | ORATS ~\$100-600/mo; CBOE DataShop per-dataset; vendor GEX ~\$50-200/mo | MED (need OI→gamma model or buy GEX directly) | HIGH — intraday/daily, strong forced-hedging mechanism, fits intraday-flat prop profile |
| 2 | **True VIX futures curve (VX1/VX2…)** | upgrade vol-carry from SVXY-proxy to real roll-yield; VIX expiry settlement | VIX futures (VX) | CBOE/CFE settlement (cheap/free historical via CBOE) + live vendor | historical near-free (CBOE); live modest | LOW | MED — overnight/daily carry; current vol-carry already weak, upgrade may not lift above bar |
| 3 | **EIA inventory consensus + actual** | P06 crude inventory surprise drift | CL/MCL (note: our MCL return series is roll-DIRTY) | EIA API free (actual) + consensus vendor (paid) | consensus ~\$ modest; actual free | LOW | MED — event; HELD BACK by dirty crude returns until clean CL series sourced |
| 4 | **Intraday order-flow / L2 book imbalance** | microstructure (Harris/Lehalle) — opening imbalance, liquidity-demand | MES/MNQ/ZN | Databento MBO/MBP (we already use Databento for MNQ!) | Databento usage-based, can be significant for tick/L2 history | HIGH (data volume + modeling) | HIGH if it works, but highest cost+complexity; defer |

## Notes that change the calculus
- **#2 VIX curve is near-free historically (CBOE) and low-complexity** → arguably do this regardless; but it only upgrades an already-weak leg (vol-carry Sharpe 0.86), so expected lift is modest. Cheap to try, low ceiling.
- **#1 gamma is the highest mechanism prior** (price-insensitive dealer hedging = textbook forced flow) and fits the intraday-flat prop profile we want. If buying ONE thing, this is it. Buying GEX directly (a vendor's pre-computed gamma exposure) is far less work than building it from raw OI.
- **#3 EIA is cheap but bottlenecked by our dirty crude data** — sourcing a clean roll-adjusted CL series is a prerequisite; until then EIA edge can't be tested honestly.
- **#4 order-flow:** we ALREADY have a Databento relationship (MNQ source). Incremental L2 is possible but expensive and high-complexity — defer until a cheaper edge is exhausted.

## Recommendation (for the operator to decide)
- **Lowest-regret first:** pull **true VIX curve historical from CBOE (near-free, low-effort)** — even though the ceiling is modest, it's cheap and cleans up an existing leg. *(This is free-ish; I can attempt it without a spend decision — flag if it requires an account.)*
- **Highest-prior paid buy:** **dealer gamma / GEX feed (#1).** If you're willing to fund one data tier, this is the one with the strongest forced-flow prior and the best prop-profile fit. Suggest starting with a *vendor-computed GEX* (cheaper, faster) before committing to raw options-OI infrastructure.
- **Hold:** order-flow (#4) until something cheaper proves the program can produce a clean candidate at all.

## What is NOT required
None of this is required to keep the report-only factory running on free data (auctions, calendars, the non-naive
COT re-spec, more T1 packets). It IS likely required to find an edge that *clears* DSR-at-N net-of-cost. That is the
honest trade-off: keep mining free data at low yield, or fund a higher-prior data tier.

**Decision owner: operator. No spend or capital action taken or implied by this memo.**
