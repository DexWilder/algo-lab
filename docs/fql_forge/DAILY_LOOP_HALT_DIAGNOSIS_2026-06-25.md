# Daily Forge Loop Halt — Diagnosis & Staged Resume Plan (report-only, needs approval)

> Surfaced 2026-06-24 by the learning-loop audit (caught an uncommitted `_TRIPWIRE_` file). DIAGNOSE-FIRST: do NOT clear tripwires or resume before the runtime-overrun cause is patched, or it just re-halts. NOTHING here is executed without explicit approval. Capital gate intact (this is the OFFLINE Lane-B dry-run research loop, not paper/live).

## What halted
- **Loop:** `com.fql.forge-daily-loop` → `research/fql_forge_daily_loop.py`, weekdays 19:00 PT. This is the **Lane-B dry-run research loop** (report-only screens), NOT the forward-day paper runner. No paper/live/registry/portfolio impact.
- **Trigger (June 3):** the 5 date-rotated candidates ran **1183s > the hard-coded 300s cap** (`TRIPWIRE_RUNTIME_MAX_SEC = 300`, line 51) → wrote `_TRIPWIRE_2026-06-03_runtime_overrun:.md` and exited (before the report stage).
- **Cascade:** the pre-run check (lines 63–71) halts if ANY `_TRIPWIRE_*` exists. So every scheduled run since has halted pre-emptively and written a new `_unresolved` tripwire → **16 tripwire files, ~3 weeks down.**
- **Safe by design:** "no registry/runtime/portfolio changes occurred." The real failure was **observability** — the alerts sat unsurfaced until the audit caught them (now fixed: audit emits an OPERATIONAL ALERT on tripwires every run).

## Root cause
Hard 300s cap is unrealistically tight for an offline dry-run: 5 rotated candidates × heavy per-candidate engine backtests (the per-bar Python-loop cost — same slowness seen in this session's sweeps, e.g. 1021s for the untried-assets sweep) → ~237s/candidate avg → easily exceeds 300s on heavy candidates.

## Fix options
- **A. Raise the cap (recommended, simplest):** `TRIPWIRE_RUNTIME_MAX_SEC` 300 → ~1800s (30 min). Appropriate for a non-capital-facing offline research loop; 1183s is fine offline.
- **B. Reduce `--top` 5→3** (fewer candidates/day, more rotation days) — keeps runs bounded under a tighter cap.
- **C. Per-candidate soft-timeout** (e.g., skip/flag a candidate >150s) — bounds total without a huge global cap; preserves the runtime tripwire as a real anomaly detector.
- **D. Optimize the engine per-bar loop** — the true fix, but a separate performance project (vectorize), not needed to resume.
- **E. Immediate tripwire notification** — DONE via the learning-loop audit OPERATIONAL ALERT.
- **Recommended combo:** A (cap→1800) + C (per-candidate soft-cap ~150s) — resumes reliably AND keeps the runtime tripwire meaningful (it'll only fire on a genuine anomaly, not normal workload).

## Staged resume plan (each step needs approval; nothing done yet)
1. **Patch** (report-only edit, pending approval): set `TRIPWIRE_RUNTIME_MAX_SEC = 1800`; optionally add per-candidate soft-cap; optionally `--top` default 5→3.
2. **Clear backlog** (pending approval): delete the 16 `research/data/fql_forge/reports/_TRIPWIRE_*` files. ⚠ This RESUMES the loop. Confirmed: resumes ONLY the Lane-B dry-run research loop; touches NO capital-facing surface.
3. **Verify:** run one manual `python3 research/fql_forge_daily_loop.py --dry-run` → confirm it completes under the new cap and writes a report (not a tripwire).
4. **Confirm steady state:** next scheduled 19:00 PT run produces a report + a clean learning-loop heartbeat.

## Capital gate
No strategy wiring, registry, portfolio, sizing, or paper/live changes. The only mutation proposed is the runtime-budget of a non-capital offline research loop, and only on explicit approval. No auto-resume.

## RESOLVED 2026-06-25 — manual dry-run PASSED
Runtime 1000.1s < 1800s cap; reports written; NO new tripwire; PASS 3 / WATCH 2. Soft-cap flagged 2 slow candidates (XB-PB-EMA-MorningOnly-MNQ 748.9s — alone exceeds old 300s cap — and XB-BB-EMA-MorningOnly-MGC-v2 244.1s) and CONTINUED without halting. Lane-B dry-run loop MANUAL-VERIFIED RESTORED. Next proof: scheduled 19:00 PT run. Follow-up (option D, non-blocking): XB-PB-EMA-MorningOnly-MNQ is pathologically slow (748.9s vs ~2.5s for ORB variants) — engine per-bar-loop perf candidate.
