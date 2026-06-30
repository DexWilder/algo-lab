# FORGE ALWAYS-ON MASTER QUEUE (2026-06-30)

> The machine's worklist. Forge = `queue → run → preflight → truth-gate → record → report → update-queue → commit →
> push → guardrails → next`. NOT "Claude picks next." Report-only; capital gate fail-closed. Runner:
> `research/forge_always_on_runner.py`; machine queue: `research/data/forge_run_queue.json`; guardrails enforce no-idle.

## P0 / P1 SYSTEM ISSUES
- **P0:** none open (git backlog 0 + persistent; guardrails firing; forge-loop un-halted + scheduled-proven 06-29 19:02).
- **P1:** close-only bias 12/186 (volume lane unfinished); 2 unrun-harness/unused-feed flags now guardrail-caught.

## RECONCILIATION OF PARKED INFRASTRUCTURE (classified)
| Item | Status | Note |
|---|---|---|
| `wp_b1_auction_harness.py` | **CLEAN_KILL** (RUN 06-30) | 799 auctions ZN/ZF/ZB×4win FOMC-clean → all KILL; superseded my P03 |
| `lever_b1_feed_validator.py` | ACTIVE (validator) | structure-only; fires on feed drop |
| `P03_auction` (mine) | **DUPLICATE** | superseded by wp_b1 |
| FEED_DEPENDENT_CANDIDATE_PACKETS: Treasury auctions | CLEAN_KILL | via wp_b1 |
| …: EIA crude surprise | DATA_BLOCKED | `eia_crude_stocks.csv` absent (operator download) |
| …: rates_multicontract (true roll-yield) | DATA_BLOCKED | feed absent |
| …: CPI surprise (consensus) | DATA_BLOCKED | `cpi_releases.csv` absent |
| …: OPEC calendar | DATA_BLOCKED | feed absent |
| FORGE_CANDIDATE_LEDGER_2026-06-17 items | SUPERSEDED/INVALIDATED | pre-truth-reset; ORB-family invalidated; others retest-required |
| P1P2_RATES_CARRY_BOARD (yield-curve proxy) | INVALIDATED | FRED yield-curve branch dead (per STAGING_MANIFEST) |
| month-end-rates re-grade | DATA_BLOCKED | needs `rates_multicontract.csv` (front+deferred) |
| `treasury_auctions.csv` / `vix.csv` (local) | ACTIVE (now used) | were re-fetched needlessly; guardrail now flags re-fetch class |

## RUNNABLE REPORT-ONLY TESTS (RUN_NOW — the runner consumes these)
1. `forge_search_engine.py` — continuous primitive sweep (~1680 combos, DSR-at-true-N) — **RUNNING (background)**.
2. opening-minutes Databento volume packet — `forge_cycle_2026-06-30_DB_P17_opening_minutes.py` — RUN_NOW.
3. volume-imbalance/aggressor-proxy packet — `forge_cycle_2026-06-30_DB_P18_volume_imbalance.py` — RUN_NOW.
4. crypto feed packets (deribit perp + DVOL BTC/ETH, okx swap, funding) — RUN_NOW (unused-feed lane).

## UNRUN HARNESSES — none (wp_b1 run; lever_b1 is a validator).
## UNUSED FEEDS — `okx_BTC_USD_SWAP.csv`, `deribit_DVOL_ETH.csv` (+ macro feeds underused) → crypto/macro packet lane.
## PARKED CANDIDATE PACKETS — reconciled above (all DATA_BLOCKED / SUPERSEDED / INVALIDATED / CLEAN_KILL).
## DATABENTO-NATIVE QUEUE — opening-minutes, volume-imbalance, cross-asset-volume, Treasury-1m event path.
## SOURCE-INTAKE PACKETS — from-knowledge only (no audio ingest); regime-conditioning using macro feeds is the real lane.
## FORCED-FLOW / EVENT QUEUE — auctions CLEAN_KILL; FOMC/pre-FOMC (free, NOT_STARTED); EIA/OPEC (DATA_BLOCKED).
## RESCUE / RETEST QUEUE — treasury_rolldown (NEEDS_BESPOKE_HARNESS); non-naive COT (optional, pre-register).
## PAID-DATA QUEUE — gamma/GEX, true-VIX-curve, trades/L2 (BLOCKED_BY_PAID_DECISION; memo provisional).
## BLOCKED-BY-FEED QUEUE — EIA, rates_multicontract, CPI-surprise, OPEC (operator download).
## COMPLETED CLEAN KILLS — ORB×5+stop_run+zn_afternoon+fx_daily (INVALIDATED); nfp/vol_managed/P03/COT/P14/P15/P16/basket (KILL); auction (wp_b1 KILL).
## CURRENT TRIAL N — 68+ (growing via search engine + runner; auto via forge_trial_ledger).

## NEXT 25 ACTIONS (runner order A→F)
1 search-engine sweep (running) · 2 opening-minutes volume · 3 volume-imbalance · 4 cross-asset-volume · 5 Treasury-1m event path ·
6 participation-cost-lane on any survivor · 7 regime-conditioning: ORB-clean × vix-regime · 8 × credit_oas-regime · 9 × dollar_index ·
10 × DVOL-regime · 11 crypto: deribit perp momentum · 12 crypto: DVOL carry · 13 okx funding-rate carry · 14 copper_gold risk-on/off filter ·
15 real_rates/inflation regime overlay · 16 reconcile FORGE_CANDIDATE_LEDGER items individually · 17 treasury_rolldown bespoke harness ·
18 free-data status memo (after 2-5) · 19 finalize paid-data memo · 20 non-naive COT (pre-register) · 21 FOMC/pre-FOMC free test ·
22 retire phase1c-verify (operator nod) · 23 apply Claw harvest config (operator) · 24 EIA/OPEC (blocked-feed) · 25 gamma/GEX (paid decision).


## SWEEP RESULT (DEFINITIVE, 2026-06-30) — primitive space EXHAUSTED
forge_search_engine.py completed: **1680 combos (20 entry × 12 filter × 6 exit × 7 asset), 1458 with ≥150 trades,
ZERO concentration-clean survivors, 0 screen-survivors.** No combo passes Sharpe≥1 + maxyr<40% + top3<30% + median≥0
+ H1,H2>0. Top: orb|ema_slope_vol_low|profit_ladder|MGC Sh=1.3 but maxyr74%/top3 48%. **CONCLUSION: the crossbred
price-primitive space contains no robust point-in-time edge at our cost/data tier.** Trial-N=1763 (primitive_sweep lane).
**PIVOT (price-primitive sweep is CLOSED):** the edge — if any on free data — is not in price/volume primitive combos.
Remaining honest levers: (a) genuinely-different mechanism classes with REAL feeds (forced-flow event-path, relative-value,
options/vol-surface) — most need data we lack; (b) the paid-data tier (gamma/VIX-curve/L2). Stop sweeping price primitives.
Database volume = cost/liquidity/regime only (all directional/confirmation uses KILLED). Queue pivots to forced-flow/event/
data-tier; no more naive single-feature price packets.
## LANGUAGE CORRECTION (2026-06-30): scope is PRIMITIVE space, not 'free data'
EXHAUSTED = crossbred price/volume/OHLC primitive expressions (+ the killed mechanism classes). NOT EXHAUSTED = structural/event/feed/source/paid stack. FOMC-drift reconciled=KILL (existing screen, not duplicated). Strategy discovery = ZERO validated primaries. Forge does NOT idle: LANE 1 operator handoff (FORGE_OPERATOR_DATA_HANDOFF_2026-06-30.md) + LANE 2 feasible-now event-path/RV packets (FREE_DATA_STATUS_AND_SOURCE_PACKETS_2026-06-30.md: FX-fix, settlement-close, rates-fly-RV, ES-NQ-lead-lag).

## P23 RATES-FLY: tradeable confirmation = CLEAN_KILL (2026-06-30)
P23 FRED 2s5s10s yield-curvature MR (annSh 1.63, research-grade) did NOT survive tradeable confirmation. P23-F DV01
futures fly (ZF/ZN/ZB=5s10s30s, costed, roll-winsorized): Sh=-1.14, DSR 0.0 global-N=1766 & family-N=7 -> CLEAN_KILL.
Lessons: (1) yield-space edge != futures-space edge (paper-to-tradeable gap is huge, as warned); (2) instrument
mismatch (signal 2s5s10s; futures 5s10s30s, no ZT 2y); (3) continuous .c.0 roll artifacts. The PROPER tradeable test
of the 2s5s10s signal is DATA_BLOCKED -> needs ZT 2y + rates_multicontract.csv (Lane-1 #1). No validated primary.
Queue moves on (Lane-2 feasible-now: FX-fix, settlement-close, ES-NQ-lead-lag).
