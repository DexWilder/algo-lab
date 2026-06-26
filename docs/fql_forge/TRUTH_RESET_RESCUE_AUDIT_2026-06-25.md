# TRUTH_RESET — Rescue Audit Ledger (2026-06-25)

> The clean inventory. Every major prior branch classified after the ORB `ema_slope` lookahead discovery.
> Report-only; capital gate fail-closed. Status vocabulary:
> **INVALIDATED** (proven artifact) · **VOID** (built on an invalidated foundation) · **CONTAMINATED→RETEST_REQUIRED**
> (used the leaky filter; needs clean point-in-time retest) · **CLEAN_BUT_WEAK_DIVERSIFIER** (real, causally clean, but
> fails edge-quality bars — not a primary) · **UNAUDITED→RETEST_REQUIRED** (not yet harnessed) · **CLEAN_KILL**
> (correctly killed earlier; no rescue needed) · **STILL_VALID** (process/doctrine; holds).

## A. ORB family and everything derived from it
| Branch | Status | Evidence |
|---|---|---|
| XB-ORB-EMA-Ladder (MNQ/MES/MGC/MCL/MYM) | **INVALIDATED** | R4 clean point-in-time Sharpe 0.27/−0.19/0.86/−0.84/−0.09; edge was ~entirely the `ema_slope` same-day-close lookahead |
| Small-diversifier package dossier | **VOID** | rationale was "improve the ORB book"; primary is invalidated |
| CV1/CV2 principled sizing | **VOID** | measured against ORB primary |
| CV3 / CV3-R forecast scaling | **VOID** | the "informative" EMA-slope-strength forecast was itself the lookahead |
| MGC vol_low refinement | **VOID** | an ORB refinement |

## B. Other strategies that use the `ema_slope` filter (same leak class)
| Branch | Status | Note |
|---|---|---|
| xb_stop_run_reversal_ema_ladder (MNQ) — **WIRED to paper probation 2026-06-15 (commit 52eb93c)** | **INVALIDATED — ACTIVE, DEACTIVATION RECOMMENDED** | uses `filter_name="ema_slope"`. Clean-vs-contaminated retest: **contaminated Sharpe 2.54 → clean 0.19** (retains 8% of net; maxDD −3051→−6959). Edge was ~entirely the lookahead. **This book has been executing PAPER probation signals for ~10 days on a contaminated validation.** It (and the ORB MNQ/MCL/MYM books, also wired + invalidated) should be DEACTIVATED — a registry/portfolio mutation that is OPERATOR-GATED (capital gate). Deactivation lever: status OUT of EVAL_STATES + controller_action=OFF. No capital was at risk (paper only). |

## A.5 ACTIVE CONTAMINATED BOOKS — deactivation recommended (operator-gated portfolio mutation)
All four currently-wired ORB/`ema_slope` probation books are INVALIDATED on clean point-in-time and are
executing PAPER signals on contaminated validations. Recommend deactivation (NOT executed — registry/portfolio
mutation is operator-gated):
- XB-ORB-EMA-Ladder **MNQ** (live-forward probation) — clean Sharpe 0.27
- XB-ORB-EMA-Ladder **MCL** (live-forward probation) — clean Sharpe −0.84
- XB-ORB-EMA-Ladder **MYM** (live-forward probation) — clean Sharpe −0.09
- xb_stop_run_reversal **MNQ** (Phase 1C wired 2026-06-15) — clean Sharpe 0.19
Paper only — no capital was ever at risk. The fail-closed capital gate is why this stayed paper.

## C. Independent premia — re-audited STANDALONE (causality-first)
| Branch | Status | Evidence |
|---|---|---|
| TSMOM (pool MNQ/MES/MGC, lb126) | **CLEAN_BUT_WEAK_DIVERSIFIER / NOT_PRIMARY** | CAUSAL_CLEAN + costs wired + rollover-clean, but Sharpe 0.52, maxDD −$21k, worst day −$5.9k, 65% net from 2024–25 |
| Vol-carry (contango→short-vol via SVXY) | **CLEAN_BUT_WEAK_DIVERSIFIER / NOT_PRIMARY** | CAUSAL_CLEAN + costs wired, but Sharpe 0.86, −18.3% worst day (crash tail), 59% top-2-year concentration, H2 decays 1.07→0.61 |

## D. Non-ORB probation books — causality-audited 2026-06-26 (harness)
| Branch | Causality verdict | Status |
|---|---|---|
| zn_afternoon_reversion (ZN) | **LOOKAHEAD_DETECTED** (7/8 splits leaking) | **CONTAMINATED → INVALIDATED pending clean retest; DEACTIVATION RECOMMENDED** (active probation) |
| fx_daily_trend (MGC) | **LOOKAHEAD_DETECTED** (8/8 splits leaking) | **CONTAMINATED → INVALIDATED pending clean retest; DEACTIVATION RECOMMENDED** (active probation) |
| vol_managed_equity (MES) | CAUSAL_CLEAN (51 signals, good coverage) | **PROVISIONALLY CLEAN** → next: standalone edge metrics + concentration/DSR |
| treasury_rolldown_carry (ZN/ZF/ZB) | CAUSAL_CLEAN but **LOW COVERAGE** (1 signal in slice) | harness ill-suited to monthly spread → **BESPOKE carry-lineage audit REQUIRED** before trust |
| nfp_level_breakout (MNQ) | CAUSAL_CLEAN but **LOW COVERAGE** (2 signals, sparse event) | **EVENT-WINDOW audit REQUIRED** on full data before trust |

**Systemic finding:** the same-day-aggregate→intraday lookahead (daily feature applied to same-day bars without a
shift) recurs across INDEPENDENTLY-written strategies — ORB, stop_run_reversal, zn_afternoon_reversion, fx_daily_trend
all leak. This is a recurring anti-pattern, not a single bug. The causality harness now catches it at the front door.

**Newly-found contaminated ACTIVE books (NOT in the 2026-06-26 approved-4 deactivation — flagged for approval):**
zn_afternoon_reversion (ZN, probation) and fx_daily_trend (MGC, probation). Plus XB-ORB-EMA-Ladder-MGC (idx 114,
`ema_slope`, shows EXECUTABLE) noted earlier. Recommend deactivating these 3 as well — awaiting explicit approval.

## E. Correctly killed earlier this session (no rescue needed)
| Branch | Status |
|---|---|
| XSMOM cross-asset momentum | **CLEAN_KILL** (MCL rollover artifact; clean-proxy retest collapsed it) |
| Crude/MCL relative-strength | **CLEAN_KILL** (100% MCL roll artifact) |

## F. Process / doctrine — STILL_VALID (and strengthened by this episode)
- Capital gate (fail-closed) — **held throughout; no capital ever touched the artifact.**
- Causality harness `research/causality_audit.py` — **new, CERTIFIED**; now mandatory preflight.
- No-lookahead regression test `research/test_no_lookahead_daily_filters.py` — **new**.
- Deflated-Sharpe/PBO gate, rollover-artifact doctrine, clean-before-rolling, concentration gates, learning-loop automation, tripwire process — all valid.

## Bottom line
**Clean baseline currently has NO primary workhorse.** Two clean-but-weak diversifiers (TSMOM, vol-carry) exist but
cannot carry a book. One paper-bound port (stop_run_reversal) is contaminated and suspended. Five non-ORB probation
books are unaudited. Normal WH discovery stays PAUSED until the inventory is complete. The next elite move is to
finish the audit, not to scramble for a new WH.
