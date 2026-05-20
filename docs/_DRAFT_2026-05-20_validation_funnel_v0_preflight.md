# Pre-Flight: Validation Funnel v0 (Item #7)

**Filed:** 2026-05-20
**Authority:** T1 (pre-flight); T2 (build approval, pending operator)
**Lane:** 2 (governance build; produces decision-grade scoring on existing candidates)
**Status:** DRAFT — execute next session if approved. **No build today.**
**Sprint:** Phase 2 / Paper-Readiness Sprint, Item #7. Heaviest single item (estimated 4 sessions in backlog).
**Input set:** `docs/_LANDSCAPE_2026-05-20_post_cost_candidate_set.md` — 12 candidates, 11 exposure clusters.

---

## Purpose

The validation funnel converts the **12 cost-aware-viable candidates** (3 probation + 9 correlation set) into a ranked, gate-checked, paper-decision-ready set. It is the gate between Forge cheap-screen evidence and paper-readiness packet evidence.

Without the funnel:
- We have 12 candidates with net PFs that pass the 1.20 backtest gate.
- We do NOT have walk-forward, concentration, regime, trade-count, or DD evidence at decision-grade quality.
- Item #8 (top-3 selection) and Item #9 (paper-readiness packets) cannot proceed on PF alone.

---

## Counter-argument (per challenge-layer doctrine)

> *"Build the validation funnel" sounds like infrastructure. The 5/18 doctrine warns against infrastructure drift. The 12 candidates already have backtest PFs — couldn't operator just pick top-3 from the highest net PFs?*

**Why we proceed anyway:**
- PF alone is exactly the cheap-screen evidence the "more truthful Forge" doctrine guards against. Picking top-3 on PF would re-introduce the bug class we just spent 2 days closing.
- Validation funnel is **not new infrastructure** — it's a single Python module that aggregates EXISTING gates (walk-forward, concentration, regime, etc.) into a decision-grade scorecard.
- The 13-point candidate-readiness scoring is already defined in the Paper-Readiness Sprint backlog. The funnel ships it.
- Each gate's logic already exists somewhere in `research/` (walk_forward_matrix.py, concentration metrics in correlation_matrix.py, etc.). The funnel composes them.

## What would prove this decision wrong

- Building the funnel takes longer than ~3 sessions (estimate 4 → ship by 2026-05-27)
- The funnel produces zero candidates with score ≥10/13 (paper-eligible)
- The funnel's verdicts disagree wildly with the existing cost integrity report (suggesting double-counting or contradiction in the gates)

## Reversal criteria

- If first run produces zero ≥10/13 candidates AND no ≥8/13 candidates, the gate thresholds are mis-calibrated against the post-cost reality. Revisit thresholds, NOT the funnel.
- If the funnel's regime gate disagrees with `regime_engine.py` (now strict per Site 2), trust regime_engine and fix the funnel — never the other way.
- All funnel output flows through reports, not registry mutation. Status changes happen only via separate operator decision packet.

---

## Scope: v0 (per Paper-Readiness Sprint Item #7)

**One Python module: `research/validation_funnel.py`.** Reads the 12 candidates from the landscape doc + cost integrity JSON, scores each against the 13-point gate, emits a ranked report.

### The 13 gates (per `_BACKLOG_post_patch_a_and_phase_1_exit.md`)

| Gate | Weight | Source of truth |
|---|---:|---|
| Cheap-screen PASS | 1 | `docs/reports/cost_integrity_reset/*reread*.json` |
| Correlation cleared (not duplicate) | 1 | `correlation_matrix.py` output |
| Cost-adjusted net PF ≥ 1.15 | 2 | cost integrity re-read |
| Walk-forward H1/H2 > 1.0 | 3 | `research/walk_forward_matrix.py` (re-run with cost-aware backtest) |
| Trade count adequate (workhorse ≥500 / tail ≥30 events) | 1 | re-read JSON |
| Concentration check passed (top-3<30%, top-10<55%, year<40%) | 2 | concentration metrics on trades_df |
| Forward-runner trades ≥30 | 2 | `state/account_state.json` / forward logs |
| Promotion humility packet present | 1 | doc existence check |

≥10 / 13 = paper-eligible
≥8 / 13 = DEFER-eligible (operator decides)
<8 / 13 = REJECT for this sprint

### Output

`docs/reports/validation_funnel/YYYY-MM-DD_validation_funnel.md` (and `.json`)

Per-candidate columns:
- strategy_id, asset, archetype
- score / 13
- gate-by-gate verdict (pass / fail / N/A)
- net PF (cost-aware)
- walk-forward H1/H2 PF ratios
- top-3 / top-10 concentration
- forward-runner trades (if probation/active)
- promotion-humility doc present?
- final verdict: PAPER_ELIGIBLE / DEFER_ELIGIBLE / REJECT
- rank within bucket

