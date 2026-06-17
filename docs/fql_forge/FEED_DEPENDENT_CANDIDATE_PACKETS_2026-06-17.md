# Feed-Dependent Candidate Packets — 2026-06-17

> **Priority reflects expected research leverage and feed availability only; it is NOT a ranking of edge, expectancy, or deployability.** Every packet below is ZERO-EVIDENCE until its real feed is joined and screened. P1/P2 are the highest-priority *daily-WH2 feed-unlock candidates*, not the strongest strategies. P3 is the first *executable feed cycle* because the Treasury CSV is closest, not because edge is presumed. P4–P7 are staged by frequency, feed accessibility, and driver diversity — again, not by edge.

> State: `LEVER_B1_FEED_GATED_NOT_IDLE`. Report-only packetizing while feed-gated — **hypotheses + test plans, NOT results.** No strategy screens run here; no synthetic data; no edge claims; no PASS/WATCH/KILL. Each packet runs ONLY once its required real feed lands. Frequency-first (mission = daily/near-daily WH2); sparse-event ideas catalogued but flagged off-target. Sourced from the 878-note backlog triage + the operator's priority feed families. In-house instruments: ZN/ZF/ZB, MGC, MCL, 6E/6J/6B(2024+), ES/MES/MNQ/MYM/M2K.

Per-packet fields: mechanism · required feed · join key/timestamp · instruments · min sample · no-lookahead risks · cheap-screen plan · kill criteria.

---

## TIER 1 — highest cadence / highest WH2 unlock potential

### P1 — Rates rolldown-carry tenor selection (RATES CARRY/CURVE)
- **Mechanism:** Daily, rank ZN/ZF/ZB by estimated carry+rolldown (yield + roll down the curve − financing); hold long the richest-carry tenor (optionally short the poorest), rebalance on signal change. Directional/relative rates exposure driven by curve shape, not price momentum.
- **Required feed:** per-tenor yields + the curve (CMT or par yields) OR multi-contract futures (F1/F2 per tenor) to compute roll; daily.
- **Join key/timestamp:** daily date; yield as-of prior close joined to next-session futures bar (strictly prior).
- **Instruments:** ZN, ZF, ZB.
- **Min sample:** ≥5y daily, ≥2 distinct rate regimes (hiking + easing).
- **No-lookahead risks:** using same-day settle yield to position same day; vintage/revision of curve data; roll-window contamination.
- **Cheap-screen plan:** compute carry signal from prior-day curve → next-day position; cost-aware; daily PnL; full board + corr to MNQ + ZN/ZF/ZB internal corr (avoid 3× same trade).
- **Kill criteria:** PF ≤1.2 cost-aware; H1/H2 not both >1.0; edge only in one rate regime (regime-dependent like the gold gate → demote); concentration top-3 ≥30%.

### P2 — Curve steepener/flattener directional state (RATES CURVE)
- **Mechanism:** Daily 2s10s (or 5s30s) slope state; trade ZN/ZB directionally (or as a duration-balanced spread) on steepening/flattening momentum or mean-reversion of the slope.
- **Required feed:** 2y/5y/10y/30y yields daily (or ZT/ZF/ZN/ZB — note ZT not in-house).
- **Join key/timestamp:** daily; slope as-of prior close.
- **Instruments:** ZN, ZB (ZF), duration-balanced.
- **Min sample:** ≥5y; both bull and bear steepenings present.
- **No-lookahead risks:** same-day slope to trade same day; spread leg timestamp mismatch.
- **Cheap-screen plan:** slope state (prior day) → next-day position; test momentum vs reversion of slope separately; board + corr.
- **Kill criteria:** as P1; plus reject if it degenerates into rate momentum (already killed) — must add value over single-tenor trend.

### P3 — Treasury auction concession→reversion (AUCTION) [WP-B1, feed nearly in hand]
- **Mechanism:** Per auction, by tenor: pre-auction concession short (T−2→T0) and/or post-auction reversion long (T0→T+2) on the matched tenor; 10y→ZN, 5y→ZF, 30y→ZB.
- **Required feed:** Treasury auction calendar + results (auction_date, tenor, type, bid-to-cover, high-yield). **This is the active WP-B1 feed → `data/feeds/treasury_auctions.csv`.**
- **Join key/timestamp:** auction_date (strictly-prior merge_asof to bars, like the cross-asset harness); auction time ~13:00 ET for intraday variants.
- **Instruments:** ZN, ZF, ZB.
- **Min sample:** ≥40 auctions/tenor (≥5y).
- **No-lookahead risks:** auction RESULT (bid-to-cover/high-yield) known only post-auction — must not gate the pre-auction leg on it; calendar staleness; reopening vs original mislabeling.
- **Cheap-screen plan:** the locked WP-B1 sequence (validate → no-lookahead audit → join audit → coverage → first-10 → board).
- **Kill criteria:** PF ≤1.2 cost-aware; concentration by year/tenor; edge only at one tenor or one era.

