# Validation Funnel v0 — Session 2 (2026-05-20) — chunk: timestop

**Filed by:** `research/validation_funnel.py`
**Authority:** T1 intelligence; no registry mutation, no status changes.
**Sprint:** Phase 2 / Paper-Readiness Sprint Item #7 — Session 2 of 4.

## Gate 4 — Walk-Forward H1/H2 (cost-aware)

- 50/50 date-midpoint split of each asset's price series
- Cost-aware backtest on each half (`engine/asset_config.py` source of truth)
- Pass requires **both halves > 1.0 net PF** (worth 3 points)

## Walk-forward results

| Candidate | Asset | H1 PF | H2 PF | Worst | Stability | H1 trades | H2 trades | Pass? | G4 pts |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|
| XB-ORB-EMA-TimeStop-MNQ | MNQ | 1.246 | 1.732 | 1.246 | 0.72 | 599 | 608 | ✓ | 3 |

## Cumulative scores after Gate 4

| Candidate | S1 | G4 | Total (out of 7) | Net PF | Notes |
|---|---:|---:|---:|---:|---|
| XB-ORB-EMA-TimeStop-MNQ | 3/4 | 3 | 6/7 | 1.507 |  |
| XB-ORB-EMA-Ladder-MNQ | 4/4 | — | 4/7 | 1.620 | deferred (different chunk) |
| XB-ORB-EMA-Ladder-MCL | 4/4 | — | 4/7 | 1.298 | deferred (different chunk) |
| XB-ORB-EMA-Ladder-MYM | 4/4 | — | 4/7 | 1.625 | deferred (different chunk) |
| XB-PB-EMA-Ladder-MNQ | 4/4 | — | 4/7 | 1.406 | deferred (different chunk) |
| XB-PB-EMA-Ladder-MYM | 4/4 | — | 4/7 | 1.202 | deferred (different chunk) |
| XB-BB-EMA-Ladder-MNQ | 4/4 | — | 4/7 | 1.237 | deferred (different chunk) |
| XB-BB-EMA-Ladder-MGC | 4/4 | — | 4/7 | 1.592 | deferred (different chunk) |
| XB-BB-EMA-Ladder-MYM | 4/4 | — | 4/7 | 1.551 | deferred (different chunk) |
| XB-VWAP-EMA-Ladder-MGC | 4/4 | — | 4/7 | 1.297 | deferred (different chunk) |
| XB-VWAP-EMA-Ladder-MYM | 4/4 | — | 4/7 | 1.325 | deferred (different chunk) |
| XB-ORB-EMA-Chandelier-MNQ | 4/4 | — | 4/7 | 1.574 | deferred (different chunk) |

## Eligible / Culled summary

- **1 candidates passed Gate 4** (full 3 pts; both halves > 1.0 net PF)
- **0 candidates failed Gate 4** (one or both halves ≤ 1.0)
- **11 candidates deferred** to other chunks

## Cost fragility notes

- **XB-ORB-EMA-Ladder-MCL** (full-sample net PF 1.298, cost 34.7% of gross avg trade) is the most cost-sensitive surviving probation candidate. Any WF half ratio < 0.6 should be flagged as compounding fragility.
- All MCL/MYM candidates run with slip=2 (conservative bias); the WF result inherits that cost basis.

---

*Session 2 chunk 'timestop'. Read-only intelligence; no decisions taken. Next chunk(s) or Session 3 to follow.*
