# Elite Novelty System Assessment (2026-07-01) — full-spectrum, evidence-backed

> Goal: not a normal backtest pipeline — the most elite, novel, self-improving strategy-discovery machine possible.
> Grading: A elite/automated/used · B functional-needs-hardening · C shallow/manual/partly-decorative · D weak/risky · F missing.
> Every C/D/F gets a concrete action (priority, file, automation, benefit, blocks-sprint?). Report-only; capital gate fail-closed.

## OVERALL: **B** — foundation is real and mostly automatic; the C-grade frontier is rich-data throughput, source mining, and creative breadth. **Decision: FOUNDATION_GO with P1 enhancements (built this turn) — no P0 blockers → sprint continues in parallel.**

## Layer grades
| # | Layer | Grade | Evidence |
|---|---|---|---|
| 1 | System architecture | **B** | inbound→queue→test→validate→learn→dashboard all exist + automatic via `post_run_learning_hook.py` (built). Weak link: full queue-runner (`forge_always_on_runner.py`) not exercised this session. |
| 2 | Anti-fake-progress | **B+ → A-** | causality/DSR/cost/expression/adversarial/data-tier all wired; **`artifact_detectors.py` (built)** turns 8 caught bugs into reusable guards. Gap: `failure_class` not backfilled; stale-tripwire P1. |
| 3 | Data superiority | **B-** | 19 sources mapped; **NEW FINDING: 1m coverage heterogeneous & non-overlapping** (MES 2024-26 vs ZN 2019-24, 1.25M rows) — cross-instrument 1m mixes eras (detector added). Rich-data utilization = 1 batch. |
| 4 | Data-tier escalation | **A-** | `family_tier_matrix.json` (built) blocks exhaustion for 8 families; wired into guardrails/adversarial/family-map/dashboard/learning_state. mean_reversion reopened. |
| 5 | Learning / compounding | **B** | loop closed (`update_learning_state`→`learning_state.json`); novelty reads weights; hook emits "what changed." Gap: only 1-2 real cycles; failure_class taxonomy not yet populated. |
| 6 | Novelty engine | **B-** | mechanism-driven (not mashups — `score_novelty_packet.py` confirms 0 WEAK, rejects RSI-crossover demo); **diversity bug fixed** (was monoculture roll/settlement). Gap: 108-combo finite internal space, 0 source-derived. |
| 7 | Creative outside-box | **C+** | 14 forced-flow surfaces templated; not yet systematically searched; several data-blocked (gamma T6, EIA). |
| 8 | Source mining | **C** (was D) | **0 source-derived packets.** `SOURCE_MINING_QUEUE_2026-07-01.md` (built) makes it systematic but unproven as a packet factory. |
| 9 | Research allocation | **C** | last 20 commits ≈ 60% infra / 40% edge — below the 60-70%-edge target. **This is the last infra-heavy turn.** |
| 10 | Candidate deepening | **B** | spreadMR_GC labeled honestly, deepening queued (Lane G), 0 cycles spent yet. |
| 11 | Automation | **B** | self-audit + guardrails + hook fresh & automatic; full cycle orchestrator exists (`forge_always_on_runner.py`) but not run this session. |
| 12 | Human-approval boundary | **A-** | clear; gamma $11.54 = `OPERATOR_COST_APPROVAL_REQUIRED` (does not block other work). |
| 13 | Roadmap | **B+** | operational on dashboard, driven by learning_state. |

## 1. Architecture — weakest links & hardening
Functional+automatic: inbound, family map (computed), learning_state, self-audit, guardrails, candidate ladder, trial ledger, dashboard, data-tier gate. **Weakest:** (a) queue-runner not exercised → **P1** exercise `forge_always_on_runner.py` on the reopened T3 queue; (b) source lane empty. What breaks if Claude forgets: nothing critical — inbound/ledger/guardrails/self-audit reconstruct state; **remaining operator-memory dependence: gamma cost approval only.**

