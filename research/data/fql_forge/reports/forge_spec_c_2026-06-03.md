# FQL Forge — Spec C: CRY-Policy-Rate-Differential-6J

**Date:** 2026-06-03  •  **Mode:** dry-run / report-only / Lane B
**Authority:** T1; no registry mutation; no Lane A touch
**Harness:** `research/monthly_rebalance_engine.py` (built 2026-06-02; smoke-passed 2026-06-03)
**Data:** Hardcoded minimum-viable Fed Funds + BoJ policy rate monthly history. FRED ingest deferred per operator decision.

## Rule

At each month-end, compute `spread = Fed Funds − BoJ policy`.
- SHORT 6J for the next month IF `spread > 12m trailing median` AND `Δspread ≥ 0`.
- Else flat. Mechanical month-end exit.

## Signal series stats

- Total months: **40**
- Short months: **12**
- Flat months: **28**

## Result (cost-aware)

| Field | Value |
|---|---:|
| n trades | 1 |
| Net PF | inf |
| Median trade | $613.75 |
| Net PnL | $614 |
| Max DD | $0 |
| Win rate | 100.0% |
| Max-year share | 100.0% |
| Top-3 share | 100.0% |
| Top-10 share | 100.0% |
| H1 PF / H2 PF | inf / inf |
| Years positive | 1/1 |
| Archetype | TAIL_ENGINE |
| Gate verdict | DEFER |
| Blocker reason | only 1 trades — below tail-engine sample minimum 30 |
| **Cheap-screen verdict** | **RETEST** |

## Safety

- No registry mutation • no Lane A touch • no scheduler change
- Data source is hardcoded canonical history; not decision-grade until FRED ingest is approved
