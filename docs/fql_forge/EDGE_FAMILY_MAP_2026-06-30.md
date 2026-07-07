# Edge-Family Map (computed 2026-07-07 12:53 UTC) — from family_status.json x trial ledger
> Regenerate: `python3 research/forge_family_map.py`. Coverage=tested/(tested+untested). family-N from ledger lane.
> **Families: 21 | active (not killed): 12 | global trial-N: 2276 | drift flags: 0**

| family | status | tier(tested→applicable) | coverage | tested | untested | family-N | next untested expressions |
|---|---|---|---|---|---|---|---|
| gamma_dealer | REGIME_INGREDIENT_VALIDATED | T6→T6 | 40% | 2 | 3 | 23 | combine GEX filter with a STRONGER base index entry (source-derived / event-conditioned); more GEX sample; GEX sizing (not just filter) |
| monthend_settlement | CLEAN_BUT_WEAK | T1→T3 ⚠gap | 25% | 1 | 3 | 7 | ZF/ZB month-end; settlement-1m revert; index-rebal |
| open_close_liquidity | CLEAN_BUT_WEAK | T3→T3 | 40% | 2 | 3 | 70 | settlement-window revert @T3; closing-imbalance @T3; liquidity-hole reversal @T3 |
| macro_event_drift | CLEAN_BUT_WEAK | T1→T3 ⚠gap | 50% | 2 | 2 | 6 | CPI drift; event-1m-path |
| fx_fixing_ratediv | UNDERTESTED | none→T3 ⚠gap | 0% | 0 | 2 | 23 | WMR 16:00 fix flow; policy-rate divergence |
| carry_commodity | SCREEN_PASS_RETAINED | T4→T4 | 88% | 7 | 1 | 10 | roll-window pressure |
| vol_risk_premium | CLEAN_BUT_WEAK | T5→T6 ⚠gap | 67% | 2 | 1 | 23 | true-curve VRP (paid) |
| inventory_eia | DATA_BLOCKED_CERT | none→T5 ⚠gap | 0% | 0 | 1 | 7 | EIA surprise hedge |
| expiry_opex | FEASIBLE | none→T6 ⚠gap | 0% | 0 | 1 | 23 | OPEX-gamma-pin (via gamma lane) |
| xasset_leadlag | UNDERTESTED | T2→T3 ⚠gap | 50% | 1 | 1 | 23 | pure latency lead-lag |
| regime_filters | UNDERTESTED | T5→T5 | 50% | 1 | 1 | 6 | regime overlay on a survivor (needs survivor) |
| execution_cost | ACTIVE_TOOL | T3→T3 | 50% | 1 | 1 | 23 | liquidity risk-filter |
| curve_rv | SUBFAMILY_KILLED | T4→T4 | 50% | 2 | 2 | 3 | 2s10s slope momentum; Kalman spread |
| trend_momentum | SUBFAMILY_KILLED | T3→T3 | 75% | 3 | 1 | 1679 | regime-conditioned trend (needs regime library) |
| positioning_cot | SUBFAMILY_KILLED | T5→T5 | 50% | 1 | 1 | 48 | COT+price-break conditional |
| auction_issuance | SUBFAMILY_KILLED | T5→T5 | 50% | 1 | 1 | 7 | tenor-divergence concession |
| intraday_micro | SUBFAMILY_KILLED | T3→T6 ⚠gap | 75% | 3 | 1 | 70 | ES-NQ lead-lag latency |
| mean_reversion | CLEAN_KILL | T3→T3 | 100% | 3 | 0 | 1679 | — |
| carry_rates | CLEAN_KILL | T4→T4 | 100% | 2 | 0 | 3 | — |
| crypto_funding | CLEAN_KILL | T5→T5 | 100% | 1 | 0 | 4 | — |
| carry_legacy_fx_rates | CLEAN_KILL | T1→T4 ⚠gap | 100% | 3 | 0 | 4 | — |

## Drift flags (family-completion integrity)
- none — no family over-claims exhaustion or falsely claims active

## Family completion rule
A family is NOT FAMILY_EXHAUSTED until coverage=100% AND cost/roll/concentration/DSR checks done on survivors. Killing a whole family from one expression is over-claim (flagged above). Endless rescue-grind on a killed family is banned.