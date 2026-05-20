# Promotion Humility Packet — `XB-ORB-EMA-TimeStop-MNQ`

*Retained variant of the XB-ORB-EMA-MNQ exposure cluster — Chandelier is the cluster leader.*
*All quoted PFs are net (cost-adjusted) per FQL evidence law.*

**Funnel result:** 9/11 paper-eligible (S1=3 / G4=3 / G5=1 / G6=2 / G7=PENDING). The 3/4 S1 reflects Gate 2 = 0 by design (cluster duplicate, not performance failure).
**Net PF (cost-aware):** 1.507 — Worst-half WF 1.246 — Stability 0.72 — Concentration top-3=11.3%, top-10=28.7%, max-year=24.9%.

## 1. Failure modes

- **Cluster duplication.** Shares the same XB-ORB-EMA-MNQ exposure as the Chandelier variant. If the Chandelier candidate fails forward, this candidate's signal is also implicated — same entry, same filter, different exit only.
- **Exit mechanic — fixed time-stop** — is more rigid than profit-ladder or chandelier. If MNQ intraday character shifts to longer-tail moves, the time-stop cuts winners early. Sensitive to session-time-of-day distribution drift.
- **TimeStop H2 = 1.732 is 0.15 below Chandelier's H2 = 1.882.** TimeStop is the materially weaker variant in the recent period.

## 2. Concentration caveat

Distribution **passes cleanly**: top-3 = 11.3%, top-10 = 28.7%, max-year = 24.9%. Healthy participation across 1207 trades. Similar shape to Chandelier (14.5% / 31.5% / 29.6%) — slightly more diffuse top-end, slightly more concentrated max-year. Effectively equivalent.

## 3. Cost caveat

Cost basis: commission $0.62/side, slippage 1 tick. Cost ratio 8.8% of gross avg trade — close to Chandelier's 7.6%. Robust.

## 4. Forward-evidence caveat

**PENDING_FORWARD_EVIDENCE.** Never forward-traded. G7 = pending. Paper-eligible NOW but **promotion-eligible only after ≥30 forward trades accumulate.**

**Important:** since TimeStop and Chandelier share the cluster, forward-testing both in parallel doubles paper-account complexity for the same exposure. Strong preference is to forward-test Chandelier alone and treat TimeStop as a follow-up variant if forward Chandelier evidence is positive.

## 5. Broker-rate caveat

MNQ rates — see XB-ORB-EMA-Ladder-MNQ packet. Same replacement priority (medium).

## 6. Cluster / correlation caveat

**RETAINED VARIANT** of the XB-ORB-EMA-MNQ exposure cluster.
- Cluster leader: XB-ORB-EMA-Chandelier-MNQ (better H2 evidence, 1.882 vs this candidate's 1.732)
- Both candidates count as **one exposure slot** for top-3 selection per the 2026-05-19 cluster decision.
- This candidate stays REGISTERED for exit-substitution evidence but **does not earn a separate top-3 slot**. If the cluster leader takes a top-3 slot, this candidate stands down for the sprint.

## 7. What would invalidate the candidate

- **Chandelier-MNQ failing forward** would invalidate this slot too (shared exposure).
- **Forward net PF < 1.0 after 30+ trades** → ARCHIVE
- **Forward net PF in [1.0, 1.15) after 50+ trades** → DEFER
- **TimeStop diverges materially from Chandelier forward** (>0.3 PF gap in same period) — the exit-substitution research becomes interesting: which exit is better in live conditions? Decision packet rather than auto-classify.
- **Time-of-day distribution drifts more than the cluster leader's** — signals time-stop mechanic is fighting the regime.

## Cluster recommendation

For the sprint: **defer TimeStop in favor of Chandelier as the cluster representative**. TimeStop remains registered for future exit-evolution research but is not part of the top-3 paper packet selection.
