# Validation Funnel v0 — Session 2 Consolidated (2026-05-20)

**Filed by:** `research/validation_funnel.py` (aggregated from 4 chunked runs)
**Authority:** T1 intelligence; no registry mutation, no status changes.
**Sprint:** Phase 2 / Paper-Readiness Sprint Item #7 — Session 2 of 4 (Gate 4 complete).

## Headline

**12 of 12 candidates pass Gate 4 walk-forward.** No candidate culled by H1/H2 splitting under cost-aware engine. The candidate pool is robust across time.

## Cost assumptions used (per FQL evidence law)

| Asset | Commission/side | Slippage (ticks) | Cost tier |
|---|---:|---:|---|
| MNQ | $0.62 | 1 | VALIDATED |
| MCL | $0.62 | 2 | VALIDATED |
| MYM | $0.62 | 2 | VALIDATED |
| MGC | $0.62 | 1 | VALIDATED |

Source of truth: `engine/asset_config.py` (post-Piece-I consolidation). Conservative estimates; replace with broker rate sheets before paper/prop.

## Gate 4 — Walk-Forward H1/H2 (cost-aware), all chunks

Sorted by worst-half PF (most fragile last):

| Candidate | Bucket | Asset | H1 PF | H2 PF | Worst | Stability | H1 trades | H2 trades | Pass? |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| XB-ORB-EMA-Ladder-MYM | probation | MYM | 1.783 | 1.429 | **1.429** | 0.80 | 187 | 184 | ✓ |
| XB-ORB-EMA-Ladder-MNQ | probation | MNQ | 1.445 | 1.781 | **1.445** | 0.81 | 599 | 608 | ✓ |
| XB-BB-EMA-Ladder-MNQ | corr-rest | MNQ | 1.276 | 1.209 | **1.209** | 0.95 | 344 | 327 | ✓ |
| XB-ORB-EMA-Ladder-MCL | probation | MCL | 1.379 | 1.199 | **1.199** | 0.87 | 450 | 468 | ✓ |
| XB-VWAP-EMA-Ladder-MGC | corr-rest | MGC | 1.246 | 1.328 | **1.246** | 0.94 | 187 | 187 | ✓ |
| XB-ORB-EMA-TimeStop-MNQ | timestop | MNQ | 1.246 | 1.732 | **1.246** | 0.72 | 599 | 608 | ✓ |
| XB-ORB-EMA-Chandelier-MNQ | corr-top | MNQ | 1.242 | 1.882 | **1.242** | 0.66 | 599 | 608 | ✓ |
| XB-BB-EMA-Ladder-MYM | corr-top | MYM | 1.216 | 2.094 | **1.216** | 0.58 | 122 | 116 | ✓ |
| XB-PB-EMA-Ladder-MNQ | corr-top | MNQ | 1.200 | 1.603 | **1.200** | 0.75 | 747 | 727 | ✓ |
| XB-VWAP-EMA-Ladder-MYM | corr-rest | MYM | 1.193 | 1.468 | **1.193** | 0.81 | 135 | 142 | ✓ |
| XB-BB-EMA-Ladder-MGC | corr-top | MGC | 1.191 | 1.915 | **1.191** | 0.62 | 152 | 139 | ✓ |
| XB-PB-EMA-Ladder-MYM | corr-rest | MYM | 1.177 | 1.218 | **1.177** | 0.97 | 235 | 235 | ✓ |

## Cumulative score after Session 2 (S1 + G4, out of 7)

| Candidate | S1 | G4 | Total | Net PF (full) | Worst-half WF | Note |
|---|---:|---:|---:|---:|---:|---|
| XB-ORB-EMA-Ladder-MYM | 4 | 3 | **7/7** | 1.625 | 1.429 | probation; strongest |
| XB-ORB-EMA-Ladder-MNQ | 4 | 3 | **7/7** | 1.620 | 1.445 | probation; deepest sample |
| XB-BB-EMA-Ladder-MGC | 4 | 3 | **7/7** | 1.592 | 1.191 | low stability (0.62) |
| XB-ORB-EMA-Chandelier-MNQ | 4 | 3 | **7/7** | 1.574 | 1.242 | cluster leader |
| XB-BB-EMA-Ladder-MYM | 4 | 3 | **7/7** | 1.551 | 1.216 | lowest stability (0.58) |
| XB-PB-EMA-Ladder-MNQ | 4 | 3 | **7/7** | 1.406 | 1.200 | deepest trade count |
| XB-VWAP-EMA-Ladder-MYM | 4 | 3 | **7/7** | 1.325 | 1.193 | |
| XB-ORB-EMA-Ladder-MCL | 4 | 3 | **7/7** | 1.298 | 1.199 | **fragile** — close to gate full+WF |
| XB-VWAP-EMA-Ladder-MGC | 4 | 3 | **7/7** | 1.297 | 1.246 | tightest stability (0.94) |
| XB-BB-EMA-Ladder-MNQ | 4 | 3 | **7/7** | 1.237 | 1.209 | tight stability (0.95) |
| XB-PB-EMA-Ladder-MYM | 4 | 3 | **7/7** | 1.202 | 1.177 | thinnest WF margin |
| XB-ORB-EMA-TimeStop-MNQ | 3 | 3 | **6/7** | 1.507 | 1.246 | retained variant (G2 fail by design) |

