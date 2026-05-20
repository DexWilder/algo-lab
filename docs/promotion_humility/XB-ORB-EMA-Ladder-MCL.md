# Promotion Humility Packet — `XB-ORB-EMA-Ladder-MCL`

*Probation since 2026-04-08. FRAGILE candidate — flagged `cost_fragility` in registry.*
*All quoted PFs are net (cost-adjusted) per FQL evidence law.*

**Funnel result:** 10/13 paper-eligible (S1=4 / G4=3 / G5=1 / G6=2 / G7=0).
**Net PF (cost-aware):** 1.298 — Worst-half WF 1.199 — Stability 0.87 — Concentration top-3=14.4%, top-10=40.8%, max-year=27.1%.

## 1. Failure modes

- **Cost-assumption fragility is the dominant risk.** Cost is **34.7% of gross avg trade** — the highest in the pool by ~3x. Any slip-estimate error compounds heavily.
- **Worst-half WF at 1.199** sits 0.001 above the 1.20 backtest gate boundary. Stability 0.87 is actually the highest of the probation pool (most consistent across halves), but absolute level is closest to the gate.
- **Energy commodity regime sensitivity.** MCL is a single-commodity (crude oil) micro. A multi-quarter regime change in oil volatility could compress edge significantly.
- **Probation forward-trade gap** (20 trades, 10 short of Gate 7): smallest sample of the three probation candidates by absolute count.

## 2. Concentration caveat

Distribution **passes** but **top-10 at 40.8%** is the highest of the paper-eligible pool (next closest is Chandelier at 31.5%). Top-3 = 14.4% is clean. Max-year = 27.1% comfortable.

The 40.8% top-10 means roughly 4% of trades carry 40% of profit — modestly outlier-dependent but well below the 55% gate. Less robust than MNQ probation (top-10 = 22.2%) but not concentration-failed.

## 3. Cost caveat

Cost basis: commission $0.62/side, slippage **2 ticks** (conservative bias per Piece I — MCL micros lag full-size CL liquidity). Cost ratio **34.7%** — the highest concern in the pool.

**Sensitivity analysis:**
- Slip = 1 tick (less conservative): net PF likely ~1.37 — comfortable
- Slip = 2 ticks (current assumption): net PF 1.298 — barely above gate
- Slip = 3 ticks (worse than assumed): net PF likely ~1.20 — at gate boundary
- Slip = 4 ticks: net PF likely below gate

**Operator action required before paper:** replace conservative estimate with actual MCL broker rate sheet. MCL is the **highest-priority asset for broker-rate replacement** in the entire pool.

## 4. Forward-evidence caveat

**20 forward trades as of 2026-05-20** — below the Gate 7 threshold of 30. G7 = 0; needs **+10 more forward trades** to clear. Smallest forward sample of probation pool. Paper-eligible now; **promotion-eligible only after accumulation AND broker-rate verification.**

The two caveats compound: even if forward accumulates cleanly to 30+ trades, broker-rate uncertainty remains the binding constraint.

## 5. Broker-rate caveat

**HIGHEST priority for broker-rate replacement in the pool.** Conservative slip=2 estimate is the assumption upon which paper-eligibility depends. Actual MCL micro fee schedule and realistic slippage observations are required before any paper deployment. If actual rates show slip > 2 ticks routinely, this candidate flips to YELLOW (1.05 ≤ net PF < 1.20).

## 6. Cluster / correlation caveat

**Distinct exposure cluster.** Only viable MCL candidate after the cost integrity reset (XB-BB-EMA-Ladder-MCL, XB-VWAP-EMA-Ladder-MCL archived; XB-PB-EMA-Ladder-MCL is monitor). This is **the sole MCL strategy carrying energy diversification** in the pool.

Implication: if this candidate fails, the pool loses MCL/energy exposure entirely.

## 7. What would invalidate the candidate

Per `XB_ORB_PROBATION_FRAMEWORK.md` + the cost_fragility flag:

- **Forward net PF < 0.90 after 30+ trades** → downgrade to WATCH (standard XB-ORB rule)
- **Forward net PF < 0.80 after 50+ trades** → ARCHIVE
- **Actual MCL slippage observed > 3 ticks routinely** → net PF approaches gate; downgrade or pause paper
- **Single-month drawdown > $1500** (the max-DD comparable) → behavioral or regime shift
- **Top-10 share rises above 45% on incremental data** → concentration health degrading
- **Behavioral drift flag** rate > 25% in forward trades
- **Energy regime change** — sustained crude vol regime shift (e.g., HV→LV for multiple months) — causes structural compression
