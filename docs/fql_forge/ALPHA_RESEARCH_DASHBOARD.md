# ALPHA RESEARCH DASHBOARD (auto-generated 2026-07-01 16:36 UTC)
> `python3 research/forge_dashboard.py` regenerates this. Single canonical state view.

## HEADLINE
- **Validated primaries: 0** (nothing above SCREEN_PASS). Capital gate: FAIL-CLOSED.
- Guardrails: **clean/P1** | Git backlog: **0** | Test scripts run: 197 | Global trial-N: **1773**

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
- portfolio: 2

## Queue depth
- RUN_NOW: 1 | total queue items: 2
- [RUN_NOW] commodity_carry_CLGC: family-aware: CL carry, GC carry, xsec, front/deferred spread mom+MR, 
- [ACTIVE_PACKET_LANE] gamma_chunked_loader_then_regime: chunked OI loader -> approx-GEX -> predeclared GEX-regime test (feasib

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
