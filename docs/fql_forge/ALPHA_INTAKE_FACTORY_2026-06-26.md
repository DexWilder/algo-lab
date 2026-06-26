# ALPHA_INTAKE_FACTORY (2026-06-26) — external mechanism funnel under TRUTH_RESET

> Flood the top of the funnel with outside mechanisms; filter brutally. Every source must produce mechanism
> packets or be discarded. Report-only; capital gate fail-closed; no WH/validated/primary/dossier/sizing language.
> Goal: **100 packets → 20 clean cheap tests → 3 deep candidates → maybe 1 survives.**

## ⚠️ Anti-false-discovery discipline (the load-bearing rule)
A big funnel that keeps the best Sharpe is a p-hacking machine. Therefore:
1. **Pre-register** each packet's directional PREDICTION + KILL criterion BEFORE any test (fields below).
2. **Trial ledger** (§8): every cheap test counts — survivors AND shelved — toward the multiple-testing N.
3. A survivor must clear **Deflated-Sharpe / PBO at the FULL trial N** (`research/forge_deflated_sharpe.py`), not raw Sharpe.
4. Mechanism must be **economically falsifiable**: if the forced participant's flow doesn't move price as predicted, it's dead.

## Mechanism strength tiers (rank by this, NOT source popularity)
**T1 forced-structural** (price-insensitive counterparty: roll, rebalance, auction, settlement, issuance) — overweight ~60%.
**T2 risk-premium** (carry/trend/vol/seasonality — crowded, published, decaying → diversifier-grade at best).
**T3 behavioral** (sentiment, positioning extremes).
**T4 technical** (pure price patterns — lowest prior; ORB lived here and was an artifact).

## Packet schema (per source item)
`id · source(+provenance: from-knowledge|web-verified) · tier · mechanism · forced participant/behavioral rationale ·
instrument · horizon · required data · DATA_FEASIBLE|DATA_BLOCKED · point-in-time risks · PRE-REGISTERED prediction ·
cheap clean test · kill criteria · priority · truth-gate status · verdict`

## Harness adapters (correct gate per shape — wrong harness = false result)
- intraday-5m → `causality_audit.audit_signal_causality` (exists)
- daily → date-aligned future-perturbation (built ad-hoc for vol_managed; TODO fold in)
- event-window → release-timestamp-known-ahead vs value-known-only-after leakage check (TODO)
- cross-asset → per-leg causality + roll-artifact per leg (TODO)
- calendar/forced-flow → deterministic-date, no value-lookahead (TODO)

---
## §1 Source queue
Books: Harris (microstructure/forced flow), Carver (risk/carry/trend construction), Chan (MR workflow), Kaufman
(idea catalog), Natenberg/Sinclair/Gatheral (vol/skew/term), Ilmanen (cross-asset premia), López de Prado (leakage/CV/DSR).
Papers: TSMOM/CTA (Baltas-Kosowski), multi-asset seasonality (Baltas), spatio-temporal momentum, VRP, microstructure (Lehalle).
Practitioner (knowledge-extracted, NOT audio-ingested): Flirting with Models, Better System Trader, Top Traders Unplugged, Chat With Traders; Carver/AQR/Man-AHL/Newfound/ReSolve interviews.
Forums (leads only): r/algotrading, r/quant, r/futuresTrading, EliteTrader, QuantConnect, futures.io.
Official/calendars (T1 forced-flow): CME specs/roll/settlement, Treasury auctions, Fed/SOMA, EIA, BLS, CFTC COT, index rebalance, OPEX/gamma.

## §2 Extracted mechanism packets (first batch)
> Provenance = from-knowledge unless marked web-verified. DATA stamp drives effort. Forced-flow weighted.

**P01 · T1 · Futures calendar-roll pressure** — longs roll front→back over the roll window (predictable, price-insensitive). MNQ/MES/MGC/MCL/ZN. Horizon: roll-window days. Data: per-contract (continuous has roll dates) — DATA_FEASIBLE (but roll-artifact-prone; needs per-contract not stitched). PIT risk: stitched continuous fakes it. Prediction: front-month underperforms back over roll window. Cheap test: calendar-day return around roll dates per asset. Kill: no consistent sign / dies after cost. Priority: HIGH.

