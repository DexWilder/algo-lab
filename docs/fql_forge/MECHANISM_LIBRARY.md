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

# N4 IV-RV sizing overlay on ORB book (2026-06-24b) → IV-RV REJECTED; flat is strong; VIX-overlay modest WATCH
Book-improvement test (NOT a new WH) on deployed orb_breakout|ema_slope|profit_ladder, MNQ/MES/MGC. No-lookahead vol signals (VIX prior close, RV prior). Schemes vs flat 1x, exposure-reported.
- **IV-RV (Sinclair "size up when IV-RV rich") REJECTED:** MNQ Sharpe 2.68→2.50, maxDD −2331→−3551, worst-day −850→−1091 — it sizes UP on ORB's worst days (1.08 vs 1.03 avg, backwards). Fails to beat simpler rules. The N4 hypothesis is wrong for an intraday momentum book.
- **Simple VIX de-risk overlay = modest WATCH:** MNQ Sharpe 2.68→2.91, worst-day −850→−649 via GENUINE bad-day timing (size 0.42 on ORB worst-20 vs 1.06 avg). MES 2.08→2.15. BUT MGC-neutral, peak maxDD marginally worse, and at matched exposure it buys a smoother curve/better worst-day at ~6% less net — risk-RESHAPING, not a free lunch. Low-priority book-improvement WATCH; prop-relevant only where worst-day matters.
- **KEY: flat 1x ORB is already excellent & hard to beat** — Sharpe 2.68, 8/8 yrs, maxDD −2331, ZERO Tradeify-DLL breaches at 1 contract. No prop-fit problem to fix → no sizing overlay is a slam dunk. inv_vol_target also mixed (helps MNQ/MGC Sharpe, hurts MES). Verdict: IV-RV KILL; vol-sizing overlays NOT adopted (modest/non-uniform); flat confirmed.

# S1 roll-yield carry (2026-06-24c, spot-front basis PROXY) → KILL standalone; effect real-but-thin
Class-B proxy (WTI spot vs front future, 2011+), NOT true term structure. Basis non-degenerate (std 1.47%) so usable, not FEED-BLOCKED.
- **Backwardation effect is REAL** (incremental test passes): wti_f backwardation days +18.9bps fwd vs contango −9.8bps vs uncond −6.4bps, across 16yrs — the documented commodity-carry factor, NOT just long-crude-beta.
- **But untradeable standalone on the proxy:** wti_f PF 1.109, dies at cost (PF@12bps 1.03), 10/16 yrs, and headline CONTAMINATED by 2020 negative-oil blowup (+44.5% Feb–May 2020, basis hit +42% as spot collapsed = non-replicable). **MCL (real micro instrument) PF 0.95 — loses outright**, 3/6 yrs.
- **Verdict: KILL standalone.** Real-but-thin signal; no tradeable edge alone on reachable proxy. True 2nd-month term-structure = class-C feed need but LOW priority (effect already shown too thin/cost-fragile to justify). Backwardation regime could have minor ENSEMBLE/filter value but not pursued now.

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

---

# Book 5 — Ernest Chan, *Quantitative Trading / Algorithmic Trading*
Theme: statistical-arbitrage & regime methodology. Mostly class-B/C/E — feeds the engine and the rulebook.

### C1 — Cointegration pairs mean-reversion *(class B, priority 3)*
- **mechanism:** two cointegrated futures' spread is stationary → trade spread reversion. **forced participant:** arbs enforcing the long-run relationship. **data:** 2 futures daily (HAVE: many micros). **instruments:** MES-MNQ, MGC-copper, MCL-Brent, ZN-ZF. **direction:** fade spread z-extreme. **no-lookahead:** rolling cointegration/beta. **cheap-screen:** ADF on spread + forward reversion of spread-z>2. **kill:** spread not stationary OOS / no edge after cost. **reachability:** HAVE. *Note: WTI-Brent already a candidate; ZN-ZF rates pair too.*
### C2 — ADF/Hurst stationarity REGIME GATE *(class C/E, priority 4)*
- **mechanism:** only run MR strategies when the series is statistically mean-reverting (Hurst<0.5 / ADF rejects); run momentum when trending. **use:** a meta-gate on entry selection. **data:** HAVE (engine already has hurst_stable_mr/trend filters). **cheap-screen:** does Hurst-gating improve MR vs momentum routing? **reachability:** HAVE. *Partially built — formalize as a router.*
### C3 — Kelly / optimal-f position sizing *(class E, priority 3)*
- **process upgrade:** size by edge/odds (fractional Kelly) rather than flat — but N4 showed flat ORB is hard to beat; apply cautiously, half-Kelly cap, prop-DLL-constrained. **rulebook item, not a strategy.**

