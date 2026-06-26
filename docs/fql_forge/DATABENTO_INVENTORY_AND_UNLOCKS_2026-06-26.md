# Databento (and feeds) inventory + unlocks — DATA_INVENTORY_RESET (2026-06-26)

> Correction of the premature "free/cheap data exhausted → paid-data fork" claim. That was stated before inventorying
> what we actually hold. This is the honest inventory. Report-only.

## 1. Databento holdings (data/databento/)
- **Schema: `ohlcv-1m`** (GLBX.MDP3), via `data/databento_loader.py`. → 1-minute **OHLCV + VOLUME**. NOT trades, NOT
  bid/ask (BBO/TBBO), NOT MBP/MBO, NOT depth.
- **Symbols: `.c.0` continuous front-month** (calendar-roll, raw stitch). NOT individual contracts → contract-level
  basis/roll-detail limited; roll-stitch artifacts present (esp. MCL — known).
- **11 instruments:** MNQ, MES, MGC, MCL, M2K (equity/metal/energy micros) + ZN, ZF, ZB (rates) + 6E, 6J, 6B (FX).
- **Granularity/coverage:** 1m files ≈ 2024-02 → 2026-03 (~2yr). 5m processed (downsample) ≈ 2019 → 2026 (~7yr).
  → 1m-native work is sample-limited to ~2yr; 5m gives 7yr. BOTH carry VOLUME.

## 2. data/feeds/ library (under-used — inventory before re-fetching!)
cot.csv (COT — already local; I needlessly re-pulled from API), cpi_levels, credit_oas, copper_gold_ratio_yahoo,
deribit_BTC_PERPETUAL, deribit_DVOL_BTC/ETH, + more. Rule going forward: check data/feeds/ BEFORE any external fetch.

## 3. CORRECTED conclusion (replaces the overbroad claim)
- **What's TRUE:** the daily/close-based OHLC + free-event-calendar mechanisms tested so far (month-end, overnight,
  COT-reversal, auction, TSMOM, vol-carry, ORB-family) are insufficient or dead.
- **What was WRONG:** "free data is exhausted." We have **1-minute bars + VOLUME, entirely unexplored** — every test
  to date used CLOSE PRICES ONLY. Volume and 1m microstructure are an unexplored vein, buildable now, no spend.
- **What still needs paid data:** bid/ask spread, trade-flow imbalance, order-book pressure (MBP/MBO), true L2
  microstructure — genuinely absent from `ohlcv-1m`. So the paid-data memo is **PROVISIONAL, not final**.

## 4. Mechanisms buildable NOW from ohlcv-1m + volume (the new factory lane)
T1/microstructure-lite (no spend):
1. **Volume imbalance** — up-minute vs down-minute volume; aggressive-direction proxy (close-vs-open per minute × volume).
2. **VWAP deviation / reversion** — intraday price vs session VWAP (volume-weighted), extension → reversion.
3. **Volume-confirmed breakouts** — breakouts on high relative volume vs low (filter, not new entry).
4. **Intraday realized-vol / liquidity regime** — 1m RV, volume-per-minute regime as a state filter for existing signals.
5. **Opening-minutes behavior** — first 1-5 min volume/range → session direction or fade (point-in-time).
6. **Time-of-day volume seasonality** — liquidity troughs/peaks; trade only in liquid windows.
7. **Volume climax / exhaustion reversal** — extreme 1m volume spikes → short-term reversal.
8. **Relative-volume (RVOL) event detection** — abnormal volume as an endogenous "event" without a calendar.
9. **Execution-cost model upgrade** — use real per-minute volume to model participation-rate slippage (improves EVERY prior cost estimate).
10. **Volume-weighted overnight/gap** — gap fills conditioned on volume (the overnight premium leg, volume-refined).

Still PAID (not in ohlcv-1m): bid/ask spread regime, trade-flow/aggressor imbalance, order-book pressure, queue dynamics.

## 5. Prior kills/shelves that may deserve RETEST with volume/1m features
- ORB / breakouts: tested close-only on 5m; **volume-confirmation filter + 1m entry timing** is a different test (retest-eligible — BUT the ema_slope lookahead is separate and must stay fixed).
- Overnight premium: refine with volume (was cost-fragile; better cost model + volume timing may change net).
- Intraday mean-reversion / VWAP: never tested with actual VWAP (volume-weighted) — prior MR used close only.
- Opening-range: 1m granularity gives a cleaner OR than 5m.

## 5b. Volume-native factory log
- **P14 VWAP-deviation reversion → CLEAN_KILL** (2026-06-26). All sides negative (MES/MNQ per-trade Sh ~−0.04 to −0.10;
  MGC below-fade ~0), pooled −0.058, DSR 0.0. Fading VWAP-extension LOSES → extension CONTINUES intraday (momentum-biased,
  consistent with overnight/intraday finding). Reversion was the wrong first pick. **Implication: test volume-CONFIRMED
  MOMENTUM, not reversion.** Next volume packets: (a) volume-confirmed breakout/continuation; (b) volume-imbalance /
  aggressor-proxy order-flow; (c) RVOL as a regime FILTER on existing signals; (d) volume-climax exhaustion; (e) opening-
  minutes 1m behavior. Vein NOT exhausted by one reversion test.

## 6. Revised hunt hierarchy
1. **Databento-native (1m + volume) packet factory FIRST** — unexplored, free, ~20 packets, truth-gate first, every test counts toward N.
2. Then the paid-data decision (memo, now provisional) — gamma/VIX-curve/trades/L2.
The "next edge costs money" conclusion is SUSPENDED until the volume/1m vein is worked.
