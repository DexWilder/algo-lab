# FULL_SYSTEM_OVERHAUL AUDIT — master ledger (2026-06-26, expanded 2026-06-29)

> Standard: nothing is "done" because a note said so. Done = has code + automation + monitoring + output + a current
> status. Report-only. Normal WH discovery PAUSED until P0 clear. Tables built from direct repo/launchd/log inspection.

## ROOT CAUSE (verified)
All 14 launchd automations RUN, but none checked the failure modes that bit us (data-usage, directive operationalization,
git durability). `monthly_system_review.py` runs (last 2026-06-27 09:00) but is BLIND to data-usage/directives.
`learning_loop_audit.py` was memory-index+git-status only (now calls guardrails, fixed 2026-06-26).

## TABLE 1 — User-directive ledger (durable directives → implementation → status)
| Directive | Source | Implemented (path) | Automated check | Status | Gap |
|---|---|---|---|---|---|
| Fail-closed capital gate | CLAUDE.md, many | `execution_approval_check` in build_portfolio_config | partial (no guardrail assert) | IMPLEMENTED_AND_WORKING | add guardrail assert |
| Truth-gate / causality first | feedback_truth_reset_causality_first | `research/causality_audit.py` (certified) | guardrail checks existence | WORKING | — |
| DSR / full-N trial ledger | feedback_deflated_sharpe_mandatory_gate | `forge_deflated_sharpe.py` + factory §8 | no auto N-tracker | IMPLEMENTED_AND_WORKING | automate trial-N counter |
| No WH/validated language pre-gate | feedback_truth_reset… | behavioral only | **none** | PARTIAL (manual) | add doc-scan guardrail |
| Use Databento / volume (not close-only) | operator (early) + inventory | volume packets P14/P15/cost-model | guardrail close-only-bias (10/184) | PARTIAL_IMPROVING | raise volume usage |
| Inventory before "exhausted/paid" claim | feedback_inventory_before_exhausted_claim | DATABENTO_INVENTORY doc | **none** | DOCUMENTED_ONLY | add guardrail: block paid-memo if inventory stale |
| Monthly full-system audit checks data/directives | this overhaul | `monthly_system_review.py` | runs but BLIND | **PARTIAL / AUDIT_FAILURE** | wire guardrails into monthly (P1) |
| Learning-loop operationalizes learning | feedback_learning_loop_automation | `forge_learning_loop_audit.py` → now calls guardrails | YES (fixed 2026-06-26) | IMPLEMENTED_AND_WORKING | — |
| Git durability | operator | — | guardrail backlog>5 (P0 firing) | **BROKEN** | operator: gh auth login + push 18 |
| No registry/scheduler/portfolio mutation w/o approval | CLAUDE.md | only approved deactivations done | — | WORKING | — |
| Report-only Lane B continues | feedback_forge_autonomous_mode | continuous | — | WORKING | — |
| Forced-flow priority | feedback_alpha_intake_factory | ALPHA_INTAKE_FACTORY (tiered) | none | WORKING | — |
| Rescue audit of false kills | operator | TRUTH_RESET_RESCUE_AUDIT | none | **PARTIAL** | false-kill retest pending (P1) |
| Rollover-artifact / clean-before-rolling | feedback_continuous_contract… | causality_audit check C | partial | WORKING | — |
| Concentration gates | feedback_validation_gates | per-test | none | WORKING | automate |

## TABLE 2 — Automation ledger (14 launchd agents; last-run = log mtime proof)
| Agent | Schedule | Last run (proof) | Fail-loud? | Checks decision-relevant risk? | Status |
|---|---|---|---|---|---|
| watchdog | every 300s | 2026-06-29 05:54 | yes (self-heal+alert) | infra health | RUNNING |
| claw-control-loop | every 1800s | 2026-06-29 05:41 | partial | claw coord | RUNNING |
| source-helpers | Sun 20:00 | 2026-06-28 20:05 | no | lead fetch | RUNNING |
| monthly-system-review | Sat 09:00 | 2026-06-27 09:00 | **no (writes doc)** | **NO — blind to data/directives** | RUNNING_BUT_BLIND |
| forward-day | wkdy 17:00 ET | 2026-06-26 17:05 | partial | paper signals | RUNNING |
| treasury-rolldown-monthly | 1st-bus 17:10 | 2026-06-26 17:10 | no | monthly spread | RUNNING |
| **forge-daily-loop** | wkdy 19:00 PT | 2026-06-26 19:00 → **[HALT]** | yes (tripwire) | research dry-run | **HALTED** (reports-dir >30d tripwire) |
| learning-loop-audit | wkdy 18:15 PT | 2026-06-26 18:42 | **yes (now calls guardrails)** | YES (post-fix) | RUNNING_FIXED |
| operator-digest | wkdy 18:00 | 2026-06-26 18:00 | macOS notify | exception intel | RUNNING |
| daily-research | wkdy 17:30 | (shared Algo runner) | partial | research stack | RUNNING |
| twice-weekly-research | Tue 18:00 | 2026-06-25 18:12 | no | factory batch | RUNNING |
| weekly-research | Fri 18:30 | 2026-06-26 18:42 | partial | integrity/kill | RUNNING |
| phase1c-24h-verify | wkdy 15:30 PT | 2026-06-26 15:30 | yes | **MOOT (book invalidated)** | RETIRE (P3) |
| (guardrails) | via learning-loop | 2026-06-26 | **yes (exit≠0)** | YES | NEW |

