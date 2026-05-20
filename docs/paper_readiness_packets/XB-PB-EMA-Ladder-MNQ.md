# Paper-Readiness Packet — `XB-PB-EMA-Ladder-MNQ`

*Phase 2 deliverable. Distinct entry family (pullback) on MNQ — non-ORB workhorse.*
*All quoted PFs are net (cost-adjusted) per FQL evidence law.*

## Paper-test readiness decision

**`PAPER_APPROVE_CONDITIONAL`** — operator approval required to add this candidate to the forward paper runner.

**Recommendation:** Add to forward paper runner. Diversifies entry family beyond ORB (the only family currently in probation). Run alongside MNQ-Ladder probation and Chandelier-MNQ (post-approval). Report at 30-forward-trade gate.

## 1. Cost-aware evidence summary

| Metric | Value |
|---|---|
| Net PF (full sample, post-Piece-I) | **1.406** |
| Cost basis | comm=$0.62/side, slip=1 tick |
| Cost as % of gross avg trade | 10.0% |
| Total trades | 1,474 (deepest sample of paper-eligible pool) |
| Cost source of truth | `engine/asset_config.py` |

## 2. Validation funnel score

**Cumulative: 11/11** (non-probation max) — paper-eligible; promotion-eligible **PENDING_FORWARD_EVIDENCE**.

| Gate | Score | Note |
|---|---:|---|
| G1 cheap-screen PASS | 1/1 | correlation-matrix candidate |
| G2 correlation cleared | 1/1 | distinct cluster (different entry family) |
| G3 cost-adjusted PF ≥ 1.15 | 2/2 | 1.406 |
| G4 walk-forward H1/H2 | 3/3 | both halves > 1.0 |
| G5 trade count | 1/1 | workhorse 1,474 ≥ 500 |
| G6 concentration | 2/2 | passes (top-3 10.2%, top-10 27.8%) |
| G7 forward trades ≥30 | PENDING | non-probation; never forward-traded |
| G8 promotion humility | 1/1 | doc filed 2026-05-20 |

## 3. Walk-forward summary

- **H1 net PF:** 1.200 (747 trades)
- **H2 net PF:** 1.603 (727 trades)
- **Worst-half PF:** 1.200 — **right at the 1.20 backtest gate**
- **Stability ratio:** 0.75
- **Pattern flag:** H1 = 1.200 is the gate boundary; any forward degradation directly threatens the candidate

## 4. Concentration findings

| Metric | Value | Gate | Verdict |
|---|---:|---:|---|
| Top-3 share | 10.2% | <30% | ✓ |
| Top-10 share | 27.8% | <55% | ✓ |
| Max-year share | **39.0%** | <40% | ✓ (borderline — 1 pp from gate) |

**Max-year share at 39.0% is 1pp under the 40% gate.** Borderline year-concentration; one weak year (e.g., a chop regime) could flip this on re-evaluation with new data.

## 5. Forward-evidence status

- **Forward trades to date:** 0 (never forward-traded)
- **Gate 7:** PENDING_FORWARD_EVIDENCE — non-probation candidate
- **What more is needed:** ≥30 forward trades under cost-aware engine
- **Expected timing:** PB strategies are slower-firing than ORB; expect ~3-6 months to 30-trade gate

## 6. Humility / failure modes

Reference: `docs/promotion_humility/XB-PB-EMA-Ladder-MNQ.md`

Top concrete failure flags:
- Entry family structurally different from probation — probation ORB evidence does NOT transfer
- Worst-half WF at 1.200 sits exactly at gate; thin margin
- Max-year 39.0% one pp under threshold
- Single-asset within the pool (MCL/MYM PB variants archived/borderline)

## 7. Cost & broker-rate caveats

- Cost ratio 10.0% (higher than ORB variants 4.9-7.6%)
- **Replacement priority medium-high** — slippage assumption matters more here than for ORB
- Robust to small broker-rate uncertainty but more sensitive than ORB

## 8. Cluster / correlation caveats

**Distinct exposure cluster** (different entry family from XB-ORB-* and XB-VWAP-*).

Note: this is the **only viable PB-Ladder variant** in the pool. MCL is archived (RED), MYM is paper-borderline (concentration fail). MNQ is the single-asset diversification benefit for this entry family. Generalization to MES/MGC remains untested.

## 9. Paper-test scope (recommended new configuration)

- **Asset:** MNQ
- **Mode:** both
- **Position sizing:** 1 contract (match existing MNQ-Ladder probation sizing)
- **Probation window:** start on operator-approval date; review at 30 forward trades
- **Forward trade target for promotion review:** 30
- **Special caveat:** pullback entries are slower-firing than ORB; expect lower trade frequency than MNQ-Ladder. Set forward-runner trade-count expectation accordingly.

## 10. What would invalidate the candidate

- Forward net PF < 1.0 after 30+ trades → ARCHIVE
- Forward net PF in [1.0, 1.15) after 50+ trades → DEFER
- Max-year share crosses 40% on next year's incremental data → concentration gate failure on re-evaluation
- Pullback signal generation rate diverges from backtest by >25% → signal logic issue
- Cost ratio drift above 15% → broker-rate assumption wrong; pushes WF closer to gate

## 11. Open requirements before promotion / live

- [ ] ≥30 forward trades under cost-aware engine (Gate 7 clear)
- [ ] Max-year share re-checked on rolling window (not just single calculation)
- [ ] Operator review at 30-trade gate
- [ ] Actual broker rate sheet replaces conservative MNQ estimate (medium-high priority for this candidate)
- [ ] Cross-asset generalization tested (MES/MGC) before considering broader paper deployment
