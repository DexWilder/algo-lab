# Search-Surface & Data-Fit Audit (2026-07-02)

> Are we finding nothing because there IS nothing, or because we search the wrong surfaces / wrong data / wrong abstraction?
> Evidence-backed. Clean kills are NOT proof the surface is empty — they prove those exact expressions died under current data/tier.
> **Verdict: we are killing honestly, but under-searching high-value structural surfaces AND mis-fitting data on 2 of them.**

## 0. Two decisive data-fit findings this audit
1. **The GEX pin kill was on the WRONG options.** `ES.OPT` parent = monthly/quarterly only (ESM5/ESH6/…); OI sample had **0 rows < 20 DTE (median 44 DTE)**. Pinning lives at **0DTE/expiry-week**, which trades under separate parents (**EW1–4, E1A, E3C** — all confirmed to exist, ~$0.01–0.09/wk). ⇒ naive-pin `CLEAN_KILL` is *wrong-data*, not *no-edge*. Weekly-OI pull launched.
2. **`bbo-1m` (bid/ask/spread) costs $0.009/wk** — nearly free, verified (median spread 0.25pt = 1 ES tick, 100% present). We had **zero quote/spread data**; this unlocks real execution realism + spread microstructure.

## 1. Current search surface
| Surface | Data / tier | Mechanism class | Packets | Killed | Retained | Depth |
|---|---|---|---|---|---|---|
| 1m+volume | T3 | intraday micro | ~19 (OR/MR/trend/close-imb/leadlag) | ~18 | 0 | broad-but-generic |
| term structure | T4 | carry/RV/spread | ~15 | ~13 | **spreadMR_GC (SCREEN_PASS)** | medium |
| options/OI/GEX | T6 | dealer reflexivity | 1 (naive pin) | 1 (wrong data) | 0 | **shallow, mis-fit** |
| source-derived | mixed | forced-flow | 3 | 0 | 3 queued | thin |
| event/calendar | T5 | event drift | ~5 | ~4 | 0 | shallow, date-flags only |
| external feeds | T5 | macro/vol/positioning | ~10 | ~8 | 0 | shallow |

## 2. Data-correctness audit (per active family)
| Family | Right data? | Richest? | Causal/PIT? | Correct vehicle? | Proxy risk | Verdict |
|---|---|---|---|---|---|---|
| GEX/dealer | **NO (monthly not weekly/0DTE)** | no (no weekly OI) | yes (prior-day OI) | MES spot for ES options OK | pin needs 0DTE | **re-pull weekly/0DTE** |
| 1m micro | partial (no quotes) | no (bbo-1m now avail) | yes | micro vehicle OK | 15m grid coarse | add spread data |
| term structure | yes | yes (T4) | yes | CL/GC full-size→micro MCL/MGC | roll-gap (guarded) | OK |
| event drift | **NO (date flags, no surprise)** | no | n/a | — | proxy = date≠surprise | **need consensus/actual** |
| settlement/closing | yes | partial (no quotes) | yes | OK | — | add spread/imbalance |
| cross-market | partial | no (no regime cond) | yes | OK | generic lead-lag | needs regime/event conditioning |
| source-derived | yes | varies | yes | OK | — | expand |

## 3. Missing-data assessment (verified costs)
| Data | For family | Have? | Databento cost | Approval? | First packet unlocked |
|---|---|---|---|---|---|
| **Weekly/0DTE options OI (EW1-4,E1A,E3C)** | GEX | no | ~$0.3/wk (~$8/3mo) | auto (<$25) | expiry/0DTE pin, gamma-flip |
| **bbo-1m quotes/spread** | micro + execution | **now sampled** | $0.009/wk | auto | spread-conditioned micro; real exec cost |
| mbp-1 top-of-book | liquidity micro | no | $4.72/wk | targeted-only | order-imbalance reversal |
| mbp-10 depth | order-book | no | $7.85/wk | targeted-only | depth-imbalance |
| trades (tick) | micro | no | $2.64/wk | ~weekly | trade-flow/absorption |
| CPI/NFP consensus+actual (surprise) | event | **NO** (levels only) | external (free-ish) | cert | surprise-reaction path |
| Auction bid-to-cover/tail/indirect | auction | partial (yield/amt, no flow) | external | cert | concession by demand-strength |
| VIX futures curve | vol | partial (spot vix) | Databento/other | check | true VRP curve |
| Index rebalance calendar | forced-flow | no | external | cert | reconstitution close |

