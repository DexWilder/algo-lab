# Close-Only / Daily Kill Rescoping (2026-07-01)

> Doctrine A applied to prior kills: **no family is permanently dead until tier proof exists.** Each prior close-only/daily
> kill is reclassified as expression-level, with the richer tier and next rich-data packet named. Driven by
> `research/data/family_status.json` (tier fields) + `learning_state.json` next-25.

| Family | Prior kill tier | Richest applicable | Classification | Next rich-data packet | Priority | Status |
|---|---|---|---|---|---|---|
| mean_reversion | T0/T2 (close/5m) | T3 | **expression killed only** | intraday 1m-path MR (volume-conditioned) | P1 | **TIER_INCOMPLETE (reopened)** |
| open_close_liquidity | T2 | T3 | expression killed only | settlement-window / closing-imbalance / liquidity-hole @T3 | P1 | OR batch killed @T3; 3 T3 exprs left |
| monthend_settlement | T1 (daily) | T3 | expression-level | settlement-1m revert @T3; ZF/ZB | P2 | tier_gap |
| macro_event_drift | T1 (daily) | T3/T5 | expression-level | event 1m-path (FOMC/CPI) @T3 | P2 | tier_gap |
| xasset_leadlag | T2 | T3 | undertested | 1m lead-lag w/ volume confirmation | P2 | tier_gap |
| volume-conditioned continuation/reversal | — | T3 | tested @T3 this cycle | (OR variant killed; other windows open) | P2 | partial |
| intraday_micro | T3 (5m vol) | T6 | subfamily killed | ES-NQ latency / order-book proxy | P3 | tier_gap (T6) |
| regime_filters | T5 | T5 | undertested | overlay on a survivor (needs survivor) | P3 | pending survivor |
| execution/cost/liquidity | T3 | T3 | tool, not alpha | liquidity risk-filter | P3 | tool |
| carry/RV (rates) | T4 | T4 | family-complete @T4 | (event-path T5 is separate family) | — | CLEAN_KILL stands @T4 |

**Rule:** these reopenings feed `learning_state.next_25_actions` and the novelty weights (tier_gap dims up-weighted). The
guardrail blocks any future `FAMILY_EXHAUSTED` on a tier_gap family.
