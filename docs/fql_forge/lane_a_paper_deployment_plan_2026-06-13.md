# Lane A Paper Deployment Plan — 2026-06-13

> **Authority:** DSCL §9 ("Lane A paper deployment planning: ALLOWED") + post-restart operator directive.
> **Status:** PLAN ONLY. No registry / scheduler / portfolio / runner mutation. No paper submission.
> **Inputs:** `LANE_A_BATCH_2026-06-12.md` (4 validated candidates), `data_source_control_layer_policy_2026-06-13.md`, `sprint_state_hold_2026-06-13.md`, `LANE_A_B_OPERATING_DOCTRINE.md` §"promotion protocol".
> **What this is:** the proposed sequence, sizing, monitoring, kill switches, and atomic-transition spec the operator would authorize to move the 4 candidates into paper trading. Every execution step below is gated on an explicit operator promotion event.

## ⚠️ DATA_AUDIT_GREEN scope (locked 2026-06-13 — mandatory in every deployment note)

> **DATA_AUDIT_GREEN proved reproducibility WITHIN the current feed.**
> **It does NOT prove independent feed correctness.**
> Clean enough to paper. Not yet clean enough for capital.

**Deployment gate this plan operates under:**
- Paper deployment: **ALLOWED** on current DATA_AUDIT_GREEN evidence.
- Live / prop promotion: **BLOCKED** until DSCL §7 satisfied (`data_source_control_layer_policy_2026-06-13.md`).

---

## 1. Candidates in scope

| # | Strategy ID | Lane / role | Robustness | Paper-deploy verdict |
|---|---|---|---|---|
| 1 | WH-MNQ-stop_run_reversal-ema_slope-PL | Daily workhorse — PRIMARY | GREEN 10/10 | **Wave 1 — deploy first** |
| 2 | WH-MNQ-first_impulse_pullback-ema_slope-PL | Daily workhorse — SECOND | GREEN 10/10 | **Wave 2 — after #1 settles** |
| 3 | WH-MNQ-range_compression_break-ema_slope-PL | Daily workhorse — THIRD | GREEN 10/10 | **Wave 3 — deferred behind #1/#2** |
| 4 | EVT-FOMC-MNQ-Long-1h | Event tail — SEPARATE lane | PASS_WITH_LOSS_TAIL_WARN | **Wave 1 (parallel) — out-of-band event path** |

All 4 are MNQ. There is also an existing **XB-ORB-EMA-Ladder-MNQ** live-forward probation. That makes single-asset MNQ concentration the dominant deployment risk — addressed in §3.

---

## 2. Why staggered, not all-at-once

The batch is genuinely diversified by *mechanism* (max pairwise corr 0.251), but it is **monolithic by asset**. Three new daily MNQ strategies + one MNQ event strategy + the incumbent XB-ORB-MNQ means up to 5 MNQ exposures firing on overlapping sessions. Staggering does two things a simultaneous launch cannot:

1. **Isolates attribution.** If MNQ paper PnL diverges from backtest, we need to know *which* new strategy caused it. One-at-a-time forward observation gives clean signal.
2. **Bounds correlated drawdown during the unproven window.** Paper is where backtest fantasy meets execution reality; we don't want 4 unproven correlated MNQ books stacking their first-month variance.

