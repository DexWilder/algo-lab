# FQL Forge Batch — 2026-06-03

**Filed by:** `research/fql_forge_batch_runner.py` (dry-run/report-only)
**Authority:** T1, no Lane A surfaces touched, no registry mutation.

## Cost assumptions used

Per FQL evidence law (CLAUDE.md): all PFs below are **net** (cost-adjusted). Source of truth: `engine/asset_config.py`. Replace conservative estimates with broker rate sheets before paper/prop.

| Asset | Commission/side | Slippage (ticks) | Tick size | Cost tier |
|---|---:|---:|---|---|
| ZN | $1.55 | 1 | 0.015625 | VALIDATED |

## Result table

| Candidate | Asset | Gap | n | PF (net) | Net PnL | Max DD | Cost (comm/slip) | Tier | Verdict |
|---|---|---|---:|---:|---:|---:|---|---|---|
| XB-DC-EMA-Ladder-ZN | ZN | Donchian breakout × proven trio — rates extension (fills rates gap) | 1266 | 0.718 | -23269 | -23726 | $1.55/1t | VALIDATED | KILL — Cheap Screen Tier |

## Summary

{
  "PASS": 0,
  "WATCH": 0,
  "KILL": 1,
  "RETEST": 0
}

## Next-batch recommendation

PASS candidates → operator-review eligible for registry append (manual decision).
WATCH candidates → consider one bounded calibration follow-up.
KILL candidates → retire; record learning.
RETEST candidates → harness/data issue; investigate before re-running.
