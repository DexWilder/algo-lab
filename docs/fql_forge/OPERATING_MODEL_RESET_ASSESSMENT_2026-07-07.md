# Operating-Model Reset Assessment (2026-07-07)

> Evidence-backed diagnosis of why progress stalled, and an executable reset. Grounded in the real ledger, not generic advice.

## Evidence base (measured, this repo)
- 1,856 trials — but **1,391 are backfilled "no_edge_inferred" from the old primitive sweep.** Real recent labeled research ≈ **~100 trials** across interesting lanes (databento_volume 57, exploratory 14, commodity_carry 10, carry/curve/macro/crypto ~12).
- **Yield of the entire effort: 1 SCREEN_PASS diversifier (spreadMR_GC) + 1 validated regime ingredient (GEX compression). 0 workhorses.**
- **371 infra scripts, 210 edge-test scripts, 157 docs, ~95 memory files, 10 source-derived packets ever.**
- Markets: MNQ/MES/MYM/M2K/MGC/MCL/ZN got ~250 trials each (mostly the dead primitive sweep); **FX 6E/6J/6B got 6 each; NG/crypto barely touched natively.**
- Failure taxonomy (recent): concentration 23, no_edge 13, dsr_searchN 9. Almost nothing dies of cost/artifact now (caught pre-test).

