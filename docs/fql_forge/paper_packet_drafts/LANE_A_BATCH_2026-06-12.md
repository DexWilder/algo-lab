# Lane A Batch Review Packet — 2026-06-12

> **Authority:** Operator #190 C (parallel Lane A packaging + Lane B continue).
> **Scope:** 4 cleared V1 candidates across 2 lanes.
> **Status:** REVIEW-ONLY. No scheduler/registry/portfolio mutation. No live/paper execution.
> **Standard:** Packet Standard V1 + V1.1 amendments.

## ⚠️ DATA_AUDIT_GREEN scope (locked 2026-06-13)

> **DATA_AUDIT_GREEN proved reproducibility WITHIN the current feed.**
> **It does NOT prove independent feed correctness.**
> Clean enough to paper. Not yet clean enough for capital.

**Deployment gate:**
- Paper deployment: ALLOWED on current DATA_AUDIT_GREEN evidence
- Live / prop promotion: BLOCKED until Data Source Control Layer passes per `docs/fql_forge/data_source_control_layer_policy_2026-06-13.md`

## Batch summary

| # | Candidate | Lane | Robustness | Data Audit | Pairwise corr to next |
|---|---|---|---|---|---|
| **1** | WH-MNQ-stop_run_reversal | Daily Workhorse — PRIMARY | GREEN (10/10) | GREEN | — |
| **2** | WH-MNQ-first_impulse_pullback | Daily Workhorse — SECOND | GREEN (10/10) | GREEN | 0.110 vs #1 |
| **3** | WH-MNQ-range_compression_break | Daily Workhorse — THIRD | GREEN (10/10) | GREEN | 0.231 vs #1, 0.251 vs #2 |
| **4** | FOMC-MNQ-Long-1h | Event Tail — SEPARATE | PASS_WITH_LOSS_TAIL_WARN | GREEN | -0.021 vs #1 |

All 4 are INDEPENDENT — max pairwise correlation 0.251 (range vs first_impulse). Genuine portfolio diversification, not redundant variants.

---

## Packet 1: WH-MNQ-stop_run_reversal (PRIMARY DAILY WORKHORSE)

| Field | Value |
|---|---|
| Strategy ID | WH-MNQ-stop_run_reversal-ema_slope-PL |
| Asset | MNQ (Nasdaq micro futures) |
| Archetype | WORKHORSE (daily) |
| Mechanism class | Mean-reversion (liquidity sweep) |
| Entry primitive | `stop_run_reversal` |
| Filter | `ema_slope` |
| Exit | `profit_ladder` (default per workhorse doctrine) |
| Calendar | N/A (continuous intraday) |

### Headline metrics

| Metric | Value |
|---|---:|
| n | 1414 |
| PF | **1.477** |
| Median trade | **+$15.51** |
| Net | $35,369 |
| Win rate | 54.7% |
| Trades/day | 1.0 |
| % days traded | **79%** |
| % profitable days | (computed; positive) |

### V1 workhorse gate compliance

✅ n ≥ 500 (1414) • ✅ PF ≥ 1.20 (1.477) • ✅ positive median • ✅ PASS_STRESS • ✅ max-yr ≤ 50% (24.9%) • ✅ yrs+ ≥ 50% • ✅ Era3 PF ≥ 1.0 (1.554) • ✅ Era3 median ≥ 0 (+$23.51)

### Robustness GREEN (10/10)

- Year-excl PF range: [1.390, 1.527]
- Era 1/2/3 PF: 1.195 / 1.599 / 1.554 — Era 3 strong recent regime
- Largest WIN +$1923 (5.4% — no concentration risk)
- Largest LOSS -$1457 (4.1%)
- Rolling 60-trade blocks: 83% > 1.0 PF, 65% > 1.2
- Max-yr/month/week: 24.9% / 7.4% / 7.9%
- Stress: 5x+4t PF 1.284, median +$6.55 (excellent cost-robust)

