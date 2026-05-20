# FQL Forge Batch — 2026-05-20

**Filed by:** `research/fql_forge_batch_runner.py` (dry-run/report-only)
**Authority:** T1, no Lane A surfaces touched, no registry mutation.

## Cost assumptions used

Per FQL evidence law (CLAUDE.md): all PFs below are **net** (cost-adjusted). Source of truth: `engine/asset_config.py`. Replace conservative estimates with broker rate sheets before paper/prop.

| Asset | Commission/side | Slippage (ticks) | Tick size | Cost tier |
|---|---:|---:|---|---|
| MES | $0.62 | 1 | 0.25 | VALIDATED |

## Result table

| Candidate | Asset | Gap | n | PF (net) | Net PnL | Max DD | Cost (comm/slip) | Tier | Verdict |
|---|---|---|---:|---:|---:|---:|---|---|---|
| VWAPPullback-MES-Long | MES | MES-long pullback diversifier (non-ORB entry on equity index) | 2501 | 0.847 | -12670 | -14444 | $0.62/1t | VALIDATED | KILL — Cheap Screen Tier |

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
