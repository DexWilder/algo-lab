# FQL Scheduled Daily Execution

## Overview
FQL runs its full daily research pipeline automatically after market close.

## Setup (one-time)

### 1. Install launchd agent
```bash
cp scripts/com.fql.daily-research.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.fql.daily-research.plist
```

### 2. Grant Full Disk Access to python3
macOS requires granting Full Disk Access for scheduled scripts:
1. Open **System Settings > Privacy & Security > Full Disk Access**
2. Click the `+` button
3. Press `Cmd+Shift+G` and paste: `/usr/local/bin/python3`
4. Add it to the list

Without this step, launchd jobs will fail silently due to macOS sandboxing.

### 3. Verify
```bash
# Check agent is registered
launchctl list | grep fql

# Manual trigger
launchctl start com.fql.daily-research

# Check logs
cat research/logs/launchd_stdout.log
cat research/logs/launchd_stderr.log
```

## Schedule
- **When**: Weekdays (Mon-Fri) at 17:30
- **What**: `python3 research/fql_research_scheduler.py --daily`

## Daily Pipeline (6 jobs)
1. Health check (60-point system validation)
2. Half-life monitor (edge decay tracking)
3. Contribution analysis (marginal Sharpe per strategy)
4. Portfolio Regime Controller (activation scoring + registry update)
5. Decision report (JSON + Markdown, from cached matrix)
6. Drift monitor (forward vs backtest comparison)

## Manual Execution
```bash
# Run full daily pipeline
python3 research/fql_research_scheduler.py --daily

# Run individual cadences
python3 research/fql_research_scheduler.py --weekly
python3 research/fql_research_scheduler.py --monthly

# Check job status
python3 research/fql_research_scheduler.py --status

# Run drift monitor standalone
python3 research/live_drift_monitor.py --save

# Run execution quality monitor
python3 execution/execution_quality_monitor.py --save
```

## Managing the Agent
```bash
# Check status
launchctl list | grep fql

# Stop/disable
launchctl unload ~/Library/LaunchAgents/com.fql.daily-research.plist

# Restart
launchctl unload ~/Library/LaunchAgents/com.fql.daily-research.plist
launchctl load ~/Library/LaunchAgents/com.fql.daily-research.plist

# Manual trigger (test)
launchctl start com.fql.daily-research
```

## Logs
- Scheduler log: `research/data/scheduler_log.json`
- Drift log: `research/data/live_drift_log.json`
- Execution log: `execution/data/execution_quality_log.json`
- launchd stdout: `research/logs/launchd_stdout.log`
- launchd stderr: `research/logs/launchd_stderr.log`

## Troubleshooting
- **Silent failure**: Grant Full Disk Access to python3 (see setup step 2)
- **Exit code 126**: Permission denied — check Full Disk Access
- **No output in logs**: launchd sandboxing — verify python3 has FDA
- **Job errors**: Check `python3 research/fql_research_scheduler.py --status`
