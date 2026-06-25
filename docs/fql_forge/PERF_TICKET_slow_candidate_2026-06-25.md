# Performance Ticket (report-only) — XB-PB-EMA-MorningOnly-MNQ runtime outlier

> Non-blocking. Opened 2026-06-25 from the daily-loop dry-run verification. Does NOT block the restored Lane-B loop (soft-cap flags it + continues). Report-only; no capital/registry/portfolio change.

## Observation
In the 2026-06-25 manual dry-run, per-candidate runtimes:
- **XB-PB-EMA-MorningOnly-MNQ: 748.9s** ← pathological outlier (alone exceeds the OLD 300s cap)
- XB-BB-EMA-MorningOnly-MGC-v2: 244.1s
- XB-BB-EMA-AfternoonOnly-MGC: 1.6s
- XB-ORB-EMA-Chandelier-MNQ: 2.9s
- XB-ORB-EMA-TimeStop-MNQ: 2.5s

So two PB/BB session-filtered candidates dominate runtime (~993s of the 1000s total); the ORB variants are ~2.5s each.

## Likely cause
The crossbreeding engine's **pure-Python per-bar loop** (`generate_crossbred_signals`) over MNQ's ~489k 5m bars, amplified for the `pb_pullback` entry + session filter (more state/feature work per bar). Same slowness seen in this session's sweeps (untried-assets sweep = 1021s). The ORB entry is fast; PB/BB session-filtered are ~100-300× slower — suggests an inefficiency specific to those entry/filter paths.

## Options (report-only, for later)
- **Profile** `generate_crossbred_signals` on XB-PB-EMA-MorningOnly-MNQ (cProfile) to find the hot path.
- **Vectorize** the per-bar loop / the PB-entry + session-filter computation.
- **Cache** `compute_features` per asset across candidates in a single loop run (currently recomputed per candidate).
- **Chunk/deprioritize** pathologically-slow candidates in the daily rotation if optimization is deferred.

## Status
OPEN / non-blocking. The restored loop tolerates it (soft-cap alert + continue, 1800s headroom). Address as a performance project, not a halt condition.