Plus a header section showing cost assumptions used (per FQL evidence law).

---

## Explicitly NOT in v0

- ❌ New gate dimensions beyond the 8 named — no scope creep
- ❌ Walk-forward parameter tuning — re-run with existing splits
- ❌ Regime-conditional scoring beyond the existing regime engine
- ❌ Forward-runner *simulation* — only consume existing forward-state data
- ❌ Registry mutation — funnel output is read-only intelligence
- ❌ Promotion decisions — even ≥10/13 still requires operator approval per the Lane 3 rule
- ❌ Re-running cost integrity re-read — funnel consumes its JSON output

---

## Build sequence (4 sessions, atomic per-gate commits)

| Session | Pieces |
|---|---|
| 1 | Skeleton + Gate 1+2+3 (cheap-screen PASS, correlation cleared, cost-adjusted PF). These three are pure data reads from existing JSON — no compute. |
| 2 | Gate 4 (walk-forward H1/H2) — heaviest; re-runs `walk_forward_matrix.py` per candidate with cost-aware backtest. |
| 3 | Gates 5+6+7 (trade count, concentration, forward-runner trades). |
| 4 | Gate 8 (promotion humility check), report rendering, ranking, final integration. |

Each session ships a committable improvement; pre-flight allows operator interrupt between sessions.

---

## Hard rule: cost-aware backtests only

Every backtest the funnel triggers (walk-forward, regime decomposition) must use the cost-aware engine. `allow_uncosted=True` is forbidden in the funnel. Any candidate that requires uncosted evaluation is automatically REJECT.

This is the doctrine made enforceable: validation evidence must inherit the same cost basis as the cost integrity reset that just landed.

## Operator-locked guardrails (2026-05-20)

The following are explicit during funnel execution and any follow-on session:

- **No pool expansion** — the funnel operates on the 12 cost-aware-viable candidates only. Adding new candidates mid-funnel reopens scope.
- **No new engine features** — funnel composes existing gates; no new entries, filters, or exits. New mechanisms require a separate pre-flight.
- **No generalized entry-registration framework** during this sprint. That is Phase 3 architectural work, not Phase 2 sprint work.
- **No paper / probation / promotion approvals** until funnel results land for every candidate. Status mutation gated on operator decision packet.
- **If a gate invalidates a candidate, surface it — do not rescue.** Funnel records the failure; rescue (parameter sweep, scope adjustment, etc.) requires a separate decision and is out of scope for v0.
- **Broker rate sheet replacement is MANDATORY** before any paper/prop decision on MCL, MYM, treasury (ZN/ZF/ZB), or FX (6B/6E/6J) candidates. Conservative estimates are valid for funnel screening; not valid for paper deployment.

These are explicit because today's pool expansion batch surfaced the failure pattern of "rescue an underperforming candidate by widening engine scope." The funnel must produce honest reject/defer/pass verdicts and stop there.

---

## Sequencing impact

| Item | Status | After this pre-flight |
|---|---|---|
| Item #3 cost integrity reset | ✅ DONE 2026-05-20 | — |
| Item #3.5 silent-default hardening | ✅ DONE 2026-05-20 | — |
| Cost-aware pool expansion batch | ✅ EXECUTED 2026-05-20 (Pick 1 KILL, Picks 2+3 deferred) | — |
| **Item #7 validation funnel v0** | **APPROVED PENDING** | Execute next 4 sessions |
| Item #8 top-3 selection | queued | Inputs from #7 |
| Item #9 paper-readiness packets | queued (deliverable by 2026-06-17) | Inputs from #8 |
| Phase 3 entry-registration framework | queued (informational) | Post-sprint |

Validation funnel is the deliverable-blocking item. 4 sessions × 1 session/day = ships by ~2026-05-27 if started next session. That leaves ~3 weeks for Items #8+#9 before the 2026-06-17 hard exit.

---

## Operator decision

| Option | Decision |
|---|---|
| ☐ Approve as written — execute next session | Default. Session 1 (Gates 1-3) is the lightest start. |
| ☐ Approve with reduced scope | Drop Gate 4 (walk-forward) if it inflates session 2 past 1 session. Replace with a placeholder column. |
| ☐ Defer until Phase 3 entry-registration framework | NOT recommended — would slide the 2026-06-17 deliverable. |
| ☐ Reject — pick top-3 directly from cost integrity report | NOT recommended — re-introduces the cheap-screen-as-validated-edge failure mode. |

---

*Filed 2026-05-20. Lane 2 governance build. Pre-flight only — execute next session per the proven pre-flight pattern. Validation funnel is the gate between cheap-screen evidence and paper-readiness packet evidence; the entire sprint's deliverable depends on it landing cleanly.*
