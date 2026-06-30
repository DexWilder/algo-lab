# ROADMAP & NOTES RECONCILIATION — second pass (2026-06-29/30)

> Standard: if a note/roadmap/directive/data source lacks code + automation + monitoring + output + a current status,
> it is NOT implemented — it is just a note. Report-only. Built from direct repo/launchd/log/feed inspection.

## 🔴 HEADLINE FINDING (the recurring failure, again)
Even the Truth-Reset / Alpha-Intake / Databento work this session was done **without reconciling against pre-existing
infrastructure**, so it DUPLICATED and MISSED:
- **`research/wp_b1_auction_harness.py`** — a purpose-built Treasury-auction harness, "all session lessons baked in"
  (validate→no-lookahead→join→coverage→predeclared mechanisms→FOMC-contamination split). **NEVER RUN.** Its feed
  **`data/feeds/treasury_auctions.csv` (3,178 rows, 2019-26) is PRESENT.** I instead built a *cruder* `P03` from the API.
- **`data/feeds/` holds ~20 feeds** (vix, treasury_auctions, treasury_yield_curve, dollar_index, real_rates, policy_rates,
  funding, inflation_expectations, energy_spot/futures, deribit BTC/ETH perp+DVOL, okx swap, credit_oas, copper_gold,
  cot, cpi). I **re-fetched VIX and COT and auctions from APIs when local copies existed.**
- Parked work never reconciled: `FEED_DEPENDENT_CANDIDATE_PACKETS_2026-06-17.md`, `FORGE_CANDIDATE_LEDGER_2026-06-17.md`,
  `P1P2_RATES_CARRY_BOARD_2026-06-17.md`, `LEVER_B_QUEUE`, month-end-rates **WATCH-marginal/contaminated re-grade**.
**Conclusion: the system is much better (sealed, self-checking) but NOT at max capacity — there is a ready harness on a
present feed that has never run, and a feed library that is mostly unused.**

