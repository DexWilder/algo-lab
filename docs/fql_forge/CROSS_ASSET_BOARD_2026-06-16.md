# Cross-Asset Confirmation/Divergence — First Board — 2026-06-16

> Track 1 frontier move after single-series exhaustion (112 candidates). Report-only. **No-lookahead is first-class** (`research/cross_asset_harness.py`): every confirming state is attached via `merge_asof(direction='backward', allow_exact_matches=False)` → matched state date is strictly < trade date; `prove_no_lookahead()` asserts 0 violations. Evidence: `forge_cycle_2026-06-16r_cross_asset.json`. No mutation/activation.

## A. No-lookahead proof
0 violations across both state families on both gold mechanisms; min lag 1 day, median lag 1 day. The harness does not leak future cross-asset info.

## B. Instrument overlap (daily bars)
Full history (2019-06-30→2026-06-15): MGC, MES, MNQ, ZN, ZF. Shorter: MCL (2021-07+), **MYM/6E/6J/6B (2024-02-29+)** — the FX basket and MYM are only ~2.4 yrs, which limits dollar-state and any MYM-inclusive mechanism.

## C/D. Board + verdicts

### MODE 1 — cross-asset state as CONFIRMATION on the gold survivors (overfit-guarded)
| Structure | Filter (strictly-prior state) | n (retain) | PF (vs base) | Verdict |
|---|---|---|---|---|
| MGC-ORB (base PF 1.495) | **RATES_up** (ZN rising/easing) | 286 (43.6%) | **1.672** | **CONFIRMATION_EDGE (lead)** |
| MGC-ORB | RATES_dn | 354 (54%) | 1.314 | no edge |
| MGC-ORB | USD_up | 97 (14.8%) | 2.122 | **OVERFIT_RISK** (PF up but cuts 85% of trades) |
| MGC-prior_day_break (base 1.341) | **RATES_dn** (ZN falling) | 212 (52.3%) | **1.939** | **CONFIRMATION_EDGE (lead)** |
| MGC-prior_day_break | RATES_up | 182 (44.9%) | 0.873 | no edge (loses) |
| MGC-prior_day_break | USD_up | 64 (15.8%) | 1.854 | **OVERFIT_RISK** |

**Finding:** the two gold mechanisms are conditioned by **OPPOSITE rates regimes** — ORB likes rates-up/easing, prior_day_break likes rates-down. That is a real, no-lookahead, decent-retention (44–52%) cross-asset signal, and it *explains the gold sleeve's low internal correlation* (+0.244): the members naturally hedge across rates regimes. The USD filters were correctly **rejected as overfit** (PF jumps only by cutting ~85% of trades) — the guard worked, exactly as intended (no rescuing edges by slashing n).

**Status: LEADS, not finished.** In-sample partitions. Before trusting: boundary-test the rates-state threshold (lookback/threshold grid, as done for ZN-FOMC) and confirm the opposite-regime complementarity holds out-of-sample. This *refines/conditions the gold sleeve* — it does not create a new engine.

### MODE 2 — STANDALONE index dispersion (laggard reversion), a trade source
- 2024+ triple (MNQ/MES/MYM): PF 1.311, n=714, 238/yr, corr-to-MNQ −0.044 → *looked* like the first true-daily decorrelated candidate.
- **Long-history check (MNQ/MES, 2019–2026, n=2166): PF 1.148 — BELOW the 1.2 gate**, H1/H2 1.041/1.247, with a **−$7,050 year in 2022**. The 1.311 was a flattering 2024+ (post-2022 all-up) regime artifact.
- **Corrected verdict: WATCH / regime-sensitive, sub-gate on full history.** Also equity-beta by construction (not a new driver). NOT a survivor. (Note: the screen script's auto-label "FORWARD_CLOCK_CREDIBLE" was overturned by the long-history test — honest correction recorded.)

## E. Archive (so we don't loop)
- USD-state confirmation on gold → OVERFIT_RISK (tiny-n). Do not pursue as a standalone filter.
- Index-dispersion laggard reversion → marginal/regime-sensitive (sub-gate long history). Parked as WATCH; revisit only with a proper engine-fidelity backtest + a behavioral reason it should beat 1.2 out-of-regime.
- RATES_dn on MGC-ORB / RATES_up on MGC-prior_day_break → no edge.

## Net
- **No new true-daily, driver-diverse, decorrelated engine yet.** True daily WH2 stays open.
- **Best durable output:** cross-asset **rates-state conditioning of the gold sleeve** (opposite-regime complementarity) — a real refinement lead pending robustness follow-up.
- The no-lookahead harness is reusable for all future cross-asset work.

## Boundaries
Report-only. No activation/wiring/registry/portfolio mutation. Cross-asset filters were NOT used to rescue dead single-series entries (only applied to live structures + tested standalone), and overfit (tiny-n PF lifts) was flagged, not promoted.
