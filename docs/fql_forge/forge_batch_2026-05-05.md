# FQL Forge Batch — 2026-05-05

**Filed by:** `research/fql_forge_batch_runner.py` (dry-run/report-only)
**Authority:** T1, no Lane A surfaces touched, no registry mutation.

## Result table

| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Verdict |
|---|---|---|---:|---:|---:|---:|---|
| XB-BB-EMA-Ladder-MYM | MYM | Workhorse cross-asset | 234 | 1.785 | 3877 | -343 | PASS |

## Summary

{
  "PASS": 1,
  "WATCH": 0,
  "KILL": 0,
  "RETEST": 0
}

## Next-batch recommendation

PASS candidates → operator-review eligible for registry append (manual decision).
WATCH candidates → consider one bounded calibration follow-up.
KILL candidates → retire; record learning.
RETEST candidates → harness/data issue; investigate before re-running.