## 2. Anti-fake-progress (per failure class)
| Failure class | Control | File | Grade | Next |
|---|---|---|---|---|
| lookahead | future-perturbation | causality_audit + `artifact_detectors.detect_lookahead` | A | — |
| same-day leakage | perturbation invariance | causality_audit | A- | apply to every T3 packet |
| stale labels | family_status + guardrail | forge_family_map | B+ | — |
| false DATA_BLOCKED | certificate required | guardrail #9 | A | — |
| false FAMILY_EXHAUSTED | tier matrix, exhaustion_allowed | family_tier_matrix + guardrail #12 | A- | — |
| weak-data closure | data-tier gate | DATA_TIER_ESCALATION_RULES | A- | — |
| expression degeneracy | active-side/sparse | validate_strategy_expression + adversarial | A- | — |
| costless results | FQL Evidence Law + detect_cost_inert | asset_config + artifact_detectors | A- | — |
| trial-N forgetting | auto ledger | forge_trial_ledger | A | — |
| overclaiming | ladder + adversarial | forge_candidate_ladder | A- | — |
| hidden git backlog | guardrail #1 | forge_system_guardrails | A | — |
| terminal-only discoveries | inbound law | capture_inbound | A- | — |
| decorative automation | self-audit facets | forge_self_audit | B+ | streak proof |
| blind source notes | triage: packet-or-archive | INBOUND_TRIAGE_RULES | B | source lane empty |
| old harness bypass | unrun-harness guardrail | guardrail #8 | B | — |
| data underuse | data-util map + tier_gap | data_sources.json | B- | T3 sweep |
| candidate hype | ladder language | ladder | A- | — |
| **units/artifact bugs** | **`artifact_detectors.py`** | artifact_detectors | **B+ (new)** | backfill failure_class |
No failure class is uncontrolled. **P1:** populate `failure_class` on all kills (taxonomy) → mineable.

## 3. Data superiority — rankings
**Top underused (highest EV):** 1m+volume T3 (7.9M bars, 1 batch run) · ZN/ZF/ZB 1m 4.7yr history · per-contract CL/GC curves (spreadMR live) · COT-conditional · DVOL T6 · CPI/EIA event windows · yield-curve slope · credit-OAS regime · copper/gold · Deribit options.
**Top unlocks:** gamma/OI T6 (needs loader+$11.54) · EIA feed (free API, cert) · true VIX/VX curve · rebalance calendars.
**Low-value/archive:** crypto perp funding (killed) · redundant 5m-close series (legacy).
**NEW RISK:** 1m date ranges differ per instrument (MES 2024-26, ZN 2019-24) — `detect_coverage_mismatch` now guards; **P1: per-instrument 1m coverage audit before any cross-instrument 1m test.** The 1m frontier must become a **family factory**, not one OR packet.

