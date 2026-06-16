# Forge Bench State — 2026-06-16

> **Mode:** Lane B / REPORT-ONLY. Current-feed mining **PAUSED** (per operator). Freeze maintained: nothing promoted/wired/mutated. Phase 1C frozen pending PHASE1C_24H_VERIFY.
> **Purpose:** concise state — what's banked, what's blocked, what unlocks after Phase 1C.

## BANKED — review-track, DATA_AUDIT_GREEN (NOT paper/live-approved, NOT wired)
**Rates-FOMC-week sleeve** (the campaign's first non-equity diversifier):
- **ZN/FOMC-week (PRIMARY)** — long, 2td-pre→2td-post scheduled FOMC, $1,200–1,500 stop. PF 1.86–1.95, +median, beta-control 2.46× (generic rates-long loses), conc 30%, window-family robust (10 variants), prop-safe (<$2K @1 micro), **DATA_AUDIT_GREEN** (0/54 contaminated windows). `CANDIDATE_ZN_FOMC_WEEK_2026-06-16.md`.
- **ZF/FOMC-week (CONFIRMATION/DEPTH)** — clean PF 1.77 (raw 1.45 also viable), **DATA_AUDIT_GREEN** (3 mechanically-flagged roll-stitch windows; one was a winner → not P&L cherry-pick; raw viable without removal). Curve-confirms ZN (5y–10y; ZB 30y KILL).
- **Classification:** ONE correlated sleeve, ZN primary, ZF depth — **not double-size.** Archetype EVENT/TAIL (n=54).

## WATCH / research-only (real but not deployable; preserved, not banked)
- **pre-OPEX seasonal (equity)** = `SEASONAL_BETA_TIMING` — real alpha but beta-laden (loses 2022) + prop-blocked. Not a diversifier.
- **ZN turn-of-month** = `STRUCTURE_FOUND` — real positive-skew tail edge, median-gate blocked.

## Reusable infra + knowledge banked
- Rates RV 2-leg pairs engine (no edge, retained for future multi-instrument work).
- Event-window seasonal + audit harness templates (ZN/ZF audit = reusable pattern).
- Exhausted-lane archive + no-repeat rules; seasonal-family validation; **FOMC-week-specific** finding (NFP/CPI-week are NOT rates seasonals); all KILL/DEFER preserved.

## BLOCKED (gated; cannot proceed now)
- **Out-of-band FOMC event executor — UNBUILT.** Required to wire ZN/ZF-FOMC; same infra also serves FOMC-MNQ Phase 1D. Blocked by activation freeze.
- ZN/ZF-FOMC **V1 packets** — pending.
- **External DSCL verification** (CME settlement, secondary vendor) — required before any capital (GREEN = feed-internal only).
- **Data-infra (lever B):** official auction/OPEC/CPI calendars + VALUE/CARRY feeds — needed to extend the bench (470 feed-blocked harvest items). `.gov` machine-fetch blocked here → needs operator-supplied files.

## Separately in-flight (not bench)
- **Lane A Wave 1 — stop_run_reversal** wired to paper (Phase 1C), awaiting **PHASE1C_24H_VERIFY** (local verifier, surfaces separately).
- **Ladder-MGC** governance review (open).

## UNLOCKS AFTER PHASE 1C (when activation reopens)
1. Build the out-of-band event executor → V1 packets → eventual paper wiring of the Rates-FOMC-week sleeve (after external DSCL).
2. Wave 2/3 sequencing (other MNQ daily workhorses).
3. ZN/ZF-FOMC advance from review-track toward paper, on the same Lane A gauntlet.

## Mission status
**The FIRST non-equity diversification sleeve has been found and banked in review-track form** — a real, audited, cross-confirmed Rates-FOMC-week sleeve. Solved at the **research-bench level, NOT yet at paper/live deployment** (deployment is gated on executor + V1 packet + external DSCL + activation reopen). Current-feed event-seasonal vein is well-mapped (FOMC-week = the edge). Further breadth requires lever B (official data) or awaits activation. **Current-feed Forge search is PAUSED (mission complete for current-feed diversification search). Next meaningful action is gated, not search-driven: Phase 1C verifier resolution → executor/V1-packet sequencing, or Lever-B feed unlock.**