## Eligible / culled summary

- **12 of 12 candidates passed Gate 4.** 0 culled.
- **11 of 12 at 7/7** cumulative.
- **1 at 6/7** (TimeStop-MNQ): perfect on Gate 4 (3/3), but loses 1 point on Gate 2 by design — retained variant of the Chandelier cluster.
- **Exposure cluster count remaining: 11** (TimeStop + Chandelier collapse to one slot).

## Observations worth flagging

1. **All 4 corr-top candidates show H2 >> H1** (stability 0.58–0.75): XB-BB-MYM has H2/H1 ratio of 1.72; XB-BB-MGC 1.61; XB-ORB-Chandelier-MNQ 1.52. Either these archetypes improved in the second half OR H2 includes regime-favorable conditions. Worth a regime decomposition (Session 3 if scoped).
2. **All 4 corr-rest candidates show H2 ≈ H1** (stability 0.81–0.97): much more time-stable. XB-PB-MYM at 0.97 is essentially identical across halves.
3. **TimeStop vs Chandelier (cluster comparison):** Chandelier H1=1.242, H2=1.882 vs TimeStop H1=1.246, H2=1.732. **H1 essentially identical, but TimeStop's H2 is 0.15 lower.** TimeStop is materially weaker in the recent period — the cluster decision to treat as one slot is reinforced; Chandelier is the better leader.
4. **Thinnest WF margin: XB-PB-EMA-Ladder-MYM at worst-half PF 1.177** — only 0.18 above the 1.0 gate. Combined with the second-thinnest full-sample net PF (1.202) and slip=2 (MYM conservative cost), this is the **second most fragile candidate after MCL**.
5. **MCL probation behavior: worst-half PF 1.199**, stability 0.87 (highest of probation). Best internal consistency of the 3 probation candidates, but absolute level is closest to the WF gate. Confirms the existing `cost_fragility` flag — broker rates remain the decisive question pre-paper.

## Cost fragility notes

- **MCL (probation)**: full-sample net 1.298, worst WF half 1.199. Two thin margins compound. Broker rate sheet replacement is still mandatory pre-paper.
- **MYM (3 candidates including probation)**: slip=2 conservative. All 3 pass cleanly but XB-PB-MYM has thinnest WF margin. If actual MYM slippage is worse than 2 ticks, that candidate likely flips.
- **MGC (2 candidates)**: slip=1, comm $0.62. Generally robust; less broker-rate-sensitive than MCL/MYM.

## Top risks before Session 3 (Gates 5+6+7)

- **Gate 5 trade count** (1 pt; workhorse ≥500 / tail ≥30 events): the MYM and MGC sample sizes are smaller (122–235 H1 trades per half). Full-sample counts may still pass workhorse threshold but worth verifying per candidate.
- **Gate 6 concentration** (2 pts; top-3 < 30% / top-10 < 55% / year share < 40%): the H2 outperformance pattern in corr-top suggests possible year concentration. Will surface in concentration metrics.
- **Gate 7 forward-runner trades ≥30** (2 pts): only the 3 probation candidates have forward-runner data. The 9 correlation candidates have not been forward-traded — they'd score 0 on Gate 7 unless the gate is restructured to N/A for non-forward candidates.

## Cluster / top-3 selection note

XB-ORB-EMA-TimeStop-MNQ remains retained variant of the XB-ORB-EMA-Chandelier-MNQ cluster. Both registered, **one exposure slot** for top-3. Chandelier wins the slot on H2 evidence (1.882 vs 1.732).

---

*Session 2 of 4 complete. 12/12 candidates pass walk-forward under cost-aware engine. Read-only intelligence; no decisions taken. Awaiting operator decision on Session 3 (Gates 5+6+7) or any framework adjustments to Gate 7 for non-forward-tracked candidates.*
