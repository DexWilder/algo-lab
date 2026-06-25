# 🔴 TRIPWIRE — `ema_slope` filter same-day-close LOOKAHEAD (CRITICAL) — 2026-06-25

> **FAIL-CLOSED / STOP.** Per `feedback_evidence_integrity_failsafe`. This is an integrity finding about the
> **deployed/probation ORB family** and everything built on it. NO promotion, sizing, wiring, or capital action
> on any ORB-derived result until resolved + operator-reviewed. Report-only. The on-disk engine is NOT modified by this audit.

## The bug
`research/crossbreeding/crossbreeding_engine.py` `compute_features()` builds the daily trend filter as:
```
daily_close = df_temp.groupby("_date")["close"].last()      # = each day's SESSION CLOSE
daily_ema20 = daily_close.ewm(span=20).mean()
daily_slope = daily_ema20.diff()
date_trend[d] = sign(daily_slope[d])                         # uses day d's CLOSE
bar_trend[bar on day d] = date_trend[d]
```
The `ema_slope` filter (`filter_ema_slope`) then rejects any intraday entry whose side disagrees with `bar_trend`.
But ORB entries fire **09:45–14:45**, all BEFORE the session close — so `date_trend[d]` embeds information
(day d's 16:00 close) that the entry decision cannot have. **Same-day-close lookahead.** Trivially favors
trades on days that closed in their direction.

## Evidence (MNQ, two independent methods agree)
1. **Sign-flip rate:** same-day vs prior-day EMA20 slope sign differs on **12.2% of days** (265/2173). Not immaterial.
2. **Conservative leaky-trade audit** (`..._baseline_lookahead_audit.py`): 17% of trades are only permitted by the
   same-day sign (prior-day trend disagrees); those carry **60.1% of total net PnL**.
3. **DECISIVE lagged-filter re-backtest** (`..._lagged_filter_decisive.py`, monkeypatched `bar_trend := prior-trading-day sign`,
   on-disk engine untouched):

   | ORB MNQ | Sharpe | maxDD | net | retains |
   |---|---|---|---|---|
   | AS-IS (same-day filter) | **2.65** | −2331 | $50,835 | — |
   | LAGGED (no-lookahead) | **0.49** | −5719 | $8,441 | **17%** |
   | LAGGED H2 (OOS) | 1.23 | −2889 | $11,796 | |

   Per-year, the honest version is **negative in 2019/2020/2021**. ~83% of net PnL evaporates without the lookahead.

## Scope — reaches the deployed system
- **Deployed/probation strategy** `strategies/xb_orb_ema_ladder/strategy.py` (XB-ORB-EMA-Ladder, **MNQ + MCL + MYM**, live-forward probation) calls `generate_crossbred_signals(... filter_name="ema_slope" ...)` — the **same leaky filter.**
- **Forward PAPER runner** `run_forward_paper.py` (line ~132/138) "generates signals on the **full dataset**" after the 17:00 ET close, then extracts the day's trades → when it computes today's daily-close trend, today's close already exists → **the forward paper evidence inherits the same lookahead.** The forward validation is NOT a clean point-in-time check of this filter.
- Therefore **both backtest AND forward-paper** validation of the entire ORB-EMA-Ladder family are contaminated.
- **This session:** every CV result (CV1/CV2 principled sizing, CV3/CV3-R forecast scaling, the whole small-diversifier dossier) uses this ORB as primary/benchmark → all rest on a contaminated foundation.

## Calibrated severity
- The lookahead **exists** (plainly in code) and **materially inflates** the backtest (two methods, large effect) — HIGH confidence.
- The honest (lagged) strategy is still modestly **positive** (Sharpe 0.49 full / 1.23 H2) → a small real ORB edge may remain, but ~83% of the believed edge was lookahead. The strategy is likely **below promotion thresholds**, not necessarily worthless.
- **Residual items to nail down (do NOT block escalation):** (a) re-measure at the DEPLOYED params `stop_mult=2.0` (audit used research `0.5`; leak is filter-level / config-independent, but quantify); (b) MCL/MYM decisive lagged re-backtest; (c) confirm the forward runner's additional regime gates (`trend_persistence==GRINDING`, `trend_regime`) don't coincidentally launder the leak (they don't fix it — they're extra filters).

## Required actions (operator-gated)
1. **Treat ALL ORB-EMA-Ladder backtest AND forward PFs as SUSPECT** pending a true point-in-time (no-lookahead) re-validation. This includes the CLAUDE.md probation PFs (MNQ 1.62 / MCL 1.30 / MYM 1.63).
2. **Freeze** any promotion / sizing / wiring / size-increase on the ORB family and on the small-diversifier dossier (its primary is contaminated). Capital gate already in force.
3. **Fix** = shift the daily trend by one day in `compute_features` (`date_trend` from prior-day close) — but that is an **engine truth-mutation affecting the deployed system**; do under explicit approval, then **re-validate the whole ORB family point-in-time** and re-run the dossier on clean ORB.
4. Re-audit other strategies using `ema_slope` / `vwap_slope` / any same-day daily aggregate for the same class of leak.

## Artifacts
- `research/forge_cycle_2026-06-25_CV3R_baseline_lookahead_audit.py` (conservative)
- `research/forge_cycle_2026-06-25_CV3R_lagged_filter_decisive.py` (decisive, monkeypatched)
- `research/forge_cycle_2026-06-25_CV3R_constant_risk_scaling.py` (where the lagged-vs-same-day gap first surfaced)

---

## REPAIR LOG (operator-approved controlled truth repair — NOT promotion)

**R1 — Engine patch (DONE).** `compute_features()` daily trend now uses `daily_ema20.diff().shift(1)` →
bars on day d use the PRIOR completed trading day's slope. On-disk engine changed (working state backed up to
`/tmp` first). The fix takes effect for tonight's 14:00 PT forward-paper run and 19:00 PT research loop.

