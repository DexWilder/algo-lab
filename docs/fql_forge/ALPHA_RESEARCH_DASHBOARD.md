# ALPHA RESEARCH DASHBOARD (auto-generated 2026-07-01 17:27 UTC)
> `python3 research/forge_dashboard.py` regenerates this. Single canonical state view.

## HEADLINE
- **Validated primaries: 0** (highest ladder rung: **SCREEN_PASS**; capital gate FAIL-CLOSED, PAPER_APPROVED+ operator-only).
- Guardrails: **clean/P1** | Self-audit: **SELF_AUDIT_CLEAN** (facets=12 PASS=10 STALE=0 BROKEN=0 DESIGNED-not-built=2) | Git backlog: **0** | Global trial-N: **1783**
- **Roadmap:** end Phase 0 → entering Phase 1 (foundation hardening: data-tier gate, learning-loop closure, infra freeze, 1m/volume harness). Doctrine: `docs/fql_forge/FOUNDATION_DOCTRINE_AND_ELITE_ROADMAP_2026-07-01.md`

## Throughput (computed live)
- Tests logged today: **17** | total kills: 6 | screen-passes: 2
- Novelty packets: **24** stored (24 today) of 108 template×instrument space
- Families: **13 active** / 21 | coverage 54% (tested exprs / total exprs)
- Candidate ladder: SCREEN_PASS=1

## Inbound capture (organizational memory — nothing floats)
- Items: **29** | NEW: 0 | P0/P1: 7/16 | source packets today: 0
- Untriaged directives: 0 | mistakes w/o control: **3** ['INB-20260625-002', 'INB-20260701-010', 'INB-20260701-011'] | unused feeds: 0
- QUEUED-missing-from-queue: 0 | source notes unresolved: 0 | oldest untriaged: 0d
- Ledger: `docs/fql_forge/INBOUND_RESEARCH_LEDGER.md` (capture: `python3 research/capture_inbound.py`)

## Trial-N by lane (family diagnostics)
- primitive_sweep: 1679
- positioning: 48
- databento_volume: 14
- commodity_carry: 10
- exploratory: 9
- forced_flow: 7
- crypto_carry: 4
- carry: 4
- macro_regime: 3
- curve_rv: 3
- portfolio: 2

## Queue depth
- RUN_NOW: 3 | total queue items: 37
- [ACTIVE_PACKET_LANE] gamma_chunked_loader_then_regime: chunked OI loader -> approx-GEX -> predeclared GEX-regime test (feasib
- [DONE] gc_detrended_carry_zscore: refined commodity TS expr (naive carry-sign KILLed 2026-07-01); de-tre
- [DONE] clgc_spread_momentum: refined commodity TS expr (naive carry-sign KILLed 2026-07-01); de-tre
- [DONE] clgc_spread_meanreversion: refined commodity TS expr (naive carry-sign KILLed 2026-07-01); de-tre
- [DONE] roll_window_pressure_contango: refined commodity TS expr (naive carry-sign KILLed 2026-07-01); de-tre
- [BACKLOG] nov_benchmark_fix_6B: execution window: benchmark-tracking funds transact at a known fix (16
- [BACKLOG] nov_benchmark_fix_6E: execution window: benchmark-tracking funds transact at a known fix (16
- [BACKLOG] nov_benchmark_fix_6J: execution window: benchmark-tracking funds transact at a known fix (16
- [BACKLOG] nov_benchmark_fix_M2K: execution window: benchmark-tracking funds transact at a known fix (16
- [BACKLOG] nov_benchmark_fix_MCL: execution window: benchmark-tracking funds transact at a known fix (16
- [BACKLOG] nov_benchmark_fix_MES: execution window: benchmark-tracking funds transact at a known fix (16
- [BACKLOG] nov_benchmark_fix_MGC: execution window: benchmark-tracking funds transact at a known fix (16

## Guardrail alerts
[P1] CLOSE-ONLY BIAS: only 15/194 forge_cycle scripts use 'volume' (8%). Databento volume vein under-worked (target: keep ACTIVE_PACKET_LANE).
[P1] INBOUND: 3 mistake/validation item(s) with NO durable control: ['INB-20260625-002', 'INB-20260701-010', 'INB-20260701-011'] (no control = not fixed)

## Highest-EV lanes NOW (family map)
1. Gamma/dealer-flow (feasible, chunked-loader pending) 2. Commodity term-structure carry (RUN_NOW) 3. Databento event-path/liquidity
4. Rates event-path/FOMC/auction (untested) 5. Source/novelty intake

## Latest verdicts (recent families)
- rates carry (daily per-contract) = CLEAN_KILL (scoped) | gamma = FEASIBLE | commodity carry = RUN_NOW | primitive sweep = exhausted (1680)

## Operator actions required
- gamma full pull \$11.54 (>threshold; approved 'pull gamma' — needs chunked loader first)
- (else: none — report-only lanes self-run)
