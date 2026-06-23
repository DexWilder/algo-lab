# Mechanism Library — Forge Hypothesis Lane

> Standing parallel lane (opened 2026-06-23). The validation engine is strong; the bottleneck is **ore quality**. This lane mines trading books / research into **buildable, testable Forge mechanism packets** — NOT summaries, NOT copied systems. Translate principles into modern packets tailored to our reachable data + micro-futures/crypto universe. Report-only; capital gate unchanged.

## Packet schema (every packet)
`mechanism` · `forced participant / behavioral reason` · `required data` · `instruments` · `expected direction` · `cadence` · `no-lookahead risks` · `cheap-screen plan` · `kill criteria` · `likely sleeve class` (workhorse / tail-engine / overlay-filter / carry) · `data reachability` (HAVE / REACHABLE / BLOCKED) · `priority` (1-5; = reachability × mechanism strength × portfolio-fit × non-redundancy).

## Workflow
Extract → score → queue HAVE+priority≥4 for cheap-screen → cheap-screen → {KILL | WATCH | STRUCTURE_FOUND → full gate}. Each book targets 10-25 packets. Do not force breadth; a sharp 12 beats a padded 25.

## Reachable-data crib (for "required data" feasibility)
HAVE: 5m futures (MNQ/MES/MGC/MCL/MYM/M2K, some 6J/6E/6B, ZN/ZF/ZB), VIX daily, DVOL daily, COT (CFTC), treasury auctions (TreasuryDirect), SOFR/EFFR/DFF/RRP/WALCL (FRED+NYFed), yield curve, copper-gold, energy spot/futures, credit OAS, CPI, dollar index, inflation-expectations, policy rates, Deribit funding/perp/options-chain-snapshot, Coinbase/Kraken spot. REACHABLE (probe): VX futures term structure (Yahoo), index reconstitution calendars, OPEX/expiry calendars, SOMA holdings (NYFed). BLOCKED: live order book / L2, single-name options, tick data, Binance/Bybit.

---

# Book 1 — Larry Harris, *Trading and Exchanges* (market microstructure)
Theme: identify **predictable / forced / constrained** participants whose flow is mechanical, then trade the price pressure they create. Harris's taxonomy (utilitarian vs informed vs parasitic; liquidity demanders vs suppliers) maps directly to forced-flow packets. We can't see the order book, so we target flows whose TIMING is calendar/rule-driven and whose footprint shows in price/volume.

### H1 — Index reconstitution forced rebalance *(priority 5)*
- **mechanism:** index funds must buy adds / sell deletes at/near the effective date → mechanical price pressure into the close of reconstitution day; partial reversal after.
- **forced participant:** passive index funds (utilitarian, price-insensitive, deadline-bound).
- **required data:** S&P/Nasdaq reconstitution effective dates (REACHABLE); MES/MNQ/M2K 5m (HAVE). **instruments:** MES/MNQ/M2K (index-level pressure; single names blocked but index-level drift is testable). **direction:** pre-effective drift in index in direction of net add/delete imbalance; fade the close-day overshoot. **cadence:** quarterly (Mar/Jun/Sep/Dec 3rd Fri) + annual Russell (Jun). **no-lookahead:** announcement vs effective date gap is public; use only post-announcement. **cheap-screen:** index return in the [announce→effective] window and the effective-day-close→next-day reversal vs baseline. **kill:** no drift/reversal beyond noise at index level (single-name effect may not aggregate). **sleeve:** tail-engine (event). **reachability:** REACHABLE. 
- *Note: index-level may wash out; the honest test is whether the aggregate imbalance is directional enough to move the future.*

### H2 — Closing-auction / MOC imbalance pressure *(priority 4)*
- **mechanism:** market-on-close orders concentrate at the cash close (16:00 ET); imbalances push the last minutes and mean-revert overnight.
- **forced participant:** index/benchmark-tracking funds forced to trade at official close.
- **required data:** MES/MNQ 5m intraday (HAVE). **instruments:** MES/MNQ. **direction:** late-day drift (15:45→16:00) continuation then partial overnight reversal; conditioned on the day's trend sign. **cadence:** daily. **no-lookahead:** use only bars up to decision time. **cheap-screen:** last-15-min return vs prior-hour, and overnight reversal of it; split by month-end / OPEX (bigger MOC). **kill:** no systematic late-day pressure after cost; effect is just momentum. **sleeve:** workhorse-ish / overlay. **reachability:** HAVE. 

