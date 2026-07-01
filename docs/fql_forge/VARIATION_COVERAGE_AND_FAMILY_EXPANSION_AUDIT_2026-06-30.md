# Variation Coverage & Family Expansion Audit (2026-06-30/07-01)

> Answers: are we consuming the FULL opportunity surface, or testing one packet at a time from an incomplete queue?
> **Blunt answer: NO — not the parked structural surface.** We exhaustively tested the DEAD families (primitive/breakout/
> volume) while the potentially-live FACTOR families (carry, value, relative-value, term-structure) sit largely untested.

## §1 Total available variation inventory (real counts)
| Source | Available | In queue | Tested (truth-gate) | Clean-killed | Blocked | Not-operationalized |
|---|---|---|---|---|---|---|
| Registry strategies | 167 | ~0 | ~74 decided | 36 rejected+28 arch | — | **83 idea + 10 watch UNTESTED** |
| forge_cycle test scripts | 194 | n/a | 194 run | most KILL | — | — |
| Primitive sweep combos | 1,680 | done | 1,680 | 1,458 (0 survivors) | — | dead family |
| research/specs/ | 23 | ~2 | ~10 | some | some | **~11 specs unqueued** |
| FORGE_CANDIDATE_LEDGER | 19 | 0 | pre-truth-reset | — | — | superseded/unreconciled |
| wp_/lever_ harnesses | 2 | run | wp_b1 KILL | — | — | — |
| data/feeds | 19 | partial | ~12 used | — | 3 feed-gated | 4 underused |
| Databento 1m/vol | 11 inst | partial | volume-lane dead | — | — | event-path/cost UNTESTED |
| Historical reports | 243 | n/a | — | — | — | old WATCH not reclassified |
**Coverage: of 167 registry, ~93 (56%) untested under the CURRENT truth-gate, and ~0% were in the queue.**

## §2 Edge-family map (coverage by FAMILY, not packet)
| Family | Best data | Tested | Untested variants | Status |
|---|---|---|---|---|
| Trend/momentum | futures | TSMOM (weak), primitive sweep | pooled/vol-target trend | **CLEAN_BUT_WEAK** |
| Mean-reversion | 5m | VWAP/primitive (dead) | — | **CLEAN_KILL** |
| **Carry** | futures + energy/rates feeds | vol-carry only (weak) | **~15 ideas: FX-rate-diff, commodity term-structure, energy-curve, futures-carry-rank, natgas, curve-segment** | **UNDERTESTED ← HIGHEST-EV** |
| Curve relative-value | ZF/ZN/ZB + yield curve | 5s10s30s fly (KILL); 2s5s10s (DATA_BLOCKED) | kalman-spread, half-life, ZF/ZN pairs | **UNDERTESTED / partial DATA_BLOCKED** |
| **Value** | FX + macro feeds | none | **FX-PPP, fx-relative-value, macro-real-yield, cross-asset-value** | **UNDERTESTED ← 2nd-EV** |
| Vol risk premium | vix.csv spot; DVOL | vol-carry (weak) | true-curve VRP | **CLEAN_BUT_WEAK / PAID for curve** |
| Dealer/gamma flow | — | none | OPEX/gamma | **PAID_DATA_REQUIRED** |
| Positioning/COT | CFTC | naive (KILL) | commercial-value-reversion, non-naive | **CLEAN_KILL (naive) / undertested (non-naive)** |
| Auction/issuance | treasury_auctions | wp_b1 (KILL) | tenor-divergence, regime-quality, instability, supply-cycle | **CLEAN_KILL (concession) / undertested (tenor/quality)** |
| Inventory (EIA/OPEC) | — | none | — | **DATA_BLOCKED (feed handoff)** |
| Macro-event drift | calendars | FOMC (KILL), NFP (KILL) | CPI, EIA 1m-path | **partial KILL / DATA_BLOCKED** |
| Month-end/settlement/rebalance | futures | ZN month-end (weak) | ZF/ZB, settlement, index-rebalance | **CLEAN_BUT_WEAK / undertested** |
| Expiry/OPEX | — | none | OPEX-week (spec exists) | **DATA_BLOCKED (options)** |
| Opening/closing liquidity | 1m | opening-drive (KILL) | settlement-close 1m | **partial KILL / undertested** |
| Intraday microstructure | 1m | volume (dead) | ES-NQ lead-lag (1m) | **CLEAN_KILL (direction) / undertested (latency)** |
| Cross-asset lead-lag | 1m | cross-asset-vol (KILL) | pure latency | **undertested** |
| Execution/cost/liquidity | 1m vol | participation-cost (null) | liquidity regime filter | **ACTIVE (tool, not alpha)** |
| Crypto funding/perp carry | deribit/okx | P22 (KILL) | — | **CLEAN_KILL (separate lane)** |
| FX fixing/rate-divergence | 6E/6J/6B + rates | none | WMR-fix, rate-divergence | **UNDERTESTED** |

