# MGC-Donchian Mutation Cycle — 2026-06-03

Authority T1 / Lane B / report-only. Operator approval: OK MGC-Donchian mutation.

## Result table

| Axis | n | PF | Median | Max-Yr | Top-3 | Top-10 | H1/H2 | Yrs+ | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|---|---|
| baseline (last cycle) | 980 | 1.205 | $4.26 | 47.5% | 42.3% | 88.2% | 1.41 / 1.10 | 6/8 | **TEMPORAL_SPLIT_REQUIRED** |
| vol-overlay (low-vol regimes only) | 772 | 1.229 | $6.76 | 43.0% | 43.7% | 91.2% | 1.58 / 1.07 | 6/8 | **TEMPORAL_SPLIT_REQUIRED** |
| vol-overlay (broader low-vol) | 823 | 1.239 | $6.76 | 42.5% | 40.2% | 83.9% | 1.59 / 1.08 | 6/8 | **TEMPORAL_SPLIT_REQUIRED** |
| alt-exit (chandelier trailing) | 980 | 1.089 | $-7.24 | 84.8% | 100.6% | 214.2% | 1.35 / 0.96 | 6/8 | **KILL** |
| alt-exit (ATR trail) | 980 | 1.120 | $-6.24 | 64.1% | 76.1% | 157.4% | 1.37 / 0.99 | 6/8 | **KILL** |
| tail-engine framing (time_stop, fewer exits) | 980 | 1.130 | $-6.24 | 56.1% | 70.4% | 145.4% | 1.39 / 1.00 | 6/8 | **KILL** |

## Notes per variant

- **baseline (last cycle)**: PF + median OK but concentration still high — temporal split required
  - **Temporal split:**
    - 2019: n=65 PF=1.943 net=$912
    - 2020: n=149 PF=1.406 net=$1705
    - 2021: n=135 PF=1.058 net=$194
    - 2022: n=140 PF=1.629 net=$1954
    - 2023: n=137 PF=1.234 net=$733
    - 2024: n=147 PF=0.961 net=$-218
    - 2025: n=141 PF=1.562 net=$3438
    - 2026: n=66 PF=0.832 net=$-1477
    - Era 1 (2019-07-01→2021-11-03): n=326 PF=1.375 net=$2906
    - Era 2 (2021-11-04→2024-03-04): n=327 PF=1.326 net=$2566
    - Era 3 (2024-03-05→2026-06-01): n=327 PF=1.090 net=$1771
- **vol-overlay (low-vol regimes only)**: PF + median OK but concentration still high — temporal split required
  - **Temporal split:**
    - 2019: n=52 PF=2.961 net=$1276
    - 2020: n=107 PF=1.593 net=$1917
    - 2021: n=100 PF=1.141 net=$387
    - 2022: n=110 PF=1.572 net=$1545
    - 2023: n=112 PF=1.358 net=$998
    - 2024: n=126 PF=0.987 net=$-65
    - 2025: n=116 PF=1.535 net=$3014
    - 2026: n=49 PF=0.734 net=$-2062
    - Era 1 (2019-07-01→2021-12-23): n=257 PF=1.567 net=$3681
    - Era 2 (2021-12-28→2024-03-15): n=257 PF=1.349 net=$2337
    - Era 3 (2024-03-20→2026-06-01): n=258 PF=1.057 net=$991
- **vol-overlay (broader low-vol)**: PF + median OK but concentration still high — temporal split required
  - **Temporal split:**
    - 2019: n=55 PF=2.348 net=$1097
    - 2020: n=119 PF=1.640 net=$2133
    - 2021: n=103 PF=1.202 net=$551
    - 2022: n=119 PF=1.632 net=$1768
    - 2023: n=122 PF=1.327 net=$954
    - 2024: n=132 PF=0.999 net=$-7
    - 2025: n=119 PF=1.569 net=$3233
    - 2026: n=54 PF=0.746 net=$-2117
    - Era 1 (2019-07-01→2021-12-16): n=274 PF=1.574 net=$3867
    - Era 2 (2021-12-23→2024-03-12): n=274 PF=1.383 net=$2619
    - Era 3 (2024-03-13→2026-06-01): n=275 PF=1.062 net=$1127
- **alt-exit (chandelier trailing)**: median flipped negative
- **alt-exit (ATR trail)**: median flipped negative
- **tail-engine framing (time_stop, fewer exits)**: median flipped negative