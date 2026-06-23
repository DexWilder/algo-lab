# Crypto Mechanism Packets — 2026-06-22

> Build-before-test. NOT "BTC breakout grids." Crypto-NATIVE forced-flow only: each packet names the forced participant, the mechanism-IMPLIED direction+timing, data (reachable per source ledger), no-lookahead, cheap-screen, kill criteria. Same discipline as the rates mechanism packets. Report-only.

## C1 — Funding-rate mean-reversion (extreme funding → unwind)
- **Forced participant:** at extreme positive funding, crowded LONGS pay a large carry → marginal longs forced to close → price pressure DOWN; extreme negative funding → crowded shorts pay → squeeze UP.
- **Implied direction:** funding >> norm → SHORT perp (or fade longs); funding << norm → LONG. Hold ~1-3 funding periods.
- **Data:** OKX/Deribit funding history; perp price. **No-lookahead:** funding for period t is set at t-start (known). **Kill:** no edge at extremes / cost (perp fees+funding) eats it / not robust across funding-threshold band.

## C2 — Funding-time drift (pre-funding positioning)
- **Forced participant:** traders position into/around the 8h funding stamp (00/08/16 UTC) to receive/avoid payment → predictable drift in the bars around funding.
- **Implied direction:** depends on funding sign — when longs must pay (pos funding), pre-stamp selling to avoid payment → fade up into stamp. **Direction conditioned on funding sign.**
- **Data:** funding stamps + intraday perp bars. **No-lookahead:** funding sign known before stamp. **Kill:** no consistent stamp-window drift / cost.

## C3 — Perp-basis compression/expansion (leverage-demand state)
- **Forced participant:** high perp-spot basis = leveraged-long demand; basis spikes mean-revert as arbs (cash-and-carry) step in.
- **Implied direction:** basis >> norm → short perp / long spot (or fade perp); basis << norm → opposite. State/relative, not naive direction.
- **Data:** Deribit perp index vs Coinbase/Kraken spot. **Kill:** no reversion / arb cost.

## C4 — Liquidation-cascade reversal (DATA-LIMITED)
- **Forced participant:** forced liquidations cascade price beyond fair value → snapback as forced selling/buying exhausts.
- **Implied direction:** after a large down-liquidation spike → LONG snapback (and mirror).
- **Data:** liquidation feeds were on Binance/Bybit (BLOCKED). Proxy: large OI drop + price spike. **Status: DATA-LIMITED** until a reachable liquidation source / OI-flush proxy is built. Lower priority.

## C5 — Weekend liquidity regime (no futures equivalent)
- **Forced participant:** thin weekend liquidity (institutions out) → different vol/trend behavior; Monday repositioning.
- **Implied direction:** test weekend vs weekday regime (range/trend/gap into Monday). Calendar-mechanical, crypto-only.
- **Data:** Coinbase/Kraken spot (24/7). **No-lookahead:** calendar. **Kill:** no weekend/weekday separation that survives cost.

## C6 — OI-flush continuation/reversal
- **Forced participant:** sharp open-interest drop = mass position closing (delever) → exhaustion (reversal) or trend-confirmation (continuation).
- **Data:** OKX OI history. **Kill:** no edge / OI data too coarse.

## Priority to run (after acquisition)
1. **C1 funding mean-reversion** — cleanest forced-flow, direction mechanism-implied, OKX funding reachable, deep history.
2. **C3 perp-basis** — leverage-state, reachable (Deribit perp + spot).
3. **C5 weekend regime** — calendar-mechanical, crypto-unique, cheap.
4. C2 funding-time (intraday, needs fine bars), C6 OI-flush, C4 liquidation (data-limited).

## RESULTS / acquisition findings (2026-06-23)
- **C5 weekend-liquidity → KILL** (`forge_cycle_2026-06-23a`, BTC/ETH/SOL, deep Coinbase price). Predeclared weekend-FADE (Monday fades Fri→Sun move) PF 0.73-0.78 negative all coins, PF@40bps worse → mechanism direction WRONG (weekend moves CONTINUE, not revert). Did NOT flip to continuation (= long-crypto-beta-timing, no forced-flow story = fishing). Exploratory DoW map: consistent cross-coin Thu-weak / Mon-Wed-strong, but beta-timing category (like MES-Monday) — logged, not pursued.
- **C1/C3 UNBLOCKED via Deribit:** Deribit funding history is DEEP (BTC-PERPETUAL 2020+, hourly, ~744/call → paginate ~31-day windows). Fixes the OKX 3-mo cap that made C1 DATA-LIMITED. **C1 funding-mean-reversion is now properly retestable on deep Deribit funding** = highest-value next crypto step (flagship forced-flow mechanism, now has the data).