## §3 Thousands-of-variations proof (dimensions)
Swept ONLY in primitive space (dead): entry×filter×exit×asset×session (1,680). **NOT swept as families:** carry-ranking
across instruments; FX rate-differential; commodity term-structure; value (PPP/real-yield); relative-value spreads
(Kalman/half-life); event-1m-path; roll-window; settlement-window; liquidity-regime risk-targeting; ensemble/basket of
clean-weak legs. **P-hacking guard:** family sweeps are PRE-DECLARED (fixed variant list per family, family-N DSR), not
open combinatorial grids.

## §4 Queue completeness — LOADED from inventory (this audit)
- **ADD_TO_QUEUE_NOW:** carry family (~15), value family (~7), relative-value (~5), FX-fix/rate-divergence, settlement-1m, ES-NQ latency.
- **SUPERSEDED:** breakout/vol_expansion/crossbreed_breakout ideas (~30) — primitive sweep killed the family.
- **CLEAN_KILL_ALREADY:** auction-concession, COT-naive, volume-direction, primitive.
- **DATA_BLOCKED:** EIA, CPI-surprise, rates_multicontract (2s5s10s proper), OPEX/gamma (paid), true-VIX-curve (paid).
- **DUPLICATE:** P03 (=wp_b1).

## §5 Family-expansion sprint (predeclared) — order by EV
A. **CARRY family batch (HIGHEST-EV, RUN_NOW):** FX-rate-differential carry (6E/6J/6B × policy_rates); cross-sectional
   futures carry-rank; commodity term-structure (energy_spot + curve); rates rolldown (yield-curve slope). Family-N DSR.
B. **VALUE family batch:** FX-PPP/real-yield; macro-real-yield value. C. **RV family:** Kalman/half-life ZF/ZN pairs (not flies).
D. **Event-1m-path:** FOMC/NFP/CPI/settlement using Databento 1m (not daily close). E. **External-source 25 packets** (in progress).
F. **Crypto-carry:** DONE (KILL, separate lane).

## §6 Evidence standard — every batch reports global-N + family-N + lane-N + packet-N + threshold + cost + causality + concentration + H1/H2 + per-year + verdict. Labels: FAMILY_EXHAUSTED/UNDERTESTED/ACTIVE_EXPANSION/DATA_BLOCKED/CLEAN_KILL/CLEAN_BUT_WEAK/SCREEN_PASS_RETAINED/RETEST_REQUIRED. No WH/primary/validated.

## §7 DIRECT ANSWERS
- **Sourcing the right strategies?** Partially. Dead families over-tested; live factor families (carry/value/RV) undertested.
- **Running the thousands of variations available?** NO — only the primitive grid (dead). Structural/factor families not swept.
- **% of available variations in queue?** Was ~0% of the 93 untested registry ideas; now loaded (carry/value/RV → RUN_NOW).
- **% tested (truth-gate)?** ~44% of registry decided; 56% (93) untested under current gate.
- **Underrepresented families?** Carry, value, relative-value, event-1m-path, FX-fix.
- **Data not exploited?** Databento 1m event-path; energy_spot/policy_rates/real_rates for carry/value; treasury curve for RV.
- **Highest-EV family NOW?** **CARRY** (untested, real mechanism, data present) → then VALUE, then event-1m-path.
- **Blocked by operator data?** proper rates-RV (rates_multicontract), EIA, CPI-surprise; PAID: gamma, true-VIX-curve.
- **Runs automatically next?** CARRY family batch (RUN_NOW), then VALUE, then event-1m-path.
- **Next 50 queue items?** carry×~15 + value×~7 + RV×~5 + event-1m×6 + FX-fix×3 + settlement×2 + source×25 (see queue).


## §8 FAMILY SPRINT — first batch run + CONVERGENT FINDING (2026-07-01)
**CARRY family batch (highest-EV untested) = CLEAN_KILL on available data:** rates-rolldown ZN Sh −0.08, cross-tenor
carry-rank Sh −0.28, FX-carry DATA_LIMITED (boj feed). BUT proper carry (cross-sectional futures ROLL-YIELD, commodity
TERM-STRUCTURE) is DATA_BLOCKED — needs per-contract front-vs-deferred (rates_multicontract + commodity curves).
**CONVERGENT CONCLUSION across families:** the FREE-DATA expression of every factor family dies (trend=weak, MR=dead,
carry=dead-proxy, curve-RV=dead-futures, positioning=dead, auction=dead), and the PROPER expressions are UNIFORMLY blocked
on the SAME missing data class: **term-structure / per-contract / options.** This is evidence-backed, not defeatist:
the systematic bottleneck is DATA (Lane-1 rates_multicontract/EIA/CPI + paid gamma/VIX-curve/options-OI), not idea supply.
Highest-EV NOW re-ranked: (1) operator drops rates_multicontract → proper carry + curve-RV unlock together; (2) VALUE
family (FX-PPP/real-yield — testable on macro feeds, next batch); (3) event-1m-path (Databento).