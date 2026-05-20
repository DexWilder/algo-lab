# Validation Funnel v0 — Final Consolidated (2026-05-20)

**Filed by:** `research/funnel_consolidate.py`
**Authority:** T1 intelligence; no registry mutation, no status changes.
**Sprint:** Phase 2 / Paper-Readiness Sprint Item #7 — **all 4 sessions complete**.

## Headline

**5 paper-eligible / 7 paper-borderline / 0 REJECT.**

Concentration (Gate 6) is the dominant culling factor — many candidates that passed walk-forward (Gate 4) fail concentration because their total profit depends on a small number of outlier trades (top-10 PnL > 100% of total net = remaining trades net negative).

## Cumulative scorecard (sorted by cumulative score)

Max possible: **13** (probation) / **11** (non-probation; G7=PENDING_FORWARD_EVIDENCE).

| Candidate | Asset | Bucket | S1 | G4 | G5 | G6 | G7 | G8 | Cumulative | Net PF | Worst WF | Classification |
|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| XB-ORB-EMA-Ladder-MNQ | MNQ | probation | 4 | 3 | 1 | 2 | 0 | 1 | **11/13** | 1.620 | 1.445 | paper-eligible (promotion gate borderline) |
| XB-ORB-EMA-Chandelier-MNQ | MNQ | correlation | 4 | 3 | 1 | 2 | PEND | 1 | **11/11** | 1.574 | 1.242 | paper-eligible (promotion PEND forward) |
| XB-PB-EMA-Ladder-MNQ | MNQ | correlation | 4 | 3 | 1 | 2 | PEND | 1 | **11/11** | 1.406 | 1.2 | paper-eligible (promotion PEND forward) |
| XB-ORB-EMA-Ladder-MCL | MCL | probation | 4 | 3 | 1 | 2 | 0 | 1 | **11/13** | 1.298 | 1.199 | paper-eligible (promotion gate borderline) |
| XB-ORB-EMA-TimeStop-MNQ | MNQ | correlation | 3 | 3 | 1 | 2 | PEND | 1 | **10/11** | 1.507 | 1.246 | paper-eligible (promotion PEND forward) |
| XB-ORB-EMA-Ladder-MYM | MYM | probation | 4 | 3 | 0 | 0 | 2 | 0 | **9/13** | 1.625 | 1.429 | paper-borderline (work needed) |
| XB-BB-EMA-Ladder-MGC | MGC | correlation | 4 | 3 | 1 | 0 | PEND | 0 | **8/11** | 1.592 | 1.191 | paper-borderline (promotion PEND forward) |
| XB-BB-EMA-Ladder-MYM | MYM | correlation | 4 | 3 | 1 | 0 | PEND | 0 | **8/11** | 1.551 | 1.216 | paper-borderline (promotion PEND forward) |
| XB-VWAP-EMA-Ladder-MYM | MYM | correlation | 4 | 3 | 1 | 0 | PEND | 0 | **8/11** | 1.325 | 1.193 | paper-borderline (promotion PEND forward) |
| XB-VWAP-EMA-Ladder-MGC | MGC | correlation | 4 | 3 | 1 | 0 | PEND | 0 | **8/11** | 1.297 | 1.246 | paper-borderline (promotion PEND forward) |
| XB-BB-EMA-Ladder-MNQ | MNQ | correlation | 4 | 3 | 1 | 0 | PEND | 0 | **8/11** | 1.237 | 1.209 | paper-borderline (promotion PEND forward) |
| XB-PB-EMA-Ladder-MYM | MYM | correlation | 4 | 3 | 1 | 0 | PEND | 0 | **8/11** | 1.202 | 1.177 | paper-borderline (promotion PEND forward) |

## Concentration detail (Gate 6)

Threshold: top-3 < 30%, top-10 < 55%, max single year < 40%.

| Candidate | top-3 | top-10 | max-year | Verdict |
|---|---:|---:|---:|---|
| XB-ORB-EMA-Ladder-MNQ | 9.2% | 22.2% | 21.1% | PASS ✓ |
| XB-ORB-EMA-Ladder-MCL | 14.4% | 40.8% | 27.1% | PASS ✓ |
| XB-PB-EMA-Ladder-MNQ | 10.2% | 27.8% | 39.0% | PASS ✓ |
| XB-ORB-EMA-Chandelier-MNQ | 14.5% | 31.5% | 29.6% | PASS ✓ |
| XB-ORB-EMA-TimeStop-MNQ | 11.3% | 28.7% | 24.9% | PASS ✓ |
| XB-ORB-EMA-Ladder-MYM | 31.0% | 58.9% | 67.6% | FAIL |
| XB-PB-EMA-Ladder-MYM | 44.7% | 110.7% | 75.4% | FAIL |
| XB-BB-EMA-Ladder-MNQ | 44.5% | 94.8% | 25.4% | FAIL |
| XB-BB-EMA-Ladder-MGC | 63.4% | 115.1% | 88.7% | FAIL |
| XB-BB-EMA-Ladder-MYM | 57.5% | 115.4% | 78.7% | FAIL |
| XB-VWAP-EMA-Ladder-MGC | 58.0% | 131.6% | 48.8% | FAIL |
| XB-VWAP-EMA-Ladder-MYM | 49.9% | 109.5% | 83.9% | FAIL |

## Forward-evidence status (Gate 7)

