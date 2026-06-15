# Forge Report — EVENT/CPI clean-events validation (fork B) — 2026-06-15

> **Mode:** Lane B / REPORT-ONLY. No promotion, no wiring.
> **Result:** EVENT infra built + assembled + validated. **No clean PASS.** Raw candidates collapsed under clean-events filtering (data-gap + small-sample). One weak DEFER (MGC pre-CPI drift). **The real blocker for EVENT progress is DATA QUALITY, not screening.**
> **Artifacts:** `forge_cycle_2026-06-15{e,f}_*` + `.json`.

## What was built/assembled (fork B)
- Multi-window event screen harness (`event_window_engine` already supported pre-drift / continuation / reversal / 30-60-120m holds / session-close).
- Reused the **verified CPI calendar** (90 events, grade `DATA_REQUIRED` = BLS recall, operator-verifiable, **not** machine-fetched-official).
- Clean-events re-validation harness enforcing `feedback_event_window_clean_events_rule` + `feedback_hold_continuity_canonical_filter` (event aligned ≤10min to release AND hold window gap-free ≤15min).

## Raw → clean (the discipline catching fiction)
The raw harness surfaced 5 "candidates"; clean-events validation dissolved them:
- **MGC pre_drift_L:** raw PF 3.242 → **clean 1.422** (42 of 84 events dropped as gap/misaligned). The raw number was ~half data-gap fiction — exactly the failure mode the locked rule exists to catch.
- **MGC post_L_120m:** raw 1.569 → **clean 0.858 KILL.** Entirely a data-gap artifact.
- **6E/6J pre/post:** clean_n collapses to 11–13 (small-sample noise; 6E median negative).
- **MNQ post_L_120m** (clean-data control, 83/84 events clean): PF 1.191 — real but sub-threshold, maxyr 65.5%.

**No clean PASS. Best clean signal = MGC pre-CPI drift, PF 1.422, DEFER** (n=42, maxyr 53.6% concentration, $5.76 median) — a WATCH/RESEARCH item, not packet-grade.

## Auction proxy
All KILL (expected — 2nd-Wed proxy is meaningless). Real edge can't be assessed without a true TreasuryDirect multi-tenor calendar. `blocked_by_data`.

## Honest conclusion — the wall is DATA, not method
Across the full report-only sweep this session — momentum cross-asset (MNQ-specific), structural/afternoon (no edge), VOL non-equity (no edge), EVENT/CPI (collapses clean) — the recurring blocker is **data quality / availability**, not screening method:
- CPI calendar is recall-grade (`DATA_REQUIRED`); MGC has multi-day gaps; auctions have no real calendar; VALUE has no fundamental feed.
- Cheap screening on existing OHLCV + recall calendars has been **exhausted** for non-MNQ diversification.

The next real diversification progress needs **DATA infrastructure** (aligns with DSCL §8 build queue):
1. Machine-fetch official CPI calendar (upgrade DATA_REQUIRED → MACHINE_FETCHED_OFFICIAL) + re-run the MGC pre-CPI-drift DEFER on clean official data.
2. Build a real TreasuryDirect multi-tenor auction calendar (unblocks the auction track).
3. Remediate MGC data gaps (affects all MGC event work).
4. (Longer) source fundamental/value + term-structure feeds for VALUE/CARRY.

## Disposition
- MGC pre-CPI-drift (clean PF 1.42): **RESEARCH/WATCH** — revisit on official CPI calendar + MGC gap remediation. Not a candidate.
- Everything else this session: KILL / insufficient-sample / blocked-by-data. Nothing promoted or wired.
- **Recommend pausing autonomous report-only screening** — the cheap avenues are exhausted; further progress is a DATA-infra decision (operator steer). Activation remains frozen pending PHASE1C_24H_VERIFY.