### Data audit GREEN

- File hash `739875437ded8a76`, signal hash `d2d31c3f0e7e86bb` deterministic
- vs committed metrics: n/PF/median EXACT MATCH

### Family review — INDEPENDENT

- vs XB-ORB-MNQ probation: corr +0.327 (low-moderate; mechanism class differs)
- vs first_impulse_pullback: +0.110 (independent)
- vs range_compression_break: +0.231 (independent)
- vs FOMC-MNQ-Long-1h: -0.021 (independent)

### Required packet labels (per operator)

- `PAPER_PACKET_CANDIDATE`
- `ROBUSTNESS_GREEN`
- `DATA_AUDIT_GREEN`
- `PRIMARY_DAILY_WORKHORSE`
- `ACTIVE_EXPOSURE_WARNING_XB_ORB_PROBATION`
- `MON_WEAKNESS_MONITOR` (Mon PF 1.03)
- `H13_KNIFE_EDGE_MONITOR` (13h PF 1.00)
- `NO_MUTATION_RECOMMENDED`
- `LANE_A_REVIEW_QUEUE`

### Behavioral monitoring notes for paper trading

- Day-of-week: Mon weak (PF 1.03), Thu strong (2.07), Tue/Wed/Fri normal
- Time-of-day: 9h-12h strong, 13h knife-edge (1.00), 14h recovers
- 2025-11-20 largest single event was a +$1923 WIN (lucky-event audit clean: removing it leaves PF 1.451)

### Operator decision checklist

- [ ] Approve for paper-trading promotion?
- [ ] Paper sizing recommendation? (suggest 1 contract initial for foundation lead)
- [ ] Coexistence with XB-ORB-MNQ probation: parallel paper-execution OK?
- [ ] Forward-monitoring SLA? (suggest 30 forward trades or 30 sessions, whichever later)
- [ ] Kill switches? (suggest: Era 3 PF < 1.0 over rolling 12 events, OR max-DD > $X)

---

## Packet 2: WH-MNQ-first_impulse_pullback (SECOND DAILY WORKHORSE)

| Field | Value |
|---|---|
| Strategy ID | WH-MNQ-first_impulse_pullback-ema_slope-PL |
| Asset | MNQ |
| Archetype | WORKHORSE (daily) |
| Mechanism class | Trend continuation (post-ORB impulse) |
| Entry primitive | `first_impulse_pullback` (built 2026-06-12) |
| Filter | `ema_slope` |
| Exit | `profit_ladder` |

### Headline metrics

| Metric | Value |
|---|---:|
| n | 1001 |
| PF | **1.354** |
| Median trade | **+$4.26** |
| Net | $13,192 |
| Trades/day | 1.0 |
| % days traded | 56% |

### V1 workhorse gate compliance

✅ All 8 hard gates pass.

### Robustness GREEN (10/10)

- Year-excl PF range: [1.317, 1.400]
- Era 1/2/3 PF: 1.038 / 1.485 / 1.434 (Era 1 borderline but improving)
- Max-yr/month/week: **20.7% / 15.2% / 11.7%** (best concentration in the batch)
- Largest WIN +$1514 (11.5%), largest LOSS -$443 (3.4%)
- Rolling 60-block: 69% > 1.0 PF, 44% > 1.2
- Stress: 5x+4t PF 1.101 (above 0.8 floor); median goes neg at 3x+2t (-$0.22) — **cost-sensitive at high stress**

### Data audit GREEN

- Signal hash `ef6e8209d1a5a84c` deterministic
- vs cycle 12c committed: n=1001, PF=1.354, median=$4.26 EXACT MATCH

### Family review — INDEPENDENT

- vs stop_run_reversal: 0.110 (independent)
- vs orb_failure_reversal: 0.024 (independent — opposite mechanism class)
- vs XB-ORB-MNQ probation: 0.430 (low-moderate — same trend-continuation family)

