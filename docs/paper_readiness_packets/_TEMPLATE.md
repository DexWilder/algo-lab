# Paper-Readiness Packet — `<STRATEGY_ID>`

*Deliverable for Phase 2 Paper-Readiness Sprint Item #9 (2026-06-17 target).*
*All quoted PFs are net (cost-adjusted) per FQL evidence law (`feedback_evidence_integrity_failsafe.md`).*

## Paper-test readiness decision

**`PAPER_APPROVE` / `PAPER_APPROVE_CONDITIONAL` / `DEFER` / `REJECT`**

Recommendation: [one-sentence operator-actionable verdict].

## 1. Cost-aware evidence summary

- **Net PF (full sample):** X.XXX
- **Cost basis:** comm=$X.XX, slip=Nt (source: `engine/asset_config.py`)
- **Cost as % of gross avg trade:** XX.X%
- **Total trades:** N
- **Net PnL (full sample):** $X,XXX

## 2. Validation funnel score

- **Cumulative:** X/13 (probation) or X/11 (non-probation)
- **Per gate:** S1=4, G4=3, G5=X, G6=X, G7=X, G8=1

## 3. Walk-forward summary

- **H1 net PF / H2 net PF:** X.XXX / X.XXX (split at YYYY-MM-DD)
- **Worst-half PF:** X.XXX
- **Stability ratio:** X.XX
- **Trade counts:** H1=N, H2=N

## 4. Concentration findings

- **Top-3 share:** XX.X% (gate <30%)
- **Top-10 share:** XX.X% (gate <55%)
- **Max-year share:** XX.X% (gate <40%)
- **Verdict:** PASS / FAIL

## 5. Forward-evidence status

- **Forward trades to date:** N
- **Gate 7:** PASS / 0 / PENDING_FORWARD_EVIDENCE
- **What more is needed:** specific count or operator action.

## 6. Humility / failure modes

Reference: `docs/promotion_humility/<STRATEGY_ID>.md` (filed 2026-05-20).

Top concrete failure-mode flags from that packet:
- ...

## 7. Cost & broker-rate caveats

- ...

## 8. Cluster / correlation caveats

- ...

## 9. Paper-test scope

- **Asset:** ...
- **Mode:** long / short / both
- **Position sizing:** ...
- **Suggested probation window for paper:** ...
- **Suggested forward trade target before promotion review:** ...

## 10. What would invalidate the candidate

Concrete thresholds (mostly from humility packet):
- ...

## 11. Open requirements before promotion / live

Checklist that must clear before live deployment (not before paper):
- [ ] forward net PF ≥ threshold at N forward trades
- [ ] actual broker rate sheet replaces conservative estimate
- [ ] ...