# Book 6 — López de Prado, *Advances in Financial Machine Learning* (CLASS-E PROCESS UPGRADES — high value)
Theme: this session ran ~12 backtests/screens; multiple-testing & overfitting controls are now the highest-leverage rulebook upgrades. These harden the very machine that is this session's real yield.

### L1 — Deflated Sharpe Ratio + PBO *(class E, priority 5)*
- **upgrade:** correct observed Sharpe for the NUMBER of trials run (we sweep dozens of families) → Deflated SR; estimate Probability of Backtest Overfitting. **why:** prevents banking a "winner" that's just the best of many tries (directly relevant to engine sweeps + cheap-screen batches). **apply:** compute DSR for any survivor before PASS; report PBO for each sweep. **reachability:** HAVE (compute from existing trial distributions). *INSTALL FIRST.*
### L2 — Combinatorial Purged Cross-Validation (CPCV) *(class E, priority 4)*
- **upgrade:** replace single H1/H2 split with purged/embargoed combinatorial CV → robust OOS estimate without leakage. **why:** H1/H2 is a weak 1-split; CPCV gives a distribution of OOS Sharpes. **apply:** to any survivor before promotion-readiness. **reachability:** HAVE.
### L3 — Meta-labeling on ORB *(class A/E, priority 5 — potential ORB IMPROVEMENT)*
- **mechanism:** train a SECONDARY model to predict which ORB primary signals will win → size up high-confidence, skip low-confidence. Improves precision/risk WITHOUT changing the primary edge. **why:** the one ORB-improvement angle not yet tried; N4 sizing failed but meta-labeling sizes by *signal-quality features* (vol regime, time, range, prior-day state) not just vol. **data:** HAVE (ORB trades + features). **cheap-screen:** does meta-label filtering improve ORB Sharpe/DD vs flat at matched exposure? **kill:** no precision lift OOS (CPCV-validated). **reachability:** HAVE. *HIGH PRIORITY — the live ORB-improvement lead.*
### L4 — Triple-barrier labeling / exit design *(class E, priority 3)*
- **upgrade:** formalize exits as profit-take / stop / time barriers (profit_ladder is ad-hoc) → principled exit comparison. **reachability:** HAVE.
### L5 — Fractional differentiation, sample-uniqueness weighting, MDA importance *(class E, priority 2)*
- **upgrades:** stationary-with-memory features; weight overlapping samples; robust feature importance. **rulebook items for when ML enters.**

# Book 7 — Antti Ilmanen, *Expected Returns* (carry / value / momentum / risk-premia classification)
Theme: classify every edge by which RISK PREMIUM it harvests → ensures the ensemble is premia-diversified, not redundant.

### I1 — Premia classification of the existing book *(class E, priority 4)*
- **upgrade:** tag each sleeve by premium harvested (ORB = intraday momentum/trend; COT = positioning; roll-carry = carry; VRP = volatility). **why:** an ensemble of 5 momentum sleeves isn't diversified. Use to GOVERN additions — a new sleeve should add a NEW premium or a decorrelated instance. **reachability:** HAVE (classification exercise). *Explains why FIP failed: same premium (intraday momentum) as ORB → redundant.*
### I2 — Time-series momentum (trend) across assets *(class A/B, priority 3)*
- **mechanism:** 1-12mo trend persistence (Ilmanen/Moskowitz TSMOM). **data:** HAVE daily futures. **instruments:** MCL/MGC/MES/ZN/6E. **direction:** long past-winners/short past-losers. **cadence:** daily/weekly. **cheap-screen:** forward return by trailing-trend sign, per asset, cost. **kill:** no persistence after cost / not cross-asset. **reachability:** HAVE.
### I3 — Defensive / low-vol anomaly *(class B, priority 2)*; ### I4 — Value/mean-reversion to fundamentals *(class B, priority 2)*; ### I5 — VRP harvest *(class B/C — see O1/N1, partially tested)*; ### I6 — Cross-premia business-cycle conditioning *(class C, priority 3 — condition sleeve weights on macro regime via the FRED/rates feeds we have)*.

