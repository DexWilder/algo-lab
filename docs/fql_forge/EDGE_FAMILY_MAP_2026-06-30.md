# Edge-Family Map (2026-06-30/07-01) — status + completion criteria per family

> A family is NOT FAMILY_EXHAUSTED without its completion criteria met. Statuses: FAMILY_EXHAUSTED / ACTIVE_EXPANSION /
> UNDERTESTED / DATA_BLOCKED_CERT / PAID_DATA / CLEAN_KILL / CLEAN_BUT_WEAK / SCREEN_PASS_RETAINED.

| Family | Status | Data | Tested | Untested / next 5 | Completion criteria |
|---|---|---|---|---|---|
| Trend/momentum | CLEAN_BUT_WEAK | futures | TSMOM, primitive sweep | pooled vol-target trend | trend+carry combo, per-asset |
| Mean reversion | CLEAN_KILL | 5m | VWAP/primitive | — | (done) |
| Carry (rates) | CLEAN_KILL (daily per-contract) | ZT/ZF/ZN/ZB | naive+xsec roll-yield | — | naive+xsec DONE → killed |
| Carry (commodity) | ACTIVE_EXPANSION (RUN_NOW) | CL/GC per-contract | — | CL carry, GC carry, xsec, spread mom, spread MR, roll-window | all 6 predeclared tested |
| Curve RV | CLEAN_KILL (2s5s10s/5s10s30s fly) | per-contract | fly | 2s10s slope momentum, Kalman spread | fly+slope+spread tested |
| Vol risk premium | CLEAN_BUT_WEAK | vix.csv/DVOL | vol-carry | true-curve VRP | curve VRP (paid) |
| **Gamma/dealer hedging** | **FEASIBLE→ACTIVE** | ES.OPT OI (pullable) | feasibility memo | chunked loader → GEX-regime → pin/flip | GEX regime test done |
| Positioning/COT | CLEAN_KILL (naive) | cot.csv | naive fade | COT+price-break conditional | conditional tested |
| Auction/issuance | CLEAN_KILL (concession) | treasury_auctions | wp_b1 | tenor-divergence | tenor variants tested |
| Inventory (EIA/OPEC) | DATA_BLOCKED_CERT | — | — | EIA surprise | feed (free API) |
| Macro-event drift | partial KILL | calendars | FOMC/NFP | CPI, event-1m-path | 1m path tested |
| Month-end/settlement/rebalance | CLEAN_BUT_WEAK | futures | ZN month-end | ZF/ZB, settlement-1m, index-rebal | variants tested |
| Expiry/OPEX | FEASIBLE (gamma) | ES.OPT | — | OPEX-gamma-pin | via gamma lane |
| Opening/closing liquidity | partial KILL | 1m | opening-drive | settlement-close, imbalance | imbalance re-spec tested |
| Intraday microstructure | CLEAN_KILL (volume direction) | 1m | volume ×3 | ES-NQ lead-lag latency | latency tested |
| Cross-asset lead-lag | UNDERTESTED | 1m | cross-asset-vol | pure latency | latency tested |
| Regime filters | UNDERTESTED | macro feeds | P19 (weak) | credit/vol regime overlay on survivors | (needs a survivor) |
| Execution/cost/liquidity | ACTIVE (tool) | 1m vol | participation-cost | liquidity risk-filter | tool, not alpha |
| Crypto funding/perp carry | CLEAN_KILL | deribit/okx | P22 hostile | — | (done) |
| FX fixing/rate-divergence | UNDERTESTED | 6E/6J/6B + rates | — | WMR-fix, rate-divergence | 2 expressions tested |
