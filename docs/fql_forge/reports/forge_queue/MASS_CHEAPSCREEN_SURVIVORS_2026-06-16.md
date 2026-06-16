# Mass cheap-screen — explicit survivor packet — 2026-06-16

> Lane B / REPORT-ONLY. Source: `forge_cycle_2026-06-16h_*`. No activation/registry/scheduler/portfolio/paper-live mutation occurred.

## Attempt accounting
- **Combos attempted:** 900 (20 entries × 3 exits × 5 filters × 3 assets ZN/MGC/MNQ).
- **Errored:** 0. **Completed with verdict:** 810. **Skipped low-n (<100 trades):** 90 (ZN 30, MGC 21, MNQ 39).
- Verdict distribution: ZN {KILL 270, low-n 30}; MGC {KILL 241, DEFER 23, fwd-clock 3, other 12, low-n 21}; MNQ {KILL 184, DEFER 16, fwd-clock 17, other 44, low-n 39}.

## 12 surfaced shapes (PF≥1.3, both halves>1, conc≤50%, median>0)
**Known MNQ-family re-surfaces (validates screen; already live/Lane-A):**
- MNQ orb_breakout×PL×ema_slope PF 1.627 (XB-ORB live workhorse)
- MNQ stop_run_reversal×PL×ema_slope PF 1.483 (Lane A Wave 1)
- MNQ range_compression_break×PL×ema_slope PF 1.35 ; MNQ first_impulse_pullback×PL×ema_slope PF 1.325 (Lane A batch)
- MGC orb_breakout×PL×ema_slope PF 1.495

**Correlated cousins (same momentum cluster → NOT diversifying, vanity-guard):**
- MNQ donchian_breakout×PL×ema_slope PF 1.62 ; MNQ orb_breakout×fixed_ratio×ema_slope PF 1.567
- MNQ donchian_breakout×fixed_ratio×ema_slope PF 1.485 ; MNQ pb_pullback×PL×ema_slope PF 1.389 (conc 43%)
- MGC orb_breakout×fixed_ratio×ema_slope PF 1.589

**Genuinely different-mechanism leads (→ WATCH-LOW):**
- **MNQ abnormal_range_followup × midline_target × ema_slope** — PF 1.355, n=224, H1/H2 1.815/1.105 (H2 weakening)
- **MGC prior_day_break × profit_ladder × ema_slope** — PF 1.341, n=405, conc 26.4%, H1/H2 1.325/1.349

## ZN: 0 survivors
Rates have no generic-technical edge → rates edge is event-seasonal only (consistent with the banked FOMC-week sleeve).

## No-repeat archive update
- **Generic-technical grid (entry×exit×filter on current assets): tapped for diversification** — re-clusters into MNQ momentum + correlated cousins. Do not re-run for diversification; only specific new entries/exits warrant spot checks.

## Confirmation
No activation, registry, scheduler, portfolio, paper/live, or prop mutation. Survivors are leads for later deep audit, NOT candidates.
