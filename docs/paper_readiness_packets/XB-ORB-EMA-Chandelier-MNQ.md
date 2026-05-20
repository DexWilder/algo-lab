# Paper-Readiness Packet — `XB-ORB-EMA-Chandelier-MNQ`

*Phase 2 deliverable. Cluster leader for the XB-ORB-EMA-MNQ exposure cluster.*
*All quoted PFs are net (cost-adjusted) per FQL evidence law.*

## Paper-test readiness decision

**`PAPER_APPROVE_CONDITIONAL`** — operator approval required to add this candidate to the forward paper runner.

**Recommendation:** Add to forward paper runner. **TimeStop variant does NOT separately enter paper** (one slot for the cluster; Chandelier wins it per H2 evidence). Run alongside the existing XB-ORB-EMA-Ladder probation; report at 30-forward-trade gate.

## 1. Cost-aware evidence summary

| Metric | Value |
|---|---|
| Net PF (full sample, post-Piece-I) | **1.574** |
| Cost basis | comm=$0.62/side, slip=1 tick |
| Cost as % of gross avg trade | 7.6% |
| Total trades | 1,207 |
| Cost source of truth | `engine/asset_config.py` |

## 2. Validation funnel score

**Cumulative: 11/11** (non-probation max) — paper-eligible; promotion-eligible **PENDING_FORWARD_EVIDENCE**.

| Gate | Score | Note |
|---|---:|---|
| G1 cheap-screen PASS | 1/1 | correlation-matrix candidate |
| G2 correlation cleared | 1/1 | cluster LEADER |
| G3 cost-adjusted PF ≥ 1.15 | 2/2 | 1.574 |
| G4 walk-forward H1/H2 | 3/3 | both halves > 1.0 |
| G5 trade count | 1/1 | workhorse 1,207 ≥ 500 |
| G6 concentration | 2/2 | passes (top-3 14.5%, top-10 31.5%) |
| G7 forward trades ≥30 | PENDING | non-probation; never forward-traded |
| G8 promotion humility | 1/1 | doc filed 2026-05-20 |

## 3. Walk-forward summary

- **H1 net PF:** 1.242 (599 trades)
- **H2 net PF:** 1.882 (608 trades)
- **Worst-half PF:** 1.242
- **Stability ratio:** 0.66 — **lowest of paper-eligible pool**
- **Pattern flag:** H2 outperforms H1 by 51%. Possible regime concentration in H2 — should be examined with a regime decomposition before live (not before paper).

## 4. Concentration findings

| Metric | Value | Gate | Verdict |
|---|---:|---:|---|
| Top-3 share | 14.5% | <30% | ✓ |
| Top-10 share | 31.5% | <55% | ✓ |
| Max-year share | 29.6% | <40% | ✓ |

Healthy participation. No outlier-dependency.

## 5. Forward-evidence status

- **Forward trades to date:** 0 (never forward-traded)
- **Gate 7:** PENDING_FORWARD_EVIDENCE — non-probation candidate
- **What more is needed:** ≥30 forward trades accumulated under cost-aware engine before promotion-eligibility
- **Expected timing:** at ~1-2 trades/week starting from paper-test commencement, ~3–6 months to 30-trade gate

## 6. Humility / failure modes

Reference: `docs/promotion_humility/XB-ORB-EMA-Chandelier-MNQ.md`

Top concrete failure flags:
- H2-outperformance pattern may be regime-conditional (stability 0.66)
- Chandelier exit family is exit-evolution-sensitive (ATR-multiple parameter)
- MNQ index regime change (same as Ladder)

## 7. Cost & broker-rate caveats

- Same as MNQ-Ladder: medium replacement priority, robust to broker-rate uncertainty
- Cost ratio 7.6% vs Ladder's 4.9% (Chandelier holds longer on average → fewer trades, lower per-trade gross)

## 8. Cluster / correlation caveats

**CLUSTER LEADER** for XB-ORB-EMA-MNQ exposure cluster.
- XB-ORB-EMA-TimeStop-MNQ is the retained variant; TimeStop's H2 (1.732) is 0.15 below this candidate's H2 (1.882).
- **Both register as one exposure slot** for top-3 selection per the 2026-05-19 cluster decision.
- TimeStop is preserved as retained variant evidence; it does NOT separately enter paper.
- If this candidate fails forward, TimeStop's slot is also impacted (shared entry+filter exposure).

## 9. Paper-test scope (recommended new configuration)

- **Asset:** MNQ
- **Mode:** both
- **Position sizing:** 1 contract (match existing MNQ-Ladder probation sizing)
- **Probation window:** start on operator-approval date; review at 30 forward trades
- **Forward trade target for promotion review:** 30
- **Special caveat:** suggest running a regime decomposition on the H1/H2 PF gap before any live decision (paper is fine; live needs the diagnosis)

## 10. What would invalidate the candidate

- Forward net PF < 1.0 after 30+ trades → ARCHIVE from paper consideration
- Forward net PF in [1.0, 1.15) after 50+ trades → DEFER
- H2 outperformance traced to single regime in retrospective decomposition → candidate is regime-dependent, not robust; downgrade
- Chandelier-specific behavior diverges from Ladder by >15% PF in same period → exit family is dominant driver (interpret separately)

## 11. Open requirements before promotion / live

- [ ] ≥30 forward trades under cost-aware engine (Gate 7 clear)
- [ ] Regime decomposition of H1/H2 PF gap (before live, not before paper)
- [ ] Operator review at 30-trade gate
- [ ] Actual broker rate sheet replaces conservative MNQ estimate
- [ ] Sustained no behavioral drift through 30-trade gate
