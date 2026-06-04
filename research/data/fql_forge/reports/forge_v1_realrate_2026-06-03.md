# FQL Forge — V1: GLD-RealRate-MGC-monthly (VALUE)

**Date:** 2026-06-03 • Mode: dry-run / report-only / Lane B
**Authority:** T1; no registry mutation
**Harness:** `research/monthly_rebalance_engine.py`
**Data:** Hardcoded minimum-viable 10y real-yield + broad USD index monthly history.

## Rule

60-month rolling regression of monthly MGC log-return vs (Δ10y real yield, ΔDXY).
- LONG when residual < -1.5σ AND month-over-month Δreal yield ≤ 0
- SHORT when residual > +1.5σ AND Δreal yield ≥ 0
- Else flat. Monthly exit.

## Signal series stats

- Total months: **84**
- LONG months: **1**
- SHORT months: **3**
- Flat months: **80**

## Result (cost-aware)

| Field | Value |
|---|---:|
| n trades | 4 |
| Net PF | 0.701 |
| Median trade | $-294.74 |
| Net PnL | $-637 |
| Max DD | $-2129 |
| Win rate | 25.0% |
| Max-year share | 0.0% |
| Top-3 | 0.0% |
| Top-10 | 0.0% |
| H1 / H2 PF | 3.024 / 0.000 |
| Years+ | 1/3 |
| Archetype | UNKNOWN | gate | KILL |
| **Verdict** | **KILL** |

## Safety

- No registry mutation • no Lane A touch • no scheduler change
- Data hardcoded; FRED ingest gated on operator approval
