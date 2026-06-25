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
| xb_stop_run_reversal_ema_ladder (MNQ) — Phase 1A paper-prep port | **CONTAMINATED → RETEST_REQUIRED** | uses `filter_name="ema_slope"`; its PORT_VERIFIED_GREEN validation was against the leaky filter. **Phase 1A/1C paper-prep SUSPENDED** pending clean retest. [retest running; result appended] |

## C. Independent premia — re-audited STANDALONE (causality-first)
| Branch | Status | Evidence |
|---|---|---|
| TSMOM (pool MNQ/MES/MGC, lb126) | **CLEAN_BUT_WEAK_DIVERSIFIER / NOT_PRIMARY** | CAUSAL_CLEAN + costs wired + rollover-clean, but Sharpe 0.52, maxDD −$21k, worst day −$5.9k, 65% net from 2024–25 |
| Vol-carry (contango→short-vol via SVXY) | **CLEAN_BUT_WEAK_DIVERSIFIER / NOT_PRIMARY** | CAUSAL_CLEAN + costs wired, but Sharpe 0.86, −18.3% worst day (crash tail), 59% top-2-year concentration, H2 decays 1.07→0.61 |

## D. Non-ORB probation books — UNAUDITED, must be harnessed
| Branch | Status | Interface |
|---|---|---|
| zn_afternoon_reversion (ZN) | **UNAUDITED → RETEST_REQUIRED** | standalone `generate_signals(df)` (uses `shift(1)`/prior close — promising but unproven); harness-able |
| treasury_rolldown_carry (ZN/ZF/ZB) | **UNAUDITED → RETEST_REQUIRED** | monthly carry spread; different interface — needs carry-lineage + point-in-time audit |
| nfp_level_breakout (MNQ) | **UNAUDITED → RETEST_REQUIRED** | event-box; harness + event-window clean-events check |
| vol_managed_equity (MES) | **UNAUDITED → RETEST_REQUIRED** | vol-scaled sizing; check vol estimate is causal |
| fx_daily_trend (MGC) | **UNAUDITED → RETEST_REQUIRED** | daily trend; harness |

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
