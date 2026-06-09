# Candidate Inventory Roster — 2026-06-09

> **Status:** Snapshot of full campaign inventory. Built as safe fallback while SMP-2 Tier 1 batch runs.
> **Authority:** Lane B research; report-only. Single source of truth for "where every candidate is."
> **Method:** Aggregates kill_taxonomy + insight docs + cycle reports.

## Aggregate counts

| Tier | Count | Notes |
|---|---:|---|
| **PAPER_PACKET (ACCEPTED)** | **1** | EVT-NFP-MGC-Long-2h, audit GREEN, not paper/live approved |
| PAPER_PACKET_CANDIDATE (in flight) | 0 | — |
| PORTFOLIO_COMPLEMENT | 2 | MES Long/Short ORB (moderate corr to MNQ) |
| DIRECTIONAL_INSIGHT (existing probation subset) | ~10 | MNQ/MES/MYM ORB Long/Short, MCL/MGC asymmetry findings |
| OBSERVATIONAL (DATA_REQUIRED) | 2 | MCL Short-PL + MCL Short-FR2 (pending #85 prop-cost) |
| OBSERVATIONAL (FAIL_STRESS) | ~12 | RCB variants, BBKC-MNQ, DC/PDB/PDF FAIL_STRESS candidates |
| RESEARCH_ONLY | 2 | RCB (concentration intrinsic) + BBKC (thin margin) |
| ARCHIVED | 1 | VRC (mechanism anti-edge) |
| KILL | ~90+ | tracked via kill_taxonomy with reasoning |

## §1 — PAPER_PACKET (accepted)

| Candidate | Asset | Mechanism | Status |
|---|---|---|---|
| EVT-NFP-MGC-Long-2h | MGC | NFP event-window, 2h hold, long | ACCEPTED 2026-06-05; audit GREEN; not paper/live approved |

## §2 — PORTFOLIO_COMPLEMENT (cross-asset siblings)

| Candidate | n | PF | Median | Corr to MNQ-both | Disposition |
|---|---:|---:|---:|---:|---|
| DIR-MES-ORB-Long-PL | 854 | 1.394 | $12.51 | 0.42 | OBSERVATIONAL portfolio sleeve |
| DIR-MES-ORB-Short-PL | 393 | 1.482 | $28.76 | 0.62 | OBSERVATIONAL portfolio sleeve |

## §3 — DIRECTIONAL_INSIGHT (subsets of existing probation)

### Cross-asset ORB directional asymmetry matrix (complete)

| Asset | LONG PF | SHORT PF | Pattern |
|---|---:|---:|---|
| MGC | 1.362 | 1.527 | Good + Better (SHORT bias) |
| MCL | 1.014 (null) | 1.41-1.45 | Null + Alive (LONG dead) |
| MYM | 1.568 | 1.578 | Symmetric |
| MES | 1.394 | 1.482 | Symmetric-leaning (SHORT slight) |
| MNQ | **1.726** | 1.489 | Good + Better LONG-bias |

All directional splits are 100%-day-overlap subsets of existing both-direction probation. Insight only.

## §4 — OBSERVATIONAL (DATA_REQUIRED)

| Candidate | Asset | n | PF | Median | Break-even RT cost | Block reason |
|---|---|---:|---:|---:|---:|---|
| MCL Short-PL | MCL | 469 | 1.408 | $7.76 | $9.74 | Pending operator prop-cost rate sheet (#85) |
| MCL Short-FR2 | MCL | 469 | 1.452 | $3.76 | $7.38 | Pending operator prop-cost rate sheet (#85) |

## §5 — OBSERVATIONAL (FAIL_STRESS)

### From new-primitive cycles (08e–08m)

| Candidate | n | PF | Median | Max-yr | Stress | Notes |
|---|---:|---:|---:|---:|---|---|
| RCB-MGC-Short-PL | 222 | 1.165 | $3.26 | — | FAIL | 08e baseline RCB |
| RCB-MGC-Both-PL | 589 | 1.173 | $0.76 | — | FAIL | 08e baseline RCB |
| RCB-MES-Both-PL | 1211 | 1.210 | $1.26 | — | FAIL | 08e baseline RCB |
| RCB-MYM-Both-PL | 395 | 1.462 | $0.76 | 68.4% | FAIL | 08e baseline RCB |
| RCB15-MYM-Short-PL | 126 | **2.070** | **$8.51** | **71.6%** | **PASS** | First-ever RCB PASS_STRESS; blocked by concentration + Era3 |
| RCB15-MYM-Short-VolLo-PL | 125 | 2.073 | $8.76 | 70.8% | PASS | Vol-overlay redundant; same as above |
| RCB15-MES-Both-PL | 947 | 1.153 | $2.51 | — | FAIL | 08g tighter compression |
| RCB15-MGC-Both-PL | 420 | 1.248 | $0.76 | — | FAIL | 08g tighter compression |
| **BBKC-MNQ-Both-PL** | **837** | **1.206** | **$2.76** | **44.9%** | **FAIL** | Cleanest BB-KC; cost-sensitive (highest unlock probability if prop-cost verified ≤ $3.00 RT) |

### From earlier cycles (08c)

| Candidate | Reason | Currently |
|---|---|---|
| DC-MGC-Long-PL | KNIFE_EDGE stress + paused family (non-ORB MCL/MGC) | OBSERVATIONAL |
| DC-MCL-Short-FR2 | FAIL_STRESS + FR2 + paused family | OBSERVATIONAL |
| PDB-MGC-Long-FR2 | FAIL_STRESS + paused family | OBSERVATIONAL |
| PDF-MGC-Short-PL | FAIL_STRESS + CURRENT_REGIME_WARNING + paused family | OBSERVATIONAL |
| PB-VolLow-MNQ | YELLOW audit + portfolio-complement classification (#65) | OBSERVATIONAL |

## §6 — RESEARCH_ONLY (productive primitives, not packet-grade)

| Primitive | Cycle classified | Reason | Future use |
|---|---|---|---|
| range_compression_break (RCB) | 08e/08g/08i | Concentration intrinsic (71.6% max-yr); vol-overlay doesn't help | Regime-shift-specific thesis (e.g., 2025-style vol-rich years) |
| bb_keltner_squeeze (BBKC) | 08m | Thin signal (PF 1.21 best); cost-sensitive | Possible session_morning filter exploration if operator approves |

## §7 — ARCHIVED

| Primitive | Reason |
|---|---|
| volatility_regime_compound (VRC) | Mechanism anti-edge: regime-SHIFT moment + ema_slope direction = consistently entering AGAINST the fade. PFs 0.30-0.80 across all 5 assets in retry. Could revive with FADE direction logic. |

## §8 — Saturated families (paused per #95 rule)

| Family | Pause trigger | Unlock criteria |
|---|---|---|
| MCL/MGC × non-ORB entries × ema_slope × profit_ladder | 08c wipeout | new primitive / data / asset / thesis / override |
| ZN/ZF × afternoon × pb_pullback/bb_reversion | 08d wipeout | same |
| 6E/6J × session-close × pb_pullback/bb_reversion/donchian | 08d wipeout | same |
| MCL × calendar-time event-window × existing event primitive | 08f + 08h (NFP-MCL + EIA-MCL both 5/5 KILL) | surprise-conditioned data + thesis update |
| Equity-index × hurst_stable_mr × bb_reversion | 08l deployment (anti-edge MES + MNQ) | filter mismatch confirmed; would need different entry combinations |

## §9 — Exhausted primitive layers (diagnostic complete)

| Layer | Diagnostic completed |
|---|---|
| ORB-family directional asymmetry | 5-asset matrix complete (MGC/MCL/MYM/MES/MNQ) |
| PL vs FR2 cost-fragility | n=10 codification (PL-default doctrine #91) |
| Vol-regime overlay on RCB | Vol filter redundant/incompatible with compression mechanism |

## §10 — DATA_REQUIRED queue

| Item | Priority | Owner |
|---|---|---|
| Prop-firm cost rate sheet (MCL + MNQ + MES) | **Highest** (cost-fragility hypothesis) | operator — template available |
| Treasury auction calendar (TreasuryDirect) | Medium | deferred per #99 |
| Surprise-conditioned EIA crude data | Medium | deferred |
| WASDE / USDA + grain assets (ZC/ZS/ZW) | Lower | deferred |
| COT-shift CFTC ingestion | Lower | deferred (rabbit-hole risk) |

## §11 — Sprint state (Day 11 of 30)

- **Day 11 of 30** (sprint start 2026-06-02; deadline 2026-07-02)
- **Day-17 review:** 2026-06-19 (scaffold at `docs/fql_forge/sprint_day17_review_scaffold.md`)
- **Status:** YELLOW (not RED) per operator #114
- **Doctrines codified this campaign:** 4 (3-tier classification, PL-default exit, asset-family saturation, no-idle-when-safe-fallback)
- **Primitives shipped this campaign:** 8 (event_window, vol_expansion, prior_day, session_close, exit_fixed_ratio, range_compression_break, volatility_regime_compound, bb_keltner_squeeze) plus 1 stress harness + 1 feature cache + 1 EIA calendar artifact
- **Filters deployed for first time this campaign:** hurst_stable_mr (08l, anti-edge with bb_reversion), hurst_stable_trend (09a in flight)
- **Closed-loop findings preserved:** 11+ kill_taxonomy headlines with mechanism evidence

## §12 — Highest-leverage next motion (recommendation rank)

1. **Prop-cost rate sheet** (operator-fillable template at `docs/reports/prop_cost_verification/prop_cost_unlock_template_OPERATOR_TO_FILL.md`). Could unlock multiple OBSERVATIONAL candidates without further infrastructure.
2. **SMP-2 Tier 1 batch** (running 2026-06-09a). 5 RUNNABLE_NOW candidates including first hurst_stable_trend deployment.
3. **SMP-2 Tier 2 NEEDS_PRIMITIVE** (gap_fill_trigger lowest cost). If SMP-2 Tier 1 fails and prop-cost stays unfilled.
4. **SMP-2 Tier 3 NEEDS_DATA** (other-than-prop-cost, e.g., Treasury auction calendar). Last resort.

## Constraints

- No registry mutation. No scheduler change. No portfolio allocation change. No paper/live promotion.
- No cost-assumption changes without operator-verified data.
- Lane B research-only.

## Source artifacts

- `research/data/fql_forge/kill_taxonomy.json`
- `research/data/fql_forge/source_mining_packet_2_2026-06-08.md`
- `docs/fql_forge/sprint_day17_review_scaffold.md`
- `docs/reports/prop_cost_verification/prop_cost_unlock_template_OPERATOR_TO_FILL.md`
- All cycle reports `research/data/fql_forge/reports/forge_cycle_*.json`
