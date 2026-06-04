# FQL Forge Batch — 2026-06-03

**Filed by:** `research/fql_forge_batch_runner.py` (dry-run/report-only)
**Authority:** T1, no Lane A surfaces touched, no registry mutation.

## Cost assumptions used

Per FQL evidence law (CLAUDE.md): all PFs below are **net** (cost-adjusted). Source of truth: `engine/asset_config.py`. Replace conservative estimates with broker rate sheets before paper/prop.

| Asset | Commission/side | Slippage (ticks) | Tick size | Cost tier |
|---|---:|---:|---|---|
| MGC | $0.62 | 1 | 0.1 | VALIDATED |

## Result table

| Candidate | Asset | Gap | n | PF (net) | Net PnL | Max DD | Cost (comm/slip) | Tier | Verdict |
|---|---|---|---:|---:|---:|---:|---|---|---|
| XB-DC-EMA-Ladder-MGC | MGC | Donchian breakout × proven trio — metals workhorse extension | 980 | 1.149 | 5105 | -4088 | $0.62/1t | VALIDATED | WATCH — Cheap Screen Tier |

## Summary

{
  "PASS": 0,
  "WATCH": 1,
  "KILL": 0,
  "RETEST": 0
}

## Next-batch recommendation

PASS candidates → operator-review eligible for registry append (manual decision).
WATCH candidates → consider one bounded calibration follow-up.
KILL candidates → retire; record learning.
RETEST candidates → harness/data issue; investigate before re-running.
