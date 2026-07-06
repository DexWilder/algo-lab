# ALPHA RESEARCH DASHBOARD (auto-generated 2026-07-06 17:26 UTC)
> `python3 research/forge_dashboard.py` regenerates this. Single canonical state view.

## HEADLINE
- **Validated primaries: 0** (highest ladder rung: **SCREEN_PASS**; capital gate FAIL-CLOSED, PAPER_APPROVED+ operator-only).
- Guardrails: **clean/P1** | Self-audit: **SELF_AUDIT_CLEAN** (facets=12 PASS=12 STALE=0 BROKEN=0 DESIGNED-not-built=0) | Git backlog: **0** | Global trial-N: **1841**
- **Mission:** MNQ/MES/MYM index workhorse (WH1). RUN_NOW mission-weighting: 18/23 WH1-aligned ({'DIVERSIFIER': 5, 'INDEX_REGIME_INPUT': 15, 'INDEX_DIRECT': 3})
- **Search posture:** the NAIVE direct-index price/volume surface (gap/fade/trend/MR/OR) is picked-over UNDER TESTED EXPRESSIONS. WH1 direct-index remains LIVE via GEX/event/regime/source-CONDITIONED mechanisms + MYM (1m now pulled). Structural surfaces (GEX/dealer-flow, event-surprise, forced-flow) are EARLY — prove over 20–50 cycles, not solved.

## Throughput (computed live)
- Tests logged today: **16** | total kills: 6 | screen-passes: 2
- Novelty packets: **38** stored (0 today) of 108 template×instrument space
- Families: **12 active** / 21 | coverage 58% (tested exprs / total exprs)
- Candidate ladder: SCREEN_PASS=1

## Inbound capture (organizational memory — nothing floats)
- Items: **53** | NEW: 0 | P0/P1: 11/28 | source packets today: 6
- Untriaged directives: 0 | mistakes w/o control: **2** ['INB-20260701-010', 'INB-20260701-011'] | unused feeds: 0
- QUEUED-missing-from-queue: 0 | source notes unresolved: 1 | oldest untriaged: 0d
- Ledger: `docs/fql_forge/INBOUND_RESEARCH_LEDGER.md` (capture: `python3 research/capture_inbound.py`)

## Trial-N by lane (family diagnostics)
- primitive_sweep: 1679
- databento_volume: 65
- positioning: 48
- exploratory: 15
- commodity_carry: 10
- forced_flow: 7
- macro_regime: 4
- crypto_carry: 4
- carry: 4
- curve_rv: 3
- portfolio: 2

## Queue depth
- RUN_NOW: 23 | total queue items: 75
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

## Data-utilization map (13/20 ACTIVE_IN_TESTS — no asset floats)
- [T2] Databento 1m OHLCV (11 instr) — ACTIVE_IN_TESTS (microstructure)
- [T3] Databento 1m + VOLUME (11 instr, ~7.9M bars) — ACTIVE_IN_TESTS (microstructure)
- [T2] 5m/downsampled processed (13) — ACTIVE_IN_TESTS (legacy)
- [T4] Per-contract rates ZT/ZF/ZN/ZB — ACTIVE_IN_TESTS (curve_rv)
- [T4] Per-contract CL/GC — ACTIVE_IN_TESTS (carry_commodity)
- [T6] Gamma/options/OI (ES.OPT) — NEEDS_LOADER (gamma_dealer)
- [T5] COT positioning — ACTIVE_IN_TESTS (positioning)
- [T5] CPI levels — QUEUED_FOR_PACKET (macro_event_drift)
- [T5] EIA stocks — CERTIFIED_BLOCKED (inventory_eia)
- [T5] Treasury auctions — ACTIVE_IN_TESTS (auction_issuance)
- [T5] FOMC/NFP calendars — ACTIVE_IN_TESTS (macro_event_drift)
- [T5] Policy rates — ACTIVE_IN_TESTS (carry_rates)
- [T5] Treasury yield curve — ACTIVE_IN_TESTS (carry_rates)
- [T5] VIX — ACTIVE_IN_TESTS (vol_risk_premium)
- [T6] DVOL BTC/ETH — ACTIVE_IN_TESTS (vol_risk_premium)
- [T5] Deribit/OKX crypto perp — ARCHIVED_LOW_VALUE (crypto_funding)
- [T5] Credit OAS — QUEUED_FOR_PACKET (regime_filters)
- [T5] Copper/gold ratio — QUEUED_FOR_PACKET (regime_filters)
- [T5] Dollar index / real rates / inflation exp — VALIDATION_PENDING (macro_regime)
- [T5] TreasuryDirect auction bid-to-cover (609 auctions) — ACTIVE_IN_TESTS (auction_issuance)
- status mix: {'ACTIVE_IN_TESTS': 13, 'NEEDS_LOADER': 1, 'QUEUED_FOR_PACKET': 3, 'CERTIFIED_BLOCKED': 1, 'ARCHIVED_LOW_VALUE': 1, 'VALIDATION_PENDING': 1}

