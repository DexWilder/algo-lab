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

---

# Batch-1 cheap-screen results (2026-06-23k/l)
Fast falsification on H5 + daily Harris microstructure. **Survivor: H5 COT-JPY→6J only.**
- **D1 stop-run reversal (daily):** KILL all (MNQ/MES PF 0.89, MGC 1.01). Next-day close-to-close fade of failed sweep doesn't work; reversal (if any) is intraday — archived.
- **D2 NR7-breakout (daily): KILL — was a CONSTRUCTION artifact, caught & resolved.** Daily-OHLC version PF 7-75 = (a) lookahead (used T+1 realized hi/lo to pick long/short direction) + (b) gap-through fill optimism (booked overnight gap as breakout profit). Proper intraday first-touch + realistic gapped fills → PF 0.996/1.11/1.02, dies at 8bps → KILL. **Lesson: breakout backtests on daily OHLC are lookahead traps; require intraday first-touch + gap-aware fills.**
- **D3 opening-drive continuation (daily):** KILL all (PF 0.87-1.07). Raw drive-continuation has no edge (ORB needs the ema_slope filter + ladder exit).
- **D4 MOC overnight reversal (daily):** MNQ WATCH (PF 1.219, H2 weak 1.086); MES/MGC KILL → NOT cross-asset robust → low priority.
- **H5 COT positioning reversal (weekly):** GOLD/EUR/SP500 KILL; CRUDE→MCL WATCH (H2 0.623 fails both-halves, lean KILL); **JPY→6J STRUCTURE_FOUND (PF 1.33, n=105, H1/H2 1.564/1.122, both halves hold)** → full-gate queued. JPY is a spec-driven carry currency — documented positioning edge; consistent with Harris informed-commercial vs uninformed-spec.

**Queued next:** full-gate COT-JPY→6J (concentration/cost/per-year/no-lookahead-COT-lag confirm); then batch-2 daily WH from Lehalle (below).

# Cadence classification (queue discipline)
Every packet tagged: **A** daily/high-cadence WH · **B** sparse-event ensemble · **C** overlay/filter · **D** feed-blocked · **E** validation/process.
Separate **WH queue (class A only)** kept below so sparse weekly/event ideas don't crowd out daily-workhorse discovery.

| Packet | Class | Status |
|---|---|---|
| H2 MOC imbalance, H6 midday-revert, H7 round-number, H8 stealth-volume, D-family | A | D1/D2/D3 KILL; D4 WATCH(MNQ); H2/H6/H8 un-screened |
| H1 reconstitution, H3 roll, H4 liquidation, H10 expiry, H11 pre-news, H12 month-end | B | un-screened |
| H5 COT | B | JPY STRUCTURE_FOUND, rest KILL/WATCH |
| H9 crypto squeeze | B | un-screened |
| N1 VX-carry, N2 slope-regime, N4 IV-RV sizing, N8 vol-throttle | C/A | un-screened (N1 needs VX probe) |
| N3/N5/N6/N7/N9/N10 vol packets | B/C | un-screened |

---

# Book 3 — Lehalle & Laruelle, *Market Microstructure in Practice* (execution / intraday liquidity)
Theme: temporary vs permanent price impact, order-flow dynamics, intraday liquidity seasonality. We have 5m (no L2), so target impact-reversion and signed-volume continuation — the **daily/high-cadence (class A) WH** the lane most needs.

### L1 — Large-print impact reversion *(class A, priority 5)*
- **mechanism:** a large trade pushes price beyond fair value (temporary impact); liquidity replenishes → partial reversion (Lehalle impact decay). **forced participant:** a metaorder demanding liquidity. **data:** 5m price+volume (HAVE). **instruments:** MNQ/MES/MGC/MCL. **direction:** after a volume-spike bar with outsized range, fade the impulse over next N bars. **cadence:** intraday/daily. **no-lookahead:** rolling volume/range baseline. **cheap-screen:** forward 30-60min return after a volume-z + range-z spike bar, fade direction; per asset, both halves. **kill:** impulse continues (permanent impact) or no edge after cost. **sleeve:** workhorse. **reachability:** HAVE.

