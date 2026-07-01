# Research OS Control Map (2026-06-30/07-01) — every mistake → a durable control

> Standard: the REPO must remember better than Claude. A lesson isn't learned until it's a guardrail/validator/checklist/
> queue-rule/status-correction. "No durable control = not fixed."

| # | Failure | Root cause | Durable control | Type | Path | Proof |
|---|---|---|---|---|---|---|
| 1 | ORB same-day-close lookahead | filter used day-d close intraday | causality audit + no-lookahead test | validator+test | causality_audit.py, test_no_lookahead_daily_filters.py | certified: catches it |
| 2 | stop_run_reversal contamination | same ema_slope filter | R4 retest + deactivation | script+registry | forge_cycle..CV3R.., registry | clean Sh 0.19 |
| 3 | false DATA_BLOCKED | asserted w/o lineage proof | certificate requirement + guardrail | guardrail+doc | forge_system_guardrails.py ch9, DATA_BLOCKER_CERTIFICATES | cert-gate [ok] |
| 4 | Databento underuse (close-only) | never used volume/1m | close-only-bias guardrail | guardrail | forge_system_guardrails.py | fires (12/186) |
| 5 | existing harness bypassed (P03 vs wp_b1) | didn't grep before building | existing-harness guardrail + reconcile rule | guardrail | forge_system_guardrails.py ch8 | flags unrun |
| 6 | monthly audit blind | checked roadmap not data/directives | guardrails wired into monthly | code | monthly_system_review.py §2 | dry-run shows |
| 7 | forge-daily-loop stale tripwire | oldest-report-age self-perpetuating | newest-age + count semantics | code | fql_forge_daily_loop.py | 06-29 19:02 fired |
| 8 | feature cache no content hash | key=(len,first,last) | OHLCV content fingerprint | code | crossbreeding_engine.py | busts on perturb |
| 9 | trial-N manual | not auto-counted | forge_trial_ledger + layered lanes | module | forge_trial_ledger.py | N=1772, lanes |
| 10 | no-WH-language drift | narrative creep | WH-language scan guardrail | guardrail | forge_system_guardrails.py ch5 | clean |
| 11 | local-only git backlog | auth broken | gh cred helper + backlog guardrail | fix+guardrail | forge_system_guardrails.py ch1 | backlog 0 |
| 12 | COT one-sided artifact | fade one side only | both-sides mandatory | method | cot intake script | KILL (both-sides) |
| 13 | MCL roll/stitch artifact | continuous stitch | per-contract pull + rollover doctrine | data+doctrine | databento_percontract_pull.py | per-contract clean |
| 14 | DVOL_ETH false "malformed" | misread blank-header | data validator | validator | validate_data_file.py | reads fine |
| 15 | CL/GC date-column dropped | ts_event=index, df[keep] dropped it | reset_index + data validator | fix+validator | databento_percontract_pull.py, validate_data_file.py | re-pull PASS |
| 16 | paid-data conclusion premature | before internal inventory | inventory-first + certificate | doc+guardrail | DATABENTO_INVENTORY, cert-gate | corrected |
| 17 | primitive overtesting, ideas parked | no coverage view | coverage audit + family map | doc | VARIATION_COVERAGE.. | 93 untested surfaced |
| 18 | feed exists no queue lane | not inventoried | unused-feeds guardrail | guardrail | forge_system_guardrails.py ch7 | flags okx/DVOL |
| 19 | automation no last-run proof | assumed running | last-run proof in audits | method | FULL_SYSTEM_OVERHAUL, monthly | log mtimes shown |
| 20 | **degenerate carry-sign expression** | sign(F1-F2)~always +1 | **expression validator (pre-test)** | **validator** | **validate_strategy_expression.py** | **flags DEGENERATE_SIDE >90%** |

## Term-structure test checklist (before any rates/commodity carry/RV)
1. `validate_data_file(per_contract)` PASS · 2. front/deferred panel built (`term_structure.build_curve`) · 3. roll days
handled (no cross-contract jump) · 4. F1/F2/F3 availability reported · 5. signal formula PREDECLARED · 6. **`assert_expression_valid`
PASS (side distribution not degenerate)** · 7. DV01/notional sanity · 8. costs/slippage · 9. H1/H2 · 10. per-year ·
11. concentration · 12. global+family+lane+packet N.

## No silent fixes rule
Bug found → document (here) + fix + add control + rerun affected + update queue/status + commit + push + guardrails.
