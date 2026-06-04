# Temporal-Split Mutation — XB-BB-EMA-Ladder-MGC

**Date:** 2026-06-03 • Authority: T1 / report-only / Lane B

## Baseline

- n = 298
- PF = 1.611
- median = $1.76
- net = $4287
- max DD = $-866

## Per-year breakdown

| Year | n | PF | Median | Net |
|---|---:|---:|---:|---:|
| 2019 | 24 | 0.846 | $-3.74 | $-41 |
| 2020 | 40 | 0.712 | $3.76 | $-433 |
| 2021 | 41 | 1.085 | $-4.24 | $59 |
| 2022 | 42 | 0.823 | $-10.24 | $-160 |
| 2023 | 46 | 1.073 | $0.76 | $48 |
| 2024 | 44 | 0.925 | $-2.24 | $-67 |
| 2025 | 40 | 1.769 | $21.26 | $775 |
| 2026 | 21 | 4.716 | $61.76 | $4105 |

## Year exclusion

| Excluded | n | PF | Median | Δ net |
|---|---:|---:|---:|---:|
| 2019 | 274 | 1.641 | $1.76 | $+41 |
| 2020 | 258 | 1.855 | $0.76 | $+433 |
| 2021 | 257 | 1.668 | $3.76 | $-59 |
| 2022 | 256 | 1.727 | $3.76 | $+160 |
| 2023 | 252 | 1.666 | $1.76 | $-48 |
| 2024 | 254 | 1.710 | $1.76 | $+67 |
| 2025 | 258 | 1.584 | $-1.74 | $-775 |
| 2026 | 277 | 1.031 | $-0.24 | $-4105 |

## Rolling-window robustness

| Window | Samples | Worst PF | Median PF | % > 1.0 | % > 1.2 |
|---|---:|---:|---:|---:|---:|
| 252d | 279 | 0.271 | 0.944 | 43% | 27% |
| 504d | 279 | 0.271 | 0.942 | 41% | 18% |

## Era split (3 equal-trade-count thirds)

| Era | Range | n | PF | Median |
|---|---|---:|---:|---:|
| 1 | 2019-07-03 → 2021-09-22 | 99 | 0.807 | $-2.24 |
| 2 | 2021-09-27 → 2024-01-18 | 99 | 0.953 | $-4.24 |
| 3 | 2024-01-23 → 2026-05-29 | 100 | 2.653 | $11.76 |

## Verdict: **RETEST_WITH_YEAR_GATE**

- Worst single-year exclusion = 2026 → PF drops to 1.031
- 12mo rolling PF > 1.2 only 27% of windows
- at least one third of the sample is unprofitable
- year gate would need defensibility check before any registry surface