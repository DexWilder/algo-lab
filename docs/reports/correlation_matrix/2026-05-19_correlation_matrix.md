# FQL Correlation Matrix — 2026-05-19

**Generated:** 2026-05-19T08:24:18
**Phase 2 Item #2** — Paper-Readiness Sprint Day 1
**Scope:** Lane 2 analysis on 12 registered 2026-05-06 forge-hybrid candidates
**Safety:** report-only; registry reclassification requires explicit operator approval (Lane 3)

**Evidence tier:** Cheap Screen Tier — correlations are backtest-derived; forward correlation may vary.

---

## 1. Executive Summary

- Candidates analyzed: **12**
- Pairs evaluated: **66**
- Min overlap days threshold for LOW_CONFIDENCE: 100

### Pair classification counts
- DISTINCT: **60**
- RELATED_VARIANT: **4**
- HIGHLY_CORRELATED: **1**
- DUPLICATE_EXPOSURE: **1**

### Same-asset findings (the ones that matter for fictional diversification)
- Same-asset DUPLICATE_EXPOSURE pairs: **1**
- Same-asset HIGHLY_CORRELATED pairs: **1**
- DISTINCT pairs (any asset): 60
- Cross-asset DUPLICATE_EXPOSURE pairs (suspicious; likely regime co-movement): 0

---
## 2. Candidates analyzed

| # | Strategy | Asset | Entry | Filter | Exit | Archetype | n_trades | PF |
|---|---|---|---|---|---|---|---:|---:|
| 1 | `XB-PB-EMA-Ladder-MNQ` | MNQ | pb_pullback | ema_slope | profit_ladder | workhorse | 1473 | 1.407 |
| 2 | `XB-PB-EMA-Ladder-MCL` | MCL | pb_pullback | ema_slope | profit_ladder | workhorse | 1069 | 1.300 |
| 3 | `XB-PB-EMA-Ladder-MYM` | MYM | pb_pullback | ema_slope | profit_ladder | tail | 470 | 1.356 |
| 4 | `XB-BB-EMA-Ladder-MNQ` | MNQ | bb_reversion | ema_slope | profit_ladder | workhorse | 671 | 1.249 |
| 5 | `XB-BB-EMA-Ladder-MGC` | MGC | bb_reversion | ema_slope | profit_ladder | tail | 293 | 1.592 |
| 6 | `XB-BB-EMA-Ladder-MCL` | MCL | bb_reversion | ema_slope | profit_ladder | tail | 462 | 1.203 |
| 7 | `XB-BB-EMA-Ladder-MYM` | MYM | bb_reversion | ema_slope | profit_ladder | tail | 239 | 1.745 |
| 8 | `XB-VWAP-EMA-Ladder-MGC` | MGC | vwap_continuation | ema_slope | profit_ladder | tail | 375 | 1.289 |
| 9 | `XB-VWAP-EMA-Ladder-MCL` | MCL | vwap_continuation | ema_slope | profit_ladder | workhorse | 505 | 1.276 |
| 10 | `XB-VWAP-EMA-Ladder-MYM` | MYM | vwap_continuation | ema_slope | profit_ladder | tail | 275 | 1.497 |
| 11 | `XB-ORB-EMA-Chandelier-MNQ` | MNQ | orb_breakout | ema_slope | chandelier | workhorse | 1207 | 1.574 |
| 12 | `XB-ORB-EMA-TimeStop-MNQ` | MNQ | orb_breakout | ema_slope | time_stop | tail | 1207 | 1.507 |

---
## 3. Structural similarity matrix (0-4 scale)

Components matched: entry + filter + exit + asset (each contributes 1). 4 = identical.

| | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | — | · | · | · | · | · | · | · | · | · | · | · |
| **2** | 3 | — | · | · | · | · | · | · | · | · | · | · |
| **3** | 3 | 3 | — | · | · | · | · | · | · | · | · | · |
| **4** | 3 | 2 | 2 | — | · | · | · | · | · | · | · | · |
| **5** | 2 | 2 | 2 | 3 | — | · | · | · | · | · | · | · |
| **6** | 2 | 3 | 2 | 3 | 3 | — | · | · | · | · | · | · |
| **7** | 2 | 2 | 3 | 3 | 3 | 3 | — | · | · | · | · | · |
| **8** | 2 | 2 | 2 | 2 | 3 | 2 | 2 | — | · | · | · | · |
| **9** | 2 | 3 | 2 | 2 | 2 | 3 | 2 | 3 | — | · | · | · |
| **10** | 2 | 2 | 3 | 2 | 2 | 2 | 3 | 3 | 3 | — | · | · |
| **11** | 2 | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | — | · |
| **12** | 2 | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 3 | — |

---
## 4. Pearson r matrix (daily PnL, outer-join with 0-fill)

| | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | — | · | · | · | · | · | · | · | · | · | · | · |
| **2** | 0.02 | — | · | · | · | · | · | · | · | · | · | · |
| **3** | 0.19 | -0.01 | — | · | · | · | · | · | · | · | · | · |
| **4** | 0.07 | 0.03 | 0.07 | — | · | · | · | · | · | · | · | · |
| **5** | -0.01 | -0.01 | -0.11 | -0.07 | — | · | · | · | · | · | · | · |
| **6** | -0.06 | 0.00 | 0.02 | 0.00 | 0.03 | — | · | · | · | · | · | · |
| **7** | 0.12 | 0.05 | 0.09 | 0.32 | 0.01 | 0.03 | — | · | · | · | · | · |
| **8** | 0.00 | 0.00 | 0.04 | 0.04 | 0.03 | -0.03 | 0.01 | — | · | · | · | · |
| **9** | -0.01 | 0.34 | 0.06 | 0.07 | -0.04 | -0.02 | 0.09 | 0.00 | — | · | · | · |
| **10** | 0.13 | -0.02 | 0.63 | -0.03 | -0.05 | -0.01 | 0.02 | -0.00 | 0.02 | — | · | · |
| **11** | 0.46 | 0.01 | 0.16 | 0.17 | -0.01 | -0.03 | 0.26 | -0.02 | 0.04 | 0.03 | — | · |
| **12** | 0.43 | -0.02 | 0.14 | 0.10 | -0.01 | -0.04 | 0.16 | -0.01 | 0.03 | 0.04 | 0.88 | — |

---
## 5. Pair classification (all 66 pairs)

Sorted by Pearson r descending (most-correlated first).

