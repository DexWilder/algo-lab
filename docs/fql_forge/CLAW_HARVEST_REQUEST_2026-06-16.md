# Claw Harvest Request — Daily-Elite Mechanisms — 2026-06-16

> For the Claw hunter/scout loop. **Harvest 50–100 daily/near-daily mechanism hypotheses from OUTSIDE the current repo idea pool.** The recent WH2 work shows current repo ingredients (OHLCV, session times, prior-day levels, ORB, EMA, ATR states, simple range logic) keep recombining the same material — the daily-elite unlock likely needs NEW raw hypotheses and new input families. That is Claw's job. Report-only; nothing here promotes or activates anything.

## Hard sort key: FREQUENCY
Mission = **DAILY ELITE strats.** Rank daily > near-daily > weekly > sparse. Sparse-event ideas may be catalogued but are OFF-TARGET for WH2 unless they unlock a broader daily/near-daily family — we already have sparse event sleeves (FOMC). Do not fill the quota with event ideas.

## Required fields per idea
1. **mechanism name**
2. **behavioral reason the edge persists** — who is *forced* to do what, when, and why (the non-negotiable field; no behavioral story → low priority)
3. **applicable instruments**
4. **expected cadence** — daily / near-daily / weekly / sparse
5. **expected diversification value vs the MNQ workhorse** (and vs the gold sleeve)
6. **required data**
7. **testable now vs feed-blocked**
8. **cheap-screen spec** (if testable now) — entry/exit/filter/horizon concrete enough to code
9. **feed request** (if feed-blocked) — exact source/schema → routes to the Lever-B queue
10. **duplicate/archive check** — confirm it is NOT on the do-not-resurface list
11. **priority score** — composite of {frequency, diversification, behavioral plausibility, testable-now}

## Anti-duplication (MANDATORY): "new mechanism or do not bring it back"
Do NOT re-surface (these are archived/dead — see no-repeat archive):
- archived ORB / EMA grids
- MNQ momentum cousins
- prior_day_break cross-asset (gold-specific; already mapped)
- generic gap-fill / gap-reversal grids
- turn-of-month calendar scraps
- FX-London / session-transition salvage
- rates afternoon_reversion / bb_reversion
- rate momentum / MR / curve-pairs already killed
- vol-expansion / keltner non-equity failures
- any archived vanity grid WITHOUT a materially new mechanism

## Where to hunt (new raw material, behaviorally grounded)
Forced-flow / structural-participant behavior is the richest vein for persistent daily edges:
- **Hedger/dealer flow:** options-dealer gamma hedging (index/gold), pension/rebalance flows, month-end/quarter-end index rebal, ETF creation/redemption pressure.
- **Forced timing:** margin-driven liquidation patterns, settlement-window behavior, roll-period flows (futures roll mechanics), auction/fixing windows (LBMA gold fix, FX fixes).
- **Cross-participant asymmetry:** commercial vs spec positioning extremes (COT), real-money vs fast-money session handoffs.
- **Volatility-regime behavior:** vol-of-vol shifts, term-structure of realized vol, post-shock dealer rebalancing.
- **Cross-asset lead/lag with a MECHANISM:** dollar→gold, real-rates→gold, crude inventory→energy, risk-on/off→index dispersion (only with a forced-flow story, not naive correlation).

## Output
- A ranked table (50–100 rows) with the 11 fields, **frequency-sorted then priority-sorted**.
- A clear split: **TESTABLE-NOW** tranche (→ Claude cheap-screens immediately) vs **FEED-BLOCKED** tranche (→ Lever-B queue with feed requests).
- Flag any idea whose behavioral story is weak or whose mechanism overlaps the archive → drop, don't pad the count.

## PACKET UPGRADE (2026-06-17) — locked requirements after backlog triage
The 878-note triage found Claw produces **0% hard kills** (defers everything) and re-harvests 6 saturated families. New requirements:
1. **Hard-kill categories, not just defer/watch.** Any mechanism matching the no-repeat archive (below) → KILL verdict, do not surface.
2. **Suppress the 6 saturated families** (already no-repeat archived; cap at one canonical each): London-FX breakout (47), PPP FX carry basket (88), Kalman/cointegration stat-arb (59), value-rebalance-timing gates (60), WTI carry slope variants (14), non-equity vol-managed sizing overlays (88).
3. **Do NOT label feed-blocked ideas "testable-now."** Testable-now requires the feed to exist in-house: 5m for `6B 6E 6J ES M2K MCL MES MGC MNQ MYM ZB ZF ZN` + FOMC/CPI **date** calendars. Anything needing ZT/ZC/ZS/NG/SI/HG, 13th-month contracts, FRED/USDA/BLS-values, COT, curve/F2, DXY → FEED-BLOCKED (route to Lever-B).
4. **Up-weight** EVENT, STRUCTURAL, RATES, CARRY, CURVE, AUCTION, CPI-detail, inventory-style leads (currently EVENT only 9%). Down-weight VALUE/CARRY-PPP (already 63% and feed-blocked).
5. **Cadence classification required:** daily / weekly / monthly / sparse-event. Frequency is a hard sort key.
6. **Every note must state:** mechanism (precise rule), feed requirement, expected cadence, distinctness from archived families, and **why it is NOT just another breakout/momentum variant** (the breakout family — ORB/donchian/dual-thrust — is dead off-MNQ/gold; do not bring back breakouts without a genuinely new structural reason).

Claw remains scout/harvester; Forge remains builder/tester/validator; no activation authority moves to Claw. (Claw is automation-owned — these are recommended config changes for the operator to apply, not self-edited.)

