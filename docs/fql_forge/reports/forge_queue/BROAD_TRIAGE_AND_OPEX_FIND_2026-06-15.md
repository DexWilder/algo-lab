# Broad Harvest Triage + first real find (pre-OPEX seasonal) — 2026-06-15

> **Mode:** Lane B / REPORT-ONLY full-search. No promotion/wiring/mutation.
> **Headline:** Broad triage of the 850-item backlog → the non-exhausted testable-now surface is the **microstructure/seasonal cluster**. First build = **pre-OPEX long-window seasonal**, which is the **first beta-controlled, robust, new-factor candidate** of the whole sweep → **WATCH (validate next).**

## Backlog cluster map (filename scan, 850 items)
VALUE 303 · CARRY 169 · spread 68 · curve 67 · vol 65 · auction 54 · breakout 51 · trend 46 · pair 45 · roll 43 · ppp 37 · range 35 · momentum 35 · session 20 · gap 16 · hurst 13 · cointegr 13 · inventory 9 · event 9 · afternoon 9 · cpi 8 · overnight 5 · liquidity 5.
→ The big clusters (VALUE/CARRY/curve/ppp/inventory/auction) are **feed-blocked**. The momentum/trend/breakout/range/vol/reversal clusters are **exhausted**. The **non-exhausted testable-now** surface = microstructure/session/gap/seasonal.

## Ranked top 10 (testable-now first)
| # | Idea | Family | Assets | Different from exhausted? | Data | Testable now | Diversification | Next action |
|---|---|---|---|---|---|---|---|---|
| 1 | **Pre-OPEX long run-up** | SEASONAL | MES/MNQ | Yes — calendar-seasonal, not intraday | OHLCV (OPEX=3rd Fri) | ✅ **TESTED → real** | Med-High (factor; equity-beta-laden) | **full robustness/prop validation** |
| 2 | FX London-open session breakout | SESSION breakout | 6E/6J/6B | Yes — FX, pre-RTH window | OHLCV (+tz map) | ✅ (needs custom pre-RTH harness; engine is RTH-only) | **High (new asset class)** | build pre-RTH session harness |
| 3 | Overnight gap bucket selection | GAP/structural | MES/MNQ/MGC/MCL | Partial — size-bucketed gap-fill vs hold | OHLCV | ✅ | Medium | build gap-bucket harness |
| 4 | Treasury roll-window regime filter | roll-seasonal | ZN/ZF/ZB | Yes — roll-date regime | OHLCV+roll dates | ✅ (pairs w/ RV engine) | Medium | low priority (filter) |
| 5 | NQ overnight-range regime → ORB | filter | MNQ | No — refines ORB (active family) | OHLCV | ✅ | Low (touches active book) | skip (don't touch active) |
| 6 | OPEC gap-hold through settlement | EVENT | MCL | Yes — energy event | needs OPEC calendar | ❌ | Medium | needs OPEC calendar (recall/WP) |
| 7 | Tokyo-open DXY bias | SESSION | 6J/6E/MGC | Yes | needs **DXY feed** | ❌ | Medium | blocked (DXY) |
| 8 | Open-interest pressure filter | positioning | many | Yes | needs **COT/OI feed** | ❌ | Medium | blocked (COT) |
| 9 | Commodity curve/inventory value | VALUE | CL/GC/… | Yes | **curve+inventory feed** | ❌ | High | WP (feed) |
| 10 | FX-PPP / cross-asset value sleeves | VALUE | FX/cross | Yes | **PPP/macro feed** | ❌ | High | WP (feed) |

## The find — pre-OPEX long-window seasonal (TESTED)
Harvest 2026-03-24_06. Mechanism: long equity index from ~11 to ~3 trading days before monthly OPEX (3rd Friday). (The note's "flip short during OPEX week" half is a **KILL** — dropped.)

| | MES | MNQ |
|---|---|---|
| LONG window PF | **1.947** | **2.468** |
| n / win rate | 84 / 69.0% | 84 / 71.4% |
| max-year concentration | 36.3% | 30.1% |
| **vs generic 7-day drift** | **1.88×** mean | **2.30×** mean |
| H1 / H2 mean (both +, win% 74/64, 76/67) | robust | robust |
| SHORT-leg (OPEX week) | KILL (0.63) | KILL (0.69) |

**Beta-control verdict:** the pre-OPEX window returns ~1.9–2.3× a generic same-length hold → genuine **seasonal alpha above beta**, not just "long equity in a bull market," and it holds in both sample halves. This is the first real diversifying lead the search has produced.

**Honest caveats:** it's **long-only equity** (carries equity beta — a market drawdown can still hurt it; it's a *seasonal-timed* long, not market-neutral); multi-day holds → overnight/weekend exposure (different prop-DD profile than the intraday-flat workhorses); n=84; the effect is documented in literature (replication confidence ↑, but crowding risk).

## Recommended next action (proceeding)
**Full robustness/prop validation of the pre-OPEX-long signal** (long-only, drop the short leg): year-exclusion stability, era split, largest single-window loss + max-DD (prop-survivability), cost-stress, exact-date-rule robustness (±1 day), and concentration gates. Then test #2 (FX London-open breakout — new asset class) and #3 (gap bucket). This is advancing a real candidate, not a repeat of an exhausted lane.

## Boundaries
Report-only; no promotion/wiring/mutation; canonical feeds + active books untouched; no exhausted-lane re-run. Phase 1C frozen pending PHASE1C_24H_VERIFY (surfaced separately).
