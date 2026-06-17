# Daily-Elite Pressure-Cooker — Idea Catalog — 2026-06-16

> Creative discovery, report-only. Target profile: frequent/near-daily cadence, distinct mechanism, prop-compatible DD, low MNQ correlation, enough trades to validate, robust across years/halves/rolling, concentration controlled, realistic after costs, simple to execute. **Gate is on promotion/activation/wiring/capital — NOT creativity.** Ideas ranked by composite of {portfolio usefulness, novelty, data availability, validation feasibility}. Mapping: `EXIST:<primitive>` = runnable now via crossbreeding engine; `NEW:<name>` = needs a (self-contained, non-production) research primitive.

## Ranking tiers
- **T1 (screen now):** runnable with existing or cheap new primitive, distinct mechanism, plausibly daily/near-daily, current data supports.
- **T2 (build then screen):** needs a new daily-structure primitive; high novelty.
- **T3 (needs new input/feed):** cross-asset confirmation / curve / COT — deferred to Lever-B, catalogued so we don't forget.

---

## FAMILY A — Failed-break / reclaim / exhaustion (mean-reversion of failed momentum)
| # | Idea | Assets | Primitive | Cadence | Tier |
|--:|---|---|---|---|---|
|A1|ORB failed-breakout reversal (fade the failed break back into range)|MGC,MYM,MES,MCL,ZN,ZF|EXIST:orb_failure_reversal|near-daily|T1|
|A2|First-hour failed drive / opening-drive exhaustion|MGC,MES,MYM,MCL|EXIST:opening_drive_exhaustion|near-daily|T1|
|A3|VWAP reclaim after washout (lose VWAP then reclaim)|MGC,MES,MCL,MYM|EXIST:vwap_reclaim|near-daily|T1|
|A4|Prior-close reclaim/reject (cross back through prior session close)|MGC,MYM,MES,MCL,ZN|NEW:prior_close_reclaim|daily|T2|
|A5|Overnight sweep + reclaim (sweep o/n high/low, reclaim into RTH)|MGC,MES,MCL|NEW:overnight_sweep_reclaim|daily|T2|
|A6|Post-trend exhaustion fade (N up-closes then fade)|MGC,MCL,ZN|NEW:post_trend_exhaustion|near-daily|T2|
|A7|False liquidity sweep of prior-day high/low then reverse|MGC,MES,MYM|NEW:pdh_pdl_sweep_reversal|daily|T2|
|A8|Stop-run reversal (already a workhorse mechanism) cross-asset re-confirm|MGC,MYM|EXIST:stop_run_reversal|near-daily|T1|

## FAMILY B — Compression → expansion (volatility regime)
| # | Idea | Assets | Primitive | Cadence | Tier |
|--:|---|---|---|---|---|
|B1|Narrow-range day (NR7) → next-day breakout|MGC,MYM,MES,MCL,ZN,ZF|NEW:narrow_range_expansion|daily|T2|
|B2|Inside-day → expansion breakout|MGC,MYM,MES,MCL,ZN,ZF|NEW:inside_day_expansion|daily|T2|
|B3|Range-compression intraday break (BB/KC squeeze release)|MGC,MYM|EXIST:range_compression_break|near-daily|T1|
|B4|Lunch compression release (midday squeeze → afternoon expansion)|MES,MYM,MGC|NEW:lunch_compression_release|near-daily|T2|
|B5|Volatility-contraction breakout (ATR pctrank low → break)|MGC,MYM,MCL|EXIST:bb_keltner_squeeze (re-screen non-archived assets)|near-daily|T1|
|B6|Prior-day-range percentile compression → expansion|MGC,ZN,MCL|NEW:pdr_compression_expansion|daily|T2|

