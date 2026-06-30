# Free-Data Status + External-Source Packet Specs (2026-06-30)

## CORRECTED conclusion (scoped, not defeatist)
**EXHAUSTED:** the crossbred PRICE/VOLUME/OHLC primitive-expression space — 1680-combo sweep, 1458 real, 0 concentration-
clean; plus volume direction/confirm/climax/imbalance, macro-regime (P19), crypto-carry (P22), auctions (wp_b1), COT,
month-end, overnight, basket, FOMC-drift (reconciled). All KILL under our harness/costs/concentration gates.
**NOT exhausted:** structural/event mechanisms requiring REAL feeds (Lane-1 downloads), Databento used as cost/liquidity/
event-path/time-of-day (not direction), external-source-mined mechanisms, and the paid-data tier. The primitive grid is
dead; the information stack above it is not. **Strategy discovery remains at ZERO validated primaries.**

## What remains LIVE (by access)
- **Operator-feed-gated (ready harnesses):** rates roll-yield, EIA energy-event, CPI-surprise → `FORGE_OPERATOR_DATA_HANDOFF_2026-06-30.md`.
- **Paid-data:** gamma/GEX, true VIX curve, options-OI, L2.
- **Free-but-untested-properly:** Databento event-path (1m around releases, not daily closes); time-of-day liquidity execution-realism; relative-value across the rates curve / equity-vs-equity with PROPER stat-arb (not naive XSMOM).
- **Low-prior free:** macro-regime overlays (P19-class died; deprioritize).

## External-source mechanism packet specs (from-knowledge; pre-registered; data-tagged)
> T1 forced-structural weighted. Each = mechanism · forced participant · data · feasibility · lane.
1. **Index-reconstitution drift** (S&P/Russell rebalance) — index funds forced-buy. Data: rebalance calendar + futures. **DATA_BLOCKED** (calendar).
2. **OPEX/quad-witch dealer-gamma pin** (Harris/dealer hedging) — Data: options OI/gamma. **PAID**.
3. **Month-end FX benchmark (WMR 4pm) flow** — Data: intraday FX (have 6E/6J/6B). **FEASIBLE** → queue (Databento 1m event-path).
4. **Treasury roll-period pressure (front→back)** — Data: per-contract (rates_multicontract). **OPERATOR-FEED**.
5. **EIA inventory surprise drift** — **OPERATOR-FEED** (#2 handoff).
6. **Settlement/VWAP-close auction pressure** — Data: 1m close behavior (have). **FEASIBLE** → queue.
7. **Vol-risk-premium term structure (Ilmanen/Sinclair)** — Data: true VIX curve. **PAID** (vix.csv is spot only).
8. **Relative-value rates curve (2s5s10s fly mean-reversion)** — Data: treasury_yield_curve.csv (HAVE). **FEASIBLE** → queue (but yield-curve branch was killed once; re-spec on FLY not level).
9. **Lead-lag ES→NQ microstructure** — Data: 1m (have). **FEASIBLE** but P21 cross-asset-vol died; re-spec as pure lead-lag latency.
10. **Carry across futures (Carver)** — Data: have; needs proper roll-adjust. **FEASIBLE-CAUTION** (roll artifacts).
11. **Pre-auction concession in cash vs futures basis** — Data: needs cash. **DATA_BLOCKED**.
12. **Funding-rate crypto carry (hostile)** — **DONE** (P22 KILL; ETH negative).
13. **Holiday/turn-of-year seasonality (cost-first)** — Data: have. **FEASIBLE-LOW-PRIOR** (overfit-prone).
14. **Credit-regime equity conditioning (credit_oas)** — partially P19 (died); re-spec as tail-hedge timing not directional.
15. **Inflation-surprise rates** — **OPERATOR-FEED** (#3 handoff).
**Feasible-now (queue, Databento event-path/RV — NOT primitive grids):** #3 FX-fix, #6 settlement-close, #8 rates-fly-RV, #9 ES-NQ-lead-lag.
**Operator-feed:** #1,#4,#5,#15. **Paid:** #2,#7. **Done/low:** #10,#12,#13,#14.