| Candidate | Probation? | Forward trades | G7 |
|---|---|---:|---|
| XB-ORB-EMA-Ladder-MNQ | yes | 24 | 0 pts (24 forward trades) |
| XB-ORB-EMA-Ladder-MCL | yes | 20 | 0 pts (20 forward trades) |
| XB-PB-EMA-Ladder-MNQ | no | — | PENDING_FORWARD_EVIDENCE (never forward-traded) |
| XB-ORB-EMA-Chandelier-MNQ | no | — | PENDING_FORWARD_EVIDENCE (never forward-traded) |
| XB-ORB-EMA-TimeStop-MNQ | no | — | PENDING_FORWARD_EVIDENCE (never forward-traded) |
| XB-ORB-EMA-Ladder-MYM | yes | 32 | 2 pts (32 forward trades) |
| XB-PB-EMA-Ladder-MYM | no | — | PENDING_FORWARD_EVIDENCE (never forward-traded) |
| XB-BB-EMA-Ladder-MNQ | no | — | PENDING_FORWARD_EVIDENCE (never forward-traded) |
| XB-BB-EMA-Ladder-MGC | no | — | PENDING_FORWARD_EVIDENCE (never forward-traded) |
| XB-BB-EMA-Ladder-MYM | no | — | PENDING_FORWARD_EVIDENCE (never forward-traded) |
| XB-VWAP-EMA-Ladder-MGC | no | — | PENDING_FORWARD_EVIDENCE (never forward-traded) |
| XB-VWAP-EMA-Ladder-MYM | no | — | PENDING_FORWARD_EVIDENCE (never forward-traded) |

## Critical findings (Sessions 1–3 net)

### 1. Concentration is the cull

8 of 12 candidates fail Gate 6 concentration despite passing walk-forward. Multiple show top-10 > 100% of total PnL (i.e., the remaining trades net negative). The strategy depends on a small number of outliers.

- **XB-ORB-EMA-Ladder-MYM**: top-3 31%, top-10 59%, max-year 68%
- **XB-PB-EMA-Ladder-MYM**: top-3 45%, top-10 111%, max-year 75%
- **XB-BB-EMA-Ladder-MNQ**: top-3 44%, top-10 95%, max-year 25%
- **XB-BB-EMA-Ladder-MGC**: top-3 63%, top-10 115%, max-year 89%
- **XB-BB-EMA-Ladder-MYM**: top-3 58%, top-10 115%, max-year 79%
- **XB-VWAP-EMA-Ladder-MGC**: top-3 58%, top-10 132%, max-year 49%
- **XB-VWAP-EMA-Ladder-MYM**: top-3 50%, top-10 110%, max-year 84%

### 2. G5 archetype/threshold issue surfaced — XB-ORB-EMA-Ladder-MYM

MYM probation: workhorse archetype + 371 full-sample trades → G5=0 (workhorse threshold is 500). But MYM's data window is only 2.0 years (per CLAUDE.md). The 500-trade workhorse threshold was calibrated for 6-year strategies. Strict application here is **biased against newer assets**.

Operator decision needed: relax G5 for data-window-limited probation candidates, or accept that MYM doesn't clear G5 until data accumulates.

### 3. Probation forward-trade counts are below 30 for MNQ and MCL

- XB-ORB-EMA-Ladder-MNQ: 24 forward trades → G7=0
- XB-ORB-EMA-Ladder-MCL: 20 forward trades → G7=0
- XB-ORB-EMA-Ladder-MYM: 32 forward trades → G7=2 ✓

MNQ and MCL each need 6–10 more forward trades to clear Gate 7. They are paper-eligible now but not promotion-eligible until forward accumulates.

### 4. The candidate pool that emerges as paper-ready

- **XB-ORB-EMA-Ladder-MNQ** — cum 11/13, net PF 1.620 (forward trades below 30 — promotion-eligible only after accumulation)
- **XB-ORB-EMA-Ladder-MCL** — cum 11/13, net PF 1.298 (forward trades below 30 — promotion-eligible only after accumulation)
- **XB-PB-EMA-Ladder-MNQ** — cum 11/11, net PF 1.406
- **XB-ORB-EMA-Chandelier-MNQ** — cum 11/11, net PF 1.574
- **XB-ORB-EMA-TimeStop-MNQ** — cum 10/11, net PF 1.507

## Cluster / top-3 selection note

- **XB-ORB-EMA-TimeStop-MNQ** is retained variant of **XB-ORB-EMA-Chandelier-MNQ** cluster — one exposure slot.

## Top-3 selection (Item #8)

Per operator lean 2026-05-20:

1. **XB-ORB-EMA-Ladder-MNQ** — probation, cum 11/13, anchor candidate
2. **XB-ORB-EMA-Chandelier-MNQ** — correlation cluster leader, cum 11/11 (TimeStop collapses to this slot)
3. **XB-PB-EMA-Ladder-MNQ** — correlation, cum 11/11, cleaner third than fragile MCL

**XB-ORB-EMA-Ladder-MCL** (cum 11/13, fragile) is the alternate. Same gate score as the top-3 but `cost_fragility` flag and lower worst-half WF (1.199 vs 1.242–1.445) make it second-choice. If the top-3 want broker-rate-light candidates only, MCL drops to alternate.

## Next: Item #9 paper-readiness packets

Each top-3 candidate already has its promotion-humility packet (filed today as part of Gate 8). Item #9 builds the full paper-readiness packet around each, combining: cost-aware funnel evidence + humility packet + forward-runner data + decision recommendation. Target ship by 2026-06-17.

---

*Final consolidated 2026-05-20. Read-only intelligence; no status mutation. Top-3 selection awaits operator confirmation.*