### L2 — VWAP-deviation reversion *(class A, priority 5)*
- **mechanism:** price stretched far from session VWAP mean-reverts as execution algos lean against it. **forced participant:** VWAP-benchmarked execution (buys when below, sells when above). **data:** 5m (HAVE). **instruments:** MNQ/MES/MGC. **direction:** price >Nσ above intraday VWAP → fade short; below → long. **cadence:** intraday/daily. **no-lookahead:** VWAP from session bars up to now. **cheap-screen:** forward return after VWAP-zscore extreme intraday; both halves; cost. **kill:** no reversion / trend dominates. **sleeve:** workhorse. **reachability:** HAVE.

### L3 — Signed-volume / order-flow imbalance continuation *(class A, priority 4)*
- **mechanism:** trade-sign autocorrelation (Lehalle) — persistent same-side flow → short-horizon continuation. **forced participant:** metaorder splitting. **data:** 5m price+volume (HAVE; sign via tick-rule proxy on 5m close-to-close). **instruments:** MNQ/MES. **direction:** signed-volume imbalance over k bars → continuation next bars. **cadence:** intraday. **no-lookahead:** causal. **cheap-screen:** forward return conditioned on signed-volume-imbalance z; both halves. **kill:** no continuation after cost. **sleeve:** workhorse. **reachability:** HAVE (proxy).

### L4 — Intraday volatility seasonality (open/close vs midday) *(class A/C, priority 4)*
- **mechanism:** vol & spread are U-shaped intraday (Lehalle); strategies should size/select by time-of-day. **data:** 5m (HAVE). **instruments:** all. **direction:** momentum at open/close, mean-revert midday (links H6). **cadence:** daily. **no-lookahead:** time-of-day is exogenous. **cheap-screen:** per-bucket PF of momentum vs MR; confirm U-shape. **kill:** no exploitable session structure beyond ORB. **sleeve:** overlay/WH. **reachability:** HAVE.

### L5 — Overnight-gap fade vs follow *(class A, priority 4)*
- **mechanism:** overnight gap incorporates info; partial fade (liquidity provision at open) vs continuation depending on gap size. **data:** 5m (HAVE). **instruments:** MES/MNQ/MGC. **direction:** small gap → fade toward prior close; large gap → follow. **cadence:** daily. **no-lookahead:** gap known at open. **cheap-screen:** open→close return conditioned on gap-size bucket & sign; both halves. **kill:** no gap-conditioned edge after cost. **sleeve:** workhorse. **reachability:** HAVE. *Apply D2 lesson: use open as entry, no stop-fill optimism.*

### L6 — First-hour range → rest-of-day expansion/exhaustion *(class A, priority 3)*
- **mechanism:** first-hour range sets the day's character; narrow first-hour → trend day; wide → range/exhaustion. **data:** 5m (HAVE). **instruments:** MNQ/MGC. **direction:** conditioned on first-hour range percentile. **cadence:** daily. **no-lookahead:** first-hour complete at 10:30. **cheap-screen:** rest-of-day |return| & directional follow by first-hour-range bucket. **kill:** no conditioning value. **sleeve:** WH/overlay. **reachability:** HAVE.

### L7 — Liquidity-resilience post-news normalization *(class B, priority 3)*
- **mechanism:** after a news shock, spreads/vol normalize on a known decay path (Lehalle resilience) → tradable normalization. **data:** 5m + econ calendar (HAVE/REACHABLE). **instruments:** ZN/MNQ/MGC. **direction:** post-shock vol-normalization drift. **cadence:** event. **cheap-screen:** post-event range decay + drift. **kill:** subsumed by event sleeves. **sleeve:** tail. **reachability:** HAVE.

### L8 — Persistent-flow (metaorder) detection via volume clustering *(class A, priority 3)*
- **mechanism:** sustained abnormal volume across consecutive bars = a metaorder working → continuation until it completes. **data:** 5m vol (HAVE). **instruments:** MCL/MGC/MNQ. **direction:** multi-bar volume persistence → continuation. **cadence:** intraday. **cheap-screen:** forward return after k-consecutive high-volume same-direction bars. **kill:** no persistence edge. **sleeve:** WH. **reachability:** HAVE. *Overlaps H8; test together.*

---