## Roadmap (operational) — Phase 1: foundation hardening
- **Exit criteria:** data-tier gate live ✅ · learning-state updater live ✅ · close-only kills rescoped ✅ · 1m+volume harness running ✅ (OR batch=kill) · data-util dashboard ✅ · self-audit artifact ✅ | REMAINING: ≥1 close-only family re-scoped edge found OR cleanly killed at T3 (in progress); self-audit clean streak ≥5
- **Blockers:** gamma T6 needs chunked-OI loader (+$11.54 gate); intraday 1m-path MR + settlement/lead-lag T3 packets not yet run
- **Data-util gaps (richer tier unused):** 9 families — ['vol_risk_premium', 'inventory_eia', 'macro_event_drift', 'monthend_settlement', 'expiry_opex', 'intraday_micro', 'xasset_leadlag', 'fx_fixing_ratediv']
- **Next-25 (from learning_state):**
  1. TEST vol_risk_premium at richer tier T6 (T5 done)
  2. TEST inventory_eia at richer tier T5 (none done)
  3. TEST macro_event_drift at richer tier T3 (T1 done)
  4. TEST monthend_settlement at richer tier T3 (T1 done)
  5. TEST expiry_opex at richer tier T6 (none done)
  6. TEST xasset_leadlag at richer tier T3 (T2 done)
  7. TEST fx_fixing_ratediv at richer tier T3 (none done)
  8. QUEUE deepen_spreadMR_GC_execution: Lane G: real 2-leg calendar-spread execution model (deferred
  9. QUEUE deepen_spreadMR_GC_searchN: Lane G: pin honest search-N for spreadMR_GC DSR (credible N<
  10. QUEUE deepen_spreadMR_GC_robustness: Lane G: param robustness spreadMR_GC (z 1.0/2.0, lookback 12
  11. QUEUE gex_expiry_0dte_pin: T6: expiry/0DTE gamma-pin — target last 1-2 days to expiry (
  12. QUEUE gex_0dte_pin_real: 0DTE/expiry-week pin on weekly OI (EW1-4/E1A/E3C) — the mech

## Guardrail alerts
[P1] CLOSE-ONLY BIAS: only 15/194 forge_cycle scripts use 'volume' (8%). Databento volume vein under-worked (target: keep ACTIVE_PACKET_LANE).
[P1] INBOUND: 2 mistake/validation item(s) with NO durable control: ['INB-20260701-010', 'INB-20260701-011'] (no control = not fixed)

## Highest-EV lanes NOW (family map)
1. Gamma/dealer-flow (feasible, chunked-loader pending) 2. Commodity term-structure carry (RUN_NOW) 3. Databento event-path/liquidity
4. Rates event-path/FOMC/auction (untested) 5. Source/novelty intake

## Latest verdicts (recent families)
- rates carry (daily per-contract) = CLEAN_KILL (scoped) | gamma = FEASIBLE | commodity carry = RUN_NOW | primitive sweep = exhausted (1680)

## Operator actions required
- gamma full pull \$11.54 (>threshold; approved 'pull gamma' — needs chunked loader first)
- (else: none — report-only lanes self-run)