| Pair | Structural (0-4) | Same asset? | Overlap days | Pearson r | Classification |
|---|---:|:---:|---:|---:|---|
| `XB-ORB-EMA-Chandelier-MNQ` ↔ `XB-ORB-EMA-TimeStop-MNQ` | 3 | ✅ | 1207 | 0.883 | DUPLICATE_EXPOSURE |
| `XB-PB-EMA-Ladder-MYM` ↔ `XB-VWAP-EMA-Ladder-MYM` | 3 | ✅ | 469 | 0.632 | HIGHLY_CORRELATED |
| `XB-PB-EMA-Ladder-MNQ` ↔ `XB-ORB-EMA-Chandelier-MNQ` | 2 | ✅ | 1519 | 0.462 | RELATED_VARIANT |
| `XB-PB-EMA-Ladder-MNQ` ↔ `XB-ORB-EMA-TimeStop-MNQ` | 2 | ✅ | 1519 | 0.431 | RELATED_VARIANT |
| `XB-PB-EMA-Ladder-MCL` ↔ `XB-VWAP-EMA-Ladder-MCL` | 3 | ✅ | 1077 | 0.338 | RELATED_VARIANT |
| `XB-BB-EMA-Ladder-MNQ` ↔ `XB-BB-EMA-Ladder-MYM` | 3 | — | 801 | 0.324 | RELATED_VARIANT |
| `XB-BB-EMA-Ladder-MYM` ↔ `XB-ORB-EMA-Chandelier-MNQ` | 1 | — | 1288 | 0.260 | DISTINCT |
| `XB-PB-EMA-Ladder-MNQ` ↔ `XB-PB-EMA-Ladder-MYM` | 3 | — | 1537 | 0.192 | DISTINCT |
| `XB-BB-EMA-Ladder-MNQ` ↔ `XB-ORB-EMA-Chandelier-MNQ` | 2 | ✅ | 1577 | 0.174 | DISTINCT |
| `XB-BB-EMA-Ladder-MYM` ↔ `XB-ORB-EMA-TimeStop-MNQ` | 1 | — | 1288 | 0.160 | DISTINCT |
| `XB-PB-EMA-Ladder-MYM` ↔ `XB-ORB-EMA-Chandelier-MNQ` | 1 | — | 1336 | 0.160 | DISTINCT |
| `XB-PB-EMA-Ladder-MYM` ↔ `XB-ORB-EMA-TimeStop-MNQ` | 1 | — | 1336 | 0.141 | DISTINCT |
| `XB-PB-EMA-Ladder-MNQ` ↔ `XB-VWAP-EMA-Ladder-MYM` | 2 | — | 1519 | 0.126 | DISTINCT |
| `XB-PB-EMA-Ladder-MNQ` ↔ `XB-BB-EMA-Ladder-MYM` | 2 | — | 1516 | 0.119 | DISTINCT |
| `XB-BB-EMA-Ladder-MNQ` ↔ `XB-ORB-EMA-TimeStop-MNQ` | 2 | ✅ | 1577 | 0.102 | DISTINCT |
| `XB-PB-EMA-Ladder-MYM` ↔ `XB-BB-EMA-Ladder-MYM` | 3 | ✅ | 544 | 0.092 | DISTINCT |
| `XB-BB-EMA-Ladder-MYM` ↔ `XB-VWAP-EMA-Ladder-MCL` | 2 | — | 653 | 0.087 | DISTINCT |
| `XB-PB-EMA-Ladder-MNQ` ↔ `XB-BB-EMA-Ladder-MNQ` | 3 | ✅ | 1706 | 0.074 | DISTINCT |
| `XB-BB-EMA-Ladder-MNQ` ↔ `XB-VWAP-EMA-Ladder-MCL` | 2 | — | 994 | 0.072 | DISTINCT |
| `XB-PB-EMA-Ladder-MYM` ↔ `XB-BB-EMA-Ladder-MNQ` | 2 | — | 976 | 0.066 | DISTINCT |
| `XB-PB-EMA-Ladder-MYM` ↔ `XB-VWAP-EMA-Ladder-MCL` | 2 | — | 795 | 0.062 | DISTINCT |
| `XB-PB-EMA-Ladder-MCL` ↔ `XB-BB-EMA-Ladder-MYM` | 2 | — | 1097 | 0.054 | DISTINCT |
| `XB-PB-EMA-Ladder-MYM` ↔ `XB-VWAP-EMA-Ladder-MGC` | 2 | — | 729 | 0.043 | DISTINCT |
| `XB-VWAP-EMA-Ladder-MYM` ↔ `XB-ORB-EMA-TimeStop-MNQ` | 1 | — | 1290 | 0.039 | DISTINCT |
| `XB-BB-EMA-Ladder-MNQ` ↔ `XB-VWAP-EMA-Ladder-MGC` | 2 | — | 895 | 0.039 | DISTINCT |
| `XB-VWAP-EMA-Ladder-MCL` ↔ `XB-ORB-EMA-Chandelier-MNQ` | 1 | — | 1366 | 0.039 | DISTINCT |
| `XB-BB-EMA-Ladder-MGC` ↔ `XB-BB-EMA-Ladder-MCL` | 3 | — | 678 | 0.034 | DISTINCT |
| `XB-BB-EMA-Ladder-MGC` ↔ `XB-VWAP-EMA-Ladder-MGC` | 3 | ✅ | 575 | 0.031 | DISTINCT |
| `XB-BB-EMA-Ladder-MCL` ↔ `XB-BB-EMA-Ladder-MYM` | 3 | — | 602 | 0.030 | DISTINCT |
| `XB-VWAP-EMA-Ladder-MYM` ↔ `XB-ORB-EMA-Chandelier-MNQ` | 1 | — | 1290 | 0.030 | DISTINCT |
| `XB-PB-EMA-Ladder-MCL` ↔ `XB-BB-EMA-Ladder-MNQ` | 2 | — | 1333 | 0.029 | DISTINCT |
| `XB-VWAP-EMA-Ladder-MCL` ↔ `XB-ORB-EMA-TimeStop-MNQ` | 1 | — | 1366 | 0.029 | DISTINCT |
| `XB-PB-EMA-Ladder-MNQ` ↔ `XB-PB-EMA-Ladder-MCL` | 3 | — | 1655 | 0.023 | DISTINCT |
| `XB-VWAP-EMA-Ladder-MCL` ↔ `XB-VWAP-EMA-Ladder-MYM` | 3 | — | 674 | 0.019 | DISTINCT |
| `XB-BB-EMA-Ladder-MYM` ↔ `XB-VWAP-EMA-Ladder-MYM` | 3 | ✅ | 422 | 0.019 | DISTINCT |
| `XB-PB-EMA-Ladder-MYM` ↔ `XB-BB-EMA-Ladder-MCL` | 2 | — | 751 | 0.018 | DISTINCT |
| `XB-BB-EMA-Ladder-MYM` ↔ `XB-VWAP-EMA-Ladder-MGC` | 2 | — | 562 | 0.014 | DISTINCT |
| `XB-PB-EMA-Ladder-MCL` ↔ `XB-ORB-EMA-Chandelier-MNQ` | 1 | — | 1537 | 0.008 | DISTINCT |
| `XB-BB-EMA-Ladder-MGC` ↔ `XB-BB-EMA-Ladder-MYM` | 3 | — | 483 | 0.006 | DISTINCT |
| `XB-VWAP-EMA-Ladder-MGC` ↔ `XB-VWAP-EMA-Ladder-MCL` | 3 | — | 784 | 0.004 | DISTINCT |
| `XB-PB-EMA-Ladder-MCL` ↔ `XB-BB-EMA-Ladder-MCL` | 3 | ✅ | 1205 | 0.003 | DISTINCT |
| `XB-BB-EMA-Ladder-MNQ` ↔ `XB-BB-EMA-Ladder-MCL` | 3 | — | 951 | 0.003 | DISTINCT |
| `XB-PB-EMA-Ladder-MNQ` ↔ `XB-VWAP-EMA-Ladder-MGC` | 2 | — | 1527 | 0.002 | DISTINCT |
| `XB-PB-EMA-Ladder-MCL` ↔ `XB-VWAP-EMA-Ladder-MGC` | 2 | — | 1217 | 0.002 | DISTINCT |
| `XB-VWAP-EMA-Ladder-MGC` ↔ `XB-VWAP-EMA-Ladder-MYM` | 3 | — | 587 | -0.004 | DISTINCT |
| `XB-BB-EMA-Ladder-MGC` ↔ `XB-ORB-EMA-Chandelier-MNQ` | 1 | — | 1319 | -0.007 | DISTINCT |
| `XB-BB-EMA-Ladder-MGC` ↔ `XB-ORB-EMA-TimeStop-MNQ` | 1 | — | 1319 | -0.008 | DISTINCT |
| `XB-BB-EMA-Ladder-MCL` ↔ `XB-VWAP-EMA-Ladder-MYM` | 2 | — | 625 | -0.008 | DISTINCT |
| `XB-PB-EMA-Ladder-MCL` ↔ `XB-PB-EMA-Ladder-MYM` | 3 | — | 1130 | -0.010 | DISTINCT |
| `XB-PB-EMA-Ladder-MNQ` ↔ `XB-BB-EMA-Ladder-MGC` | 2 | — | 1529 | -0.011 | DISTINCT |
| `XB-PB-EMA-Ladder-MCL` ↔ `XB-BB-EMA-Ladder-MGC` | 2 | — | 1186 | -0.011 | DISTINCT |
| `XB-VWAP-EMA-Ladder-MGC` ↔ `XB-ORB-EMA-TimeStop-MNQ` | 1 | — | 1336 | -0.011 | DISTINCT |
| `XB-PB-EMA-Ladder-MNQ` ↔ `XB-VWAP-EMA-Ladder-MCL` | 2 | — | 1558 | -0.012 | DISTINCT |
| `XB-PB-EMA-Ladder-MCL` ↔ `XB-VWAP-EMA-Ladder-MYM` | 2 | — | 1099 | -0.018 | DISTINCT |
| `XB-VWAP-EMA-Ladder-MGC` ↔ `XB-ORB-EMA-Chandelier-MNQ` | 1 | — | 1336 | -0.021 | DISTINCT |
| `XB-BB-EMA-Ladder-MCL` ↔ `XB-VWAP-EMA-Ladder-MCL` | 3 | ✅ | 780 | -0.022 | DISTINCT |
| `XB-PB-EMA-Ladder-MCL` ↔ `XB-ORB-EMA-TimeStop-MNQ` | 1 | — | 1537 | -0.024 | DISTINCT |
| `XB-BB-EMA-Ladder-MCL` ↔ `XB-ORB-EMA-Chandelier-MNQ` | 1 | — | 1347 | -0.030 | DISTINCT |
| `XB-BB-EMA-Ladder-MNQ` ↔ `XB-VWAP-EMA-Ladder-MYM` | 2 | — | 849 | -0.031 | DISTINCT |
| `XB-BB-EMA-Ladder-MCL` ↔ `XB-VWAP-EMA-Ladder-MGC` | 2 | — | 738 | -0.032 | DISTINCT |
| `XB-BB-EMA-Ladder-MCL` ↔ `XB-ORB-EMA-TimeStop-MNQ` | 1 | — | 1347 | -0.037 | DISTINCT |
| `XB-BB-EMA-Ladder-MGC` ↔ `XB-VWAP-EMA-Ladder-MCL` | 2 | — | 720 | -0.043 | DISTINCT |
| `XB-BB-EMA-Ladder-MGC` ↔ `XB-VWAP-EMA-Ladder-MYM` | 2 | — | 524 | -0.047 | DISTINCT |
| `XB-PB-EMA-Ladder-MNQ` ↔ `XB-BB-EMA-Ladder-MCL` | 2 | — | 1547 | -0.057 | DISTINCT |
| `XB-BB-EMA-Ladder-MNQ` ↔ `XB-BB-EMA-Ladder-MGC` | 3 | — | 831 | -0.072 | DISTINCT |
| `XB-PB-EMA-Ladder-MYM` ↔ `XB-BB-EMA-Ladder-MGC` | 2 | — | 688 | -0.107 | DISTINCT |