## TABLE 1 — Operator-directive ledger
| Directive | Cat | Expected | Impl path | Automated | Last proof | Status | Gap/Fix | Pri |
|---|---|---|---|---|---|---|---|---|
| Use Databento / volume | data | volume-native research | P14-16, cost-model | guardrail close-only-bias | guardrail 06-30 (11/186) | PARTIAL | raise usage | P2 |
| Databento 1m/volume lane | research | ≥distinct volume mechs | 4 packets run | trial-ledger | N=68 | PARTIAL | opening/imbalance left | P2 |
| No close-only drift | data | flag close-only | guardrail | yes | firing | WORKING | — | — |
| Monthly full-system review | audit | data+directive checks | monthly_system_review.py +guardrails §2 | launchd Sat | ran 06-27; wired 06-29 | WORKING(newly) | next-run proves | P2 |
| Learning-loop audit | learn | operationalize | forge_learning_loop_audit.py→guardrails | launchd wkdy18:15 | 06-26 18:42 | WORKING | — | — |
| Guardrails in daily+monthly | audit | fail-loud both | wired both | yes | firing | WORKING | — | — |
| Unused-data audit | data | flag unused feeds | guardrail (databento only) | partial | — | **PARTIAL** | extend to data/feeds/ | P1 |
| Trial-N auto counter | research | automatic N | forge_trial_ledger.py | record/count | N=68 | WORKING | — | — |
| DSR-at-full-N | research | mandatory | forge_deflated_sharpe + ledger | per-test | used | WORKING | — | — |
| No WH/validated language | doc | block premature | guardrail WH-scan | yes | clean | WORKING | — | — |
| Causality-first preflight | research | gate first | causality_audit.py | manual call | certified | WORKING | auto-enforce | P2 |
| Feature-cache content hash | execution | bust on change | crossbreeding_engine | n/a | verified | WORKING | — | — |
| Cost sensitivity real | research | costs move PnL | causality_audit B + cost-model | per-test | participation model | WORKING | — | — |
| Roll/MCL artifact caution | data | flag rolls | causality_audit C + doctrine | per-test | MCL invalidated | WORKING | — | — |
| Paper/probation truth-audited | strategy | all books audited | rescue+overhaul | manual | done | WORKING | — | — |
| Invalidated books deactivated | capital | OFF | registry status=watch | done | 7 books OFF | WORKING | — | — |
| Capital gate fail-closed | capital | no exec w/o approval | execution_approval_check | per-build | held | WORKING | — | — |
| No mutation w/o approval | capital | — | — | — | only approved deactivations | WORKING | — | — |
| Report-only Lane B active | execution | continuous | — | — | continuous | WORKING | — | — |
| Forced-flow priority | research | tier T1 | factory tiers | — | applied | WORKING | — | — |
| Alpha-intake factory | research | book/source→packets | ALPHA_INTAKE doc | manual | active | PARTIAL | source-intake not automated | P2 |
| Books/podcasts/YouTube intake | source | mechanism packets | from-knowledge | **none** | — | DOCUMENTED_ONLY | honest: can't ingest audio | P3 |
| Rescue false-kill review | research | classify kills | RESCUE doc | manual | done 06-29 | WORKING | — | — |
| Data-tier / paid memo | data | decision frame | PAID_DATA memo | — | provisional | PARTIAL | finalize after free | P2 |
| Paid conclusion blocked till inventory | data | gate | memo PROVISIONAL | guardrail-able | enforced manually | PARTIAL | guardrail it | P1 |
| Git push-as-you-go | git | durable | gh cred helper | persistent | backlog 0 | **WORKING(fixed)** | — | — |
| Automation last-run proof | audit | evidence | this report + overhaul | manual | proven | PARTIAL | add to guardrail | P2 |
| 19:00 forge-loop scheduled proof | automation | unattended run | launchd | **06-29 19:02 fired** | log mtime | **WORKING** | confirm report artifact | P2 |
| Phase1C verifier retired | automation | remove moot | launchd present | — | moot | **NOT DONE** | disable agent | P3 |
| Treasury auction harness (wp_b1) | research | run on feed | wp_b1_auction_harness.py | **NEVER RUN** | — | **MISSING-EXECUTION** | run it (feed present) | **P1** |
| Feed-drop auto-validator | automation | drop→validate | manifest claims it | **no watcher found** | — | DOCUMENTED_ONLY | manual run | P2 |

## TABLE 2 — Roadmap-item ledger
| Item | State | Evidence | Next |
|---|---|---|---|
| Truth Reset | DONE_AND_PROVEN | causality_audit certified | — |
| Full System Overhaul | DONE_BUT_NEEDS_PROOF→PROVEN | guardrails firing | — |
| Databento inventory | PARTIAL | missed full feeds lib | extend |
| Databento packet factory | PARTIAL | 4 packets (3 kill+null) | opening/imbalance |
| Alpha Intake Factory | PARTIAL | factory doc; source-intake manual | — |
| Forced-flow event lane | PARTIAL | P02/03/04 + COT done | wp_b1, EIA |
| Treasury rolldown bespoke harness | NOT_STARTED | RETEST_REQUIRED | build |
| Free-data status memo | NOT_STARTED | — | after opening/imbalance |
| Paid-data memo | PARTIAL | provisional | finalize |
| COT lane | DONE (naive KILL) | intake+test | non-naive pre-reg optional |
| EIA lane | BLOCKED | feed-gated (eia_crude_stocks.csv absent) | operator download |
| Treasury auction lane | **DUPLICATED/INCOMPLETE** | P03 crude done; wp_b1 UNRUN on present feed | **run wp_b1** |
| FOMC/pre-FOMC lane | NOT_STARTED | queued | run (free) |
| VIX/vol-carry lane | PARTIAL | vol-carry weak; vix.csv unused; true curve paid | — |
| gamma/GEX paid lane | BLOCKED | paid-data decision | operator |
| Rescue false-kill review | DONE_AND_PROVEN | RESCUE doc | — |
| Daily Forge loop | DONE_AND_PROVEN | un-halted, 06-29 19:02 fired | — |
| Monthly system review | DONE_BUT_NEEDS_PROOF | guardrails wired; next-run proves | — |
| Monthly Claw/source refresh | PARTIAL | CLAW_HARVEST config NOT applied | operator |
| Learning-loop audit | DONE_AND_PROVEN | calls guardrails | — |
| Guardrail integration | DONE_AND_PROVEN | daily+monthly | — |
| Git durability | DONE_AND_PROVEN | backlog 0, persistent | — |
| month-end-rates re-grade | BLOCKED | needs rates_multicontract.csv | operator feed |
| FEED_DEPENDENT_CANDIDATE_PACKETS | PARTIAL/UNRECONCILED | doc exists | reconcile |