## 2026-06-17 REFRESH — STRUCTURAL-MECHANISM harvest (the reachable-simple-screen surface is exhausting)
The session has now screened single-series behavioral (112 cands), cross-asset confirmation, FRED rates curve/carry, macro-gold (real-rate/breakeven), and energy dislocation (stale+fresh) — all KILL for a non-MNQ daily WH2. Data access is NO LONGER the bottleneck (FRED + Yahoo reachable); simple price-pattern mechanisms on liquid futures look arbitraged. So harvest must shift to **market-STRUCTURE / FLOW / participant-behavior** mechanisms.

**Harvest ONLY (frequency-first, non-gold, non-MNQ):**
- **Auction-flow** (Treasury issuance concession/reversion, bidder composition, allotment stress)
- **Roll-yield / carry** in true futures term-structure form (front-vs-deferred), not yield-curve proxy
- **Inventory-surprise** (EIA petroleum/gas vs consensus or seasonal)
- **Settlement / calendar flow** (month/quarter-end duration rebalance, index reconstitution, options-expiry/gamma, futures roll-week)
- **Positioning / proxy** (COT extremes, ETF creation/redemption, fund-flow proxies)
- **Cross-asset forced-flow** (copper/gold growth signal, dollar regime, real-rate→assets, risk-on/off composite)

**EXCLUDE from LANE 1 (WH2 diversifier) ONLY:** generic OHLCV/ORB/breakout/trend/EMA/ATR variations UNLESS tied to a concrete market-structure reason; gold-timing overlays; MNQ momentum cousins; everything on the no-repeat archive.

**SCOPE CORRECTION (2026-06-17, see `FORGE_TWO_LANE_DOCTRINE_2026-06-17.md`):** the gold/MNQ exclusion is **Lane-1-only**, NOT global. **LANE 2 (paper-bench / sleeve-improvement) WELCOMES MNQ + MGC/gold harvest** — better workhorses, replacements, overlays, packet-grade candidates on existing sleeves. Tag each harvested note `lane:1-diversifier` or `lane:2-sleeve-improvement`. Lane-2 MNQ/MGC notes must still target a genuine improvement (better PF/OOS/DD/concentration or a non-duplicate addition/overlay), not another generic variant.

**Required per note:** mechanism + the **structural reason it persists (who is forced to trade what, when, why)** + required feed + expected cadence + instruments + distinctness from archive. A note without a forced-flow / structural story = auto-KILL, not WATCH.

## 2026-06-18 STRUCTURAL SEED-LIST (concrete mechanisms to expand — "harvest structural flow" is too abstract)
Claw keeps defaulting to saturated families because the directive was abstract. Expand THESE specific forced-flow mechanisms (each has a who-is-forced story). Tag reachable-now vs feed-blocked; do NOT re-surface the dead/saturated list above.

| # | Mechanism | Who is forced (why it persists) | Instrument | Data |
|--:|---|---|---|---|
| S1 | Treasury auction concession/reversion | dealers/real-money position around scheduled issuance supply | ZN/ZF/ZB | feed (auctions CSV — staged) |
| S2 | Futures roll-period flow (clean) | longs MUST roll front→deferred before First Position Day | ZN/MCL/MES | feed (front+deferred / clean roll) |
| S3 | Index reconstitution (Russell late-Jun, S&P qtrly) | index funds MUST rebalance to new constituents on effective date | M2K/MES | reconstitution dates (partial reachable) |
| S4 | Options-dealer gamma (OPEX pin/unpin) | dealers hedge gamma into/after 3rd-Fri expiry | MES/MNQ | feed (options gamma/OI) |
| S5 | ETF creation/redemption pressure | APs transact underlying to clear primary-market flow | MES/MGC | feed (ETF flow) |
| S6 | COT positioning extremes (commercial vs spec) | crowded specs forced to unwind at extremes | rates/crude/FX | feed (CFTC COT) |
| S7 | Crude inventory-state (EIA surprise) | hedgers/specs reprice on weekly supply shock | MCL | feed (EIA) |
| S8 | FX fixing-window flow (London 4pm/WMR) | benchmark-tracking funds MUST trade at the fix | 6E/6J/6B | intraday + fix times (partial 2024+) |
| S9 | Coupon/dividend ex-date flows | index futures reprice around large dividend/coupon dates | MES | feed (dividend/coupon calendar) |
| S10 | Settlement-window behavior (cash close vs futures) | hedgers square into cash settlement | ZN/MES | reachable intraday (mostly untested) |
| S11 | Quad-witch expiry-DAY mechanics (not week) | simultaneous futures+options expiry forces unwinds | MES/MNQ | reachable (OPEX-week=beta; expiry-day untested) |
| S12 | OPEC/EIA crude event calendar | producers/hedgers reprice on supply decisions | MCL | feed (OPEC/EIA calendar) |

**Most structural-flow mechanisms are FEED-BLOCKED** — which is exactly why the highest-EV path is data-staging, not more reachable screens. Reachable-now untested: S10 (settlement-window), S11 (expiry-day), partial S3/S8. Claw should harvest VARIANTS/refinements of these (with behavioral stories) and route feed-blocked ones to the Lever-B queue — NOT regenerate dual-thrust/Kalman/London/PPP-carry.

## Operator note on Claw health (2026-06-16)
Claw is infrastructure-healthy but (1) throttled by an 18-note/day budget that causes idle spin, (2) sitting on an 868-note unprocessed pickup backlog (Claw→Claude handoff broken — Claude must triage), and (3) skewed toward feed-blocked VALUE/CARRY. This request re-aims it: frequency-first, testable-now daily mechanisms, feed-blocked → Lever-B queue. Recommend raising the note budget for this harvest sprint.