---
## 6. Per-candidate summary

| Candidate | # DUPLICATE peers (same-asset) | # HIGHLY_CORRELATED peers (same-asset) | # DISTINCT peers |
|---|---:|---:|---:|
| `XB-PB-EMA-Ladder-MNQ` | 0 | 0 | 9 |
| `XB-PB-EMA-Ladder-MCL` | 0 | 0 | 10 |
| `XB-PB-EMA-Ladder-MYM` | 0 | 1 | 10 |
| `XB-BB-EMA-Ladder-MNQ` | 0 | 0 | 10 |
| `XB-BB-EMA-Ladder-MGC` | 0 | 0 | 11 |
| `XB-BB-EMA-Ladder-MCL` | 0 | 0 | 11 |
| `XB-BB-EMA-Ladder-MYM` | 0 | 0 | 10 |
| `XB-VWAP-EMA-Ladder-MGC` | 0 | 0 | 11 |
| `XB-VWAP-EMA-Ladder-MCL` | 0 | 0 | 10 |
| `XB-VWAP-EMA-Ladder-MYM` | 0 | 1 | 10 |
| `XB-ORB-EMA-Chandelier-MNQ` | 1 | 0 | 9 |
| `XB-ORB-EMA-TimeStop-MNQ` | 1 | 0 | 9 |