## TABLE 3 — Automation ledger (proof-based)
| Automation | Launch | Schedule | Last run | Fail-loud | Would catch Databento-underuse / halted-loop / git-backlog / unworked-directive? | Status |
|---|---|---|---|---|---|---|
| guardrails | via learning-loop | wkdy | 06-30 | **yes (exit≠0)** | **YES / partial / YES / partial** | WORKING |
| learning-loop-audit | launchd | wkdy 18:15 | 06-26 | yes(now) | via guardrails | WORKING |
| monthly-system-review | launchd | Sat (1st-Sat save) | ran 06-27; file 2026-05 | now yes(§2) | now YES | WORKING(newly) |
| forge-daily-loop | launchd | wkdy 19:00 PT | **06-29 19:02** | tripwire | n/a | WORKING(un-halted) |
| forward-day (paper) | launchd | wkdy 17:00 ET | 06-26 | partial | n/a | RUNNING |
| watchdog | launchd | 300s | 06-29 | yes | infra only | RUNNING |
| claw-control-loop | launchd | 1800s | 06-29 | partial | no | RUNNING |
| source-helpers | launchd | Sun/Wed 20:00 | 06-28 | no | no | RUNNING |
| treasury-rolldown-monthly | launchd | 1st-bus 17:10 | 06-26 | no | no | RUNNING |
| operator-digest | launchd | wkdy 18:00 | 06-26 | notify | no | RUNNING |
| twice/weekly-research | launchd | Tue/Fri | 06-25/26 | partial | no | RUNNING |
| phase1c-24h-verify | launchd | wkdy 15:30 | 06-26 | yes | **MOOT** | RETIRE(P3) |
| trial-ledger | script | on-call | N=68 | n/a | n/a | WORKING |
| wp_b1_auction_harness | script | manual | **NEVER** | n/a | n/a | UNRUN(P1) |

## TABLE 4 — Data-source inventory & usage (the under-counted library)
| Source | Range | #scripts using | Status | Next |
|---|---|---|---|---|
| Databento 1m OHLCV+vol (11) | 2024-26 | ~4 | UNDERUSED→ACTIVE | opening/imbalance |
| 5m processed (11) | 2019-26 | most (close-only) | UNDERUSED(volume) | — |
| feeds/treasury_auctions.csv | 2019-26, 3178 | (wp_b1 unrun) | **INVENTORIED_UNUSED** | **run wp_b1** |
| feeds/vix.csv | 1990-26 | re-fetched instead | INVENTORIED_UNUSED | vol packets |
| feeds/treasury_yield_curve | 1962-26 | — | INVALIDATED (FRED proxy killed) | — |
| feeds/cot.csv | weekly | 14 | ACTIVE (re-fetched anyway) | — |
| feeds/cpi_levels | monthly | 51 | ACTIVE_USED | — |
| feeds/DVOL BTC/ETH | daily | 12 | ACTIVE (crypto vein) | — |
| feeds/deribit BTC/ETH perp | daily | 2 | UNDERUSED | crypto |
| feeds/credit_oas | daily | 2 | UNDERUSED | risk-regime filter |
| feeds/copper_gold_ratio | daily | 2 | UNDERUSED | risk-regime |
| feeds/dollar_index, real_rates, policy_rates, inflation_exp, funding, energy_spot/futures, okx | various | ~0-few | **INVENTORIED_UNUSED** | macro/regime packets |
| eia_crude_stocks / rates_multicontract / opec / cpi_releases | absent | — | DATA_BLOCKED (feed-gated) | operator download |
| MCL crude | — | — | INVALIDATED_BY_DATA_QUALITY | — |