## 4. Data-tier escalation — CONFIRMED protecting us
All 21 families tier-stamped; old kills rescoped (`CLOSE_ONLY_KILL_RESCOPING`); close-only kills blocked from family-kill (guardrail #12 + adversarial `DATA_TIER_INSUFFICIENT`); dashboard shows gaps; `family_tier_matrix.json` = exhaustion_allowed per family (8 blocked). Grade A-.

## 5. Learning/compounding — mostly closed
Every result → `post_run_learning_hook` → ledger/learning_state/family_map/queue/dashboard/guardrails/self-audit + "what changed" diff. Novelty weights shift with outcomes. **P1: backfill failure_class; prove queue reprioritization over ≥5 cycles.**

## 6. Novelty — mechanism-driven, diversity fixed. **P1:** add source-derived packets; **P2:** grow template/instrument space beyond 108.

## 7. Outside-the-box surfaces (A–J) — see novelty templates; gamma(T6)/EIA data-blocked-certified; **P1: first cheap test per LOCAL surface via T3 harness.**

## 8. Source mining — `SOURCE_MINING_QUEUE_2026-07-01.md` built; **P1: convert ≥3 source items to packets (prove the factory).**

## 9. Allocation — currently infra-heavy; **corrective: next turn ≥60% rich-data T3 tests.** Enforced by roadmap + this assessment.

## 10. Candidate deepening — spreadMR_GC unchanged (SCREEN_PASS/DSR-borderline/gold-specific). Advancement gated on: search-N, execution realism, roll/artifact audit, robustness, adversarial, tier-sufficiency, cost. **Lane G, not dominant.**

## 11. Automation — self-audit/guardrails/hook automatic+fresh. **P1: run `forge_always_on_runner.py` on the T3 queue to prove end-to-end orchestration.**

## 12. Approval boundary — report-only work proceeds; only gamma $11.54 and capital surfaces gated. `OPERATOR_COST_APPROVAL_REQUIRED` for gamma (or raise auto-threshold to $15).

## 13. Roadmap — Phase 1 hardening ~complete; exit needs T3 sweep + clean-streak≥5.

## 14. Missing elite features
| Feature | Verdict |
|---|---|
| Meta-research DB | **PARTIAL→build** — trial ledger extended (failure_class/data_tier/dsr fields, built); backfill P1 |
| Failure taxonomy | **built** (`FAILURE_CLASSES` + `failure_taxonomy()`); populate P1 |
| Mechanism graph | **QUEUE P2** |
| Cross-market hypothesis generator | **QUEUE P2** |
| Regime library | **QUEUE P2** |
| Execution realism simulator | **QUEUE P1** (needed for spreadMR_GC deepening + 2-leg/time-of-day) |
| Artifact detector library | **BUILT** (`artifact_detectors.py`) |
| Full cycle orchestrator | exists (`forge_always_on_runner.py`) + `post_run_learning_hook`; **exercise P1** |

## 15. FINAL REPORT
- **Overall grade:** B (foundation real, rich-data/source/creative are the frontier).
- **Top 10 regression risks:** stale-tripwire uncontrolled; 1m coverage mismatch; failure_class unpopulated; source lane empty; allocation infra-drift; novelty finite space; queue-runner unproven; execution-realism absent (deepening blocked); gamma stuck on $ gate; only-1-T3-batch (thin rich-data evidence).
- **Top 10 missing automations:** failure_class autotag; queue reprioritization proof; source→packet pipeline; execution-realism sim; cross-market generator; regime library; mechanism graph; per-instrument coverage audit; scheduled full-cycle run; DSR-layered auto-report.
- **Top 10 underused data:** 1m+volume T3; ZN/ZF/ZB 4.7yr 1m; CL/GC curves; COT-conditional; DVOL T6; CPI/EIA windows; yield-curve slope; credit-OAS regime; copper/gold; Deribit options.
- **Top 10 novelty ops:** settlement-window revert; closing-imbalance; liquidity-hole reversal; intraday 1m-path MR; ES-NQ lead-lag+volume; roll-window pressure; gamma pin (T6); month-end duration; WMR fix; contango bleed.
- **Top 10 source-mining targets:** CME roll methodology; options dealer-hedging papers; CTA/trend/carry papers; microstructure (Kyle/VPIN); auction-concession studies; month-end rebalance studies; VRP literature; term-structure carry papers; crypto funding research; execution/TWAP-VWAP notes.
- **Top 10 immediate actions:** (built) artifact_detectors, post_run_hook, novelty scorer, tier matrix, novelty diversity, ledger meta-fields, source queue, assessment; (next) T3 settlement batch; per-instrument coverage audit.
- **Top 25 research actions:** in `learning_state.next_25_actions` (led by RETEST mean_reversion@T3).
- **P0:** none. **P1:** failure_class backfill · source→packet ×3 · exercise queue-runner · execution-realism sim · per-instrument 1m coverage audit · gamma cost approval · stale-tripwire control. **P2:** mechanism graph · cross-market gen · regime lib · grow novelty space.
- **Files built:** `artifact_detectors.py`, `post_run_learning_hook.py`, `score_novelty_packet.py`, `family_tier_matrix.json` (gen), ledger meta-fields, novelty diversity, `SOURCE_MINING_QUEUE`, this doc.
- **Guardrail:** P1_WARN (no P0) · **Self-audit:** CLEAN 12/12 · **Learning_state:** fresh · **Dashboard:** fresh.
