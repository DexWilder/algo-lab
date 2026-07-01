# Edge-Family Map (computed 2026-07-01 16:50 UTC) — from family_status.json x trial ledger
> Regenerate: `python3 research/forge_family_map.py`. Coverage=tested/(tested+untested). family-N from ledger lane.
> **Families: 20 | active (not killed): 13 | global trial-N: 1776 | drift flags: 0**

| family | status | data | coverage | tested | untested | family-N | next untested expressions |
|---|---|---|---|---|---|---|---|
| carry_commodity | ACTIVE_EXPANSION | LOCAL | 43% | 3 | 4 | 3 | GC de-trended z-carry; spread momentum; spread mean-reversion |
| gamma_dealer | FEASIBLE | REPULL_PAID | 20% | 1 | 4 | 9 | chunked-OI loader; approx-GEX; GEX-regime pin |
| monthend_settlement | CLEAN_BUT_WEAK | LOCAL | 25% | 1 | 3 | 7 | ZF/ZB month-end; settlement-1m revert; index-rebal |
| trend_momentum | CLEAN_BUT_WEAK | LOCAL | 50% | 2 | 2 | 1679 | pooled vol-target trend; trend+carry combo |
| macro_event_drift | CLEAN_BUT_WEAK | LOCAL | 50% | 2 | 2 | 3 | CPI drift; event-1m-path |
| open_close_liquidity | CLEAN_BUT_WEAK | LOCAL | 33% | 1 | 2 | 14 | settlement-close revert; opening-imbalance re-spec |
| fx_fixing_ratediv | UNDERTESTED | LOCAL | 0% | 0 | 2 | 9 | WMR 16:00 fix flow; policy-rate divergence |
| vol_risk_premium | CLEAN_BUT_WEAK | LOCAL | 67% | 2 | 1 | 9 | true-curve VRP (paid) |
| inventory_eia | DATA_BLOCKED_CERT | CERT | 0% | 0 | 1 | 7 | EIA surprise hedge |
| expiry_opex | FEASIBLE | REPULL_PAID | 0% | 0 | 1 | 9 | OPEX-gamma-pin (via gamma lane) |
| xasset_leadlag | UNDERTESTED | LOCAL | 50% | 1 | 1 | 9 | pure latency lead-lag |
| regime_filters | UNDERTESTED | LOCAL | 50% | 1 | 1 | 3 | regime overlay on a survivor (needs survivor) |
| execution_cost | ACTIVE_TOOL | LOCAL | 50% | 1 | 1 | 9 | liquidity risk-filter |
| curve_rv | SUBFAMILY_KILLED | LOCAL | 50% | 2 | 2 | 3 | 2s10s slope momentum; Kalman spread |
| positioning_cot | SUBFAMILY_KILLED | LOCAL | 50% | 1 | 1 | 48 | COT+price-break conditional |
| auction_issuance | SUBFAMILY_KILLED | LOCAL | 50% | 1 | 1 | 7 | tenor-divergence concession |
| intraday_micro | SUBFAMILY_KILLED | LOCAL | 50% | 1 | 1 | 14 | ES-NQ lead-lag latency |
| mean_reversion | CLEAN_KILL | LOCAL | 100% | 2 | 0 | 1679 | — |
| carry_rates | CLEAN_KILL | LOCAL | 100% | 2 | 0 | 3 | — |
| crypto_funding | CLEAN_KILL | LOCAL | 100% | 1 | 0 | 4 | — |

## Drift flags (family-completion integrity)
- none — no family over-claims exhaustion or falsely claims active

## Family completion rule
A family is NOT FAMILY_EXHAUSTED until coverage=100% AND cost/roll/concentration/DSR checks done on survivors. Killing a whole family from one expression is over-claim (flagged above). Endless rescue-grind on a killed family is banned.