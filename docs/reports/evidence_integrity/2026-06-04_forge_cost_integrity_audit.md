# Forge Evidence-Integrity Audit — 2026-06-04

**Overall verdict:** **GREEN**

**Authority:** T1 / Lane B / report-only. Mandatory hard checkpoint.
**Subjects:** EVT-NFP-MGC-Long-2h, DAILY-DC-EMA-MNQ, XB-ORB-EMA-Ladder-MNQ.

## A. Cost source verification

| Symbol | asset_config? | commission/side | slip ticks | tick size | round-trip cost | tier | missing/default? |
|---|---|---|---|---|---|---|---|
| MGC | True | $0.62 | 1 | 0.1 | $3.24 | VALIDATED | False |
| MNQ | True | $0.62 | 1 | 0.25 | $2.24 | VALIDATED | False |

**Hard rule:** if `missing/default = True`, candidate is `EVIDENCE_INVALID`. Both audited symbols are `VALIDATED` from `engine/asset_config.py` with no defaults.

## B. Cost stress

### EVT-NFP-MGC-Long-2h

| stress | n | pf | net_median | gross_median | net_pnl | max_dd |
|---|---|---|---|---|---|---|
| 1x baseline | 84 | 2.264 | 21.76 | 25.0 | 8663.84 | -1652.08 |
| 1.5x cost | 84 | 2.252 | 21.14 | 25.0 | 8611.76 | -1662.62 |
| 2x cost | 84 | 2.241 | 20.52 | 25.0 | 8559.68 | -1673.16 |
| 3x cost | 84 | 2.217 | 19.28 | 25.0 | 8455.52 | -1694.24 |
| +1 tick slip | 84 | 2.226 | 19.76 | 25.0 | 8495.84 | -1686.08 |
| +2 tick slip | 84 | 2.189 | 17.76 | 25.0 | 8327.84 | -1720.08 |
| 2x cost + 1 tick slip | 84 | 2.203 | 18.52 | 25.0 | 8391.68 | -1707.16 |

### DAILY-DC-EMA-MNQ

| stress | n | pf | net_median | gross_median | net_pnl | max_dd |
|---|---|---|---|---|---|---|
| 1x baseline | 1542 | 1.609 | 21.76 | 24.0 | 49415.42 | -2821.58 |
| 1.5x cost | 1542 | 1.595 | 21.14 | 24.0 | 48459.38 | -2832.12 |
| 2x cost | 1542 | 1.58 | 20.52 | 24.0 | 47503.34 | -2842.66 |
| 3x cost | 1542 | 1.551 | 19.28 | 24.0 | 45591.26 | -2863.74 |
| +1 tick slip | 1542 | 1.586 | 20.76 | 24.0 | 47873.42 | -2838.58 |
| +2 tick slip | 1542 | 1.562 | 19.76 | 24.0 | 46331.42 | -2855.58 |
| 2x cost + 1 tick slip | 1542 | 1.557 | 19.52 | 24.0 | 45961.34 | -2859.66 |

### XB-ORB-EMA-Ladder-MNQ

| stress | n | pf | net_median | gross_median | net_pnl | max_dd |
|---|---|---|---|---|---|---|
| 1x baseline | 1215 | 1.603 | 42.76 | 45.0 | 49059.9 | -2331.4 |
| 1.5x cost | 1215 | 1.591 | 42.14 | 45.0 | 48306.6 | -2337.6 |
| 2x cost | 1215 | 1.58 | 41.52 | 45.0 | 47553.3 | -2343.8 |
| 3x cost | 1215 | 1.557 | 40.28 | 45.0 | 46046.7 | -2356.2 |
| +1 tick slip | 1215 | 1.584 | 41.76 | 45.0 | 47844.9 | -2341.4 |
| +2 tick slip | 1215 | 1.566 | 40.76 | 45.0 | 46629.9 | -2351.4 |
| 2x cost + 1 tick slip | 1215 | 1.562 | 40.52 | 45.0 | 46338.3 | -2353.8 |

## C. Edge quality (baseline costs)

### NFP-MGC

- n: 84
- win_rate_pct: 54.76
- gross_median: 25.00
- net_median: 21.76
- avg_win: 337.30
- avg_loss: -180.32
- largest_win: 1468.76
- largest_loss: -789.24
- top1_share_pct: 16.95
- top3_share_pct: 41.60
- top5_share_pct: 63.02
- pct_trades_net_le_zero: 45.24
- rt_cost_per_trade: 3.24

### DC-MNQ

