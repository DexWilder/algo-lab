# Paper-Readiness Packet — `XB-ORB-EMA-Ladder-MNQ`

*Phase 2 deliverable. Anchor candidate of the workhorse trio.*
*All quoted PFs are net (cost-adjusted) per FQL evidence law.*

## Paper-test readiness decision

**`PAPER_APPROVE`** (continue current probation paper-test; no scope change needed).

**Recommendation:** This candidate is already in active forward paper-test (probation since 2026-04-06, 24 forward trades to date). Continue current paper run; promotion gate triggers at +6 more forward trades. No change to current deployment posture required.

## 1. Cost-aware evidence summary

| Metric | Value |
|---|---|
| Net PF (full sample, post-Piece-I) | **1.620** |
| Cost basis | comm=$0.62/side, slip=1 tick |
| Cost as % of gross avg trade | **4.9%** (lowest in pool) |
| Total trades | 1,207 |
| Net PnL (full sample, MNQ-MES point_value basis) | ~$52,009 |
| Cost source of truth | `engine/asset_config.py` (post-Piece-I consolidation) |

## 2. Validation funnel score

**Cumulative: 11/13** (probation max) — paper-eligible, promotion-eligible borderline.

| Gate | Score | Note |
|---|---:|---|
| G1 cheap-screen PASS | 1/1 | original promotion cleared 2026-04-06 |
| G2 correlation cleared | 1/1 | distinct cluster |
| G3 cost-adjusted PF ≥ 1.15 | 2/2 | 1.620 |
| G4 walk-forward H1/H2 | 3/3 | both halves > 1.0 |
| G5 trade count | 1/1 | workhorse 1,207 ≥ 500 |
| G6 concentration | 2/2 | passes cleanly |
| G7 forward trades ≥30 | **0/2** | 24 forward (needs +6) |
| G8 promotion humility | 1/1 | doc filed 2026-05-20 |

## 3. Walk-forward summary

- **H1 net PF:** 1.445 (599 trades)
- **H2 net PF:** 1.781 (608 trades)
- **Worst-half PF:** 1.445 — comfortably above the 1.20 backtest gate
- **Stability ratio:** 0.81 (most consistent of probation pool by absolute level)
- **Pattern:** H2 stronger than H1 — recent regime favorable, but H1 still strong

## 4. Concentration findings

| Metric | Value | Gate | Verdict |
|---|---:|---:|---|
| Top-3 share | 9.2% | <30% | ✓ |
| Top-10 share | 22.2% | <55% | ✓ |
| Max-year share | 21.1% | <40% | ✓ |

**Cleanest concentration profile in the entire pool.** No outlier-dependency; broad participation across 1,207 trades. Sets the bar for what concentration health looks like.

## 5. Forward-evidence status

- **Forward trades to date:** 24 (since promotion 2026-04-06)
- **Gate 7:** 0/2 — needs **+6 more forward trades** to clear ≥30 threshold
- **Expected timing:** at current pace (~1-2 trades/week), gate clears in 3–6 weeks (mid-June to early July)
- **Paper-test action:** continue current probation forward run; no change

## 6. Humility / failure modes

Reference: `docs/promotion_humility/XB-ORB-EMA-Ladder-MNQ.md`

Top concrete failure flags:
- MNQ index regime change to choppy/range-bound (multi-month) compresses edge
- Liquidity transition (slip > 1 tick routine) raises cost ratio
- Behavioral drift: forward direction mix / time-of-day distribution drift >20% from backtest

## 7. Cost & broker-rate caveats

- Current cost basis is conservative estimate (CME retail-broker typical for MNQ micros).
- **MNQ replacement priority: medium** — high-liquidity asset, small cost ratio, robust to broker-rate uncertainty.
- Cushion to gate: even a doubling of slippage (1→2 ticks) keeps net PF above 1.20.

## 8. Cluster / correlation caveats

**Distinct exposure cluster.** No overlap with the other 2 paper-eligible MNQ candidates (Chandelier on exit substitution; PB-Ladder on entry substitution). Counts as one independent slot for top-3.

## 9. Paper-test scope (current configuration)

- **Asset:** MNQ (Micro E-mini Nasdaq-100)
- **Mode:** both (long + short)
- **Position sizing:** 1 contract (existing probation config)
- **Probation window:** 2026-04-06 → ongoing (per `XB_ORB_PROBATION_FRAMEWORK.md`)
- **Forward trade target for promotion review:** 30 (gate per framework); 100 for full promotion gate

## 10. What would invalidate the candidate

Per `XB_ORB_PROBATION_FRAMEWORK.md` (now explicit net PF per Piece H):

- Forward net PF < 0.90 after 30+ trades → downgrade to WATCH
- Forward net PF < 0.80 after 50+ trades → ARCHIVE
- Forward WR < 40% (vs backtest 56–61%)
- 3+ consecutive behavioral flags
- Max forward drawdown > 2× backtest max DD
- Zero trades for 20+ trading days (signal generation broken)
- Cost-ratio drift > 10% (slippage assumption proven materially wrong)

## 11. Open requirements before promotion / live

- [ ] Forward net PF ≥ 1.15 at ≥30 forward trades (Gate 7 clear)
- [ ] Operator review at 30-trade gate per probation framework
- [ ] Actual broker rate sheet replaces conservative MNQ estimate (medium priority)
- [ ] Sustained no behavioral drift through 30-trade gate