### Required packet labels

- `PAPER_PACKET_CANDIDATE`
- `ROBUSTNESS_GREEN`
- `DATA_AUDIT_GREEN`
- `SECOND_DAILY_WORKHORSE` (per operator preference: ahead of range_compression in queue)
- `ACTIVE_EXPOSURE_WARNING_XB_ORB_PROBATION` (corr 0.430)
- `COST_FRAGILE_HIGH_STRESS_MONITOR` (median goes neg at 3x+2t)
- `ERA_1_BORDERLINE_MONITOR` (Era 1 PF 1.038)
- `NO_MUTATION_RECOMMENDED`
- `LANE_A_REVIEW_QUEUE`

### Operator decision checklist

- [ ] Approve for paper-trading promotion?
- [ ] Paper sizing: smaller than stop_run primary?
- [ ] Coexistence with stop_run + XB-ORB probation: review needed
- [ ] Forward-monitoring SLA?
- [ ] Kill switches?

---

## Packet 3: WH-MNQ-range_compression_break (THIRD DAILY WORKHORSE)

| Field | Value |
|---|---|
| Strategy ID | WH-MNQ-range_compression_break-ema_slope-PL |
| Asset | MNQ |
| Archetype | WORKHORSE (daily) |
| Mechanism class | Volatility breakout (compression → expansion) |
| Entry primitive | `range_compression_break` |
| Filter | `ema_slope` |
| Exit | `profit_ladder` |

### Headline metrics

| Metric | Value |
|---|---:|
| n | 1244 |
| PF | 1.370 |
| Median trade | +$9.01 |
| Net | $18,610 |
| Trades/day | 1.0 |
| % days traded | 69% |

### V1 workhorse gate compliance

✅ All 8 hard gates pass.

### Robustness GREEN (10/10)

- Year-excl PF range: [1.301, 1.415]
- Era 1/2/3 PF: 1.122 / 1.204 / **1.727** (Era 3 strongest of any candidate)
- Max-yr: 32.1%, max-month: 13.3%, max-week: 7.1%
- Stress: 5x+4t PF 1.134, median **$0.05** (knife-edge at extreme stress)

### Data audit GREEN

- Signal hash `27247233d680c564` deterministic; vs committed exact match

### Family review

- vs XB-ORB-MNQ probation: corr **0.495** (highest correlation to existing probation — borderline moderate)
- vs stop_run_reversal: 0.231 (independent)
- vs first_impulse_pullback: 0.251 (independent)
- vs BBKC archive: 0.420

### Required packet labels

- `PAPER_PACKET_CANDIDATE`
- `ROBUSTNESS_GREEN`
- `DATA_AUDIT_GREEN`
- `SECONDARY_DAILY_WORKHORSE` (operator preference: deferred behind first_impulse)
- `ACTIVE_EXPOSURE_WARNING_XB_ORB_PROBATION` (corr 0.495)
- `COST_FRAGILE_AT_5X_4T_STRESS` (median $0.05)
- `DEFER_BEHIND_PRIMARY_AND_SECOND_WORKHORSE`
- `NO_MUTATION_RECOMMENDED`
- `LANE_A_REVIEW_QUEUE`

### Operator decision checklist

- [ ] Approve for paper-trading promotion? (recommend after stop_run + first_impulse forward observation)
- [ ] Paper sizing?
- [ ] Forward-monitoring SLA?
- [ ] Kill switches?

---

## Packet 4: FOMC-MNQ-Long-1h (EVENT-TAIL LANE)

| Field | Value |
|---|---|
| Strategy ID | EVT-FOMC-MNQ-Long-1h |
| Asset | MNQ |
| Archetype | TAIL_ENGINE (event-window) |
| Mechanism class | Macro event-window |
| Entry | `event_window_engine` (long, 12-bar hold) |
| Calendar | OFFICIAL Fed.gov FOMC scheduled meetings |
| Hold | 1h post-announcement (12 × 5min bars) |

