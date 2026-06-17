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

## Operator note on Claw health (2026-06-16)
Claw is infrastructure-healthy but (1) throttled by an 18-note/day budget that causes idle spin, (2) sitting on an 868-note unprocessed pickup backlog (Claw→Claude handoff broken — Claude must triage), and (3) skewed toward feed-blocked VALUE/CARRY. This request re-aims it: frequency-first, testable-now daily mechanisms, feed-blocked → Lever-B queue. Recommend raising the note budget for this harvest sprint.