# WH untried-assets engine sweep (2026-06-24d) → NO survivor; ORB-dominant across 9-asset universe
216 runs (M2K/MCL/MYM/6E/6J/6B × 6 entries × 3 filters × 2 exits), 1021s. **No family-supported non-ORB WH** (none clears n≥50 + PF≥1.25 + median>0 + H1/H2>1 + top10<35 + neighbor-filter support).
- **ORB|ema_slope|profit_ladder is best/near-best on EVERY asset:** M2K PF 1.28 (8/8 yrs, med +6.8), MCL 1.197 (5/6), MYM 1.551 (3/3, capped), 6E 1.406 (3/3), 6J 1.239 (3/3), 6B 1.068 (2/3). Universal across equity/energy/FX micros.
- **Every non-ORB challenger is fat-tailed, NEGATIVE median** (first_impulse_pullback −12/−14, range_compression −10/−30, vol_expansion −17, prior_day_break −11) → fails workhorse median gate everywhere, same signature as MNQ/MES/MGC. Higher-PF ones (MYM range-comp 1.60, 6B prior-day 1.47) are 3yr + concentrated (top10 30-48%) + median-neg → rejected/capped.
- **SCOPED conclusion (NOT "WH dead"):** tested engine-routed WH mechanisms are ORB-DOMINATED across the full 9-asset micro universe. Per Ilmanen premia-lens (I1): every WH harvests the SAME premium (intraday momentum) → challengers return ORB-lite or fat-tailed. **Implication: a second WH likely needs a DIFFERENT premium (carry/positioning/vol/value/mean-reversion) or a better data tier — not another momentum entry.**
- **Minor note:** ORB works on 6E/6J FX (3yr, capped WATCH) — a possible same-premium cross-asset ORB extension, but more momentum instances need decorrelation proof (sleeve-addition); low priority.
- **Branch → L3 ORB meta-labeling** (improve the proven book) is now the highest-value WH-adjacent test. Non-ORB fat-tailed entries → possible tail-engine archetypes (not pursued now).

