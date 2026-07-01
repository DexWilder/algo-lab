# ALPHA RESEARCH DASHBOARD (auto-generated 2026-07-01 16:51 UTC)
> `python3 research/forge_dashboard.py` regenerates this. Single canonical state view.

## HEADLINE
- **Validated primaries: 0** (highest ladder rung: **PACKET**; capital gate FAIL-CLOSED, PAPER_APPROVED+ operator-only).
- Guardrails: **clean/P1** | Git backlog: **0** | Test scripts run: 199 | Global trial-N: **1776**

## Throughput (computed live)
- Tests logged today: **10** | total kills: 6 | screen-passes: 1
- Novelty packets: **24** stored (24 today) of 108 template×instrument space
- Families: **13 active** / 20 | coverage 45% (tested exprs / total exprs)
- Candidate ladder: PACKET=1

## Trial-N by lane (family diagnostics)
- primitive_sweep: 1679
- positioning: 48
- databento_volume: 14
- exploratory: 9
- forced_flow: 7
- crypto_carry: 4
- carry: 4
- macro_regime: 3
- curve_rv: 3
- commodity_carry: 3
- portfolio: 2

## Queue depth
- RUN_NOW: 28 | total queue items: 29
- [ACTIVE_PACKET_LANE] gamma_chunked_loader_then_regime: chunked OI loader -> approx-GEX -> predeclared GEX-regime test (feasib
- [RUN_NOW] gc_detrended_carry_zscore: refined commodity TS expr (naive carry-sign KILLed 2026-07-01); de-tre
- [RUN_NOW] clgc_spread_momentum: refined commodity TS expr (naive carry-sign KILLed 2026-07-01); de-tre
- [RUN_NOW] clgc_spread_meanreversion: refined commodity TS expr (naive carry-sign KILLed 2026-07-01); de-tre
- [RUN_NOW] roll_window_pressure_contango: refined commodity TS expr (naive carry-sign KILLed 2026-07-01); de-tre
- [RUN_NOW] nov_benchmark_fix_6B: execution window: benchmark-tracking funds transact at a known fix (16
- [RUN_NOW] nov_benchmark_fix_6E: execution window: benchmark-tracking funds transact at a known fix (16
- [RUN_NOW] nov_benchmark_fix_6J: execution window: benchmark-tracking funds transact at a known fix (16
- [RUN_NOW] nov_benchmark_fix_M2K: execution window: benchmark-tracking funds transact at a known fix (16
- [RUN_NOW] nov_benchmark_fix_MCL: execution window: benchmark-tracking funds transact at a known fix (16
- [RUN_NOW] nov_benchmark_fix_MES: execution window: benchmark-tracking funds transact at a known fix (16
- [RUN_NOW] nov_benchmark_fix_MGC: execution window: benchmark-tracking funds transact at a known fix (16

## Guardrail alerts
[P1] CLOSE-ONLY BIAS: only 15/194 forge_cycle scripts use 'volume' (8%). Databento volume vein under-worked (target: keep ACTIVE_PACKET_LANE).

## Highest-EV lanes NOW (family map)
1. Gamma/dealer-flow (feasible, chunked-loader pending) 2. Commodity term-structure carry (RUN_NOW) 3. Databento event-path/liquidity
4. Rates event-path/FOMC/auction (untested) 5. Source/novelty intake

## Latest verdicts (recent families)
- rates carry (daily per-contract) = CLEAN_KILL (scoped) | gamma = FEASIBLE | commodity carry = RUN_NOW | primitive sweep = exhausted (1680)

## Operator actions required
- gamma full pull \$11.54 (>threshold; approved 'pull gamma' — needs chunked loader first)
- (else: none — report-only lanes self-run)