## 4. Search-right-places audit (graded)
| Zone | Status | Packets | Data ready | Missing | Next 3 tests | Grade |
|---|---|---|---|---|---|---|
| A Forced-flow events | thin | roll/settlement/auction-concession (killed) | partial | rebalance cal, EIA shock | index-rebalance close, month-end 1m, roll-window CL | **C** |
| B Dealer/options reflexivity | mis-fit | 1 (wrong options) | **weekly OI pulling** | 0DTE OI | 0DTE pin, gamma-flip range, call/put-wall | **C+** (highest upside) |
| C Institutional exec windows | shallow | open/close/settlement (killed) | **bbo-1m unlocks** | quotes | spread-conditioned close, VWAP-band, post-open absorption | **C+** |
| D Event surprise/path | weak | date-flags only | **no** | consensus/actual | (blocked until surprise data) | **D** |
| E Cross-market dislocation | weak | generic lead-lag (killed) | partial | regime cond | gold/real-yield, NQ/ES gamma-state, crude/USD inventory | **D** |
| F Positioning/crowding | shallow | COT naive (killed) | partial | fund flows | COT+price-break conditional | **C-** |
| G Vol/convexity | shallow | vol-carry weak, DVOL | partial | RV-vs-IV | vol-crush drift, DVOL regime | **C** |
| H Execution/cost alpha | absent→unlocking | — | **bbo-1m** | — | time-of-day spread, 2-leg spread, micro-vs-full | **D→C** |

## 5. Are we overtesting the wrong thing? — YES.
The T3 sweeps are dominated by **generic intraday MR / trend / continuation / breakout** (all killed, correctly). These are the crowded, arbed surfaces. **Action:** cap generic price/volume packets; every new price/volume packet must cite a forced-flow or structural justification (enforced via `score_novelty_packet` non-generic gate). Redirect queue to B/C/D/E structural zones.

## 6. Novelty quality — OK internally, thin externally
Source packets (roll-window, GEX-pin, liquidity-hole) are mechanism-driven (scorer: 0 WEAK). Internal novelty is finite (108 combos). **Gap: external source engine is 3 packets, not a factory.**

## 7. Elite search upgrade plan
**Top 10 changes:** (1) pull weekly/0DTE options OI → real GEX branch; (2) integrate bbo-1m spread → execution realism + spread micro; (3) acquire event surprise (consensus/actual) for CPI/NFP; (4) auction flow detail (bid-to-cover/tail); (5) build regime library (vol/liquidity/gamma/rates/$); (6) regime/event-condition cross-market (not generic lead-lag); (7) cap generic price/volume; (8) index-rebalance calendar; (9) targeted mbp for liquidity-hole; (10) grow source engine to ≥5 packets/cycle.
**Top 25 next tests (diverse — NOT one family):** see §Decision.

## 8. Decision
- **Correct data?** Improving but NO on 3 fronts: GEX (monthly not weekly/0DTE), event (flags not surprise), execution (no quotes → bbo-1m fixes).
- **Right places?** Partly — under-searching forced-flow events, dealer reflexivity done wrong, event-surprise absent, cross-market generic.
- **Must change before next 10–20 runs:** weekly-OI + bbo-1m integrated; queue rebalanced across B/C/D/E; cap generic price/volume.
- **Can run immediately:** real GEX expiry/0DTE pin (once weekly OI lands); spread-conditioned institutional-window tests (bbo-1m); spreadMR_GC deepening; source-derived forced-flow.

### Required output
- **Files updated:** this audit; `data/databento_weekly_oi_pull.py`; `data/databento_gex_loader.py`; `data_budget.json` (bbo-1m + weekly pulls); queue rebalanced.
- **Data gaps:** weekly/0DTE OI (pulling), event surprise (consensus/actual), quotes (bbo-1m unlocked), auction flow, rebalance calendar.
- **Source gaps:** external engine still thin (3 packets).
- **Top 10 search-surface risks:** GEX mis-fit; event-surprise absent; over-testing generic price/volume; cross-market generic; no regime library; no quote/spread (until now); source engine thin; execution realism immature; 0DTE untested; finite internal novelty.
- **Top 25 next actions:** balanced — see queue (GEX-0DTE ×5, spread-window ×5, term-structure/spreadMR ×4, event-surprise-prep ×4, cross-market-regime ×4, source ×3).