### H3 — Futures roll forced flow (calendar roll pressure) *(priority 4)*
- **mechanism:** longs/shorts roll from front to next quarterly over the roll window (e.g., 8 days before expiry); mechanical calendar-spread pressure + front-month liquidity drain.
- **forced participant:** funds/CTAs with maturity mandates rolling on schedule (Goldman roll, etc.).
- **required data:** futures continuous + roll calendar (HAVE/REACHABLE). **instruments:** MES/MNQ/MCL/MGC. **direction:** calendar-spread drift during the canonical roll window; possible front-month softness. **cadence:** quarterly (energy monthly). **no-lookahead:** roll dates known. **cheap-screen:** calendar-spread return during roll window vs outside; front-month relative behavior. **kill:** no edge after spread execution cost. **sleeve:** carry/tail. **reachability:** HAVE for outrights; spread needs 2 contracts. 

### H4 — Margin-driven liquidation cascade *(priority 3)*
- **mechanism:** after a large adverse move, leveraged/weak holders hit margin calls → forced selling overshoots fair value → snapback.
- **forced participant:** over-levered specs (constrained, price-insensitive in the cascade).
- **required data:** futures intraday (HAVE); leverage proxy via COT spec positioning extremes (HAVE). **instruments:** MCL/MGC/MNQ (high-leverage venues). **direction:** after N-sigma down day WITH stretched spec longs (COT) → long snapback. **cadence:** episodic/tail. **no-lookahead:** COT released Fri for Tue; lag it. **cheap-screen:** forward return after (big down move × COT spec-long extreme) vs big-down-move alone (does positioning add?). **kill:** snapback no better than unconditional post-selloff bounce (the O2 trap — must beat the dip-buy control). **sleeve:** tail-engine. **reachability:** HAVE. 
- *Apply the O2 lesson: must beat the generic post-selloff rebound control to earn its keep.*

### H5 — COT positioning-extreme reversal (commercials vs large specs) *(priority 4)*
- **mechanism:** when large specs reach a positioning extreme while commercials take the other side, the spec crowd is "forced" by eventual exhaustion → mean-reversion. Classic Harris informed (commercial hedger) vs uninformed-trend (spec) dichotomy.
- **forced participant:** trend-following large specs at saturation.
- **required data:** COT (HAVE), futures price (HAVE). **instruments:** MGC/MCL/6E/6J/ZN (deep COT). **direction:** fade spec extreme (short when specs max-long vs commercial max-short). **cadence:** weekly. **no-lookahead:** COT Tue snapshot released Fri → only actionable from Fri close. **cheap-screen:** forward 1-4wk return conditioned on spec z-score extreme; per-asset. **kill:** no reversion / not robust across the COT band / contributes via one asset. **sleeve:** tail/carry. **reachability:** HAVE. 

### H6 — Time-of-day liquidity regime (open trend / lunch revert / close) *(priority 4)*
- **mechanism:** liquidity & participant mix vary intraday — informed flow at open, thin uninformed "lunch" chop, benchmark flow at close. Harris: liquidity suppliers widen when adverse-selection risk is high.
- **forced participant:** time-segmented (open=informed momentum; midday=noise mean-revert).
- **required data:** 5m futures (HAVE). **instruments:** MNQ/MES/MGC. **direction:** open-range continuation (already in ORB family); midday (11:30-13:30 ET) mean-reversion of morning move. **cadence:** daily. **no-lookahead:** intraday only. **cheap-screen:** midday reversal of AM move; PF by session bucket. **kill:** no session-specific edge beyond ORB. **sleeve:** workhorse. **reachability:** HAVE. *Partly explored via ORB; midday-revert is the fresh angle.*

### H7 — Round-number / psychological magnet *(priority 2)*
- **mechanism:** orders cluster at round numbers (Harris: clientele/tick effects) → magnet then rejection.
- **forced participant:** retail limit-order clustering + stop placement.
- **required data:** 5m futures (HAVE). **instruments:** MGC (1000s), MNQ (100s). **direction:** approach-and-pin vs break-through continuation. **cadence:** daily. **no-lookahead:** intraday. **cheap-screen:** behavior of price near round levels vs random levels. **kill:** no statistical magnet/rejection. **sleeve:** overlay. **reachability:** HAVE. *Low priority — easy to fool yourself.*

### H8 — Stealth-trading volume footprint (informed accumulation) *(priority 3)*
- **mechanism:** informed traders split orders to hide; abnormal sustained volume w/o news → informed accumulation → continuation (Harris order-anticipation).
- **forced participant:** informed traders leaking footprint via volume.
- **required data:** 5m futures price+volume (HAVE). **instruments:** MCL/MGC/MNQ. **direction:** abnormal volume-cluster + small price move → continuation in cluster direction. **cadence:** daily/intraday. **no-lookahead:** rolling volume baseline, no future bars. **cheap-screen:** forward return after volume z-spike with low contemporaneous range. **kill:** volume spikes are just news/vol, no continuation edge. **sleeve:** workhorse. **reachability:** HAVE. 

