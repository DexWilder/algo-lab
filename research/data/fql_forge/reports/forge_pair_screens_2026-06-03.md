# Pair Screens — 2026-06-03

Authority T1 / Lane B / report-only. Harness: `research/pairs_engine.py`.
Operator approval: OK wire first pair candidate (expanded to 3 per directive).

## Result table

| Pair | Hedge | n | PF | Median | Max-Yr | Yrs+ | H1/H2 | Eras (PFs) | Verdict |
|---|---|---:|---:|---:|---:|---|---|---|---|
| PAIR-A-MES-ZN-yieldgap-monthly | vol_adjusted | 11 | 0.360 | $193.23 | 0.0% | 2/6 | 0.69/0.20 | 0.52 / 1.37 / 0.15 | **KILL (PF < 1.2)** |
| PAIR-B-ZN-ZB-curve-monthly | vol_adjusted | 0 | nan | $0.00 | 0.0% | 0/0 | nan/nan | — | **KILL (insufficient-n)** |
| PAIR-C-MGC-MCL-realasset-monthly | vol_adjusted | 10 | 0.950 | $255.81 | 0.0% | 3/5 | 0.18/inf | 0.10 / 0.54 / inf | **KILL (PF < 1.2)** |

## Per-pair detail

### PAIR-A-MES-ZN-yieldgap-monthly
- Thesis: Equity vs rates yield-gap value: long the cheaper, short the richer at monthly rebalance
- Verdict: **KILL (PF < 1.2)**
- Per-year:
  - 2020: n=1 PF=inf net=$700
  - 2021: n=3 PF=0.427 net=$-1932
  - 2022: n=2 PF=inf net=$652
  - 2024: n=1 PF=0.000 net=$-760
  - 2025: n=2 PF=0.000 net=$-4082
  - 2026: n=2 PF=0.435 net=$-1275

### PAIR-B-ZN-ZB-curve-monthly
- Thesis: Rates curve trade: ZN (10y) vs ZB (30y) z-spread; vol-adjusted to neutralize duration
- Verdict: **KILL (insufficient-n)**
- Per-year:

### PAIR-C-MGC-MCL-realasset-monthly
- Thesis: Commodity relative-value: gold vs crude as inflation-sensitive real-asset spread
- Verdict: **KILL (PF < 1.2)**
- Per-year:
  - 2020: n=1 PF=0.000 net=$-112
  - 2021: n=3 PF=0.075 net=$-5135
  - 2022: n=2 PF=inf net=$796
  - 2023: n=3 PF=inf net=$1143
  - 2024: n=1 PF=inf net=$3027