**P02 · T1 · Equity-index month-end duration/rebalance flow** — pensions/index funds buy at month-end (cash inflows, duration extension). MES/MNQ. Horizon: last 1–3 + first 1 session. Data: index futures + calendar — DATA_FEASIBLE. PIT risk: none (deterministic dates). Prediction: positive drift last N sessions of month. Cheap test: month-end window returns vs rest. Kill: insignificant / cost-fragile. Priority: HIGH.

**P03 · T1 · Treasury auction concession + post-auction reversal** — dealers demand price concession into 10y/30y auctions, reverse after. ZN/ZB. Horizon: T-2 to T+2 around auction. Data: Treasury auction calendar (web-verify) + ZN/ZB — DATA_FEASIBLE. PIT risk: auction dates known ahead ✓; results known only after ✓ (event adapter). Prediction: yields cheapen into auction (futures down), richen after. Cheap test: ZN return T-2→T0 vs T0→T+2. Kill: no reversal / cost. Priority: HIGH.

**P04 · T1 · Month-end Treasury index duration extension** — bond index funds extend duration last day of month. ZN/ZF/ZB. Data: calendar + rates futures — DATA_FEASIBLE. Prediction: ZN positive drift into month-end. Cheap test: month-end window. Kill: insignificant. Priority: MED-HIGH.

**P05 · T1 · FX benchmark-fix (London 4pm WMR) window pressure** — benchmark-tracking flow concentrates at the fix. 6E/6J/6B (have 5m). Horizon: intraday fix window. Data: intraday FX — DATA_FEASIBLE. PIT risk: intraday, use only pre-fix data. Prediction: directional drift into fix tied to prior trend. Cheap test: return in fix window conditioned on morning move. Kill: no edge after cost. Priority: MED.