### P4 — EIA inventory-surprise gated crude (EIA INVENTORY)
- **Mechanism:** Weekly EIA petroleum status: actual draw/build vs consensus (or vs 5-yr seasonal). Surprise draw → long MCL into/through settlement; surprise build → short. Optional curve gate (F1-F2 backwardation confirms).
- **Required feed:** EIA weekly crude stocks (Wed 10:30 ET) + consensus or 5-yr-average baseline.
- **Join key/timestamp:** release datetime (Wed 10:30 ET, holiday-shifted); strictly at/after release.
- **Instruments:** MCL.
- **Min sample:** ≥150 weekly releases (≥3y); ~52/yr (near-daily-ish cadence).
- **No-lookahead risks:** consensus must be the pre-release vintage; holiday shifts; using the revised number.
- **Cheap-screen plan:** surprise sign (at release) → intraday/through-settlement hold; cost-aware (MCL cost-fragile — explicit cost ratio); board.
- **Kill criteria:** cost ratio eats edge (MCL history); concentration; PF ≤1.2; works only without curve gate (then it's just EIA-drift, re-check vs prior EIA WATCH-LOW).

---

## TIER 2 — monthly/event cadence, distinct driver

### P5 — CPI surprise-conditioned gold↔rates (CPI / INFLATION SURPRISE) [revives #T12 correctly]
- **Mechanism:** CPI MoM surprise vs consensus (hot → long MGC / short ZN; cool → long ZN), held to next release or N days. The inflation-DRIVER version of #T12 (which died as a date-only proxy).
- **Required feed:** BLS CPI MoM actual + consensus (point-in-time). **Note: in-house calendar has dates only — VALUES are the unlock.**
- **Join key/timestamp:** release datetime (08:30 ET); strictly at/after.
- **Instruments:** MGC, ZN.
- **Min sample:** ≥60 releases (≥5y); 12/yr (monthly — flag: not daily; only WH2-relevant if it anchors a broader inflation-regime daily sleeve).
- **No-lookahead risks:** consensus vintage; revised CPI; same-day-close gating.
- **Cheap-screen plan:** surprise sign → directional hold; compare gold leg / rates leg / rotation separately; board.
- **Kill criteria:** PF ≤1.2; works only on outright not surprise (then it's trend, not inflation-driver); cadence too sparse to matter for WH2 → reclass to event sleeve.

### P6 — FX policy-rate-differential carry, USD/JPY (FX CARRY)
- **Mechanism:** Monthly: Fed−BoJ policy-rate spread state (wide + widening → short 6J / USD-strong); continuous position. Canonical FX carry driver.
- **Required feed:** FRED FEDFUNDS + BoJ policy rate (monthly), or OIS.
- **Join key/timestamp:** month-end rate as-of prior month; strictly prior.
- **Instruments:** 6J (6E for EUR variant) — **caveat: 6J/6E in-house only 2024+ (short history).**
- **Min sample:** ≥10y ideally — blocked by short in-house FX history → would need extended 6J futures or spot proxy.
- **No-lookahead risks:** rate-change announcement timing; month-end look-ahead; short sample over-fit to 2024+ regime.
- **Cheap-screen plan:** spread state (prior month) → monthly position; board; **explicit short-sample caveat**.
- **Kill criteria:** insufficient sample (likely, given 2024+); single-regime; PF ≤1.2.

---

## TIER 3 — sparse event (catalogue; OFF-TARGET for daily WH2)

### P7 — OPEC decision continuation, crude (OPEC EVENT)
- **Mechanism:** OPEC/OPEC+ decision (cut/hold/raise) → MCL impulse hold through settlement / next session.
- **Required feed:** OPEC decision calendar + outcomes (~8-10/yr).
- **Join/instruments/risks:** decision datetime → MCL; headline-timing/scheduled-vs-emergency risk.
- **Min sample:** ~50 events over 7y — **sparse**; tail-engine archetype, not workhorse.
- **Cheap-screen plan / kill:** event-window board; kill if concentration high or n insufficient. **Flag: sparse → not WH2; only catalog.**

---

## Priority for when feeds arrive (research leverage + feed access — NOT edge)
1. **P3 Treasury auctions** — first executable cycle because the CSV is closest, not because edge is presumed.
2. **P1/P2 rates carry/curve** — highest *daily-WH2 feed-unlock* potential; needs curve/multi-contract feed. Zero-evidence until screened.
3. **P4 EIA crude** — near-daily, distinct energy driver, cheap public feed.
4. **P5 CPI surprise** — revives #T12 with real values; monthly.
5. **P6 FX carry** — distinct driver but short in-house FX history (sample-blocked).
6. **P7 OPEC** — sparse, catalog only.

Feed acquisition instructions for each (exact source / drop path / schema): see `LEVER_B_QUEUE_2026-06-16.md` → "Feed delivery".

## Boundaries
Packets only. No screens, no synthetic data, no edge claims, no labels, no mutation. Each runs only once its real feed exists. Archive of dead/blocked in-house mechanisms unchanged (no circular rediscovery).
