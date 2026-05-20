# Promotion Humility Packet — `XB-PB-EMA-Ladder-MNQ`

*Pullback-entry crossbreed on MNQ; never forward-traded.*
*All quoted PFs are net (cost-adjusted) per FQL evidence law.*

**Funnel result:** 10/11 paper-eligible (S1=4 / G4=3 / G5=1 / G6=2 / G7=PENDING).
**Net PF (cost-aware):** 1.406 — Worst-half WF 1.200 — Stability 0.75 — Concentration top-3=10.2%, top-10=27.8%, max-year=39.0%.

## 1. Failure modes

- **Entry family is structurally different from probation.** Pullback entries (waiting for retracement to EMA) are slower-firing than ORB breakouts. Different signal characteristic = different exposure profile, which is the diversification value, but it also means probation evidence on ORB does NOT transfer.
- **Worst-half WF is at the 1.200 line.** Net PF 1.200 in H1 is exactly at the backtest workhorse gate. Any forward degradation directly threatens the candidate.
- **Max-year share at 39.0%** is one tick under the 40% Gate 6 threshold. Borderline year-concentration; a single weak year (e.g., 2023 chop) could flip this.

## 2. Concentration caveat

Distribution **passes** but **margins are thin on max-year share** (39.0% vs 40% threshold). Top-3 = 10.2%, top-10 = 27.8% — broadly distributed within years, but ONE year carries 39% of total PnL. Worth verifying which year and what conditioned it.

## 3. Cost caveat

Cost basis: commission $0.62/side, slippage 1 tick. Cost ratio 10.0% of gross avg trade. Higher than ORB variants (4.9–7.6%) because pullback strategies generate fewer trades with larger per-trade size, so each commission is a larger fraction of edge. Robust to broker-rate uncertainty in absolute terms, but more sensitive than ORB.

## 4. Forward-evidence caveat

**PENDING_FORWARD_EVIDENCE.** Never forward-traded. G7 = pending. Paper-eligible NOW; **promotion-eligible only after ≥30 forward trades accumulate**.

For a non-ORB entry family on MNQ, the 30-forward-trade requirement is more important than for ORB variants because the entry mechanism's behavior under live conditions hasn't been observed at all.

## 5. Broker-rate caveat

MNQ rates — see XB-ORB-EMA-Ladder-MNQ packet. Replacement priority **medium-high** for this candidate specifically because cost ratio is 10% (vs 5% for ORB-Ladder); slippage assumption matters more.

## 6. Cluster / correlation caveat

**Distinct exposure cluster.** Different entry family (pb_pullback) from XB-ORB-EMA-Chandelier-MNQ (orb_breakout). Correlation matrix classified as DISTINCT.

Note: there are PB-Ladder variants on other assets (MYM, MCL) — MCL is archived (RED), MYM is paper-borderline (concentration fail). So **MNQ is the only viable PB-Ladder variant in the pool**. Single-asset exposure; diversification benefit conditional on it generalizing to MES/MGC in future testing.

## 7. What would invalidate the candidate

- **Forward net PF < 1.0 after 30+ trades** → ARCHIVE
- **Forward net PF in [1.0, 1.15) after 50+ trades** → DEFER
- **Max-year share crosses 40% on the next year's data** → concentration gate failure on re-evaluation
- **Pullback signal generation rate diverges from backtest expectation by >25%** → signal logic issue
- **Cost ratio drift above 15%** → broker-rate or slippage assumption is wrong; would push WF closer to gate