## FAMILY C — Daily structural patterns (open/close/range geometry)
| # | Idea | Assets | Primitive | Cadence | Tier |
|--:|---|---|---|---|---|
|C1|Outside-day reversal (engulfing prior range → fade)|MGC,MYM,MES,MCL,ZN|NEW:outside_day_reversal|daily|T2|
|C2|Prior-day-break continuation (already gold-specific; re-confirm bounds)|MGC|EXIST:prior_day_break|near-daily|T1(banked)|
|C3|Prior-day midpoint reversion (revert toward pdm)|MGC,ZN,MCL|NEW:prior_day_midpoint_revert|near-daily|T2|
|C4|Gap continuation vs reversal BY REGIME (trend-up→continue, range→fill)|MES,MYM,MGC|NEW:gap_regime_split|daily|T2|
|C5|Open-in-prior-range vs open-outside (location-conditioned day type)|MGC,MES,MCL|NEW:open_location_daytype|daily|T2|
|C6|Two-day breakout (break 2-day high/low)|MGC,MCL,ZN,ZF|NEW:two_day_break|daily|T2|

## FAMILY D — Session / time-of-day asymmetries
| # | Idea | Assets | Primitive | Cadence | Tier |
|--:|---|---|---|---|---|
|D1|Afternoon continuation (trend persists into close)|MGC,MES,MYM,MCL|EXIST:afternoon_continuation|near-daily|T1|
|D2|Afternoon reversion (already dead on rates; re-screen gold/crude only)|MGC,MCL|EXIST:afternoon_reversion (gold/crude only)|near-daily|T1(low)|
|D3|Session-handoff edge (London→NY, NY→close momentum carry)|MGC,MCL,MES|NEW:session_handoff|near-daily|T2|
|D4|Last-hour structural drift / power-hour|MGC,MES,MYM|NEW:power_hour_drift|near-daily|T2|
|D5|Opening auction / cash-open behavior (first 5-15m structural bias)|MES,MYM,MGC|NEW:cash_open_bias|daily|T2|
|D6|Time-of-day asymmetry map (which hour has persistent skew per asset)|all|NEW:tod_asymmetry (diagnostic)|n/a|T2|

## FAMILY E — Behavioral state machines (post-outcome conditioning)
| # | Idea | Assets | Primitive | Cadence | Tier |
|--:|---|---|---|---|---|
|E1|Post-large-loss snapback (after big down day, mean-revert long)|MGC,MES,MYM,MCL|NEW:post_large_loss_snapback|daily|T2|
|E2|Post-large-win continuation vs fade (after big up day)|MGC,MES,MCL|NEW:post_large_move_followthrough|daily|T2|
|E3|Volatility-shock response (ATR spike → next-day behavior)|MGC,MCL,MES|NEW:vol_shock_response|daily|T2|
|E4|Consecutive-close state (3 up / 3 down → revert or continue)|MGC,ZN,MCL|NEW:consecutive_close_state|daily|T2|
|E5|Regime-gated trend vs MR (hurst state machine switches mechanism)|MGC,MES|EXIST filters: hurst_stable_trend / hurst_stable_mr|near-daily|T1|

## FAMILY F — Cross-asset state / confirmation (T3, needs multi-series alignment)
| # | Idea | Assets | Primitive | Cadence | Tier |
|--:|---|---|---|---|---|
|F1|Gold/Dollar confirmation (MGC long only when DXY/6E weak)|MGC×6E|NEW:cross_confirm (gold-dollar)|daily|T3|
|F2|Gold/Rates confirmation (MGC vs ZN real-rate proxy)|MGC×ZN|NEW:cross_confirm (gold-rates)|daily|T3|
|F3|Crude/Equity-risk confirmation (MCL with risk-on filter)|MCL×MES|NEW:cross_confirm (crude-risk)|daily|T3|
|F4|ZN/ZF curve confirmation (steepening/flattening gate)|ZN×ZF|NEW:curve_confirm|daily|T3|
|F5|Multi-index divergence (MNQ vs MYM vs M2K dispersion → mean-revert laggard)|MNQ/MYM/M2K|NEW:index_dispersion|near-daily|T3|
|F6|Risk-on/off composite filter applied to existing edges|all|NEW:risk_state_filter|n/a|T3|