## C1 RETESTED ON DEEP DATA (2026-06-23) → KILL (real verdict) + mechanistic insight
`forge_cycle_2026-06-23b`, Deribit 2020-2026 (2366 days, ~260 extreme events/coin). **C1 funding-mean-reversion (directional) = KILL** (BTC PF 0.744, ETH 0.784, both 1/7 yrs+). Decomposition: shorting high-funding lost on PRICE (−83/−88%) because crypto trended UP (crowded longs were right; funding stays high BECAUSE the trend persists); funding carry collected (+19.7%) didn't offset. **Did NOT flip to momentum** (= long-crypto-beta, no independent story). Both coins agree → robust KILL.
**INSIGHT: funding is a CARRY signal, not a DIRECTIONAL one.** The real funding edge is DELTA-NEUTRAL (long spot / short perp, harvest funding while hedged) = a market-neutral carry sleeve (Track-A ensemble candidate, low corr), NOT a directional workhorse. → reframes C3.

## C3 reframed — DELTA-NEUTRAL funding/basis carry (the mechanistically-correct use)
- **Mechanism:** when perp funding is persistently positive, long spot + short perp collects funding delta-hedged; basis/funding = the carry yield. Forced participant: leveraged longs pay funding to the hedged carry-provider.
- **Test:** funding-carry yield (after both legs' costs + borrow) vs realized vol; is the net carry positive and stable? Market-neutral → judge by Sharpe/consistency + correlation to bench (P-SLEEVE), NOT directional PF.
- **Status: NEXT** — Deribit funding (have) + spot (Coinbase, have). Delta-neutral so price-direction risk hedged; the question is whether net carry survives execution cost.

## C3 ATTEMPTED → CONSTRUCTION-INVALID (NOT a KILL) — timestamp misalignment (2026-06-23)
`forge_cycle_2026-06-23c` showed delta-neutral carry net −55% to −95% → SUSPICIOUS (gross funding is +6.8%/yr positive). Audit: **corr(spot_ret, perp_ret)=0.95 (should be ~0.999), daily basis-drift std=1.0% (should be ~0.1-0.2%)** → Deribit perp sampled at a different intraday clock (last hourly funding stamp ~23:xx UTC) than Coinbase daily close (00:00 UTC) → the hedge isn't truly delta-neutral → −55% is a sampling artifact, NOT a carry verdict. **Status: CONSTRUCTION-INVALID / INCONCLUSIVE.** Did NOT report as KILL (would be a false negative from a data bug — same discipline as data-limited≠kill).
**FIX (next):** sample BOTH legs at the SAME UTC timestamp — either Deribit perp + Deribit-index-spot at matching stamp, or align Coinbase spot to the perp sample time; then basis-drift std should drop to ~0.1-0.2% and the hedge actually neutralizes. Re-run C3 only after same-timestamp alignment. Crypto carry remains a live ensemble candidate (untested-properly), NOT killed.

## C3-FIXED attempt 2 → STILL CONSTRUCTION-INVALID (hedge-validation gate held)
`forge_cycle_2026-06-23d`: tried Deribit perp daily candle (tradingview 1D) + Coinbase daily — hedge STILL not clean (corr 0.72, drift std 2.4%; cross-venue daily-bar boundaries differ). **Hedge-validation gate (printed BEFORE verdict) correctly REFUSED to report carry metrics → CONSTRUCTION-INVALID, no false KILL/bank.** Two alignment attempts failed (funding-stamp index ~23:xx; tradingview 1D ticks) → clean cross-venue DAILY alignment isn't achievable from free daily candles.
**PROPER FIX (next, deeper acquisition): intraday SAME-TIMESTAMP pairs** — Deribit hourly perp aligned to the funding-record index_price stamps (basis = perp/index at IDENTICAL stamps), or any single-venue perp+index at one resolution. Then corr→~0.999, hedge neutralizes, carry judged. **C3 carry remains UNRESOLVED (not killed, not banked) — DATA/CONSTRUCTION-limited pending same-stamp intraday data.** It is STILL the best crypto ensemble candidate; just genuinely hard to validate on free daily cross-venue data.

## C3 → DATA/CONSTRUCTION-BLOCKED (one proper intraday attempt done; packetized)
`forge_cycle_2026-06-23d` + intraday probe: tried Deribit perp HOURLY candle vs funding-record index hourly → **corr −0.017** (basis LEVELS tight at 68bps std = same asset, but perp candle-close vs index-stamp are ~59min-offset instants → returns don't align). Free Deribit endpoints cannot deliver synchronized perp-mark + index at the IDENTICAL second. **Verdict: DATA/CONSTRUCTION-BLOCKED (NOT KILL).** One clean intraday attempt done per operator boundary.
**FEED REQUIREMENT (packetized):** synchronized perp-mark AND index at the identical timestamp — sources: Deribit book/ticker snapshots (build a recorder), a paid crypto data vendor with aligned perp+index, or exchange tick data. Until then C3 carry is UNRESOLVED (best crypto ensemble candidate, blocked on data sync — not a strategy verdict).

## NEW VEIN OPENED — Deribit options / vol-surface (richer ore, reachable)
Probed reachable: **DVOL (Deribit BTC volatility index, VIX-equivalent) — daily OHLC, deep history** (paginates); 892 live BTC option instruments. DVOL sidesteps the perp/index hedge-timestamp problem (single clean daily series). Mechanism packets:
- **O1 — vol-risk-premium:** DVOL (implied) vs trailing realized vol → when IV >> RV (rich vol), structural short-vol/vol-mean-reversion bias; forced participant: option buyers overpay for protection. Single daily series, no hedge-sync issue. PRIORITY next.
- **O2 — DVOL mean-reversion / regime:** DVOL extreme → mean-revert; or DVOL regime as a FILTER/risk-throttle on other sleeves.
- **O3 — expiry/pinning** (needs option chain history — snapshot-only live; harder).
- **O4 — DVOL as a cross-asset risk-state** gating equity/crypto sleeves.

## O1 DVOL variance-risk-premium → STRUCTURE_FOUND (first real crypto edge; cost-gated)
`forge_cycle_2026-06-23e`. DVOL (Deribit BTC implied-vol index, 1918d 2021-2026) vs 30d realized vol → VRP = IV−RV; predeclared **rich VRP (z>1) → LONG spot next day** (fear overpriced; option buyers overpay for protection). NO flip.
- **BTC: PASS strict gates** — PF 1.201, mean +20.9bps, max-single 3.4%, top3 9.0%, yrs+ 5/6, **corr to MNQ −0.055** (decorrelated), and **beats unconditional long +20.9 vs −3.3bps** (real conditioning edge, not beta).
- **ETH: same direction confirms** (+16.2 vs −4.9bps) but weaker → KILL on strict gates. Mechanism direction right on both coins.
- **Monotonic dose-response (key validation):** z>0.5 PF 1.013 / z>1.0 1.201 / z>1.5 1.485 / z>2.0 2.770. Richer overpriced-fear → bigger bounce. Not a threshold cherry-pick.
- **Per-year:** 2021 +43.8 / 2022 −25.3 (LUNA/FTX crash — fear was UNDERpriced, fade fails: mechanism-coherent regime weakness) / 2023 +7.9 / 2024 +51.7 / 2025 +25.3 / 2026 +21.8 bps. 5/6 positive, bad year bounded.
- **HARD CONSTRAINT — cost:** PF 1.201@10bps → 1.100@20bps → **0.924@40bps (KILL)** → 0.778@60bps. z>1.0 edge DIES at retail crypto spot taker fees (~40-60bps); survives only ≤~25bps (institutional/maker). The **z>1.5 variant (mean +55bps) is materially more cost-robust** (survives ~40bps) — that, not z>1.0, is the tradable expression.
- **Verdict: STRUCTURE_FOUND (NOT deployable as-is).** First genuine crypto mechanism (every prior crypto test KILLed). Decorrelated-from-equity ensemble property is exactly what WH2-diversification wants. GATED on: (1) realistic BTC-spot execution cost — what can the account actually trade at? if >30bps, z>1.5 only; (2) regime-aware crash guard; (3) ETH/SOL breadth weaker. Report-only; no mutation; no promotion.

## O1-z>1.5 FULL-GATE + CRASH-GUARD audit (2026-06-23f) — candidate confirmed STRUCTURE_FOUND, NOT deployable
Operator correction applied: **z>1.0 = mechanism EVIDENCE; z>1.5 = the CANDIDATE** (cost-robust). Full-gated z>1.5 (n=77):
- **Cost-robust ✓** PF 1.485@10 → 1.28@30 → 1.19@40 → **1.04@60bps** (z>1.0 died @40). This is why z>1.5 is the candidate.
- **Decorrelated ✓** MNQ −0.03, MES −0.03, MGC −0.22; low concentration (max-single 9.4%, PF-ex-top3 1.11); beats unconditional hold (55 vs 7.5bps); makes PnL OUTSIDE opex week (diversifier vs existing sleeves).
- **Temporal stability ✗ (the brake)** H1 PF 0.938 (LOSES, −10.5bps) / H2 2.976; only **4/6 yrs+** (2023 −25, 2025 −12bps); 2024 (+117) & 2026 (+156) carry it. Tightening to cost-robust threshold made per-year stability WORSE (n=77, some yrs n=4). Crash regime (BTC>50% off ATH) PF 0.933.
- **CRASH-GUARD packet result:** NO regime filter rescues stability — spot>200dSMA (uptrend) still 2025 −390bps on n=34; "not-rising-vol" guard INVERTS edge to PF 0.52. **Mechanistic finding: the VRP-fade edge LIVES in elevated/rising-vol periods, not calm** (fading rich DVOL works when vol is high). 2025 weakness is genuine, not filter-removable.
- **HEADLINE TENSION: no single threshold is both cost-robust AND temporally stable** — z>1.0 stable(5/6)/cost-fragile(dies@40); z>1.5 cost-robust(60bps)/unstable(4/6, H1<0). Mechanism real; neither expression clean.
- **Disposition:** STRUCTURE_FOUND / COST-GATED / REPORT-ONLY. Resolution = out-of-sample forward accrual (report-only clock), NOT more filtering. Forward-clock candidate (Track-2 EXPERIMENTAL_FORWARD_CLOCK) pending operator decision; needs real BTC-spot execution cost pinned. NO promotion/wiring/mutation.

## O2 DVOL cross-asset regime overlay (2026-06-23g) — KEY PIVOT: mechanism's tradable home may be EQUITY
DVOL as risk-state filter on existing equity/gold daily (no-lookahead DVOL_t → ret_t+1; n~1581):
- **Cross-asset consistent (mechanism validation):** DVOL_spike z>1.5 → next-day **MNQ +20.5bps (PF 1.52) / MES +16.4bps (PF 1.59)**, lift +14/+12bps vs uncond. DVOL high-pct>0.8 → equity +13.8/+10.3 (lift +7.7/+6.1); DVOL low-pct<0.2 → equity −2.2/−0.7 (lift −8/−5). MNQ & MES agree direction+magnitude. MGC largely indifferent (+3-5bps, no strong gold-hedge angle).
- **INSIGHT: O2 == O1 mechanism (rich/spiking implied vol → next-day risk-asset bounce, fear overpriced) measured on EQUITY.** Cross-asset consistency (BTC + MNQ + MES all show it) = strong mechanism validation.
- **DEPLOYMENT PIVOT:** crypto expression cost-gated (O1 dies at retail spot fees); **equity execution is ~1-2bps (MES/MNQ futures) → the mechanism's TRADABLE HOME may be equity, not crypto.** "DVOL-spike z>1.5 → next-day long MES/MNQ" could be cost-viable where crypto isn't.
- **Status: promising v1 screen (raw returns, pooled).** NOT banked as edge. Needs: full-gate (H1/H2, per-year stability — same brake that hit O1-z>1.5), test on ACTUAL ORB-sleeve PnL (overlay) vs as a standalone long-tilt, DVOL close-stamp vs US-open no-lookahead confirm, cost/robustness. Report-only; no mutation.
- **NEXT TEST (highest-value):** full-gate "DVOL-spike z>1.5 → next-day long MES" at equity costs — if per-year stable, this is the actually-deployable expression of the VRP mechanism.

## O2-EQUITY FULL GATE (2026-06-23h) → V2 PASS_REVIEW (best lead of session; report-only, not deployable)
Rigorous no-lookahead (5m bars ET confirmed via 17:00 CME halt; DVOL close 00:00 UTC = ~19-20:00 ET prior eve, known ~13h before T 09:30 entry). DVOL-spike z>1.5 → long MES/MNQ. Predeclared variants V1 intraday / V2 24h-hold.
- **Edge is OVERNIGHT, not intraday:** V1 (09:30→16:00) KILL both (PF ~1.0, ~0bps — no RTH bounce). V2 (09:30 T→09:30 T+1, overnight-concentrated) PASS_REVIEW both.
- **V2 stability (clean — the gate O1-z>1.5 failed):** MNQ H1/H2 1.39/1.27, **6/6 yrs+** (2021 +43→2026 +6bps); MES 1.38/1.51, 5/6 (2022 flat). Low concentration (max-single 3.8-5.5%). Survives 6bps cost (PF 1.26-1.34).
- **DECISIVE incremental validation — DVOL is NOT a VIX proxy:** DVOL-spike WITHOUT VIX-spike (108/123 days) = mean 18.9bps MES / 21.6bps MNQ, PF 1.54-1.65 — STRONGER than pooled. Also survives no-realized-vol-spike control (PF 1.2-1.4). DVOL carries unique info.
- **Qualifier 1 — ~70% is post-selloff dip-buying:** followDOWN +22-26bps PF 1.6-1.74 vs followUP +5-7bps PF 1.1-1.19. Residual DVOL-specific edge survives after up-days (not PURELY dip-buying) but most of it is.
- **Qualifier 2 — fat left tail:** worst-5 sum −12.9% MES / −17.3% MNQ vs ~+18% gross. Overnight gap risk material; MES gentler tail, MNQ better consistency. Needs tail-aware sizing.
- **Verdict: V2 PASS_REVIEW (report-only).** Cross-market translation worked: crypto-discovered fear signal → stable, cost-viable, VIX-incremental equity overnight hold. NOT deployable yet. NEXT: (a) isolate the pure overnight leg (16:00→09:30) + tail clustering audit; (b) marginal-value regression (DVOL coef controlling for prior-ret + VIX); (c) sleeve-overlay on actual MNQ ORB workhorse PnL; (d) MES-vs-MNQ risk-adjusted. No mutation.

## Revised priority (2026-06-23, post-O2-equity PASS_REVIEW)
1. **O2-equity refinement:** overnight-leg isolation + tail-clustering + marginal-value regression + sleeve overlay on real ORB PnL (standalone long-tilt vs filter/overlay — operator's split).
2. Mechanism Library lane kickoff (Harris + Natenberg/Sinclair).
3. O1 crypto = evidence-only unless BTC all-in execution <~30bps (operator input).
4. C3 carry — blocked pending synchronized perp+index feed.

## Revised priority (2026-06-23, post-full-gate)
1. **O2 — DVOL as cross-asset regime/risk-state filter on existing equity/gold/rates sleeves** (execution-cost-FREE; gates books we already trade) — NEXT.
2. O1 forward-clock (report-only) to accrue OOS years — pending operator go + execution-cost number.
3. Mechanism Library lane kickoff (Harris + Natenberg/Sinclair first) — standing parallel lane.
4. SOL/breadth only if data clean (don't force; BTC is the liquid expression, ETH already weaker).
5. C3 carry — blocked pending synchronized perp+index feed (packetized).

## Revised priority (2026-06-23)
1. **C1 via Deribit deep funding** (now unblocked) — flagship forced-flow, mechanism-implied direction, deep data. Acquire Deribit funding 2020+ + price, rerun C1 with full PnL decomposition.
2. **C3 perp-basis** (Deribit perp index vs spot) — also unblocked.
3. More crypto PRICE rungs (vol compression/expansion, post-large-range MR, Asia→US handoff) — but DoW/beta-timing rungs deprioritized (C5 showed they're beta).
4. C2/C6/C4 — fine-bar/OI/liquidation data checks.

## Boundaries
Report-only; mechanism-implied direction (no fishing/flipping — C5 honored this); no mutation.