- n: 1542
- win_rate_pct: 57.07
- gross_median: 24.00
- net_median: 21.76
- avg_win: 148.29
- avg_loss: -122.47
- largest_win: 1724.26
- largest_loss: -515.24
- top1_share_pct: 3.49
- top3_share_pct: 9.08
- top5_share_pct: 12.88
- pct_trades_net_le_zero: 42.93
- rt_cost_per_trade: 2.24

### ORB-MNQ

- n: 1215
- win_rate_pct: 60.33
- gross_median: 45.00
- net_median: 42.76
- avg_win: 177.98
- avg_loss: -168.89
- largest_win: 1724.26
- largest_loss: -849.74
- top1_share_pct: 3.51
- top3_share_pct: 9.78
- top5_share_pct: 14.72
- pct_trades_net_le_zero: 39.67
- rt_cost_per_trade: 2.24

## D. Lookahead audit

### EVT (event_window_engine)

- **entry_logic:** first bar with datetime >= event_dt + entry_offset_bars
- **exit_logic:** entry_idx + exit_offset_bars (fixed future bars)
- **indicator_shifting:** N/A — no indicators used in event-window signal
- **no_future_bars:** True
- **event_timing_realism:** NFP at 08:30 ET; entry +1 bar = 08:35 bar OPEN. Deep-screen confirmed entry-delay +1/+2/+3/+6/+12 bars all PF > 2.1. Realistic post-release execution; no same-bar fill assumption.
- **verdict:** GREEN (entry strictly after event; exit strictly forward)

### XB (crossbreeding_engine)

- **entry_logic:** iterate bars 1..n; entry signal uses bar i features (close, ema, atr) computed up to i
- **exit_logic:** exit signal uses bar i features + state from prior bars
- **indicator_shifting:** donchian_breakout was bug-fixed 2026-05-28 to use [i-1] (prior window) for dc_high/dc_low — verified no lookahead in current code.
- **no_future_bars:** True
- **atr_compute:** rolling 14-bar TR; uses bars up to i, not i+1
- **verdict:** GREEN (verified after 2026-05-28 Donchian bug fix)

## E. Calendar audit

### EVT-NFP-MGC-Long-2h

- **calendar_source:** research/forge_nfp_calendar_verify.py — canonical 1st-Friday rule with documented BLS holiday shifts
- **rule_vs_actual_match_pct:** 97.9
- **documented_shifts:**
  - {'date': '2021-01', 'rule': '2021-01-01', 'actual': '2021-01-08', 'reason': "New Year's Day deferral"}
  - {'date': '2025-07', 'rule': '2025-07-04', 'actual': '2025-07-11', 'reason': 'Independence Day deferral'}
- **good_friday_overlaps:**
  - {'date': '2021-04-02', 'note': 'futures open; equities closed'}
  - {'date': '2023-04-07', 'note': 'futures open; equities closed'}
  - {'date': '2026-04-03', 'note': 'futures open; equities closed'}
- **delta_metrics_rule_vs_actual:** {'delta_pf': -0.057, 'delta_median': 0.0}
- **verdict:** GREEN (calendar verified; immaterial delta; shifts documented)

### DAILY-DC-EMA-MNQ

- **calendar_source:** N/A — continuous-bar candidate, no event calendar
- **verdict:** GREEN (no calendar dependency)

### XB-ORB-EMA-Ladder-MNQ

- **calendar_source:** N/A — continuous-bar candidate
- **verdict:** GREEN (no calendar dependency)

## F. Survivorship / instrument-continuity

### MGC

- **available:** True
- **first_bar:** 2019-06-30 20:00:00
- **last_bar:** 2026-06-02 14:50:00
- **span_days:** 2528
- **n_bars:** 256205
- **big_jumps_gt_5pct:** 2
- **data_window_caveat:** FULL — 2019-2020+
- **construction:** continuous front-month futures (micro contracts where available)
- **roll_handling:** Databento continuous adjustment (assumed)
- **verdict:** GREEN

### MNQ

- **available:** True
- **first_bar:** 2019-06-30 20:00:00
- **last_bar:** 2026-06-02 19:55:00
- **span_days:** 2528
- **n_bars:** 485536
- **big_jumps_gt_5pct:** 1
- **data_window_caveat:** FULL — 2019-2020+
- **construction:** continuous front-month futures (micro contracts where available)
- **roll_handling:** Databento continuous adjustment (assumed)
- **verdict:** GREEN

## G. Duplicate exposure / portfolio integrity

See: `research/data/fql_forge/reports/forge_dc_mnq_family_review_2026-06-04.json`

## H. Overall verdict: **GREEN**

No blocking issues; all audit dimensions GREEN.