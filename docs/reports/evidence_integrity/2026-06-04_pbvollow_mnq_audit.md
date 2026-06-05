# Evidence-Integrity Audit — DAILY-PB-VolLow-MNQ

**Overall:** **YELLOW**

**Classification:** PORTFOLIO_COMPLEMENT_CANDIDATE (audit YELLOW due weak median per dim C; portfolio contribution strong per G; operator decides)

**Subject:** DAILY-PB-VolLow-MNQ (pb_pullback + ema_slope_vol_low(40) + profit_ladder on MNQ)

## A. Cost source

- asset_config_present: True
- commission/side: $0.62
- slippage ticks: 1, tick size: 0.25
- round-trip cost: $2.24
- cost tier: VALIDATED
- verdict: **GREEN**

## B. Cost stress

| stress | n | PF | net median | net PnL | max DD |
|---|---|---|---|---|---|
| 1x baseline | 1445 | 1.365 | $3.26 | $21205 | $-1850 |
| 1.5x cost | 1445 | 1.346 | $2.64 | $20309 | $-1889 |
| 2x cost | 1445 | 1.329 | $2.02 | $19413 | $-1928 |
| 3x cost | 1445 | 1.294 | $0.78 | $17621 | $-2006 |
| +1 tick slip | 1445 | 1.336 | $2.26 | $19760 | $-1913 |
| +2 tick slip | 1445 | 1.307 | $1.26 | $18315 | $-1976 |
| 2x cost + 1 tick slip | 1445 | 1.301 | $1.02 | $17968 | $-1991 |
| 2x cost + 2 tick slip | 1445 | 1.273 | $0.02 | $16523 | $-2054 |

verdict: **GREEN**

## C. Edge quality

- **n:** 1445
- **win_rate_pct:** 51.07
- **gross_median:** 5.50
- **net_median:** 3.26
- **avg_win:** 107.56
- **avg_loss:** -82.28
- **largest_win:** 1094.76
- **largest_loss:** -421.24
- **top1_share_pct:** 5.16
- **top3_share_pct:** 12.76
- **top5_share_pct:** 19.31
- **pct_trades_net_le_zero:** 48.93
- **max_consec_losses:** 8
- **max_dd_duration_trades:** 133
- **rt_cost_per_trade:** 2.24

verdict: **YELLOW (median positive but very weak < $5)**

## D. Lookahead

- **candidate_class:** XB (crossbreeding_engine)
- **entry_logic:** pb_pullback uses bar i features (ema, atr) computed up to i
- **exit_logic:** profit_ladder uses bar i + state from prior bars
- **indicator_shifting:** donchian bug-fixed 2026-05-28; pb_pullback uses no prior-shifted indicators
- **no_future_bars:** True
- **verdict:** GREEN

## E. Calendar

- {'calendar_source': 'N/A — continuous-bar candidate', 'verdict': 'GREEN'}

## F. Survivorship

- **symbol:** MNQ
- **available:** True
- **first_bar:** 2019-06-30 20:00:00
- **last_bar:** 2026-06-02 19:55:00
- **span_days:** 2528
- **n_bars:** 485536
- **big_jumps_gt_5pct:** 1
- **data_window_caveat:** FULL — 2019-2020+
- **verdict:** GREEN

## G. Duplicate / portfolio

- family review verdict: **PARALLEL_COMPLEMENT_CANDIDATE**
- daily corr: 0.426
- drawdown overlap: 66.8%
- losing-day overlap: 16.1%
- both-full-size total PnL: $70265
- both-full-size max DD: $-2638

## H. Temporal robustness

- **yrs_pos:** 7
- **n_yrs:** 8
- **era_3_pf:** 1.578525802783537
- **era_3_median:** 13.26
- **verdict:** GREEN
### Per-year
| year | n | PF | median | net |
|---|---|---|---|---|
| 2019 | 106 | 0.779 | $-0.74 | $-362 |
| 2020 | 207 | 1.260 | $1.26 | $2011 |
| 2021 | 209 | 1.346 | $4.76 | $2328 |
| 2022 | 210 | 1.040 | $-20.24 | $506 |
| 2023 | 210 | 1.416 | $2.26 | $2763 |
| 2024 | 204 | 1.277 | $-7.24 | $2386 |
| 2025 | 209 | 2.110 | $23.76 | $9947 |
| 2026 | 90 | 1.307 | $20.76 | $1626 |

### Era split
| era | n | PF | median | net |
|---|---|---|---|---|
| 1 | 481 | 1.227 | $0.76 | $3267 |
| 2 | 482 | 1.233 | $-1.24 | $4985 |
| 3 | 482 | 1.579 | $13.26 | $12953 |

verdict: **GREEN**

## Overall: YELLOW

- **[YELLOW]** C: YELLOW (median positive but very weak < $5)

## Classification

PORTFOLIO_COMPLEMENT_CANDIDATE (audit YELLOW due weak median per dim C; portfolio contribution strong per G; operator decides)
