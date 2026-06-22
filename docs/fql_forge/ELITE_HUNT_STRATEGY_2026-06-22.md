# Making the Forge More Elite — Strategic Synthesis — 2026-06-22

> Written after a very thorough session that mapped the reachable search space and hardened the engine. The honest evidence now points to specific structural moves, not more of the same.

## What the evidence says (where edge IS and ISN'T)
- **NOT found (mapped empty for daily non-MNQ/non-gold WH2):** single-series price patterns, calendar-directional, intraday time-of-day, cross-asset overlays, vanilla auction windows, auction-result-conditioned, funding-stress directional. Simple directional edge on liquid futures is largely arbitraged.
- **Found & real (but event/tail/overlay, not daily workhorses):** FOMC-week rates (a genuine ~0-corr diversifier — P-SLEEVE confirmed it adds net AND cuts combined DD), FOMC-MNQ-1h, pre-holiday equity, MGC-prior_day_break, MGC-ORB low-vol overlay; plus the incumbent momentum workhorses (MNQ-ORB, gold-ORB).

## Reframe #1 — the target may be wrong. Build an ENSEMBLE of sparse decorrelated edges.
We keep hunting a mythical "second daily workhorse." The evidence says that's rare/arbitraged. But we HAVE found multiple genuinely decorrelated event/tail sleeves — and P-SLEEVE shows they improve the bench (net + DD). **An elite portfolio is often an ensemble of many sparse, decorrelated edges, not 2-3 daily workhorses.** Shift the objective function: a candidate's value = its MARGINAL diversification to the bench (corr, combined-DD delta), not its standalone PF. Goal becomes "add the next decorrelated sleeve," which we're already good at finding.

## Reframe #2 — the bottleneck is now DATA/INPUTS, not testing.
The testing engine is now elite (catches NaN-rolling, lookahead, contamination, thin-window cost, routing bugs, fill-optimism, overfit; predeclared-band confirmation; mechanism packets; no false bank survived audit all session). It has been mining a FINITE reachable ingredient set: OHLCV + a few macro/COT series. More recombination of the same inputs → more kills. **Genuinely new edges need genuinely new INFORMATION not in price.**

## New AREAS to source (ranked by reachability × inefficiency)
1. **Crypto (FREE, reachable, genuinely new asset class).** Binance/Coinbase/Kraken public APIs, 24/7, retail-heavy, less efficient, no vendor cost. The single highest-EV NEW area we can source today at $0. Funding-rate/perp-basis, weekend effects, liquidation cascades = real forced-flow.
2. **Options / vol-surface (paid-ish, high inefficiency).** Dealer gamma/skew/term-structure → hedging flows (the genuine forced-flow class we keep theorizing about). Needs an options data feed.
3. **Cross-sectional equity factors / breadth / dispersion.** Needs equity universe data; classic decorrelated factor space.
4. **Intraday order-flow / microstructure (tick, depth).** Needs tick data; where short-horizon edge actually lives.
5. **Event surprise data (earnings, econ consensus).** Upgrades event sleeves from date-only to surprise-conditioned (the missing piece that killed #T12 CPI and limits auctions).

## Operational upgrades to make the Forge itself more elite
1. **Close the Claw→Forge loop.** 868-note backlog still unprocessed; Claw still defaults to saturated families. Frequency-first, mechanism-packet sourcing; apply the structural seed-list. Sourcing quality is the real throughput constraint.
2. **Execution-realism layer in the engine.** Bake realistic fills/slippage (thin-window cost, MAE stop-slippage) into backtests so screens are deployment-grade from the start — not caveated after. Several "edges" this session were fill/cost artifacts.
3. **Forward / live-paper validation pipeline.** The banked event sleeves' real test is forward performance. Stand up a report-only forward tracker for FOMC-week rates etc. (the actual path to a paper packet).
4. **Mechanism library.** A growing catalog of forced-participant stories → systematic packet generation (vs ad-hoc). Each entry: who's forced, when, implied direction, data needed.
5. **Bench/portfolio objective (P-SLEEVE formalized).** Make marginal-diversification the standing scorecard; run P-SLEEVE on every new candidate.

## Honest priority for the operator
- **Highest-EV new vein at $0:** crypto sourcing (new asset class, free, less efficient, forced-flow present). Concrete next build.
- **Highest-EV data buy:** options/vol-surface (the real forced-flow class).
- **Highest-EV consolidation:** forward-validate the FOMC-week rates diversifier toward a paper packet (it's the best real find).
- **Stop expecting:** a daily non-MNQ/non-gold workhorse from reachable price/macro data — that's mapped empty.

## Boundaries
All report-only. New-area sourcing = acquire structural + screen with the same hardened discipline. No promotion/wiring/mutation without approval.