### Headline metrics

| Metric | Value |
|---|---:|
| n (clean events) | 54 of 58 scheduled (93.1%) |
| PF | **1.774** |
| Median trade | **+$67.01** |
| Net | $3,253 |
| Win rate | **64.8%** |

### V1 tail-engine gate compliance

✅ All 9 hard gates pass • Soft Era3 median flag: +$97.76 (positive)

### Robustness 11/12 — PASS_WITH_LOSS_TAIL_WARN (V1.1-B)

- 11 checks pass; the 1 fail is max-event-share 16.9% which is a **LOSS** (2022-01-26 -$1152)
- Removing the largest LOSS INCREASES PF from 1.774 to **2.443** — strategy ABSORBS worst loss
- Per V1.1 Amendment B: LOSS_TAIL_ABSORPTION → PASS_WITH_LOSS_TAIL_WARN (not FAIL)

### Data audit GREEN

- Calendar source MACHINE_FETCHED_OFFICIAL Fed.gov
- Signal hash `7ffb294c76847d76` deterministic; vs committed all match

### Family review — INDEPENDENT vs ALL inventory

- vs Packet #1 archive (NFP-MGC): -0.025 (zero day overlap)
- vs XB-ORB-MNQ probation: 0.009 (independent)
- vs stop_run_reversal: -0.021 (independent)
- vs first_impulse_pullback: 0.030 (independent)
- vs range_compression_break: 0.018 (independent)

This is a genuinely orthogonal event-tail packet — its inclusion is purely additive to the portfolio.

### Required packet labels

- `PAPER_PACKET_CANDIDATE`
- `EVENT_TAIL_ENGINE`
- `PASS_WITH_LOSS_TAIL_WARN`
- `DATA_AUDIT_GREEN`
- `INDEPENDENT_VS_DAILY_WORKHORSES`
- `LANE_A_REVIEW_QUEUE`

### Operator decision checklist

- [ ] Approve for paper-trading promotion as separate event-tail lane?
- [ ] Sizing: per-event sizing different from daily workhorse?
- [ ] Calendar feed source for live: operator-confirmed Fed.gov or alternative?
- [ ] Forward monitoring after each scheduled FOMC?
- [ ] Kill switches: 3 consecutive event losses? PF < 1.30 over rolling 12 events?

---

## Strategic batch context

This batch represents the campaign's first multi-candidate review packet after Factory Stabilization + RED Recovery + V1 ratification.

**Diversification achieved (mechanism classes):**
- Mean-reversion (stop_run_reversal — liquidity sweep)
- Trend continuation (first_impulse_pullback — post-ORB impulse)
- Volatility breakout (range_compression_break)
- Macro event (FOMC-MNQ event window)

**Asset concentration:** All 4 on MNQ. (Single-asset portfolio — future diversification target.)

**Existing exposure:** XB-ORB-EMA-Ladder-MNQ probation (ACTIVE_EXPOSURE per V1.1-A; counts for collision risk).

## Cross-references

- `docs/fql_forge/PACKET_STANDARD_V1_2026-06-11.md`
- `docs/fql_forge/packet_standard_v1_1_amendments.md`
- `docs/fql_forge/packet_standard_v1_inventory_rescore.md`
- Robustness cycle 11r (stop_run, range_compression)
- Robustness cycle 12d (first_impulse_pullback, orb_failure_reversal PARTIAL)
- FOMC-MNQ robustness cycle 11o
- Data audit cycle 12a (3 candidates) + cycle 12e (first_impulse_pullback)

## What this batch does NOT do

- ❌ Does not mutate registry / scheduler / portfolio
- ❌ Does not authorize paper/live promotion
- ❌ Does not commit to sizing or risk-budget allocation
- ❌ Does not modify XB-ORB-MNQ probation status

All Lane A actions remain operator-gated.