### H9 — Short-sale constraint / squeeze (crypto funding analog) *(priority 3)*
- **mechanism:** when shorting is constrained/expensive (deep negative funding in perps), forced short-covering squeezes price up (Harris short-sale constraint chapter).
- **forced participant:** trapped shorts paying to stay short. **required data:** Deribit funding (HAVE). **instruments:** BTC/ETH perp (directional) — links to C1 (KILLed directional) but the SQUEEZE (extreme-negative funding only) sub-case wasn't isolated. **direction:** extreme NEGATIVE funding → long squeeze. **cadence:** episodic. **no-lookahead:** funding known at period start. **cheap-screen:** forward return after deep-negative-funding extreme only (not symmetric). **kill:** no squeeze asymmetry (C1 found symmetric mean-rev fails; test if neg-tail alone differs). **sleeve:** tail. **reachability:** HAVE. 

### H10 — Quarterly expiry settlement pressure (cash-settled index) *(priority 3)*
- **mechanism:** triple-witching settlement forces unwinds/rolls of futures+options hedges → concentrated flow at quarterly settle.
- **forced participant:** hedgers/arbs unwinding at settlement. **required data:** 5m MES/MNQ + expiry calendar (HAVE/REACHABLE). **instruments:** MES/MNQ. **direction:** settle-day open/close behavior + post-expiry drift release. **cadence:** quarterly. **no-lookahead:** calendar. **cheap-screen:** expiry-day & day-after returns vs baseline. **kill:** no post-expiry drift after cost. **sleeve:** tail. **reachability:** HAVE+REACHABLE. *Links to OPEX work already done — extend to settlement specifically.*

### H11 — Liquidity-supplier withdrawal around scheduled news *(priority 4)*
- **mechanism:** market makers widen/withdraw before scheduled releases (adverse-selection spike) → thin pre-release tape → exaggerated move on release → fade or follow. Harris adverse-selection.
- **forced participant:** liquidity suppliers protecting against informed flow. **required data:** 5m futures + econ calendar (HAVE/REACHABLE). **instruments:** ZN/MNQ/MGC around FOMC/CPI/NFP. **direction:** pre-release drift suppression + release-bar impulse continuation/fade. **cadence:** event. **no-lookahead:** calendar. **cheap-screen:** realized range pre vs post release; impulse follow-through. **kill:** subsumed by existing event sleeves / no edge. **sleeve:** tail-engine. **reachability:** HAVE. *Coordinate with FOMC/rates sleeves to avoid double-count.*

### H12 — Order-anticipation of predictable benchmark flow (month-end) *(priority 4)*
- **mechanism:** month-end index/bond rebalancing & pension flows are predictable → anticipators front-run → drift into month-end. Harris order-anticipators (parasitic but informative).
- **forced participant:** pensions/balanced funds rebalancing to targets at month-end. **required data:** 5m futures (HAVE). **instruments:** MES/MNQ (equity inflow), ZN/ZF (bond rebalance). **direction:** month-end drift sign conditioned on the month's equity/bond relative move (rebalancers sell winners/buy losers). **cadence:** monthly. **no-lookahead:** month's return known by last 1-2 days. **cheap-screen:** last-2-day return conditioned on intra-month equity-bond divergence. **kill:** no rebalance drift after cost. **sleeve:** tail/overlay. **reachability:** HAVE. *Links to month-end rates sleeve already noted.*

---

# Book 2 — Natenberg *Option Volatility and Pricing* + Sinclair *Volatility Trading*
Theme: the **variance risk premium** and **vol dynamics** create systematic, behaviorally-driven edges. We can't trade single-name options (BLOCKED), but vol-as-signal and VIX/VX-term-structure-as-instrument ARE reachable. KEY LESSON from O1/O2: a vol signal must beat equity-native controls (VIX/RV/dip) — bake the incremental-value test into every cheap-screen.