**Databento special:** OHLCV+volume only (no trades/bid-ask/MBP); 11 futures; volume used in ~4 recent + ~6 older scripts;
volume mechanisms still untested: opening-minutes, imbalance, cross-asset-volume, Treasury-1m event path. Cost-model: done(null).

## TABLE 5 — Research/strategy ledger (current truth)
| Branch | Current status | Causality | Cost | DSR-N | Commit | Next |
|---|---|---|---|---|---|---|
| ORB×5, stop_run, zn_afternoon, fx_daily | INVALIDATED (lookahead) | fail | y | — | deactivated | — |
| nfp | CLEAN_KILL | y | y | n | — | — |
| vol_managed | KILL(beta) | clean | y | — | — | — |
| TSMOM / vol-carry | CLEAN_BUT_WEAK | y | y | weak | — | basket-leg |
| XSMOM, crude | CLEAN_KILL(artifact) | y | y | — | — | — |
| ZN month-end P04 | SCREEN_PASS_RETAINED | y | y(robust) | 0.86 fail | — | shelved |
| overnight P13 | shelved/cost | y | y(robust) | fail | — | — |
| basket | BASKET_FAIL | y | stress | fail | — | — |
| P03 auction | CLEAN_KILL (crude) | y | y | 0.41 | — | **superseded by wp_b1** |
| P14/P15/P16 volume | CLEAN_KILL | y | y | 0.0 | f6ee69c | — |
| COT | CLEAN_KILL(naive) | y | y | best-of-48 | — | non-naive opt |
| treasury_rolldown | RETEST_REQUIRED_BESPOKE | — | — | — | — | build harness |
| CV1/2/3, MGC vol_low | VOID (ORB-derived) | — | — | — | — | — |
| month-end-rates (prior) | WATCH-marginal/contaminated | unproven | — | — | — | re-grade (feed-gated) |
| crypto C1/C3/C5/O1/O2 | (per memory) KILL/DATA-BLOCKED/opened | mixed | — | — | — | DVOL vein |
| FEED_DEPENDENT packets | PARKED/UNRECONCILED | — | — | — | — | reconcile |

## TABLE 6 — Believed-automated vs actually-automated
| System | Reality |
|---|---|
| Monthly audit | was AUTOMATED-BUT-BLIND → now automated+guardrailed (proof next run) |
| Learning-loop | AUTOMATED+PROVEN (calls guardrails) |
| Trial-N accounting | was MANUAL → now AUTOMATED |
| Guardrail check | AUTOMATED+PROVEN |
| No-WH scan | AUTOMATED+PROVEN |
| Unused-data audit | AUTOMATED-PARTIAL (databento only; feeds/ not covered) |
| Git durability check | AUTOMATED+PROVEN |
| Daily Forge loop | was HALTED → now RUNNING+PROVEN (06-29 19:02) |
| Feed-drop auto-validator | DOCUMENTED_ONLY (no file-watcher) |
| Source intake (books/podcasts) | DOCUMENTED_ONLY (from-knowledge, not automated) |
| Claw monthly refresh | EXISTS-but-config-NOT-APPLIED (recycling dead families) |
| Capital gate | AUTOMATED+PROVEN |
| Data update jobs | AUTOMATED (data/processed appends) |