# L3 ORB meta-labeling (2026-06-24e) → META_IMPROVES_screen_only (NOT credible; regime knowledge retained)
Improve ORB precision via entry-time features (purged/embargoed CV, no leakage, numpy logistic, matched-exposure). Audited a contradiction (PF 1.68→2.04 but DSR=0.0): DSR fallback mis-scales for per-trade single-model (it's for multi-trial SWEEPS, where the self-test confirms it works) → correct gate = OOS-lift significance vs RANDOM same-size selection.
- **Meta-model (logistic, 51% retained):** PF 2.038, exp $64.16, lift +$17.27/trade, **bootstrap p=0.153 (NOT significant)**.
- **Simple rule (top-3 stable features, 67% retained):** PF 2.036, exp $66.22, lift +$19.33, **p=0.098** — BEATS the black box (more trades, more significant) = "simple stable rule > fragile model" confirmed. Still sub-0.05.
- **VERDICT: screen_only — NOT adopted.** Neither clears p<0.05. Deeper validation package NOT run (reserved for a real pass).
- **DURABLE TAKEAWAY (regime knowledge, corroborated):** stable sign-1.0 coefs say ORB wins more on prior-day-UP (trend-align +0.21), HIGH realized vol (+0.17, RE-CONFIRMS MGC low-vol-exclusion), EARLY entry (entry_hour −0.11). Retained as research note + borderline (p~0.10) WATCH regime-filter to revisit with more data. NOT tradeable now.
- **STRATEGIC CLOSE:** FIP (add similar entry)=ORB-lite; N4 (broad-vol resize)=hurt; L3 (select ORB signals)=marginal/insignificant. **Flat ORB is hard to improve AND hard to beat.** Confirmed: the second edge needs a DIFFERENT PREMIUM (carry/positioning/vol/value/mean-reversion), not more momentum. → pivot to different-premium queue.

# C1 cointegration ZN-ZF (2026-06-24f, first different-premium test) → KILL_not_stationary
Construction-first (audit → rolling no-lookahead beta → stationarity → strategy). **Stationarity gate caught it up front:** ADF-t(spread)=−1.05 (need <−2.9), half-life 569d → spread TRENDS (Fed-cycle curve 2019-23), does NOT mean-revert. z-band reversion faded the trend → lost EVERY year (0/8, net −$627k, PF 0.39, no-stop unbounded hold). KILL.
- **USEFUL: decorrelation confirmed** — corr to ORB/MNQ −0.069. Rates ARE a different premium SPACE that would diversify equity; the problem is the mean-reversion EXPRESSION, not the space.
- **Reconciles with deployment:** the rates edge that WORKS is CARRY (Treasury-Rolldown-Carry-Spread, already in probation) — carry harvests the curve, reversion fights its trend. Consistent.
- **WTI-Brent = CONSTRUCTION-BLOCKED** (more likely-stationary econ spread, but no tradable Brent leg in our data → class-C feed need; not faked on daily proxy).
- **Lesson:** cointegration on a TRENDING macro series (rate curve) fails; mean-reversion premium needs a genuinely range-bound/arb-bounded spread. The ADF gate prevented overfitting a spread into existence.

# VX term-structure carry / VRP (2026-06-24g) → WATCH_vol_carry (strongest non-ORB lead; 2 caveats) + DSR-gate FIX
Volatility premium (genuinely different). ^VIX/^VIX3M slope → contango-only long SVXY (short-vol), backwardation→flat. No-lookahead (prior-close slope). 2016-2026.
- **Term-structure crash-timing WORKS:** maxDD −43% vs −181% (unconditional always-short-vol), Feb-2018 −17% vs −125%, Mar-2020 −14% vs −71%, Sharpe 0.89 vs 0.43, 8/11 yrs+. The carry is real and timing earns its keep.
- **Statistically credible:** PSR≈significant (Sharpe 0.89 over 10yr ~3SE>0). [DSR auto-verdict said PASS_REVIEW — OVERRIDDEN, see below.]
- **CAVEAT 1 — only half-diversifying:** corr-to-ORB = 0.50 (short-vol = long-risk-on). Real risk = COINCIDENT drawdowns with ORB in risk-off events (unrun sleeve-addition question).
- **CAVEAT 2 — prop-incompatible tail:** −43% maxDD, −18% worst-day. Needs vol-targeting / small-sleeve cap; not deployable at size as-is.
- **VERDICT: WATCH_vol_carry (NOT PASS_REVIEW).** Auto-logic credited PSR+timing+robust but lacked a decorrelation/tail gate; PSR-pass ≠ research-candidate. STATISTICALLY_CREDIBLE_CANDIDATE pending: (a) sleeve-addition battery vs ORB (does it offset or COMPOUND ORB bad days? 0.50 corr is the flag), (b) tail-sizing for prop viability. First different-premium that didn't die.
- **DSR-GATE FIX (forge_deflated_sharpe.py):** old fallback mis-scaled deflation benchmark for per-period/daily Sharpes → spurious DSR~0 (bit L3 + VX). Fixed: without trial-dispersion, report PSR (P(SR>0)) not a fabricated benchmark; true multiple-testing deflation requires caller to pass sr_trials_std (works correctly, self-test confirms). L3's bootstrap workaround already gave the honest p=0.098.

# VX sleeve-addition battery (2026-06-24h) → EXPRESSION ARCHIVE / PREMIUM VALIDATED-decorrelated
Decisive test: does VX offset or compound ORB's worst days?
- **CORRECTION of 24g's 0.50 corr — it was a buy-and-hold-PROXY artifact.** vs the ACTUAL ORB STRATEGY (long/short intraday), VX-timed corr = **−0.164** (decorrelated). Stress-window corr −0.06, ex-crisis −0.17.
- **VX OFFSETS ORB's worst days (decisive PASS):** ORB worst-10/20/50 → VX +0.56%/+0.35%/+0.05% (positive). Contango-timing keeps VX OUT of vol stress → does NOT compound. Genuine diversification (opposite of the "risk-on-in-disguise" failure).
- **But marginal additive benefit:** +$2k VX → combined Sharpe 2.76→2.82, MAR 22.18→22.43, worst-day unchanged −$850, 0 DLL (real but tiny). $5k+ → Sharpe flat/down, tail+DLL grow (VX tail dominates). **VX DRAGS ORB's strong years** (2022 combined +$6.0k vs ORB-alone +$9.2k — short-vol bled while ORB thrived).
- **VERDICT: ARCHIVE this expression / WATCH the premium.** A +0.06-Sharpe sprinkle that drags good years + huge standalone tail isn't deployment-worthy. BUT vol-carry is now the FIRST VALIDATED genuinely-decorrelated, ORB-offsetting premium — strategically the key finding. Pursue a BETTER vol expression (cleaner instrument / VIX-futures sleeve / optimized crash-filter) rather than the raw SVXY-contango version; or hold as a small future sleeve.
- Lesson: correlate candidate vs the ACTUAL strategy PnL, never a buy-and-hold proxy (the proxy inflated corr 0.50→true −0.16).

# vol-carry CLEANER expression (2026-06-24i, the one disciplined attempt) → STOP branch / premium retained-small
Short-VXX (no SVXY leverage-reset), graded-by-slope exposure, 4-guard crash filter, prior-close no-lookahead. Judged on combined ORB book.
- **WORSE than the raw version** — not even tail-reduction success: +$3k → Sharpe 2.76→2.61 (lift −0.15), net $51717→$50484 (VX contributed −$1.2k). $6k+ → DLL breaches. **avg exposure 0.65** (NOT hiding by sitting out — negative result is genuine).
- **Offset weakened:** worst-10/20 offset (+0.26/+0.19%) but worst-50 COMPOUNDS (−0.16%). Dragged 2022 (+$6.7k vs +$9.2k).
- **3-WAY (decisive):** ORB alone Sharpe 2.76 | +raw-SVXY-$2k 2.82 (marginal+) | +clean-VXX-$3k 2.61 (worse). Cleaner vehicle did NOT help → limit is the EXTRACTABLE diversification benefit, not the vehicle.
- **VERDICT: STOP vol-carry branch.** One disciplined attempt spent. **PREMIUM RETAINED as VALIDATED-BUT-SMALL/future-sleeve** (decorrelation −0.09/−0.16 + bad-day offset finding stands); revisit only with actual VIX-futures data (class-C) — marginal benefit doesn't justify the feed now.
- **Pivot → next different-premium: COT-commercial positioning** (genuinely different; commercial-hedger angle, untested — JPY was spec-fade).

# TSMOM (2026-06-24j) → WATCH premium + the SESSION'S KEY STRUCTURAL INSIGHT
Pooled 6-mo (lb126) across MNQ/MES/MGC/MCL: Sharpe 0.46, **8/8 yrs+**, **corr-to-ORB −0.05**, PSR 0.90, no catastrophic tail. Cleanest decorrelated premium found. (lb21 noise; per-asset MCL negative — pooled benefit is cross-asset.) Positioning-direction (COT) marked EXHAUSTED (comm=−spec mirror, corr −0.99 → commercial-follow = killed spec-fade relabeled).
- **Diversification properties GOOD:** decorrelated −0.05, OFFSETS ORB worst-20 (+$74/day).
- **But cannot improve combined book:** ORB alone Sharpe 2.76 / +0.5×TSMOM 2.21 (maxDD −2331→−7463, 0→19 DLL) / +1.0× 1.65. Net-$ rises = just leverage; Sharpe craters, tail blows out.
- **KEY STRUCTURAL INSIGHT (durable):** ORB's Sharpe 2.76 is so HIGH that NO decorrelated lower-Sharpe premium improves the combined book risk-adjusted — combined Sharpe blends toward the weaker stream. vol-carry AND TSMOM (the 2 cleanest decorrelated premia) BOTH fail as ORB additions for this identical reason. → the second-sleeve value proposition is NOT Sharpe-improvement; it is (a) decorrelated CAPACITY (more capital at lower blended Sharpe — portfolio-size choice), (b) a SEPARATE capital pool (run standalone, not blended), or (c) a premium with Sharpe COMPARABLE to ORB (none reachable found).
- **VERDICT: WATCH premium / not a combined-book improver** (same shelf as vol-carry: validated-decorrelated-but-can't-beat-2.76). Naive 1-contract sizing caveat noted (tiny allocations would offset ORB tail marginally but contribution negligible).

# ALLOCATION CURVE (2026-06-24k) → RETRACTS the overreach; BOTH premia improve the book at SMALL size
Operator-required curve (0.05×→1.0×) before any universal claim. My prior "a 2.76-Sharpe book can't be improved by a lower-Sharpe premium" was WRONG — an artifact of testing only oversized 0.5×/1.0× allocations. **At proper SMALL sizing both decorrelated premia IMPROVE the combined ORB book (Sharpe AND MAR AND maxDD):**
- ORB alone: Sharpe 2.84, MAR 22.07, maxDD −2331, worst-day −850, 0 DLL.
- **TSMOM 0.05×: Sharpe 2.97, MAR 23.45, maxDD −2306, 0 DLL** (improves all). 0.10×: Sharpe 3.01 peak (MAR slips 21.33). 0.25×+ degrades + DLL breaches.
- **Vol-carry $1–3k: Sharpe 2.88–2.91, MAR 22.21–22.51, maxDD better, worst-day unchanged −850, 0 DLL** (tail_better=True). $5k+ worst-day degrades.
- **CORRECTED CONCLUSION: the second-sleeve search SUCCEEDED.** Two decorrelated premia (TSMOM ~0.05–0.10×, vol-carry ~$1–3k), sized correctly, lift combined Sharpe+MAR with 0 DLL. Earlier "archive/marginal/can't-improve" verdicts were WRONG-SIZED. A lower-Sharpe diversifier DOES help when small + decorrelated. Scoped insight retained ONLY as: naive OVERSIZED allocations of low-Sharpe premia hurt; small ones help.
- **VERDICTS UPGRADED → RESEARCH_CANDIDATE (small-sleeve):** TSMOM-0.05–0.10× and vol-carry-$1–3k. Next (report-only): combined-book per-year + walk-forward of the allocation choice + DSR + robustness of the small-size pick, before any deployment discussion. Capital gate intact (no sizing/wiring mutation).

# SMALL-SLEEVE VALIDATION (2026-06-24l) → VALIDATED & ROBUST (session's first combined-book improvement)
Per-year + walk-forward on the small-allocation candidates. NOT curve-fit:
- **Per-year (ORB 2.84 → +0.05×TSMOM 2.97 / +$2k VX 2.91 / +both 3.02):** TSMOM improves **6/8 yrs**, VX 5/8. Crucially rescues ORB's WEAK years (2019 ORB −1.16 → +1.85; +both 9.06) — diversification helps most when ORB struggles, slight drag only when ORB already great (2026). Textbook.
- **Walk-forward OOS PASSES:** allocation chosen on H1 (0.10×) applied blind to H2 → Sharpe 3.58 vs ORB-alone 3.38. Improvement survives OOS.
- Allocation not knife-edge (0.05× & 0.10× both help), 0 DLL breaches.
- **VERDICT: TSMOM-0.05–0.10× & vol-carry-$2k = VALIDATED small decorrelated-sleeve RESEARCH_CANDIDATES.** Robust per-year + walk-forward, help ORB's weak years, 0 prop cost. Combined → Sharpe 3.02. Improvement MODEST (+0.13–0.18 Sharpe) but real & robust. 2019 spike on partial data → reliable evidence is consistent 2021-2025 lifts + OOS pass.
- **First robustly-validated combined-book improvement of the session.** Came directly from the operator's small-sizing pushback. Report-only; actual sizing/deployment GATED (operator decision). Next report-only: DSR on combined, finer walk-forward, vol-carry cleaner-vehicle at small size, and the "both-sleeves" interaction.

# BOTH-SLEEVE INTERACTION (2026-06-24m) → VALIDATED_RESEARCH_CANDIDATE_SMALL_DIVERSIFIER (package)
Decisive question (additive or redundant?) → ADDITIVE / regime-complementary:
- **corr(TSMOM-sleeve, VX-sleeve) = 0.19** (low, distinct). **2022 tell: TSMOM +$936 (trend year) vs VX −$1249 (high-vol year) = OPPOSITE regime exposures.** TSMOM=trend/vol-expansion premium; VX=calm/contango premium. Different engines, not one "risk regime."
- ORB worst-20 roles differ: VX offsets (+$7/day), TSMOM neutral (−$6). **CAVEAT: 2020 COVID both slightly negative (TSMOM −$616 whipsawed by V-reversal) → rescue works for ORB weak-GRIND years (2019/2021), NOT sharp V-crashes.**
- **Package (0.05×TSMOM + $2k VX): Sharpe 2.84→3.02 (beats either alone 2.97/2.91 = additive), MAR 22.07→23.27, 0 DLL.** Both walk-forward halves improve (H1 2.21→2.33, H2 3.38→3.61). PSR 1.0 (combined SR significant). Allocation grid: TSMOM MAR-optimal 0.025–0.05× / Sharpe-optimal 0.10×; VX $1–3k all improve, 0 DLL.
- **VERDICT: VALIDATED_RESEARCH_CANDIDATE_SMALL_DIVERSIFIER (package).** First real small second-sleeve package. ORB=primary engine; small TSMOM+VX=additive regime-complement stabilizers. MODEST (+0.18 Sharpe) but real, robust (per-year 6/8, both OOS halves, PSR), 0 prop cost. Report-only; DEPLOYMENT (sizing/wiring/paper) = operator-gated capital decision. Remaining report-only: cost/execution realism for the sleeves (TSMOM overnight-hold financing, VX ETP realism), finer DSR with proper trial-dispersion, V-crash guard for TSMOM.

# STAGED-PACKET RESULTS (2026-06-24)
- **Month-end rebalance drift (24p) → KILL_no_rebalance_drift.** MES last-2-day window, 84 months, conditioned on intra-month MES-vs-ZN divergence (rebalance-flow hypothesis). Unconditional last-2-day return −10bps/PF 0.81 (no calendar drift); divergence-conditioned PF 1.02 (nothing). **Decisive: corr(divergence, month-end return) = −0.06 ≈ 0** (hypothesis needs clearly negative) → flow effect not tradeably present. Adequate sample → real KILL, not data-limited.
- **XSMOM (24o) → KILL as cross-sectional premium (two audits downgraded it).** Gross lb21 looked elite (Sharpe 1.55, 6/6 yrs, decorrelated from ORB 0.12 & TSMOM 0.22, PSR 0.9999) BUT:
  - **AUDIT 1 (cost):** first cost-stress showed IDENTICAL Sharpe across 0-20bps = bug (prev updated before turnover calc → cost never charged). Fixed → net 5bps/leg Sharpe 1.38 (survives cost, monotonic decay 1.55→0.85@20bps). So cost-robust.
  - **AUDIT 2 (data/concentration, decisive):** worst-day −13.8% = MCL −22.2% (rollover-gap artifact; MCL has 18 days >8%, max 26.5% — stitching glitches). Clean re-tests: winsorized ±8% holds (1.41) so NOT pure glitch, BUT **NO-MCL collapses to Sharpe 0.65** → the edge is entirely CRUDE-CONCENTRATED, not a broad cross-sectional premium. A "diversified" sleeve that dies when one asset is removed isn't diversified ([[feedback_concentration_is_load_bearing]]).
  - **Verdict: KILL** as cross-sectional premium. Residual crude-relative-strength = at most WATCH, ONLY on clean roll-adjusted crude data (MCL untrustworthy). Lesson reinforced: audit "too-good" (Sharpe 1.55) + "identical-across-stress" (cost bug) + suspicious tail (data glitch) — all three fired here.

# MGC vol_low refinement CLASSIFIED (2026-06-25) → validated asset-specific ORB refinement (overlay-grade WATCH)
Per-year: vol_low improves MGC-ORB PF in 6/8 yrs (incl. the WEAK years — 2021 0.862→0.939, net −327→−123 — and every recent year 2024/25/26); 2 givebacks (2020/2022) are years ORB already strong. PSR 1.0 (SR>0 significant). With 24q risk-gate (PF 1.495→1.607, better maxDD/worst-day, H1/H2 both better) → VALIDATED asset-specific (MGC) ORB refinement, overlay-grade. NOT universal (MNQ negligible), NOT deployment, report-only. Preserved as a real ORB-refinement WATCH per mature-WH-posture.

# WH composite-filter sweep (24q + full-gate) → ema_slope baseline CONFIRMED; vol_low = MGC-specific WATCH
Engine-routed (orb_breakout × filters × profit_ladder, MNQ/MES/MGC), judged vs single ema_slope baseline on RISK not PF.
- **ema_slope_vol_high → collapses** (PF 0.77/0.83, removes ~93% of trades) — refutes a naive "ORB likes high vol"; it's MODERATE vol ORB likes, EXTREME vol hurts.
- **session_morning → REJECT (trade-deletion mirage):** PF +0.04 but net $ FELL all 3 assets (MNQ 50835→47602, −176 trades) and maxDD WORSE (−2331→−2503). Higher PF from cutting trades ≠ improvement (risk-over-PF rule).
- **vol_low → asset-specific MGC WATCH:** MNQ negligible; MES mild (maxDD −1509→−1423, 7/8→8/8 yrs); **MGC genuine (PF 1.495→1.607, net +$877, maxDD −1022→−847, worst-day better, H1/H2 better, −75 trades).** Excluding extreme-vol days helps GOLD specifically (mechanistic; dovetails locked MGC vol-regime sensitivity). NOT universal.
- **VERDICT: no universal composite beats ema_slope → BASELINE CONFIRMED** (load-bearing). vol_low = MGC-ORB-specific refinement WATCH (overlay-grade, report-only). Discipline note: risk-metrics correctly rejected session_morning's headline PF gain; 5-variant marginal "wins" were noise/deletion.

# FX rate-differential carry (24r) → DATA_LIMITED
6E/6J/6B futures, only 2.3yr (2024-03+). Per-ccy ann: 6E +2.0% / 6J −2.2% / 6B +1.8%. Short-JPY funding carry Sharpe 0.25 (+2.3%/yr, the known 2024-26 regime, mild positive but not bankable); XS long-short Sharpe 0.12 (noise). DATA_LIMITED (2.3yr, 3 ccy) → not a reachable edge; needs longer FX history / more currencies = DATA-TIER item.

# DATA-TIER UNLOCK PACKET (priority — the evidence-backed next lever; report-only feed requirements)
Reachable different-premium space now well-mapped; the highest-value unlocks require better DATA, not more grinding of thin veins. Packetized feed requirements:
1. **Roll-adjusted continuous futures (esp. crude/MCL)** — back-adjusted at roll dates → fixes the rollover-gap artifacts ([[feedback_continuous_contract_rollover_artifacts]]) that contaminated XSMOM/S1; reopens crude relative-strength + commodity carry cleanly.
2. **True VIX-futures curve (VX1/VX2 term structure)** — a clean vehicle for the ALREADY-VALIDATED vol-carry premium (vs the SVXY-ETP decay/leverage-reset artifacts); could lift vol-carry from "validated-small" toward a deployable sleeve.
3. **Longer FX history + more currencies** — to make FX carry judgeable (currently 2.3yr/3ccy = data-limited).
4. **Options/gamma feed (SPX/index OI, dealer-gamma proxies)** — dealer-positioning pinning; currently BLOCKED for single-name; needs reachable OI/GEX source.
5. **Tick/L2/order-flow** — to reopen the daily-microstructure WH well (raw 5m MR/impact KILLed at 5m resolution; tick may differ).
**Posture (locked):** stop vanity-grinding mapped thin/redundant veins; prioritize these data-tier unlocks; KEEP report-only Library expansion + new-premium staging active. Reachable space better-mapped ≠ research done.

# STAGED NEXT PACKETS (ready-to-run, 2026-06-24, report-only) — queue stays live while shells compute
Concrete construction specs, judged by PORTFOLIO ROLE (Sharpe-improver / small-diversifier / tail-overlay / capacity / separate-pool), DSR-gated, corr-vs-actual-ORB-PnL:
- **XSMOM (cross-sectional momentum / relative-strength)** *(class B, priority 4)* — rank {MNQ,MES,MGC,MCL,M2K} by trailing 1/3mo return; long top-2 / short bottom-2, dollar-neutral, weekly rebalance. DISTINCT from TSMOM (relative not absolute → possibly decorrelated from both ORB AND TSMOM → could add a 3rd regime). Cheap-screen → if decorrelated+positive → small-sleeve allocation curve.
- **Month-end rebalance drift** *(class B, priority 3)* — last-2 / first-1 trading days, MES/MNQ vs ZN (pension/balanced rebalance flow); direction conditioned on intra-month equity-vs-bond divergence. No-lookahead (month return known by last 2 days). Calendar-mechanical.
- **Cross-asset carry portfolio** *(class B/carry, priority 3)* — combine reachable carries (rates roll-down [deployed Treasury-Rolldown], commodity roll [S1 thin], FX carry via rate differentials) into ONE diversified carry sleeve; test as separate-pool premium. Carry premium = different from momentum/vol.
- **WH engine composite-filter sweep** *(class A, priority 3)* — re-sweep ORB-family entries × COMPOSITE filters (ema_slope+session_morning, ema_slope_vol_high) × profit_ladder, on MNQ/MES/MGC — does a composite filter beat single ema_slope? (one more engine-routed WH shot).
- **Options/gamma** *(class D, packetize)* — dealer-gamma pinning needs SPX/single-name options OI = largely BLOCKED → write feed-requirement packet (reachable: ^GEX-style proxies? CBOE data?), do not force.

Data-tier packetization (the unlock for a Sharpe-COMPARABLE edge per [[feedback_high_sharpe_incumbent_diversification]]): true VIX-futures curve (vs SVXY ETP), front/2nd futures term structure, tick/L2/order-flow, options surface, better COT transforms. Library → 100+ continues. WH-family ideas → engine. Completed dossier section / running shell ≠ pause.

# UPDATED PRIORITY QUEUE (post untried-assets batch)
**Class-E process (install — hardens the machine, highest leverage):** L1 Deflated-SR+PBO → L2 CPCV → I1 premia-classification.
**ORB-improvement lead:** L3 meta-labeling on ORB (the one untried improvement angle; N4-sizing failed but feature-based precision filtering is different).
**WH engine lane:** untried-assets results (batch-24d) → survivors to sleeve-addition + DSR/PBO; then composite-filter sweeps.
**Sparse/carry/ensemble:** I2 TSMOM, C1 cointegration pairs (WTI-Brent, ZN-ZF), N1 VX-carry (probe VX), S2 commercial-COT.
**Packet count:** ~50 across 7 books → continue to 100+.

## Boundaries
Report-only; no promotion/wiring/scheduler/registry/portfolio mutation. Packets are hypotheses, not candidates, until cheap-screened. Every breakout/stop-based packet MUST use intraday first-touch + gap-aware fills (D2 lesson). Every vol packet MUST pass the incremental-value test vs VIX/prior-day/RV (O1/O2 lesson). Every sweep SURVIVOR must clear Deflated-SR/PBO (L1) before being called more than a screen pass (multiple-testing control). Every same-premium addition must pass the sleeve-addition battery (FIP lesson).