**Findings:** (a) forge-daily-loop HALTED on a stale reports-dir tripwire — needs clearing/retarget (P1); (b) monthly-review
RUNS_BLIND (P1 wire guardrails in); (c) phase1c-24h-verify is MOOT (stop_run invalidated) → retire (P3).

## TABLE 3 — Data inventory & usage
| Source | Schema/fields | Symbols | Range | Loader | Used by | Underused? | State |
|---|---|---|---|---|---|---|---|
| Databento 1m | OHLCV+volume | 11 futures | ~2024-26 | databento_loader.py | P14/P15/cost-model | improving | ACTIVE_PACKET_LANE |
| 5m processed | OHLCV+volume | 11 | 2019-26 | (downsample) | most tests (close-only) | volume under-used | ACTIVE |
| feeds/cot.csv | COT net | — | weekly | — | (re-fetched via API) | YES | INVENTORIED_UNUSED |
| feeds/cpi_levels | CPI | — | monthly | — | none | YES | INVENTORIED_UNUSED |
| feeds/credit_oas | credit spread | — | daily | — | none | YES | INVENTORIED_UNUSED |
| feeds/copper_gold_ratio | ratio | — | daily | — | none | YES | INVENTORIED_UNUSED |
| feeds/deribit_BTC_PERPETUAL, DVOL | crypto perp/vol | BTC/ETH | daily | — | crypto vein (paused) | YES | INVENTORIED_UNUSED |
| TreasuryDirect API | auctions | UST | live | P03 | P03 | — | EXHAUSTED_BY_CLEAN_TEST |
| CFTC COT API | positioning | 8 | weekly | COT intake | COT test | — | EXHAUSTED (naive) |
| MCL crude | OHLCV | MCL | — | — | — | — | INVALIDATED_BY_DATA_QUALITY |

## TABLE 4 — Strategy/research ledger (current truth status)
| Branch | Old verdict | Current truth | Causality | Cost | Full-N DSR | Next |
|---|---|---|---|---|---|---|
| ORB family ×5 | "validated WH" | **INVALIDATED** (lookahead) | fail→fixed | y | n/a | none |
| stop_run_reversal | PORT_VERIFIED_GREEN | **INVALIDATED** (lookahead) | fail | y | — | deactivated |
| zn_afternoon, fx_daily_trend | probation | **INVALIDATED** (lookahead) | fail | — | — | deactivated |
| nfp_level_breakout | probation | **CLEAN_KILL** | leak+gatefail | y | n | none |
| vol_managed_equity | probation | **KILL (long-beta)** | clean | y | — | none |
| TSMOM | clean-but-weak | CLEAN_BUT_WEAK | clean | y | weak | basket-leg |
| vol-carry | clean-but-weak | CLEAN_BUT_WEAK | clean | y | weak | basket-leg |
| ZN month-end (P04) | SCREEN_PASS | SCREEN_PASS_RETAINED | clean | y(robust) | fail 0.86 | shelved |
| overnight (P13) | structural | structural / cost-killed | clean | y(robust) | fail | shelved |
| basket (B1/B2) | — | BASKET_FAIL | clean | y | fail realistic | none |
| P03 auction | — | CLEAN_KILL | clean | y | fail 0.41 | none |
| COT positioning | — | CLEAN_KILL (naive) | clean | y | best-of-48 | non-naive pre-reg only |
| P14 VWAP-rev, P15 vol-mom | — | CLEAN_KILL | clean | y | 0.0 | none |
| treasury_rolldown_carry | probation | **RETEST_REQUIRED_BESPOKE** | unproven | — | — | bespoke harness |
| Databento volume lane | — | ACTIVE (3 worked) | clean | y | — | climax/opening/regime untested |
**No WH/validated/primary/candidate anywhere. No validated primary exists.**

## TABLE 5 — Code/control ledger
| Control | Path | Test/evidence | Status |
|---|---|---|---|
| causality audit | research/causality_audit.py | certified (catches ORB) | ✅ |
| no-lookahead regression | research/test_no_lookahead_daily_filters.py | PASS | ✅ |
| DSR/PBO | research/forge_deflated_sharpe.py | self-test + used | ✅ |
| system guardrails (fail-loud) | research/forge_system_guardrails.py | catches backlog=18, bias | ✅ NEW |
| guardrails wired to learning-loop | forge_learning_loop_audit.py | runs+surfaces | ✅ |
| participation cost model | …_DB_participation_cost_model.py | reassessment null | ✅ standing tool |
| feature-cache content hash | — | — | ❌ MISSING (P1) |
| trial-N auto counter | — | manual in factory §8 | ❌ PARTIAL (P1) |
| no-WH-language doc scan | — | — | ❌ MISSING (P2) |

## TABLE 6 — Remediation queue
- **P0 (blocks trust):** (1) git auth → push 18-commit backlog [OPERATOR]. (2) guardrails wired+firing [DONE].
- **P1 (before any candidate):** (3) clear/retarget forge-daily-loop reports-tripwire (HALTED); (4) wire guardrails INTO monthly-review; (5) feature-cache content-hash; (6) rescue false-kill retest; (7) trial-N auto counter.
- **P2 (throughput):** (8) finish volume lane (climax/opening/regime); (9) no-WH-language doc-scan guardrail; (10) feeds-library packets (cpi/credit_oas/copper_gold).
- **P3 (cleanup):** (11) retire phase1c-24h-verify (moot); (12) paid-data decision after volume lane done.
