# FQL Forge — FOMC Drift Event-Window Screens — 2026-06-04

Authority T1 / Lane B / report-only.
Calendar: 58 canonical FOMC meeting dates (2019-2026), 14:00 ET release.

## Result table

| Candidate | n | PF | Median | Max-Yr | Top-3 | Yrs+ | H1/H2 | Verdict |
|---|---:|---:|---:|---:|---:|---|---|---|
| EVT-FOMC-Drift-MES-Long | 55 | 0.817 | $16.26 | 0.0% | 0.0% | 3/8 | 0.93/0.71 | **KILL (PF < 1.15)** |
| EVT-FOMC-Drift-MES-Short | 55 | 1.113 | $-23.74 | 188.0% | 423.6% | 3/8 | 0.98/1.27 | **KILL (median negative)** |
| EVT-FOMC-Drift-ZN-Long | 55 | 1.349 | $43.78 | 99.5% | 104.7% | 5/8 | 1.33/1.36 | **TEMPORAL_SPLIT_REQUIRED** |
| EVT-FOMC-Drift-ZN-Short | 55 | 0.451 | $-112.48 | 0.0% | 0.0% | 2/8 | 0.45/0.45 | **KILL (median negative)** |
| EVT-FOMC-Drift-MES-Long-30min | 55 | 1.254 | $21.26 | 97.0% | 124.1% | 3/8 | 1.05/1.42 | **TEMPORAL_SPLIT_REQUIRED** |