# Book 4 — Jack Schwager, *A Complete Guide to the Futures Market* (roll / term structure / seasonality / flow)
Theme: futures-native structural edges — carry, roll, term structure, COT, seasonality, report reactions. Mostly **class B (carry/event)** but high portfolio-fit for the rates/energy/metals universe.

### S1 — Roll-yield / term-structure carry *(class B/carry, priority 5)*
- **mechanism:** backwardation → positive roll yield (long earns as price rolls up to spot); contango → negative. Harvest the structural carry (Schwager term structure). **forced participant:** hedgers paying the carry. **data:** front+next futures (HAVE for MCL/MGC outrights; spread needs 2 contracts). **instruments:** MCL/MGC. **direction:** long when backwardated, short/avoid when contango. **cadence:** daily/weekly. **no-lookahead:** term structure observable. **cheap-screen:** forward return conditioned on front-next basis sign. **kill:** no carry edge after roll cost. **sleeve:** carry. **reachability:** HAVE (outright proxy) / REACHABLE (true spread). *Honest reachable VRP-style carry — the commodity analog of N1.*

### S2 — COT commercial-hedger signal *(class B, priority 4)*
- Extends H5 with Schwager's commercial-hedger emphasis: commercials are the informed hedgers; follow commercial extreme (not just fade spec). **data:** COT (HAVE). **instruments:** MCL/MGC/6J (JPY already STRUCTURE_FOUND). **cheap-screen:** forward return following commercial-net extreme (vs spec-fade — are they the same signal?). **sleeve:** tail/carry. **reachability:** HAVE. *Decompose vs H5 to avoid double-count.*

### S3 — Inventory/report-day reaction (EIA crude, USDA) *(class B, priority 3)*
- **mechanism:** scheduled inventory reports force repricing; over/under-reaction (Schwager report trading). **forced participant:** hedgers reacting to mandated data. **data:** MCL 5m + EIA calendar (HAVE / REACHABLE — EIA .gov was BLOCKED; calendar dates may be hardcodable Wed 10:30 ET). **instruments:** MCL. **direction:** report-bar impulse fade/follow. **cadence:** weekly (Wed). **cheap-screen:** Wed-10:30 impulse + follow-through vs baseline. **kill:** no systematic reaction edge. **sleeve:** tail. **reachability:** REACHABLE (calendar). 

### S4 — Inter-market lead-lag (copper-gold → rates; crude → equities) *(class B/C, priority 3)*
- **mechanism:** structural inter-market relationships (Schwager) — one market leads another. **data:** copper-gold (HAVE), yields (HAVE), MCL/MES (HAVE). **instruments:** pairs/overlay. **direction:** lead-market signal → lagging-market position. **cadence:** daily. **cheap-screen:** lagged cross-correlation → forward predictive test (no-lookahead). **kill:** no out-of-sample lead-lag. **sleeve:** overlay/tail. **reachability:** HAVE. *Links to copper-gold-rates work already done.*

### S5 — Seasonal calendar tendency *(class B, priority 2)*
- **mechanism:** recurring seasonal flows (energy demand, harvest, fiscal). **data:** futures history (HAVE). **instruments:** MCL/MGC. **direction:** month/seasonal-window bias. **cadence:** seasonal. **no-lookahead:** calendar. **cheap-screen:** per-month return stability across years (HIGH overfit risk — require many years + mechanism). **kill:** not stable across years / no mechanism. **sleeve:** tail. **reachability:** HAVE. *Low priority — seasonality is overfit-prone; demand a forced-flow reason.*

### S6 — Open-interest + price confirmation *(class C, priority 3)*
- **mechanism:** rising OI + rising price = new money confirming trend; rising price + falling OI = short-covering (weak) (Schwager OI analysis). **data:** COT OI (HAVE, weekly) / daily OI (REACHABLE?). **instruments:** MCL/MGC. **direction:** OI-confirmed trends continue; OI-divergent reverse. **cadence:** weekly. **cheap-screen:** forward return by (price-change × OI-change) quadrant. **kill:** no quadrant edge. **sleeve:** overlay. **reachability:** HAVE (weekly OI). 

---