---
## 7. Proposed reclassifications (operator approval required)

**This is Lane 2 analysis. Any registry change is Lane 3 and requires explicit operator approval.**

| Candidate | Recommendation | Reason | Suggested action |
|---|---|---|---|
| `XB-PB-EMA-Ladder-MNQ` | **KEEP_DISTINCT** | No same-asset peer crosses HIGHLY_CORRELATED threshold | No registry change needed |
| `XB-PB-EMA-Ladder-MCL` | **KEEP_DISTINCT** | No same-asset peer crosses HIGHLY_CORRELATED threshold | No registry change needed |
| `XB-PB-EMA-Ladder-MYM` | **ACKNOWLEDGE_RELATED** | Same-asset highly-correlated peer(s); not duplicate but related | Update relationships.related list in registry to reflect peer ties |
| `XB-BB-EMA-Ladder-MNQ` | **KEEP_DISTINCT** | No same-asset peer crosses HIGHLY_CORRELATED threshold | No registry change needed |
| `XB-BB-EMA-Ladder-MGC` | **KEEP_DISTINCT** | No same-asset peer crosses HIGHLY_CORRELATED threshold | No registry change needed |
| `XB-BB-EMA-Ladder-MCL` | **KEEP_DISTINCT** | No same-asset peer crosses HIGHLY_CORRELATED threshold | No registry change needed |
| `XB-BB-EMA-Ladder-MYM` | **KEEP_DISTINCT** | No same-asset peer crosses HIGHLY_CORRELATED threshold | No registry change needed |
| `XB-VWAP-EMA-Ladder-MGC` | **KEEP_DISTINCT** | No same-asset peer crosses HIGHLY_CORRELATED threshold | No registry change needed |
| `XB-VWAP-EMA-Ladder-MCL` | **KEEP_DISTINCT** | No same-asset peer crosses HIGHLY_CORRELATED threshold | No registry change needed |
| `XB-VWAP-EMA-Ladder-MYM` | **ACKNOWLEDGE_RELATED** | Same-asset highly-correlated peer(s); not duplicate but related | Update relationships.related list in registry to reflect peer ties |
| `XB-ORB-EMA-Chandelier-MNQ` | **FLAG_FOR_OPERATOR_REVIEW** | Same-asset duplicate-exposure peer(s): ['XB-ORB-EMA-TimeStop-MNQ'] | Operator decides: KEEP both as distinct (different exits/filters retain real value) OR mark as variant_of_XB-ORB-EMA-TimeStop-MNQ |
| `XB-ORB-EMA-TimeStop-MNQ` | **FLAG_FOR_OPERATOR_REVIEW** | Same-asset duplicate-exposure peer(s): ['XB-ORB-EMA-Chandelier-MNQ'] | Operator decides: KEEP both as distinct (different exits/filters retain real value) OR mark as variant_of_XB-ORB-EMA-Chandelier-MNQ |

---
## 8. Caveats & limitations

- Single-run-per-candidate (no 3× reproducibility in v1; separate item)
- Pearson on daily PnL (Spearman not included in v1)
- Outer-join with 0-fill: no-trade days count as zero correlation contribution
- Pairs with overlap_days < 100 flagged LOW_CONFIDENCE
- 66 pairwise tests at α=0.05 → ~3 false-positive 'duplicates' by chance; use stricter r ≥ 0.85
- Cross-asset high r may indicate regime co-movement, NOT strategy duplication — classified separately
- Backtest-derived; forward correlation may diverge

---
## 9. Safety affirmation

- Report-only. NO registry mutation occurred during this analysis.
- NO Lane A surfaces touched (runtime / scheduler / portfolio / checkpoint / hold-state).
- NO source-helper / candidate pool / promotion / paper-readiness changes.
- Any registry reclassification based on §7 proposals requires explicit operator approval (Lane 3, surgical commit pattern).