**R2 — Unit test (DONE, PASS).** `research/test_no_lookahead_daily_filters.py` asserts the point-in-time
invariant by perturbing day-d's session close UP vs DOWN and checking day-d trend is invariant:
- FIXED engine: day-d trend invariant to day-d close (PASS); day d+1 correctly responds.
- PRE-FIX (un-shifted): day-d trend FLIPS with day-d close (FAIL) → the test provably catches the leak.
(Found en route: `compute_features` has an in-memory cache keyed only by `(len, first_dt, last_dt)` — it ignores
close CONTENT, so corrected/perturbed same-range data returns STALE features. Secondary sharp-edge, not a
lookahead; the test clears `_FEATURE_CACHE` between perturbations. Worth a follow-up content-hash key.)

**R3 — Same-day-aggregate filter audit (DONE).** Only `ema_slope` carried the same-day-close lookahead.
- `ema_slope` daily trend — WAS leaky → FIXED.
- `vwap_slope` — session VWAP is cumulative-within-session, causal → SAFE.
- `prev_day_high/low/close/range/midpoint/range_pctrank` — all `.shift(1)` (prior day) → SAFE.
- `atr_pctrank`, `bw_pctrank`, `range_20_pctrank`, `vol_of_vol_pctrank`, `hurst`, `rsi` — trailing rolling, causal → SAFE.
- `ema_slope_vol_high/low` — stack bar_trend (now fixed) + atr_pctrank (safe) → now CLEAN.
- Donchian `dc_high/low_N` include the current bar (line ~407, pre-documented) — separate entry-logic note,
  NOT this class; deployed ORB does not use Donchian.

**R4 — ORB family point-in-time revalidation (RUNNING).** `..._R4_orb_family_revalidation.py` re-runs
MNQ/MES/MGC/MCL/MYM at the DEPLOYED `stop_mult=2.0`, CLEAN (fixed) vs CONTAMINATED (monkeypatched un-shift),
full metrics + H1/H2. Establishes the true point-in-time baseline. [results appended on completion]

**R5 — Downstream re-run (PENDING R4).** Small-diversifier package / TSMOM+vol-carry vs CLEAN ORB; MGC vol_low;
CV3/CV3-R only if a clean ORB edge survives.

**R6 — Forward-runner audit (PENDING).** `run_forward_paper.py` generates signals on full-day data after close →
the engine fix removes the ema_slope leak from forward signals going forward, but PRIOR forward evidence was
generated with the leak → mark prior ORB forward evidence contaminated; consider a true intraday point-in-time
signal path.

**Capital gate unchanged throughout:** no promotion, sizing, wiring, registry, scheduler, portfolio, or paper/live action.

**Do NOT delete this tripwire or resume ORB-dependent advancement without explicit operator review.**
