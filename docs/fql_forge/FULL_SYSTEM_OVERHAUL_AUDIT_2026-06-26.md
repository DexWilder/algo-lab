# FULL_SYSTEM_OVERHAUL AUDIT (2026-06-26) — execution-memory failure root cause

> Goal: verify that what we SAY/believe/document/automate is actually implemented, scheduled, monitored, and USED.
> Trigger: Databento pulled but ignored (tests close-only); paid-data near-conclusion before inventory; contaminated
> books active until manual challenge; 14 unpushed commits. These are execution-memory failures, not strategy failures.
> Report-only. Normal strategy discovery PAUSED until P0 items below are clear.

## ROOT CAUSE (one sentence)
**Every automation RUNS, but none of them check the things that actually failed** — data-usage ("are we using the
richest data we have?"), directive operationalization ("did 'use Databento' change behavior?"), or git durability.
The monthly review audits roadmap/registry/memory but is BLIND to data-usage and directive compliance. The learning-
loop audit only repairs the memory index + reports `git status`. So documentation never had teeth to change behavior.

## §1 User-directive ledger (classified, honest)
| Directive | State | Evidence |
|---|---|---|
| Use Databento data | **BROKEN → fixing** | data/databento/*_1m.csv (OHLCV+volume) present since Mar; ALL tests used close-only 5m until 2026-06-26. Not operationalized. |
| Truth gate / causality first | IMPLEMENTED_AND_WORKING | `research/causality_audit.py` certified (catches ORB lookahead) |
| No WH/validated language before causality | IMPLEMENTED_AND_WORKING | held across COT/basket/P03/P13/P14 |
| DSR / full-N trial ledger | IMPLEMENTED_AND_WORKING | `forge_deflated_sharpe.py` + ALPHA_INTAKE_FACTORY §8 ledger (N tracked) |
| Monthly full-system assessment | **PARTIAL / AUDIT_FAILURE** | `monthly_system_review.py` runs but checks roadmap/registry/memory/harvest only — NOT data-usage, NOT directive compliance, NOT unused-data. Blind to the failure. |
| Learning-loop audit operationalizes learning | **PARTIAL (no teeth)** | `forge_learning_loop_audit.py` = memory-index frontmatter + git-status only. No data/directive/backlog checks. |
| Git durability | **BROKEN** | push fails (`could not read Username` — no token in env); 14 commits local-only |
| Fail-closed capital gate | IMPLEMENTED_AND_WORKING | held throughout; `execution_approval_check` in build_portfolio_config |
| No registry/scheduler/portfolio mutation w/o approval | IMPLEMENTED_AND_WORKING | only operator-approved deactivations performed |
| Report-only Lane B continues | WORKING | continuous this session |
| Alpha-intake factory + forced-flow priority | IMPLEMENTED (new) | ALPHA_INTAKE_FACTORY_2026-06-26.md |
| No paid-data conclusion before internal inventory | **was BROKEN → corrected** | violated 2026-06-26; caught by operator; memory `feedback_inventory_before_exhausted_claim` locked |
| Unused-data audit | **MISSING** | no automation checks whether available data is used. THE core gap. |
| Rescue audit of false kills | PARTIAL | rescue ledger exists; false-kill review still pending |

## §2 Automation audit (14 launchd agents — all LOADED)
Firing confirmed today (Jun 26 logs): watchdog, claw-control-loop (every 30m), forge-morning-digest (08:00).
- `monthly-system-review` — EXISTS; latest output `docs/reports/monthly_system_review/2026-05_FQL_SYSTEM_REVIEW.md`
  (written Jun 6; reviews May). **AUDIT_FAILURE: does not check data-usage / directive compliance / unused feeds.**
- `learning-loop-audit` — EXISTS; narrow (memory index + git status). No teeth.
- `forge-daily-loop` (19:00 PT research), `forward-day`, `daily-research`, `twice-weekly`, `weekly-research`,
  `operator-digest`, `source-helpers`, `treasury-rolldown-monthly`, `phase1c-24h-verify` (now moot — book invalidated),
  `watchdog` — loaded. Last-exit code 0 where checked.
- **Gap: NO automation asserts "richest available data is used," "directives operationalized," or "git backlog < N."**
  Remediation = new fail-loud guardrail (`research/forge_system_guardrails.py`, built this cycle) wired into the
  weekday learning-loop audit so it runs EVERY cycle, not monthly, and FAILS LOUD.

## §3 Data inventory & usage state
| Vein | State | Note |
|---|---|---|
| Databento 1m OHLCV+VOLUME (11 inst) | **INVENTORIED_UNUSED → ACTIVE_PACKET_LANE** | volume/1m never used until 2026-06-26; must run ≥20 native packets before any "exhausted" claim |
| 5m OHLCV (downsample, 7yr) | partially used (close-only) | volume column ignored |
| data/feeds/cot.csv | INVENTORIED_UNUSED (re-fetched needlessly) | check feeds BEFORE external fetch |
| feeds: cpi_levels, credit_oas, copper_gold, deribit BTC perp, DVOL BTC/ETH | INVENTORIED_UNUSED | candidate packet inputs (macro/credit/crypto-vol) |
| Treasury auctions (TreasuryDirect API) | EXHAUSTED_BY_CLEAN_TEST | P03 CLEAN_KILL |
| COT (CFTC API + local) | EXHAUSTED_BY_CLEAN_TEST (naive) | non-naive needs pre-reg |
| MCL crude | INVALIDATED_BY_DATA_QUALITY | roll-stitch artifacts |
Full detail: `DATABENTO_INVENTORY_AND_UNLOCKS_2026-06-26.md`.

## §4 Strategy/research ledger
Authoritative ledger already maintained in `TRUTH_RESET_RESCUE_AUDIT_2026-06-25.md` + `ALPHA_INTAKE_FACTORY_2026-06-26.md`
(§7-§8). Summary: ORB×5/stop_run/zn_afternoon/fx_daily/nfp = INVALIDATED; vol_managed = KILL(beta); TSMOM/vol-carry/
ZN-month-end = CLEAN_BUT_WEAK / SCREEN_PASS_RETAINED; overnight = structural/cost-killed; basket = FAIL; P03/P14 = KILL;
treasury_rolldown = RETEST_REQUIRED_BESPOKE; Databento-volume lane = ACTIVE. No WH/validated/primary anywhere.

## §5 Code-control audit
| Control | Status |
|---|---|
| causality audit | ✅ `causality_audit.py` (certified) |
| DSR / full-N | ✅ `forge_deflated_sharpe.py` + ledger |
| cost-sensitivity | ✅ in causality_audit + per-test |
| feature-cache content hash | ❌ MISSING (cache keys on len/first/last only; known sharp-edge) — P1 |
| data-inventory / unused-data check | ❌ MISSING → building in guardrails — P0 |
| directive-compliance check | ❌ MISSING → building — P0 |
| git-backlog warning | ❌ MISSING → building — P0 |
| roll-artifact audit | ✅ in causality_audit (check C) |
| same-day-aggregate leakage test | ✅ `test_no_lookahead_daily_filters.py` |
| fail-closed capital gate | ✅ `execution_approval_check` |
| deactivation evidence | ✅ deactivation_history in registry |

## §6 Monthly-audit redesign (fail loud, run every cycle)
The monthly review stays for narrative, but the ENFORCEMENT moves to `research/forge_system_guardrails.py` run by the
weekday learning-loop audit. It must FAIL LOUD (non-zero exit + ALERT line surfaced into context) on: unused Databento
data, close-only-test heuristic, git backlog > threshold, stale automations, directive non-compliance, paid-data memo
referenced while internal data uninventoried. Monthly review to additionally call guardrails and embed results.

## §7 Git durability
Push BROKEN: `could not read Username for https://github.com` (no credential helper / PAT in this environment).
**14 commits committed locally, unpushed** (work durable on disk + in git objects, NOT on remote → single-machine risk).
Required operator action: `gh auth login` or set a PAT / credential helper, then `git push origin main`.
Guardrail adds a hard ALERT when backlog > 5. Risk: MEDIUM (durable locally; lost only if disk lost before push).

## §8 Remediation queue
- **P0 (before trusting further research):** (1) build + wire fail-loud guardrails (unused-data, close-only, git-backlog,
  directive-compliance) into weekday learning-loop audit; (2) operator restores git auth → push 14-commit backlog.
- **P1 (before any candidate):** (3) feature-cache content-hash key; (4) monthly review calls guardrails + checks data-usage;
  (5) finish rescue false-kill review.
- **P2 (throughput):** (6) Databento-native volume packet lane (≥20 packets); (7) participation-rate cost model from volume.
- **P3 (cleanup):** (8) retire moot automations (phase1c-24h-verify — book invalidated); (9) feeds-library packet intake.
