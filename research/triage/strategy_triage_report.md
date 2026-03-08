# Strategy Triage Report — Algo Lab

## Harvest Summary

- **Total harvested scripts:** 54
- **Families:** vwap (23), orb (18), ict (13)
- **With Pine source:** 23

## Triage Results

| Label | Count |
|-------|-------|
| Convert Now | 8 |
| Hold for Later | 39 |
| Component Only | 3 |
| Already Converted | 3 |
| Reject | 1 |

## Cluster Map

Total clusters: 8

### VWAP-mean_reversion-2 (20 members)
- **Representative:** HYE Mean Reversion VWAP Strategy (AF=5)
- **Entry model:** mean_reversion
- **Members:**
  1. HYE Mean Reversion VWAP Strategy — AF=5, label=convert_now
  2. VWAP-RSI Scalper FINAL v1 — AF=5, label=already_converted
  3. VWAP Retest + EMA9 Cross + Candle Pattern V2 — AF=5, label=hold_for_later
  4. RSI of VWAP — AF=5, label=hold_for_later
  5. ES Scalping Pro: EMA + VWAP + ATR — AF=5, label=hold_for_later
  6. VWAP and RSI Strategy — AF=5, label=hold_for_later
  7. VWAP Mean Reversion v2 — AF=4, label=hold_for_later
  8. VWAP Bands Backtest — AF=4, label=component_only
  9. EMA and VWAP CROSS — AF=4, label=hold_for_later
  10. VWAP Breakout Strategy (Momentum, Vol, VWAP, RSI, TrSL) — AF=4, label=hold_for_later
  11. JS-TechTrading: VWAP Momentum_Pullback Strategy — AF=4, label=hold_for_later
  12. VWAP Stdev Bands Strategy (Long Only) — AF=4, label=hold_for_later
  13. RSI-VWAP Indicator Strategy — AF=4, label=hold_for_later
  14. VWAP Strategy (Neptuko) — AF=4, label=hold_for_later
  15. BabyShark VWAP Strategy — AF=4, label=hold_for_later
  16. VWAP and BB Strategy [EEMANI] — AF=4, label=hold_for_later
  17. VWAP Breakout NY Open Only — AF=4, label=hold_for_later
  18. EMA + VWAP Strategy — AF=4, label=hold_for_later
  19. VWAP Breakout Strategy + EMAs + Clean Cycle/TP/SL Plots — AF=4, label=hold_for_later
  20. VWAP+15EMA with RSI — AF=3, label=hold_for_later

### ORB-breakout-4 (17 members)
- **Representative:** Gold ORB Strategy (15-min Range, 5-min Entry) (AF=5)
- **Entry model:** breakout
- **Members:**
  1. Gold ORB Strategy (15-min Range, 5-min Entry) — AF=5, label=convert_now
  2. IU Opening Range Breakout Strategy — AF=5, label=hold_for_later
  3. NY Opening Range Breakout - MA Stop — AF=5, label=hold_for_later
  4. NY ORB Breakout Strategy (MambaFX x DoyleStyle) — AF=5, label=hold_for_later
  5. ORB Breakout Strategy with VWAP and Volume Filters — AF=5, label=already_converted
  6. 15-Minute ORB Breakout Strategy with VWAP and Volume Filters — AF=5, label=hold_for_later
  7. ORB Algo | Flux Charts — AF=5, label=hold_for_later
  8. ORB Strategy + Backtesting (fixed timestamp) — AF=5, label=hold_for_later
  9. 15 min orb (15min ORB Retest Strategy) — AF=5, label=hold_for_later
  10. 15-Min Opening Range Breakout — AF=5, label=hold_for_later
  11. High-Low Breakout Strategy with ATR Trailing Stop Loss — AF=5, label=hold_for_later
  12. Long-Only Opening Range Breakout (ORB) with Pivot Points — AF=4, label=component_only
  13. Reversal & Breakout Strategy with ORB — AF=4, label=hold_for_later
  14. Open Drive — AF=4, label=hold_for_later
  15. Script_Algo - ORB Strategy with Filters — AF=3, label=component_only
  16. ORB Breakout Strategy with reversal — AF=3, label=hold_for_later
  17. Strategy: Range Breakout — AF=3, label=hold_for_later

