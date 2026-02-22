# Lucid 100K — Changelog & Lessons Learned

## Strategy Overview
- **Goal**: Pass Lucid 100K straight-to-funded eval, then maximize payouts
- **Instruments**: MES (primary lock engine), MGC (diversifier), MNQ (payout engine)
- **Timeframe**: 5-minute
- **Architecture**: Dual-algo regime-switching (Trend Pullback + VWAP Mean Reversion)
- **Prop Rules**: $4,000 EOD trailing drawdown, locks at +$3,100 profit, 80-90% split

---

## Version History

### v1 / strategy.pine (GPT original)
- Basic dual-algo with regime detection
- Phase sizing (2 → 5 contracts after $3,100)
- Prop guardrails: 3 trades/day, $600 daily loss, 2 consec loss halt
- `process_orders_on_close=true` (unrealistic fills)

### v4 — Claude (lucid_v4.pine)
- Break-even stop at 1R (replacing trailing)
- Session warmup (15 min)
- Stronger entry confirmation (prior bar high/low break)
- Reversion blackout (30 min from open)
- Performance-gated Phase 2 (PF check)
- Weekly loss guard
- Cooldown after halt (reduced contracts next day)
- Lucid EOD drawdown simulation
- `process_orders_on_close=false` (realistic fills)

### v4 — GPT
- Phase-aware mode switching (P1 Trend-only, P2 Auto)
- Phase-aware MTF filters (P1 strict 15m+60m, P2 relaxed 15m only)
- Phase-aware guardrails (different limits per phase)
- Best time windows (AM/PM power windows)
- Dynamic throttle (P1 down day → trend-only)
- Trail after +1R

### v5 — Ultimate (lucid_v5_ultimate.pine)
- **Merged Claude v4 + GPT v4**
- 3-stage exits: SL/TP bracket → Break-even at 1R → Trail at 1.5R
- All phase-aware features
- Range expansion filter (bar >= 60% avg range)
- VWAP slope check (flat VWAP for reversion)
- Stronger rejection candle (40% wick ratio)
- Entry markers on chart (PB/REV triangles, BE/TR diamonds)

### v6 — Final (lucid_v6_final.pine)
- Phase-aware exit parameters (separate P1/P2 SL/TP/BE/Trail)
- Risk-per-trade dollar cap
- Intraday drawdown guard (phase-aware)
- `syminfo.pointvalue` auto-detection for multi-asset
- Force Trend-only P1 toggle
- Full Lucid EOD trailing drawdown sim with bust/lock detection
- Learning metrics (days to target, halt counts by type)
- Complete status label with all diagnostics

### v6.1 — Patched (GPT patches integrated by Claude)
- **Risk cap → qty cap**: ATR stops never squeezed; contract qty capped instead
- **Stable P2 gate**: PF 1.1 / 25 trades (was 1.2 / 10) + `blockP2AfterHalt` + `usePhase2Gate` toggle
- **Time-based warmup**: `(time - sessionOpenTime) / 60000` instead of bar count (works on any TF)
- **Strong close entry**: `closePos >= 0.80` / `<= 0.20` as OR alternative to prior-bar break

### v6.2 — Current (GPT patches + Claude validation)
- **Min stop ticks floor**: `minStopTicks=20` prevents ATR compression from creating absurd stops
- **Actual fill price**: `strategy.position_avg_price` for BE/Trail math (not signal bar close)
- **Reversion MTF toggle**: `revRequireMTF` — Claude set default to `true` (GPT had `false`)
- **DD after green peak**: `ddOnlyAfterGreen` toggle — only count intraday DD if day was profitable first
- **entryPx := na reset**: Clean state machine between trades
- **Status label**: Added min stop display, total trades count, cleaner risk formatting

---

## Key Lessons Learned

### Entry Quality
- **Crossover entries fail on MES 5m** — Ultimate Combo v1 proved this (86 trades, -$1,121, 0.506 PF)
- **Pullback entries are safer** — wait for price to pull back to EMA21, then confirm with prior-bar break or strong close
- **51% of crossover trades lasted ≤5 minutes** — instant stops from entering at the peak of momentum
- **Strong close (top/bottom 20%) catches momentum** that doesn't quite break prior bar extremes

### Exit Management
- **Trailing stops from entry = bad** — gets stopped out before trend develops
- **3-stage approach works**: bracket → BE → trail, each activated by R-multiples
- **Break-even at 1R protects capital** without cutting winners too early
- **Trail only after 1.5R** — gives enough room for the trade to breathe
- **Never squeeze stop distance for risk** — cap contract quantity instead

### Risk Management
- **ATR compression creates tiny stops** — the minStopTicks floor (20 ticks) prevents this
- **Risk per contract = stopDist * pointVal** — cap qty, not stop distance
- **Process_orders_on_close=false is critical** — realistic fill simulation
- **Use actual fill price** (strategy.position_avg_price) for all post-entry math

### Prop Firm Specific
- **Phase 1 = survival mode**: trend-only, strict MTF, 2 trades/day, tight guardrails
- **Phase 2 gate needs stability**: PF 1.1 over 25 trades (not 1.2 over 10 — too noisy)
- **Block Phase 2 after halt day** — if guardrails fired yesterday, don't scale up today
- **Cooldown sizing** — day after halt, reduce to 1 contract
- **Dynamic throttle** — P1 losing day disables reversion entirely
- **Mean reversion needs MTF protection in P1** — counter-trend trades against HTF = danger

### Session/Timing
- **15-minute warmup avoids open volatility**
- **Time-based warmup** (not bar-count) works across all timeframes
- **Reversion blackout (30 min)** — don't mean-revert in the first 30 min
- **Power windows**: AM 08:45-11:00, PM 13:30-15:10

### Architecture
- **Regime detection (ADX + EMA slope + VWAP slope)** correctly routes to trend vs reversion
- **Phase-aware everything** — mode, MTF, guardrails, exits, sizing all differ by phase
- **Forward references in Pine Script** — `var` declarations must appear before first use
- **Initial bracket uses `close`** because fill price is unknown at signal time — acceptable tradeoff

---

## Backtest Results Log

| Version | Instrument | Period | Trades | Win% | PF | Net P&L | Max DD | Notes |
|---------|------------|--------|--------|------|----|---------|---------|----|
| Ultimate Combo v1 | MES 5m | ? | 86 | 47.7% | 0.506 | -$1,121 | ? | Crossover entries — failed |
| Lucid v6.2 | — | — | — | — | — | — | — | **PENDING TEST** |

---

## Parameter Sweep TODO
- ADX min: test 14, 16, 18, 20
- revDistATR: test 1.2, 1.4, 1.6, 1.8
- tpATR P1: test 1.8, 2.1, 2.5
- BE after R: test 1.0, 1.25, 1.5
- Trail after R: test 1.5, 1.75, 2.0
- revRequireMTF: test ON vs OFF
- ddOnlyAfterGreen: test ON vs OFF
- minStopTicks: test 15, 20, 25
- Power Windows ON vs OFF