**P06 · T1 · EIA crude inventory surprise drift** — Wed 10:30 ET inventory release forces positioning. CL/MCL. Horizon: event day. Data: EIA calendar (web-verify) + MCL (roll-artifact caution) — DATA_FEASIBLE. PIT risk: release VALUE known only after 10:30 (event adapter — don't use post-release in pre-release signal). Prediction: post-release drift in surprise direction. Cheap test: 10:35→close return by inventory-surprise sign (needs EIA data). Kill: no drift / MCL-artifact. Priority: MED (data-tier: EIA feed).

**P07 · T1 · Index OPEX / quad-witching gamma pin** — dealer hedging pins price near max-gamma into expiry. MES/MNQ. Data: options OI/gamma — **DATA_BLOCKED (free feeds)** → feed-acquisition queue. Priority: HIGH-if-data.

**P08 · T1 · VIX expiry (VRO special settlement)** — known settlement flow on VIX expiry Wed. VIX futures — **DATA_BLOCKED (true VX curve)** → feed-acq. Priority: MED-if-data.

**P09 · T2 · Cross-asset carry combo (rates/equity/gold/FX)** — Carver/Ilmanen: carry premium diversified across asset classes. ZN/MES/MGC/6E. Data: futures (have) + carry proxy — DATA_FEASIBLE. PIT risk: carry must use t-1 curve/roll. Prediction: high-carry assets outperform low. Cheap test: monthly carry-ranked long/short. Kill: crowded/decayed/cost. Priority: MED (diversifier-grade).

**P10 · T2 · Carry+trend combination overlay** — Carver: combine carry & trend forecasts (low correlation) for better risk-adjusted than either. Multi-asset futures. Data: have. Prediction: combined Sharpe > each alone OOS. Cheap test: blend TSMOM(weak) + carry, compare. Kill: no diversification benefit. Priority: MED.

**P11 · T2 · Same-calendar-month seasonality (cost-first)** — Baltas multi-asset seasonality. Commodities/index. Data: have. PIT risk: in-sample seasonal fit = overfit; needs OOS + cost. Prediction: same-month historical sign persists OOS. Cheap test: month-of-year sign, strict OOS + cost. Kill: dies OOS or after cost (paper flags turnover). Priority: LOW-MED (overfit-prone).

**P12 · T1 · Overnight-session forced flow / globex gap** — overnight inventory imbalance resolves at cash open. MES/MNQ (have 5m). Data: DATA_FEASIBLE. PIT risk: use only overnight data for open prediction (no same-day-close leak — the lesson). Prediction: overnight range/imbalance predicts first-hour direction. Cheap test: overnight feature → first-hour return, causal. Kill: no edge / lookahead. Priority: MED.

## §3 Required feeds / data-acquisition queue (DATA_BLOCKED packets)
- Options OI / dealer gamma surface (P07) — for gamma-pin / OPEX.
- True VIX futures curve VX1/VX2 (P08, + vol-carry upgrade).
- EIA inventory actual+forecast series (P06) — for surprise sign.
- CFTC COT positioning (for COT-extreme reversal packet, T3).
- Treasury auction results detail (P03 enrichment).

## §4 Build priority (next loop)
1. Finish **treasury bespoke carry harness** (in-flight; validates P03/P04/P09 lane infra too).
2. Build **calendar/forced-flow adapter** → test P01, P02, P04 (all DATA_FEASIBLE, deterministic dates, T1).
3. Build **event adapter** → P03, P06.
4. Then T2 diversifiers P09/P10 only if a T1 survives (need a book to diversify).

## §5 Truth-gate status
- P02, P04: causality CLEAN BY CONSTRUCTION (deterministic calendar dates, no value-lookahead). Cost applied.
- **P04 ZN** is the lead — but SCREEN_PASS only; must clear DSR-at-full-N + window-robustness + decay check before candidate language.

## §6 Retest/rescue links — see TRUTH_RESET_RESCUE_AUDIT_2026-06-25.md (false-kill review pending)

## §7 Verdicts
- **P02 equity month-end (MES/MNQ): KILL** — premise false; out-of-window mean > in-window mean.
- **P04 ZN month-end duration extension: SCREEN_PASS_RETAINED** (deepened 2026-06-26).
  **METRIC CORRECTION (own it):** the first-pass "Sharpe 2.38" was computed on ACTIVE DAYS ONLY (capital idle ~85% of
  the month inflates it). Proper full-period strategy Sharpe (flat outside window) = **0.64**. The 2.38 was misleading.
  **Mechanism is REAL & clean** — passes every robustness check: window-family coherent (last_1→5: 0.13/0.34/0.64/0.53/0.42,
  builds toward month-end, not a single-window miracle); **cross-tenor confirmed** (ZF 0.81, ZB 0.35 — all positive,
  coherent duration-extension curve story); survives quarter-end roll-month exclusion (0.49); survives dropping best
  year 2020 (0.51); survives 3× slippage (0.32); recent years persistent (2022-26 all positive); execution knowable.
  **BUT FAILS the mandatory DSR-at-N gate: DSR=0.8627 at N=10 (< 0.95, below even 0.90 marginal).** Standalone edge too
  weak to clear multiple-testing significance. → **SCREEN_PASS_RETAINED, NOT a candidate.** Class = clean-but-weak
  forced-flow, same tier as TSMOM/vol-carry. Possible future role: a leg in a forced-flow BASKET (curve ZN+ZF + other
  T1 signals) — a portfolio question for LATER, not now. Not WH/primary/candidate.

## §8 Trial ledger (multiple-testing N) — DSR must use this N
| # | packet | test date | raw Sharpe | counted in N | verdict |
|---|---|---|---|---|---|
| 1 | P02 equity month-end MES | 2026-06-26 | 0.25 | yes | KILL |
| 2 | P02 equity month-end MNQ | 2026-06-26 | 0.44 | yes | KILL/weak |
| 3 | P04 ZN month-end last_3 (canonical) | 2026-06-26 | 0.64* | yes | SCREEN_PASS_RETAINED (*corrected from 2.38 active-days-only artifact) |
| 4-7 | P04 ZN window family last_{1,2,4,5} | 2026-06-26 | 0.13/0.34/0.53/0.42 | yes | robustness configs |
| 8-9 | P04 cross-tenor ZF/ZB last_3 | 2026-06-26 | 0.81/0.35 | yes | confirm direction |
| 10 | P04 DSR-at-N=10 | 2026-06-26 | DSR=0.86 | — | FAILS gate (<0.95) |
| running N = 10 | | | | | P04 retained-not-promoted |