## TABLE 7 — Missed-capability / unused-info
| Unused capability | Why it matters | Why missed | Guardrail that should catch it | Action | Pri |
|---|---|---|---|---|---|
| wp_b1_auction_harness on present feed | purpose-built, lessons-baked, FEED PRESENT | didn't reconcile; built P03 instead | unused-harness/feed check | **run it** | **P1** |
| treasury_auctions.csv (local) | re-fetched from API | no feeds inventory check | feeds-usage guardrail | use local | P1 |
| vix.csv (1990-26 local) | re-fetched VIX | same | same | use local | P2 |
| ~10 macro feeds (dollar_index, real_rates, policy_rates, funding, inflation_exp, energy, credit_oas, copper_gold) | regime/macro packets unbuilt | no feeds-usage tracking | feeds-usage guardrail | regime-filter packets | P2 |
| Databento 1m volume | opening/imbalance untested | close-only habit | close-only guardrail (now on) | run packets | P2 |
| FEED_DEPENDENT_CANDIDATE_PACKETS / FORGE_CANDIDATE_LEDGER | parked candidate inventory | no reconcile step | this reconciliation | reconcile | P2 |
| month-end-rates WATCH-marginal | un-regraded marginal | feed-gated + forgotten | candidate-ledger check | re-grade on feed | P2 |
| Claw harvest config | recycling dead families | automation-owned, not applied | — | operator apply | P3 |
| deribit/okx crypto feeds | DVOL vein partial | — | — | crypto packets | P3 |

## TABLE 8 — Remediation queue
**P0 (trust):** none open — git pushed (backlog 0, persistent); guardrails firing; loop un-halted+scheduled-proven.
**P1 (before any candidate):** (1) **run `wp_b1_auction_harness.py` on treasury_auctions.csv** [Claude] — proof: report+verdict;
(2) **extend guardrail unused-data check to data/feeds/** [Claude] — proof: guardrail flags unused feeds;
(3) guardrail-enforce "paid-memo provisional until feeds inventory clean" [Claude];
(4) reconcile FEED_DEPENDENT_CANDIDATE_PACKETS into the strategy ledger [Claude].
**P2 (throughput):** (5) opening-minutes + (6) volume-imbalance Databento packets; (7) free-data status memo; (8) finalize paid-data memo;
(9) macro/regime packets from unused feeds; (10) month-end-rates re-grade IF rates_multicontract feed arrives.
**P3 (cleanup):** (11) retire phase1c-24h-verify [operator nod — scheduler change]; (12) apply Claw harvest config [operator];
(13) EIA/OPEC packets [blocked-by-feed]; (14) gamma/GEX [blocked-by-paid-decision].

## FINAL SUMMARY
- **Thought automated but wasn't:** monthly audit (blind→fixed), trial-N (manual→fixed), feed-drop validator (doc-only), source intake (doc-only), Claw config (not applied).
- **Had data but didn't use:** treasury_auctions.csv (+ wp_b1 harness), vix.csv, ~10 macro feeds, Databento volume (partly).
- **Notes not operationalized:** feed-staging queue, candidate ledgers, month-end-rates re-grade, wp_b1.
- **Running but blind:** monthly review (now fixed); Claw (recycling dead).
- **Halted/obsolete:** forge-daily-loop (now running); phase1c-verify (obsolete, retire).
- **Active research lanes:** Databento volume (opening/imbalance left); forced-flow (wp_b1 auctions, FOMC free); treasury bespoke; paid-data decision.
- **For max capacity:** run wp_b1, extend feeds guardrail, reconcile parked packets, finish volume lane, then paid decision.
- **Next 10 actions:** (1) run wp_b1 auctions; (2) extend guardrail to data/feeds/; (3) reconcile feed-dependent packets; (4) opening-minutes volume packet; (5) volume-imbalance packet; (6) free-data status memo; (7) macro/regime feed packets; (8) finalize paid-data memo; (9) retire phase1c (operator nod); (10) confirm monthly-review next-run includes guardrails.


## ADDENDUM (2026-06-30): wp_b1 harness RUN (reconciliation action #1 executed)
`research/wp_b1_auction_harness.py` run on present `treasury_auctions.csv` (799 auctions ZN/ZF/ZB x 4 windows, FOMC-contamination split): **ALL KILL** (clean-of-contam PF 0.51-1.04, erratic max-year). Auction lane = **CLEAN_KILL via the proper purpose-built harness** — supersedes the cruder P03 (64 ten-year-only). Demonstrates the reconciliation's value: using existing infra gave a more rigorous, multi-tenor, FOMC-clean verdict. P1 #1 DONE.