### ICT-sweep_reversal-3 (11 members)
- **Representative:** Liquidity Sweeper (AF=5)
- **Entry model:** sweep_reversal
- **Members:**
  1. Liquidity Sweeper — AF=5, label=convert_now
  2. Liquidity Sweep Filter Strategy [AlgoAlpha X PineIndicators] — AF=5, label=hold_for_later
  3. PineScript-SMC-Strategy — AF=5, label=hold_for_later
  4. Captain Backtest Model [TFO] — AF=5, label=already_converted
  5. Order Block Volumatic FVG Strategy — AF=5, label=hold_for_later
  6. Liquidity Sweep Reversal Strategy — AF=4, label=hold_for_later
  7. ICT Master Suite [Trading IQ] — AF=4, label=hold_for_later
  8. Smart Money Concept Strategy - Uncle Sam — AF=4, label=hold_for_later
  9. FVG Strategy - Fair Value Gap — AF=4, label=hold_for_later
  10. Gold Fair Value Gap Entry (FVG GOLD) — AF=3, label=hold_for_later
  11. ICT Indicator with Paper Trading — AF=2, label=reject

### ICT-mixed-7 (2 members)
- **Representative:** SMC Strategy (AF=4)
- **Entry model:** mixed
- **Members:**
  1. SMC Strategy — AF=4, label=convert_now
  2. Smart Money Concept + Strategy Backtesting Toolkit [Shah] — AF=4, label=hold_for_later

### VWAP-breakout-1 (1 members)
- **Representative:** RVWAP Mean Reversion Strategy (AF=5)
- **Entry model:** breakout

### VWAP-mixed-5 (1 members)
- **Representative:** Dynamic Swing Anchored VWAP STRAT (AF=4)
- **Entry model:** mixed

### VWAP-mixed-6 (1 members)
- **Representative:** GCK VWAP BOT (AF=4)
- **Entry model:** mixed

### ORB-gap-8 (1 members)
- **Representative:** Gap Momentum System (TASC 2024.01) (AF=4)
- **Entry model:** gap

## Top Conversion Candidates (convert_now)

| # | ID | Title | Family | AF | Complexity | Entry | Regime | Freq |
|---|-------|-------|--------|----|------------|-------|--------|------|
| 1 | vvedding--rvwap-mean-reversion-strategy | RVWAP Mean Reversion Strategy | vwap | 5 | medium | breakout, mean_reversion | range_bound | medium |
| 2 | hye0619--hye-mean-reversion-vwap-strateg | HYE Mean Reversion VWAP Strategy | vwap | 5 | easy | mean_reversion, crossover | range_bound | medium |
| 3 | ict-002-mejunda-liquidity-sweeper | Liquidity Sweeper | ict | 5 | medium | sweep_reversal | volatile | low |
| 4 | orb-003-krypson-gold-orb-strategy | Gold ORB Strategy (15-min Range, 5- | orb | 5 | medium | — | mixed | medium |
| 5 | pineindicators--dynamic-swing-anchored-v | Dynamic Swing Anchored VWAP STRAT | vwap | 4 | medium | — | mixed | low |
| 6 | gckprofittrading--gck-vwap-bot | GCK VWAP BOT | vwap | 4 | medium | — | mixed | medium |
| 7 | ict-004-danieltbolsch-smc-strategy | SMC Strategy | ict | 4 | medium | — | mixed | medium |
| 8 | orb-018-pinecodertasc-gap-momentum | Gap Momentum System (TASC 2024.01) | orb | 4 | medium | gap | mixed | medium |

## Component-Only Candidates

- **VWAP Bands Backtest** (vwap) — Extract: multi-target exit system
- **Long-Only Opening Range Breakout (ORB) with Pivot Points** (orb) — Extract: pivot-based trailing stop
- **Script_Algo - ORB Strategy with Filters** (orb) — Extract: SuperTrend filter

## Family Coverage Summary

| Family | Total | Convert Now | Hold | Component | Converted | Reject |
|--------|-------|-------------|------|-----------|-----------|--------|
| vwap | 23 | 4 | 17 | 1 | 1 | 0 |
| orb | 18 | 2 | 13 | 2 | 1 | 0 |
| ict | 13 | 2 | 9 | 0 | 1 | 1 |

## Recommended Next Conversion Round

Based on triage results, the next conversion round should target:

1. **RVWAP Mean Reversion Strategy** (vwap) — highest automation fitness; best in cluster; range_bound regime specialist; source code available
2. **Liquidity Sweeper** (ict) — highest automation fitness; best in cluster; volatile regime specialist
3. **Gold ORB Strategy (15-min Range, 5-min Entry)** (orb) — highest automation fitness; best in cluster

---
*Generated by research/triage/run_triage.py*
