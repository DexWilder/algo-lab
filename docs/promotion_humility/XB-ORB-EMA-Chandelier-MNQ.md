# Promotion Humility Packet — `XB-ORB-EMA-Chandelier-MNQ`

*Cluster leader for the XB-ORB-EMA-MNQ exposure cluster (TimeStop variant collapses to this slot).*
*All quoted PFs are net (cost-adjusted) per FQL evidence law.*

**Funnel result:** 10/11 paper-eligible (S1=4 / G4=3 / G5=1 / G6=2 / G7=PENDING).
**Net PF (cost-aware):** 1.574 — Worst-half WF 1.242 — Stability 0.66 — Concentration top-3=14.5%, top-10=31.5%, max-year=29.6%.

## 1. Failure modes

- **H2-outperformance pattern is regime-conditional.** WF stability 0.66 because H1 = 1.242 vs H2 = 1.882. The H2 lift (51% higher PF) is meaningful and could reflect either (a) strategy improvement in recent regime or (b) regime concentration in H2. A regime decomposition should run before live deployment to distinguish.
- **Chandelier exit family is exit-evolution-sensitive.** Trailing-stop logic depends on ATR multiple — small parameter perturbations could materially change behavior. Robustness to `trail_mult ± 0.5` should be verified.
- **MNQ index regime change** (same as MNQ-Ladder candidate): a multi-month chop regime would compress edge.

## 2. Concentration caveat

Distribution **passes cleanly**: top-3 = 14.5%, top-10 = 31.5% of total PnL. Max-year = 29.6%. Healthy participation across the 1207-trade sample. No outlier-dependency.

## 3. Cost caveat

Cost basis: commission $0.62/side, slippage 1 tick. Cost ratio 7.6% of gross avg trade. Slightly higher than the Ladder variant (4.9%) because Chandelier exit holds positions modestly longer on average, generating fewer trades and lower per-trade gross. Still robust to broker-rate uncertainty.

## 4. Forward-evidence caveat

**PENDING_FORWARD_EVIDENCE.** This candidate has never been forward-traded. G7 = pending (not 0, not failed). Paper-eligible NOW; **promotion-eligible only after ≥30 forward trades accumulate** per the operator-locked Gate 7 framing 2026-05-20.

The 30-forward-trade requirement is more important here than for the existing probation candidates because Chandelier's exit family hasn't been live-tested at all.

## 5. Broker-rate caveat

MNQ rates — see XB-ORB-EMA-Ladder-MNQ packet. Same broker-rate replacement priority (medium).

## 6. Cluster / correlation caveat

**Cluster LEADER** for the XB-ORB-EMA-MNQ exposure cluster.
- XB-ORB-EMA-TimeStop-MNQ is the retained variant of this cluster. TimeStop's H1=1.246 is essentially identical to this candidate's H1=1.242, but TimeStop's H2=1.732 is 0.15 below this candidate's H2=1.882. **TimeStop does not add diversifying signal — Chandelier is the better cluster slot.**
- Counts as **one exposure slot** for top-3 selection (TimeStop does not take a separate slot).

## 7. What would invalidate the candidate

- **Forward net PF < 1.0 after 30+ trades** → ARCHIVE from paper consideration
- **Forward net PF in [1.0, 1.15) after 50+ trades** → DEFER, more forward needed
- **H2 outperformance traced to single regime in retrospective decomposition** → candidate is regime-dependent, not robust; downgrade
- **Chandelier-specific behavior diverges from Ladder by >15% PF in same period** → exit family is dominant driver (good or bad signal — needs operator interpretation)
