# FQL Forge Batch — 2026-05-05

**Filed by:** `research/fql_forge_batch_runner.py` (dry-run/report-only)
**Authority:** T1, no Lane A surfaces touched, no registry mutation.

## Result table

| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Verdict |
|---|---|---|---:|---:|---:|---:|---|
| XB-BB-EMA-Ladder-MES | MES | Workhorse cross-asset (BB + proven trio) | 682 | 0.930 | -823 | -2604 | KILL |

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