# Batch-2 cheap-screen results (2026-06-23m) — Lehalle class-A daily WH
Realistic intraday fills (D2 lesson applied). **Almost all KILL — informative.**
- **L2 VWAP-deviation reversion:** KILL all (PF 0.61-0.67, strongly negative). Intraday deviations CONTINUE, don't revert.
- **L1 large-print impact reversion:** KILL all (PF 0.64-0.80). Volume/range spikes CONTINUE (permanent>temporary impact at 5m/60min).
- **L5 small-gap fade:** KILL all. **L5 large-gap follow:** MES WATCH (PF 1.16 but H2 0.65) / MNQ,MGC KILL → not robust, parked.
- **STRATEGIC FINDING (scoped — corrected 2026-06-23):** batches 1+2 falsified GENERIC 5m intraday MEAN-REVERSION & simple microstructure translations (stop-run next-day fade, VWAP/impact reversion, raw drive-continuation, NR-breakout, crude gap fade/follow). At 5m these instruments are MOMENTUM-dominated intraday — raw MR loses. **CORRECT scope: generic intraday-MR is dry. NOT "daily WH is exhausted"** — we have MNQ ORB workhorse evidence on this exact tier. Inference: **the productive WH family is momentum / continuation / ORB-adjacent / regime-conditioned**, not raw reversion. Data-tier exhaustion (needing tick/L2) is a HYPOTHESIS, not a conclusion. → Stop grinding 5m MR; bias the WH queue to momentum/ORB-adjacent/regime/overlay packets (batch-3). Sparse/carry/positioning (COT-JPY etc.) is a productive PARALLEL lane, NOT a replacement for WH discovery.

# COT-JPY full gate (2026-06-23n) → KILL (cheap-screen pass was a one-sided directional artifact)
Both-sides decomposition (operator-required) exposed it: **long_pf 4.90 (+65bps) vs short_pf 0.348 (−59bps)** — entire "edge" is one leg ("long JPY when specs short" = JPY directional trend), NOT a symmetric positioning-REVERSAL. 4/8 yrs+. A reversal mechanism must work both sides; this doesn't. The PF 1.33 cheap screen masked a directional artifact; the gate caught it. → KILL. (Lesson: COT/positioning packets MUST pass both-sides decomposition — one-sided = directional trend, not forced-flow reversal.)

# WH batch-3 momentum/ORB-adjacent (2026-06-23o) → all KILL, BUT the right lesson is METHODOLOGICAL
M1 first-hour-regime, M3 AM/power-hour momentum, M4 prior-day breakout continuation — all KILL raw. **Scoped correctly (NOT "momentum is dry"):** raw momentum entries fail for the SAME reason raw MR fails — the cheap-screen tests a bare entry + crude fixed-horizon exit, but the proven ORB workhorse works BECAUSE of its ema_slope filter + profit_ladder exit. **My raw-entry cheap screens are structurally blind to real WH — they strip the filter+exit bundle that carries the edge.**
- **METHOD PIVOT (key):** the crossbreeding engine (research/crossbreeding/crossbreeding_engine.py) already has the right ENTRY primitives (orb_breakout, prior_day_break, vol_expansion, range_compression_break, afternoon_continuation, first_impulse_pullback, vwap_continuation, abnormal_range_followup...) × proven FILTERS (ema_slope, vol_regime, ema_slope_vol_high/low, session) × proven EXITS (profit_ladder, atr_trail, chandelier). **WH discovery must SWEEP entry×filter×exit through this engine (the bundle that produced the ORB WH) — NOT raw entry→horizon screens.** Batch-4 = engine-based crossbred sweep of momentum/ORB-adjacent entries with ema_slope/vol_regime filters + profit_ladder/atr_trail exits.
- Raw cheap screens remain useful for FAST FALSIFICATION of novel mechanisms NOT in the engine (MR, gaps, COT) — but proven-family WH hunting routes through the engine.