## Step 1 — Diagnosis (blunt)
The historical ORB-obsession (#1) **is already fixed** — we tested carry, gamma, auction, microstructure, cross-index. That's not the current failure. The real failure modes, in priority:
- **(#7/#6) INVERTED FUNNEL — the #1 problem.** 371 infra scripts to produce ~100 real trials → 1 diversifier. We built an institutional-grade *validator* and feed it a hobbyist-grade *idea funnel*. Elite labs test thousands cheaply; we test ~10 mechanisms with heavy per-mechanism ceremony.
- **(#4/#9) DATA is the binding constraint on the mechanisms that matter.** Forced-flow edges (ETF create/redeem, fund rebalance, real event-surprise, gamma full history, roll flow) need flow data we don't have. We keep hitting "sample-too-short / data-blocked" on exactly the non-arbed mechanisms.
- **(#2) Structural sample-size squeeze.** Big-n mechanisms (ORB/MR/trend, 1000s of days) are arbed/dead; interesting mechanisms (GEX 166d, auction 255d) are too sparse to clear DSR. We're pinched between "dead" and "too-thin."
- **(#3) External harvesting essentially absent** — 10 source packets *ever*, ~95% internally generated. Novelty is finite (a 108-combo template space).
- **(#5) Market breadth is illusory** — 12 instruments "tested" but with the *same* dead primitive sweep. No instrument-*native* mechanism discovery for NG, FX, crude, crypto.
- **Not the failure:** validation rigor, over-filtering-per-se, portfolio testing. Those are fine or absent-but-secondary.

**One sentence:** *We over-engineered the kill-machine and under-fed the idea/data funnel; the constraint is DATA + BREADTH + EXTERNAL SOURCING, not validation or process.*

## Step 2 — Keep / Modify / Kill
**A. KEEP (real assets, protect):** the validation stack (causality audit, layered DSR, expression/data validators, artifact detectors, adversarial review) — it *worked*: caught alignment bugs, forced a retraction, refused to promote 3× on GEX. Org memory (inbound/ledger/family-map/dashboard/self-audit) — nothing floats. The 2 validated assets (spreadMR_GC diversifier; GEX regime ingredient). Durable provider-retry pattern.
**B. MODIFY:** novelty engine (finite templates → external-source-fed); trial ledger (make it the mineable meta-DB it's meant to be); mission classification (good, keep enforcing); cheap-screen (exists but per-mechanism, needs to become a broad factory).
**C. KILL / STOP:** (1) building MORE validation/org infrastructure — we have 371 scripts and 157 docs, that's the disease not the cure; (2) re-testing OHLCV/session transforms of index micros — that well is empirically dry; (3) per-mechanism deep-ceremony on sparse data before breadth; (4) treating "12 instruments" as breadth when it's one sweep replicated.

## Step 3 — Reset decision: **PARTIAL RESET.**
Not "no" (the generation funnel is structurally too narrow to fix by broadening alone). Not "full" (the validator + org memory + 2 assets are genuine, hard-won, and rare — throwing them out repeats years of work). **Keep the validated assets and the kill-machine; rebuild the research *factory* — generation, breadth, and DATA — from a blank sheet.** The factory is what's broken; the validator is what's good.

## Step 4 — New alpha factory (throughput-first, ceremony-last)
1. **Mechanism harvest** (external + forced-flow map) → 2. **Source mining** (papers/exchange/GitHub → mechanism, not indicator) → 3. **Data acquisition** (the gate; see Step 9) → 4. **Hypothesis packet** (forced participant / timing / data-tier / expression / kill / expected-failure) → 5. **Cheap-screen template** (mechanism × window × instrument × filter × exit × cost — *batch of 50-200*, not 1) → 6. **Robustness gate** (H1/H2, per-year, cross-instrument) → 7. **OOS** (frozen, held-out years) → 8. **Cost/execution** (real spread from bbo-1m) → 9. **Portfolio contribution** (corr to spreadMR_GC + existing; add only if it diversifies) → 10. **Paper packet** → 11. **Archive/lesson** (meta-DB) → 12. **Daily/weekly cadence**. The shift vs today: **steps 1-5 run at 10-50× current volume; steps 6-11 stay as-is.**

## Step 5 — Forced-flow mechanism map (prioritized)
| Mechanism | Edge | Data | Instruments | Freq | Have? | Cheap screen | Artifact risk | Use |
|---|---|---|---|---|---|---|---|---|
| Opening auction | imbalance resolution | 1m | MES/MNQ/MYM | daily | ✅ | first-30m vs rest | session/tz | WH |
| Closing auction/MOC | index rebalance flow | 1m + MOC | index | daily | partial | last-15m→next | tested weak | WH |
| Stop runs | liquidity sweeps | 1m + depth | index/FX | intraday | ✅(1m) | wick-reversal | look-ahead | WH |
| **Dealer gamma/GEX** | hedging reflexivity | options OI | MES/MNQ | daily | ✅(weekly) | **DONE→regime ingredient** | OI staleness | regime layer |
| OPEX | expiry clustering | options OI | index | monthly | ✅ | OPEX-week vol | small-n | diversifier |
| Treasury auctions | dealer concession | TreasuryDirect | ZN/index | ~weekly | ✅ | tail/BTC→rates | regime-specific | diversifier |
| TSY month-end/settlement | duration extension | calendar | ZN/ZB | monthly | ✅(cal) | last-sessions | small-n | diversifier |
| Fed ops | rate/QT flow | Fed calendar | rates/index | event | partial | FOMC-window | small-n | diversifier |
| **Index rebalance** | reconstitution buy | rebal calendar | MES/M2K | quarterly | ❌ | rebal-day close | **need calendar** | WH candidate |
| **ETF create/redeem** | primary-market flow | ETF flow feed | index/sector | daily | ❌ | flow→next-day | **need feed** | WH candidate |
| Mutual-fund month-end | forced rebalance | flows/calendar | index/bonds | monthly | partial | month-end | small-n | diversifier |
| Pension rebalance | quarterly duration | proxy | equity/bond | quarterly | ❌ | quarter-end | proxy-only | diversifier |
| **Commodity roll** | ETF roll bleed | per-contract | CL/NG/GC | monthly | ✅ | roll-window | roll-gap | diversifier |
| EIA inventory | producer hedge | EIA API | CL/NG | weekly | ❌(free key) | surprise→CL | consensus gap | diversifier |
| OPEC events | supply shock | calendar | CL | event | ❌ | event-window | rare | diversifier |
| FX fixing (WMR) | benchmark flow | 1m | 6E/6J/6B | daily | ✅(1m) | 16:00-fix | tz/timing | diversifier |
| Crypto funding/liq | perp basis/cascade | funding+liq | BTC/ETH | 8h/intraday | partial | funding→spot | feed depth | diversifier |
| Vol-target/CTA flow | mechanical de/re-lever | vol proxy | index | daily | ✅(vix) | vol-spike→flow | reflexive | regime input |
| Corporate buyback | blackout windows | calendar | index | seasonal | ❌ | blackout | proxy | diversifier |
| Dividend/coupon reinvest | scheduled inflow | calendar | index/bonds | quarterly | partial | ex-div window | small-n | diversifier |
| Bond issuance | supply pressure | TreasuryDirect | ZN/ZB | event | ✅ | issue-window | overlap auction | diversifier |
**The pattern: the WH-candidate forced-flow mechanisms (index rebalance, ETF flow, closing-auction, stop-runs) are exactly the ones we lack DATA for.** That is the real gap.

## Step 6 — Market expansion (we ARE too concentrated in index+rates+gold)
- **Daily workhorses:** MES/MNQ/MYM/M2K (liquid, mean-revert + microstructure), MCL (energy trend/roll). **Native, not replicated sweep.**
- **Diversifiers:** MGC (gold carry — spreadMR_GC lives here), NG (seasonal/weather/roll — *untested natively*), ZN/ZF/ZB (carry/RV — done, mostly dead), CL (roll/inventory).
- **Event:** rates around auctions/Fed; index around OPEX/rebalance; CL around EIA.
- **Seasonal/flow:** NG (winter), grains (n/a), commodity rolls, FX fixing.
- **Carry/value:** rates curve (done), commodity term-structure (spreadMR_GC), FX carry (6E/6J/6B — **6 trials only, badly under-tested**), crypto funding.
- **Highest untapped-EV:** NG native (seasonality+roll, never done), FX carry+fixing (barely touched), crypto funding (barely touched), MCL native energy. **Action: instrument-native mechanism screens for NG, FX trio, crypto — not the index sweep re-run.**

## Step 7 — External harvesting (the biggest absence: 10 packets ever)
Per source → extract → hypothesis → anti-retail-filter:
- **Academic/SSRN/AQR/Man/Two-Sigma public:** extract the *mechanism + horizon + market*, not the backtest; require a forced-participant story; reject if it's an indicator with a curve-fit lookback.
- **Exchange (CME/ICE/CBOE) calendars/methodology:** roll schedules, settlement procedures, rebalance dates → directly testable forced-flow.
- **GitHub/QuantConnect:** mine for *data sources and mechanisms*, treat strategies as hypotheses to *disprove*, never copy (most are overfit retail).
- **Futures seasonality / options-structure / CTA-carry-value literature:** convert to predeclared packets.
- **Mechanism-vs-indicator test:** every harvested packet must name *who is forced to trade, when, and why they can't wait*. No forced-participant → reject as indicator-mining.

## Step 8 — Mass-screening engine (the throughput fix)
`mechanism → entry-window → instrument → filter → exit → risk → cost → validation-split`, generated in **batches of 50-200** per mechanism family. Targets: **~200 cheap screens/week** (vs ~10 now). Anti-snoop: pre-declared families + layered trial-N (already built) + mandatory DSR-at-full-N. **Dedup by return-stream correlation** (>0.9 corr to an existing survivor = "same trade, new name," drop). Cluster by (mechanism, instrument, holding-period). Keep only genuinely orthogonal return streams (corr < 0.5 to book).

## Step 9 — Feed-gate fix (research must not stop; acquire in priority order)
| Priority | Feed | Source | Cost | Min schema | Fallback proxy |
|---|---|---|---|---|---|
| 1 | Treasury auctions | TreasuryDirect API | free ✅DONE | date, BTC, high/median yield, indirect/direct | — |
| 2 | EIA inventory | EIA API (free key) | free (needs key) | date, actual, prior | actual-vs-AR-forecast proxy |
| 3 | Macro event calendar + surprise | scrape/vendor | low | date, time, actual, consensus | FRED actual + AR-forecast proxy |
| 4 | Fed operations | Fed calendar | free | FOMC/minutes/speakers dates | policy_rates (have) |
| 5 | **ETF flows** | vendor (paid) | $$ | daily create/redeem by fund | AUM-change proxy (weak) |
| 6 | Options gamma/OI full history | Databento ES.OPT | ~$ (chunked) | OI by strike/expiry | weekly OI (have, 563d) |
| 7 | Futures roll data | CME methodology | free | roll dates/ratios | per-contract (have) |
| 8 | Crypto funding/liquidation | Deribit/exchange APIs | free-ish | funding, liq levels | funding.csv (partial) |
**Rule:** feed-gated ⇒ run the proxy screen + queue the acquisition, never idle. Nothing is `DATA_BLOCKED` without a certificate.

## Step 10 — Promotion standards (thresholds)
- **Cheap-screen survivor:** Sh>0.5, PF>1.1, positive median, causal, n≥100.
- **Research candidate:** + robust across params, H1/H2 same sign, max-year<50%, cross-instrument OR clear single-market mechanism, **DSR≥0.95 at family-N**.
- **Review-track:** + OOS survives (held-out years), cost-degradation <30%, corr-to-book <0.5.
- **Paper-ready:** + execution realism (real spread), portfolio contribution positive, drawdown/MAR acceptable, operational plan.
- **Live-eligible:** + paper forward-confirm, operator + capital gate (always fail-closed).
**Hard gates:** DSR≥0.95 at defensible N; max-year<50%; corr-to-book<0.5; no candidate language before OOS.

## Step 11 — Cadence
- **Daily:** harvest 10-20 mechanism notes (external + map), convert 3-5 → packets, run cheap screens (batch), archive failures with failure_class, escalate survivors, close-the-step (learning hook), commit.
- **Weekly:** deep-validate survivors (robustness/OOS/cost/portfolio), review feed blockers + acquire next feed, update mechanism map, portfolio-gap review.
- **Monthly:** external research harvest sprint, market-expansion review, dead-zone audit, diversification audit, infra-freeze audit (kill stale scripts).

## Step 12 — 30-day reset plan (execution-weighted)
- **Week 1:** audit (this doc); freeze/prune the 371-script sprawl (archive one-offs); build the forced-flow mechanism map (done here); set up external-harvest queue; acquire feeds #2-4 (EIA/event-surprise/Fed — mostly free). *Deliverable: mechanism map + 2 new feeds live.*
- **Week 2:** build the mass-screen template (one generic runner, batches of 50-200); run first **broad multi-market native screens** — NG seasonal/roll, FX carry+fixing, crypto funding, MCL energy (the untapped markets). *Deliverable: ~200 screens across ≥6 markets.*
- **Week 3:** deep-validate survivors; portfolio-contribution test vs spreadMR_GC; dedup by correlation; apply the validated GEX regime filter to any surviving index entry; expand to forced-flow cluster (auction/rebalance/OPEX). *Deliverable: 1-3 research candidates or a clean "these markets are also dry" verdict.*
- **Week 4:** candidate packet(s) or honest null; failure archive; next-30-day roadmap; **explicit A/B: did the broad-native-screen + data-acquisition model outproduce the old deep-ceremony loop?** *Deliverable: go/no-go on the new factory.*

## Step 13 — Brutally honest
1. **What we're doing wrong:** validating like a hedge fund, generating like a hobbyist. 371 scripts, 10 source packets, 1 diversifier. We polish the killer and starve the funnel. And we keep re-testing the driest ground (index OHLCV/session transforms).
2. **Stop immediately:** building more infra/docs; re-running index price/volume sweeps; deep-ceremony on sparse single mechanisms before breadth; treating replicated sweeps as market breadth.
3. **Double down on:** the validation discipline (it works — keep it), the GEX regime ingredient, and above all **DATA acquisition + broad native multi-market screening**.
4. **Build next:** the generic mass-screen runner (batches, not one-offs) + acquire EIA/event-surprise/Fed feeds + the first NG/FX/crypto native screens.
5. **Fastest credible path:** *get the forced-flow/flow data we lack and screen it broadly across all markets* — non-arbed edge lives in flow data + under-tested markets (NG/FX/crypto), not in more index-price transforms. Data + breadth, not more cleverness on the same thin ground.
6. **Institutional version:** thousands of hypotheses/week across dozens of markets, rich flow/positioning/options data, automated broad screening, and a small validated survivor set — we already have the *survivor-validation* half (rare and good); we lack the *throughput + data* half.
7. **Next Claude run:** STOP the assessment/meta loop. (a) Prune/freeze infra; (b) acquire EIA + event-surprise proxy feeds (free); (c) build the generic batch-screen runner; (d) run the first broad native screen on the 3 most under-tested markets (NG, FX trio, crypto funding). Report screens-run, survivors, and whether new markets beat the index dead-zone.