The event-tail (#4) deploys in parallel with Wave 1 because it is **orthogonal** (corr to every daily workhorse in [-0.021, +0.030]) and fires on a disjoint calendar (scheduled FOMC only) — it adds no daily-session collision.

---

## 3. Aggregate MNQ exposure governance (cross-candidate)

This is the load-bearing constraint and must be decided before Wave 1.

| Concern | Evidence | Recommendation |
|---|---|---|
| Correlation to XB-ORB-MNQ probation | stop_run **0.327**, first_impulse **0.430**, range_compression **0.495** | Deploy in ascending-correlation order → stop_run first (already the PRIMARY). range_compression (0.495) is the most collinear with the incumbent; deploy last and only after observing combined exposure. |
| Simultaneous daily MNQ books | up to 4 (3 new + XB-ORB) | Propose a **paper-stage MNQ concurrency cap**: no more than 2 new daily workhorses live in paper at once until the first reaches its forward-SLA. |
| Per-strategy sizing | all intraday-flat, 1 trade/day | **1 contract initial** each (foundation-lead sizing). No size increase during paper. |
| Net intraday MNQ size | 1 contract × N concurrent | Keep aggregate new-MNQ paper exposure ≤ 2 contracts until Wave 1 clears SLA, ≤ 3 thereafter. |

The intraday-flatness advantage (sprint synthesis) means each book's worst single day is bounded by its intraday MAE — no overnight/event hold-through stacking. That is what makes a staggered multi-book MNQ paper deployment tolerable at all.

---

## 4. Per-candidate deployment specification

Each candidate's promotion event must satisfy all five prerequisites of the `LANE_A_B_OPERATING_DOCTRINE.md` promotion protocol (framework attestation / plumbing readiness / portfolio role / atomic registry transition / 24h post-promotion verification). Recommendations below populate the operator decision checklist from the batch packet.

### 4.1 Packet 1 — WH-MNQ-stop_run_reversal (Wave 1, PRIMARY)

| Field | Recommendation |
|---|---|
| Sizing | 1 contract |
| Coexistence w/ XB-ORB-MNQ | OK — corr 0.327 (lowest of the three); deploy first |
| Forward-monitoring SLA | **30 forward trades OR 30 sessions, whichever later** (≈ matches 79% days-traded cadence → ~38 calendar days) |
| Kill switches | (a) rolling-12-trade Era-3 PF < 1.0; (b) realized max-DD breach of operator $ ceiling; (c) **Mon PF < 0.9 over first 6 Mondays** (Mon weakness flag, PF 1.03); (d) 13h-bucket PF < 0.85 (H13 knife-edge monitor) |
| Carry-over flags | `MON_WEAKNESS_MONITOR`, `H13_KNIFE_EDGE_MONITOR`, `ACTIVE_EXPOSURE_WARNING_XB_ORB_PROBATION` |

### 4.2 Packet 2 — WH-MNQ-first_impulse_pullback (Wave 2)

| Field | Recommendation |
|---|---|
| Sizing | 1 contract (≤ primary) |
| Coexistence | corr 0.430 to XB-ORB **and** trend-continuation family overlap → deploy only after #1 has ≥ 10 clean forward trades |
| Forward-monitoring SLA | 30 forward trades OR 30 sessions (56% days-traded → longer wall-clock, ~54 days) |
| Kill switches | (a) rolling-12 PF < 1.0; (b) **median-trade goes negative over rolling 20** (cost-fragile: median already -$0.22 at 3x+2t stress); (c) Era-1-style regime check — alert if forward PF < 1.10 |
| Carry-over flags | `COST_FRAGILE_HIGH_STRESS_MONITOR`, `ERA_1_BORDERLINE_MONITOR`, `ACTIVE_EXPOSURE_WARNING_XB_ORB_PROBATION` |

### 4.3 Packet 3 — WH-MNQ-range_compression_break (Wave 3, deferred)

| Field | Recommendation |
|---|---|
| Sizing | 1 contract |
| Coexistence | corr **0.495** to XB-ORB (highest) → **deploy last**, only after Waves 1 & 2 are both inside SLA and showing no MNQ over-concentration in paper PnL |
| Forward-monitoring SLA | 30 forward trades OR 30 sessions (69% days-traded) |
| Kill switches | (a) rolling-12 PF < 1.0; (b) **median ≤ $0 over rolling 20** (knife-edge: median $0.05 at 5x+4t); (c) Era-3 regression alert (Era 3 PF 1.727 is its whole thesis — if forward PF < 1.2, re-review) |
| Carry-over flags | `COST_FRAGILE_AT_5X_4T_STRESS`, `DEFER_BEHIND_PRIMARY_AND_SECOND_WORKHORSE` |

### 4.4 Packet 4 — EVT-FOMC-MNQ-Long-1h (Wave 1 parallel, event lane)

| Field | Recommendation |
|---|---|
| Execution path | **Out-of-band event path** (like Treasury-Rolldown monthly), NOT the daily forward runner. Fires only on scheduled FOMC announcements, long, 12×5min-bar hold. |
| Sizing | Per-event sizing, decoupled from daily workhorse contracts (event variance profile differs) |
| Calendar feed | MACHINE_FETCHED_OFFICIAL Fed.gov — operator must confirm the live calendar source is the same graded feed used in backtest |
| Forward-monitoring | Review after **each** scheduled FOMC; SLA is event-count based (not session-based) — minimum 4 forward FOMC events before any promotion talk |
| Kill switches | (a) 3 consecutive event losses; (b) rolling-12-event PF < 1.30; (c) any single event loss exceeding the historical worst (-$1152, the absorbed 2022-01-26 loss) |
| Carry-over flags | `PASS_WITH_LOSS_TAIL_WARN`, `INDEPENDENT_VS_DAILY_WORKHORSES` |

---

## 5. DSCL deployment-note obligations (per candidate, BEFORE paper start)

Per DSCL §10, components 1–6 (the data-lineage *declaration*) can and should be drafted before paper begins; components 7–9 (*verification*) proceed during the paper observation window and gate the eventual live/prop decision.

**Before Wave 1 starts**, each candidate's deployment note must carry:
- The mandatory DATA_AUDIT_GREEN scope sentence (§ top of this doc).
- DSCL components 1–6 drafted: feed/vendor declaration, symbol mapping, session template, timezone handling, roll logic, bar-construction method.

**During paper observation** (the natural 30–90 day runway):
- Component 7 — CME settlement comparison across all 6 §5 named categories (incl. **rollover-adjacent days, mandatory**).
- Component 8 — secondary-vendor spot-check across the same 6 categories.
- Component 9 — paper-execution reconciliation (expected vs actual fills).

No candidate advances paper→live until DSCL §7 (all five conditions) is satisfied and operator-reviewed.

---

## 6. Atomic registry transition spec (operator-gated — NOT executed by this plan)

When the operator authorizes a candidate's promotion event, exactly these fields change **together in one commit** (partial updates rejected per doctrine §190):

- `status` → `probation`
- `controller_action` → `PROBATION` (daily workhorses) / out-of-band event handler registration (FOMC)
- `execution_path` → forward-runner universe (workhorses) / event engine (FOMC)
- `promoted_date` → promotion date
- `lifecycle_stage` → from `watch` to active
- Add to `research/live_drift_monitor.py` BASELINE["strategies"] with correct shape classifier
- Add to runner universe via `build_portfolio_config` (workhorses only)
- Confirm scorecards/digest recognize the new IDs

**Plumbing-readiness pre-check (must pass before authorizing):** strategy code loads under the runner, monitor baseline can classify the shape, data pipeline includes MNQ (it does — incumbent XB-ORB-MNQ proves the path), event engine path exists for #4 (Treasury-Rolldown proves an out-of-band path exists).

### Post-promotion verification (within 24h, per protocol step 5)
Confirm each promoted strategy appears correctly in: (a) the forward runner / event engine, (b) the drift monitor, (c) the daily digest and scorecards. If any surface is missing the strategy, the promotion is incomplete and rolls back.

---

## 7. Proposed sequence (summary)

```
Wave 1  (now, on operator approval)
  ├─ #1 stop_run_reversal      → daily forward runner, 1 contract
  └─ #4 FOMC-MNQ-Long-1h       → out-of-band event path, per-event size
        ↓ (after #1 ≥ 10 clean forward trades, no MNQ over-concentration)
Wave 2
  └─ #2 first_impulse_pullback → daily forward runner, 1 contract
        ↓ (after Waves 1 & 2 inside SLA)
Wave 3
  └─ #3 range_compression_break → daily forward runner, 1 contract
```

Gate between waves = the prior wave's forward-SLA progress + the MNQ concurrency cap (§3), reviewed by the operator. Each wave is a separate promotion event.

---

## 8. What this plan does NOT do (boundaries)

- ❌ Does not mutate registry / scheduler / portfolio / runner universe / monitor baseline.
- ❌ Does not submit any paper or live order.
- ❌ Does not modify the Lane A batch packet or candidate status.
- ❌ Does not authorize promotion — each wave is an explicit operator decision.
- ❌ Does not touch XB-ORB-MNQ probation status, OpenClaw, or `asset_config`.
- ❌ Does not advance any candidate toward live/prop — that path stays BLOCKED behind DSCL §7.

Lane B remains PAUSED. No Lane B research resumed.

## 9. Operator decision sheet (what I need to proceed)

1. **Approve staggered sequence** (§7) — or override the wave ordering?
2. **Approve sizing** — 1 contract per daily workhorse; per-event size for FOMC?
3. **Approve MNQ concurrency cap** (≤ 2 new daily books in paper until Wave 1 clears SLA)?
4. **Confirm forward-SLA** — 30 trades or 30 sessions (whichever later) for workhorses; 4 FOMC events for #4?
5. **Confirm kill switches** as specified per candidate (§4)?
6. **Authorize DSCL components 1–6 drafting** as deployment notes before Wave 1 (documentation-only, in-bounds)?
7. **Authorize Wave 1 promotion event** (#1 + #4) — the first registry/runner mutation, executed atomically per §6?

## 10. Cross-reference

- `docs/fql_forge/paper_packet_drafts/LANE_A_BATCH_2026-06-12.md`
- `docs/fql_forge/data_source_control_layer_policy_2026-06-13.md`
- `docs/fql_forge/sprint_state_hold_2026-06-13.md`
- `docs/LANE_A_B_OPERATING_DOCTRINE.md` — promotion protocol (the 5 prerequisites)
- `docs/XB_ORB_PROBATION_FRAMEWORK.md` — incumbent MNQ governance (collision reference)