## FAMILY G — Cleaner re-takes of archived failures (only with a NEW twist; not vanity re-runs)
| # | Idea | Assets | Primitive | Why not a vanity re-run | Tier |
|--:|---|---|---|---|---|
|G1|Overnight gap-hold ONLY on MGC (the one marginal survivor PF 1.106) + regime gate|MGC|EXIST:gap variant + new regime gate|adds regime gate to the lone survivor, not the dead grid|T2|
|G2|Donchian breakout cross-asset (only MNQ tried)|MGC,MYM,MCL|EXIST:donchian_breakout|primitive never screened off-MNQ|T1|
|G3|VWAP continuation (distinct from reclaim)|MGC,MES,MCL|EXIST:vwap_continuation|never broadly screened|T1|

---

## T1 screen-now tranche (this cycle)
EXIST primitives **not yet broadly screened off-MNQ**, mapped to wishlist:
`orb_failure_reversal` (A1), `opening_drive_exhaustion` (A2), `vwap_reclaim` (A3), `afternoon_continuation` (D1), `donchian_breakout` (G2), `vwap_continuation` (G3) — across MGC, MYM, MES, MCL, ZN, ZF (+ MNQ as correlation reference). Full WH2 board + MNQ correlation + cadence tier + brutal kill.

## T2 build-then-screen tranche (this cycle, self-contained new primitives)
Highest-novelty DAILY-cadence mechanisms unlocking multiple ideas:
`inside_day_expansion` (B2), `narrow_range_expansion` (B1), `outside_day_reversal` (C1), `prior_close_reclaim` (A4), `post_large_loss_snapback` (E1). Built in `research/wh2_daily_primitives.py` (NON-production, report-only), screened via the validated `run_backtest`.

## T3 deferred (catalogued, needs Lever-B / multi-series harness)
All FAMILY F cross-asset confirmation ideas + curve/COT. Not lost — queued for when feeds/alignment harness exist. These are the most likely source of a genuinely new *driver*-diverse daily engine.

## CYCLE 1 RESULT (`forge_cycle_2026-06-16p`) — brutal kill, one honest negative
Screened 58 candidates (T1 existing not-tried × assets + T2 new daily-structure primitives × assets). **Tally: 55 KILL, 1 REJECT_MNQ_COUSIN, 1 KILL_low_n, 1 apparent survivor — which then failed the additive check.**

- **MES donchian_breakout** → correctly REJECTED as MNQ-cousin (corr +0.55).
- **MGC donchian_breakout** → looked like the first *true-daily* (123/yr) non-MNQ candidate (PF 1.25, MNQ corr +0.12), BUT additive check: **+0.496 corr to the wired MGC-ORB book** and +0.441 to MGC prior_day_break, with H2 decay (1.42→1.17). **Verdict: REDUNDANT gold-breakout, NOT additive.** Marginal + decaying. Does not advance the mission.
- **Everything else died across all assets** — failed-break reversal, opening-drive exhaustion, vwap reclaim/continuation, afternoon continuation, inside-day, NR7, outside-day reversal, prior-close reclaim, post-large-loss snapback: all KILL on MGC/MES/MYM/MCL/ZN/ZF.

**Honest conclusion:** the off-MNQ daily-elite edge in current single-series data lives almost entirely in the **gold-breakout cluster** (ORB / prior-day / donchian) — one driver, one mechanism family, already captured. The *behavioral / structural / reversion* mechanisms (the real mechanism diversity) do not survive as elite edges. The daily-elite gap is therefore **not a creativity deficit** — it's that genuinely diverse daily mechanisms aren't present as elite edges in current single-series data.

**Next creative frontier (NOT exhausted, needs NO new feed):** the **cross-asset confirmation / divergence family** (catalog F1–F5) — gold↔dollar, gold↔rates, crude↔equity-risk, ZN↔ZF curve, multi-index dispersion — built from data we ALREADY hold, just time-aligned. That is the unexploited creative direction and the most likely source of a genuinely *driver-diverse* daily engine. Cycle 2 target.

## Kill-archive discipline
Every screened combo that fails is recorded in the cycle JSON with its blocker tag so we never loop. Archived-dead grids (NOT re-run): prior_day_break cross-asset, range_compression/first_impulse cross-asset, afternoon_reversion/bb_reversion/prior_day_fade on rates/FX, vol_expansion/keltner on non-equity, gap grids, TOM, FX-London, rate momentum/MR/pairs.