# WH Batch-4 — engine crossbred sweep (2026-06-23p): HARNESS VALIDATED; one MNQ lead
48 families (8 entries × 3 filters × 2 exits) × 3 assets, proven param neighborhood (stop0.5/target4.0/trail2.5), family-ranked.
- **METHOD PROVEN:** the engine reproduces the deployed WH — orb_breakout|ema_slope|profit_ladder = ONLY clean cross-asset survivor (MNQ 1.614/MES 1.447/MGC 1.495, all median+, 7-8/8 yrs, top10 ~9-17%). The same orb_breakout that "KILLed" as a RAW screen scores 1.6 through the engine → **"book research didn't fail; the raw-entry harness did"** is confirmed empirically.
- **ema_slope load-bearing CONFIRMED:** orb_breakout with none/vol_regime filter collapses to PF ~1.05. vol_regime ≈ none (no-op for these entries). **profit_ladder > atr_trail** for ORB family (MGC 1.495 vs 1.085) — consistent w/ pl-workhorse-default doctrine.
- **No NEW entry beats ORB on the strict cross-asset+median gate.** Properly instrumented, the daily-WH space at this param neighborhood is ORB-dominated.
- **ONE LIVE LEAD — first_impulse_pullback|ema_slope|profit_ladder:** MNQ workhorse-grade standalone (PF 1.317, median +4.01, H1/H2 1.18/1.42, 7/8 yrs, top10 14.3%, max-yr 21.9% — the 7/8 + 22% argues AGAINST the prior 2025-artifact flag for THIS config). MES borderline (1.24), MGC weak (1.08) → NOT cross-asset robust. Weaker than ORB (1.32 vs 1.61) but a DIFFERENT entry. **Value question = is it a decorrelated additive MNQ sleeve (sleeve-addition test: per-year DD stability + bad-day OFFSET vs ORB), NOT standalone-PF.** Note: atr_trail version had 3/3 PF>1.2 but median −14 to −18 (fat-tail, fails workhorse median) — profit_ladder is the real config.
- **SLEEVE-ADDITION TEST (2026-06-24a) → ARCHIVE: ORB-lite, not a diversifier.** vs deployed MNQ ORB book: **87.2% same-day overlap, 877 same-direction days, ZERO conflicts** — fires on the same setups/side. Bad-day offset = ADDS_LOSS (−$99.7 on ORB's 20 worst days, bleeds alongside). Combined book WORSE on every risk axis: PF dilutes 1.614→1.52, maxDD worsens −$2331→−$2483, worst-day −$850→−$1195, and **creates a NEW Tradeify-DLL breach day ORB alone never had**. Only gross $ rises = ~2× MNQ directional exposure (= sizing ORB up), not decorrelated PnL. corr 0.435 (moderate) but overlap+same-direction+ADDS_LOSS+worsened-DD/prop is decisive → **ARCHIVED as ORB-lite** (per sleeve-addition rule: needs bad-day OFFSET or low corr AND must not worsen DD/tail; fails all). FIP standalone is real but redundant with ORB on MNQ; not cross-asset (batch-4). Lead closed. Engine harness remains the validated WH instrument.

# WH QUEUE (class A only — daily/high-cadence, ranked) — protect from sparse-idea crowding
1. **L2 VWAP-deviation reversion** (HAVE) — cleanest daily intraday MR; high cadence.
2. **L1 large-print impact reversion** (HAVE) — impact decay, intraday.
3. **L5 overnight-gap fade/follow** (HAVE) — daily, apply gap-aware fills (D2 lesson).
4. **L3 signed-volume continuation** (HAVE) — intraday momentum proxy.
5. **L4 intraday vol seasonality / H6 midday-revert** (HAVE) — session-conditioned.
6. **L6 first-hour range conditioning** (HAVE).
7. **H2 MOC imbalance** (HAVE) — re-test with gap-aware overnight.
8. **L8/H8 metaorder volume persistence** (HAVE).
*(D1/D2/D3 KILLed; D4 MNQ-only WATCH parked.)*

# Sparse/carry/overlay queue (class B/C)
COT-JPY full-gate (live survivor) · S1 roll-carry · N1 VX-carry (probe VX) · N4 IV-RV sizing · H1/H10/H12 calendar-flow · S3 EIA-report · S4 inter-market.

## Boundaries
Report-only; no promotion/wiring/scheduler/registry/portfolio mutation. Packets are hypotheses, not candidates, until cheap-screened. Every breakout/stop-based packet MUST use intraday first-touch + gap-aware fills (D2 lesson). Every vol packet MUST pass the incremental-value test vs VIX/prior-day/RV (O1/O2 lesson).