### N1 — VIX-futures term-structure carry (contango roll-down) *(priority 5)*
- **mechanism:** VIX futures are usually in contango; longs in vol decay toward spot as time passes → short-vol carry (Sinclair's core VRP harvest, the tradable version). Backwardation = stress regime.
- **forced participant:** structural hedgers (over)paying for protection → vol sellers earn the premium.
- **required data:** VX futures term structure (REACHABLE via Yahoo ^VIX + VX or VXX/SVXY proxies); VIX (HAVE). **instruments:** VX futures / vol ETPs (check tradability) — or express as a regime signal for equity. **direction:** contango steep → short-vol bias / risk-on for equity; backwardation → risk-off. **cadence:** daily. **no-lookahead:** term structure known at close. **cheap-screen:** equity forward return conditioned on VX term-structure slope (contango vs backwardation); and slope as standalone carry. **kill:** slope adds nothing beyond VIX level; carry dies after roll cost. **sleeve:** carry/overlay. **reachability:** REACHABLE (probe VX data). 
- *The honest tradable form of the VRP that O1 couldn't harvest in crypto — here the instrument exists.*

### N2 — VIX term-structure SLOPE as equity regime filter *(priority 4)*
- **mechanism:** backwardation (front VX > back) signals acute stress / capitulation; contango = calm. Slope is a cleaner risk-state than VIX level (Sinclair).
- **forced participant:** crash-hedging demand inverting the curve. **required data:** VX term structure (REACHABLE). **instruments:** overlay on MES/MNQ/MGC sleeves. **direction:** backwardation → mean-revert/risk-off filter; contango → risk-on. **cadence:** daily. **no-lookahead:** EOD slope. **cheap-screen:** does slope-regime improve workhorse bad-day avoidance BETTER than VIX level? (apply O2-overlay method head-to-head). **kill:** no improvement over VIX level. **sleeve:** overlay-filter. **reachability:** REACHABLE. 

### N3 — VIX mean-reversion from extremes *(priority 3)*
- **mechanism:** VIX is strongly mean-reverting; extreme spikes revert (vol clusters then decays — Natenberg/GARCH). **forced participant:** panic protection buyers at the spike. **required data:** VIX (HAVE). **instruments:** equity (long after VIX spike) — BUT this is exactly the O2 mechanism; **must beat the dip-buy/prior-day control or it's redundant.** **direction:** VIX spike → forward equity up. **cadence:** episodic. **no-lookahead:** VIX EOD. **cheap-screen:** forward equity return after VIX z-extreme, controlled for prior-day return (marginal regression, as in O2-refine). **kill:** marginal t<2 vs controls (LIKELY — O2 already suggests this). **sleeve:** tail. **reachability:** HAVE. *Low-ish priority: probably redundant with O2 findings; included for completeness/closure.*

### N4 — Implied-vs-realized vol premium as position-SIZING overlay *(priority 4)*
- **mechanism:** when IV >> RV (rich premium), forward vol tends to fall → favorable for risk-taking; when RV > IV, de-risk. Sinclair vol-timing. Use as a SIZING/throttle overlay on existing workhorses, not a standalone.
- **forced participant:** systematic vol underwriters. **required data:** VIX (IV proxy) + realized vol from futures (HAVE). **instruments:** sizing overlay on MNQ/MES/MGC ORB. **direction:** scale exposure up when IV-RV rich & falling, down when RV spiking. **cadence:** daily. **no-lookahead:** both EOD. **cheap-screen:** does IV-RV-scaled sizing improve workhorse Sharpe/DD vs flat sizing? **kill:** no risk-adjusted improvement. **sleeve:** overlay-filter (sizing). **reachability:** HAVE. *High portfolio-fit: sizing overlays apply to deployed books.*

### N5 — Put-skew as crash-fear contrarian gauge *(priority 3)*
- **mechanism:** steep put skew = expensive crash insurance = fear; extreme skew often contrarian-bullish (Sinclair skew dynamics). **forced participant:** tail-hedgers bidding puts. **required data:** skew proxy — SKEW index (REACHABLE via CBOE?) or Deribit option-chain snapshot skew (HAVE snapshot only, no history). **instruments:** equity (CBOE SKEW) / BTC (Deribit). **direction:** extreme skew → contrarian long. **cadence:** daily. **no-lookahead:** EOD. **cheap-screen:** forward return after skew extreme vs VIX control. **kill:** redundant with VIX/no history. **sleeve:** tail. **reachability:** REACHABLE (CBOE SKEW) / BLOCKED-history (Deribit). 

### N6 — Event vol crush (FOMC/CPI implied-vs-realized) *(priority 4)*
- **mechanism:** implied vol bid into scheduled events, crushes after → the realized move usually < implied (Natenberg event pricing). **forced participant:** event-hedgers overpaying pre-event. **required data:** VIX + futures realized around event dates (HAVE) + econ calendar (REACHABLE). **instruments:** MES/MNQ/ZN around FOMC/CPI/NFP. **direction:** post-event vol-crush → short-vol/risk-on drift; pre-event range compression. **cadence:** event. **no-lookahead:** calendar. **cheap-screen:** post-event realized vs pre-event implied; forward drift. **kill:** subsumed by existing FOMC sleeves. **sleeve:** tail-engine. **reachability:** HAVE. *Coordinate with FOMC family to avoid double-count.*

### N7 — Vol-of-vol (VVIX) extreme as equity timing *(priority 2)*
- **mechanism:** VVIX (vol of VIX) extremes mark peak uncertainty → contrarian. **required data:** VVIX (REACHABLE?). **instruments:** equity overlay. **direction:** VVIX spike → forward equity up. **cadence:** episodic. **no-lookahead:** EOD. **cheap-screen:** marginal value beyond VIX. **kill:** redundant w/ VIX (likely). **sleeve:** tail/overlay. **reachability:** REACHABLE (probe). *Low priority.*

### N8 — Realized-vol clustering / GARCH regime throttle *(priority 4)*
- **mechanism:** vol clusters (high vol begets high vol); a GARCH/EWMA regime label gates strategy participation (Sinclair). **forced participant:** n/a (statistical) — but vol regime governs which sleeves work (momentum in trending-vol, MR in stable-vol). **required data:** futures returns (HAVE). **instruments:** regime overlay on all. **direction:** enable momentum sleeves in expanding-vol, MR/carry in compressing-vol. **cadence:** daily. **no-lookahead:** EWMA causal. **cheap-screen:** does vol-regime gating improve workhorse PF/DD? (head-to-head vs VIX regime). **kill:** no improvement vs simpler VIX filter. **sleeve:** overlay-filter. **reachability:** HAVE. *Validated pattern already (MGC low-vol exclusion) — generalize.*

### N9 — Weekend/overnight vol decay (theta calendar) *(priority 3)*
- **mechanism:** option time-decay over weekends/holidays is anticipated → vol sellers position; underlying often drifts in low-vol holiday windows (Natenberg theta). **forced participant:** vol sellers harvesting weekend theta. **required data:** futures intraday + holiday calendar (HAVE). **instruments:** MES/MNQ pre-holiday/weekend. **direction:** low-vol pre-holiday drift (risk-on grind). **cadence:** calendar. **no-lookahead:** calendar. **cheap-screen:** pre-holiday/Friday→Monday drift & range vs baseline. **kill:** no calendar edge after cost (C5 crypto-weekend KILLed — equity may differ). **sleeve:** tail/overlay. **reachability:** HAVE. 

### N10 — Term-structure backwardation as capitulation-reversal trigger *(priority 4)*
- **mechanism:** when VX curve inverts hard (acute panic), it marks near-term capitulation → strong forward equity returns (Sinclair stress regime). The sharper-edged cousin of N3, conditioned on curve not level.
- **forced participant:** forced de-grossing / crash hedging at the inversion. **required data:** VX term structure (REACHABLE). **instruments:** MES/MNQ. **direction:** deep backwardation → forward long. **cadence:** episodic/tail. **no-lookahead:** EOD slope. **cheap-screen:** forward return after backwardation extreme, controlled vs VIX level + prior-day (incremental test). **kill:** redundant with VIX level. **sleeve:** tail-engine. **reachability:** REACHABLE. 

---

## Cheap-screen queue (HAVE + priority≥4, ranked)
1. **N1** VIX-futures term-structure carry — *probe VX data first (REACHABLE→HAVE)*; highest if data lands.
2. **H5** COT positioning-extreme reversal (HAVE, deep COT) — clean forced-flow, weekly cadence.
3. **N4** IV-RV sizing overlay (HAVE) — high portfolio-fit, applies to deployed books.
4. **H1** Index reconstitution forced rebalance — needs calendar (REACHABLE).
5. **H2** MOC/closing imbalance (HAVE) — daily, intraday.
6. **H12** Month-end rebalance drift (HAVE) — links to existing month-end work.
7. **N8** Vol-regime throttle (HAVE) — generalize the proven MGC low-vol exclusion.
8. **H11** Pre-news liquidity withdrawal (HAVE) — coordinate w/ event sleeves.
9. **H4** Margin liquidation cascade (HAVE) — *must beat post-selloff control (O2 lesson)*.
10. **H6** Midday mean-reversion (HAVE).

Every vol-derived packet (N3/N10/H4) carries the **mandatory incremental-value test** (marginal regression vs VIX/prior-day/RV) baked into its cheap-screen — the O1/O2 lesson, so we don't re-discover a redundant signal.

## Boundaries
Report-only; no promotion/wiring/scheduler/registry/portfolio mutation. Packets are hypotheses, not candidates, until cheap-screened.
