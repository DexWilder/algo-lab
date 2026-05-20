# Post-Cost Candidate Landscape — 2026-05-20

**Authority:** T1 intelligence (reflects state on disk; no decisions made by this doc).
**Sprint:** Phase 2 / Paper-Readiness Sprint — input to validation funnel v0.
**Cost basis:** post-Piece-I `engine/asset_config.py` (single source of truth). All PFs below are **net (cost-adjusted)**.
**Cost assumption caveat:** conservative estimates; replace with broker rate sheet before paper/prop, especially for MCL.

---

## Bucket 1 — Probation (3 candidates)

These already passed prior gates and are in active forward tracking. Re-read confirms all three remain above the 1.20 backtest workhorse gate.

| Strategy | Asset | Trades | Net PF | Δ-A (slip 1→2) | Cost % of gross avg | Concern | Notes |
|---|---|---:|---:|---:|---:|---|---|
| XB-ORB-EMA-Ladder-MNQ | MNQ | 1183 | **1.620** | 0.000 | 4.9% | 🟢 GREEN | Anchor candidate. MNQ slip already 1; unchanged. |
| XB-ORB-EMA-Ladder-MCL | MCL | 898 | **1.298** | -0.070 | 34.7% | 🟢 GREEN | **Fragile** — `cost_fragility` flag set. Broker rates required before paper. |
| XB-ORB-EMA-Ladder-MYM | MYM | 340 | **1.625** | -0.038 | 13.4% | 🟢 GREEN | Lowest-sample probation; comfortable margin. |

Validation-funnel priority: **all 3** qualify by gate; ranking within bucket prefers MNQ (deepest sample, lowest cost ratio) then MYM then MCL (margin sensitivity).

---

## Bucket 2 — Correlation-matrix idea candidates (post-cost reduction: 12 → 9 viable)

Original 12 candidates from `research/correlation_matrix.py` (Item #2). Three eliminated after cost-aware re-read; 9 remain viable for top-3 paper-readiness selection.

### Viable (9)

| Strategy | Asset | Trades | Net PF | Δ-B (gross→net) | Cost % | Concern |
|---|---|---:|---:|---:|---:|---|
| XB-ORB-EMA-Chandelier-MNQ | MNQ | 1207 | **1.574** | -0.063 | 7.6% | 🟢 GREEN |
| XB-ORB-EMA-TimeStop-MNQ | MNQ | 1207 | **1.507** | -0.063 | 8.8% | 🟢 GREEN |
| XB-BB-EMA-Ladder-MGC | MGC | — | **1.592** | -0.157 | 16.5% | 🟢 GREEN |
| XB-BB-EMA-Ladder-MYM | MYM | — | **1.551** | -0.194 | 20.4% | 🟢 GREEN |
| XB-PB-EMA-Ladder-MNQ | MNQ | 1474 | **1.406** | -0.055 | 10.0% | 🟢 GREEN |
| XB-VWAP-EMA-Ladder-MYM | MYM | — | **1.325** | -0.157 | 28.3% | 🟢 GREEN |
| XB-VWAP-EMA-Ladder-MGC | MGC | — | **1.297** | -0.119 | 24.9% | 🟢 GREEN |
| XB-BB-EMA-Ladder-MNQ | MNQ | — | **1.237** | -0.046 | 14.6% | 🟢 GREEN |
| XB-PB-EMA-Ladder-MYM | MYM | — | **1.202** | -0.144 | 37.9% | 🟢 GREEN |

### Eliminated by cost reset (3)

| Strategy | Asset | Net PF | Cost % | Verdict | Status now |
|---|---|---:|---:|---|---|
| XB-PB-EMA-Ladder-MCL | MCL | 1.058 | 78.3% | 🟡 YELLOW (marginal) | `monitor` (per decision pass 2026-05-20) |
| XB-VWAP-EMA-Ladder-MCL | MCL | 1.040 | 83.7% | 🔴 RED | `archived` (cost-aware fail) |
| XB-BB-EMA-Ladder-MCL | MCL | 0.983 | **109.2%** | 🔴 RED | `archived` (cost exceeds gross edge) |

### Cluster-leader retention reminder

Per the cluster decision 2026-05-19: XB-ORB-EMA-Chandelier-MNQ (cluster_leader) and XB-ORB-EMA-TimeStop-MNQ (retained_variant) are **one exposure cluster** despite being distinct registry entries. Top-3 selection should treat them as a single slot.

---

## Bucket 3 — Pool expansion batch (1 tested, 2 deferred)

Operator-approved expansion batch 2026-05-20. Tested under cost-aware engine on day one.

| Strategy | Status | Result |
|---|---|---|
| VWAPPullback-MES-Long | KILL (pruned from runner) | Net PF 0.847 on 2501 trades. Approximation over-fires vs practitioner spec. Higher-fidelity reimplementation = separate future pre-flight. |
| BBW-Percentile | DEFERRED | Requires new BBWP cross-above-SMA *entry* mechanism, not the filter extension the packet estimated. Wait for Phase 3 entry-registration framework. |
| FX-Daily-Donchian-Breakout | DEFERRED | Requires 6J daily-bar data pipeline, donchian state-tracking verification on daily bars, and FX-donchian RETEST flag resolution. |

Pool-expansion batch result: **+0 to viable candidate pool.** Bucket is currently empty for validation-funnel input.

---

## Validation-funnel v0 input set (Bucket 1 ∪ Bucket 2 viable)

**12 candidates total** for validation funnel v0:
- 3 probation (Bucket 1)
- 9 correlation viable (Bucket 2)
- 0 pool expansion (Bucket 3 produced no viable additions)

After cluster-leader collapse (Chandelier + TimeStop = 1 exposure slot): **11 distinct exposure clusters.**

The validation funnel should produce a ranked candidate set that feeds Item #8 top-3 selection and ultimately Item #9 paper-readiness packets by 2026-06-17.

---

## Bucket 4 (informational only) — Phase 3 queue

**Generalized entry-registration framework** is the underlying unblocker for the "stuck at ~60 strategies" problem. Today's pool-expansion batch confirmed the diagnosis: most convert_next ideas need new entry mechanisms, not just filter/exit tweaks. Build only after Phase 2 paper-readiness deliverables ship.

This bucket is NOT input to validation funnel; it's queued as Phase 3 architectural work.

---

*Filed 2026-05-20. Reflects state after Item #3 cost integrity reset, Item #3.5 silent-default hardening, and operator decision pass. Source: `docs/reports/cost_integrity_reset/2026-05-20_cost_integrity_impact_report.md` + `docs/fql_forge/forge_batch_2026-05-20.md`. No decisions made by this doc.*
