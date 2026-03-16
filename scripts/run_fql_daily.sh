#!/bin/bash
# FQL Daily Research Scheduler — runs after market close
# Triggered by launchd: com.fql.daily-research
#
# Schedule: weekdays at 17:30 ET (after market close)
# Logs: research/logs/
# Alert: exits nonzero if any job fails

set -euo pipefail

ALGO_LAB="/Users/chasefisher/projects/Algo Trading/algo-lab"
LOG_DIR="$ALGO_LAB/research/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M")
LOG_FILE="$LOG_DIR/daily_run_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"

echo "=== FQL Daily Research Run — $(date) ===" | tee "$LOG_FILE"

cd "$ALGO_LAB"

# Run the daily pipeline
python3 research/fql_research_scheduler.py --daily 2>&1 | tee -a "$LOG_FILE"
PIPELINE_EXIT=${PIPESTATUS[0]}

# Run drift monitor
echo "" | tee -a "$LOG_FILE"
echo "=== Drift Monitor ===" | tee -a "$LOG_FILE"
python3 research/live_drift_monitor.py --save 2>&1 | tee -a "$LOG_FILE"
DRIFT_EXIT=${PIPESTATUS[0]}

# Check for failures
FAILED=0
if [ $PIPELINE_EXIT -ne 0 ]; then
    echo "ALERT: Daily pipeline exited with code $PIPELINE_EXIT" | tee -a "$LOG_FILE"
    FAILED=1
fi
if [ $DRIFT_EXIT -ne 0 ]; then
    echo "ALERT: Drift monitor exited with code $DRIFT_EXIT" | tee -a "$LOG_FILE"
    FAILED=1
fi

# Check scheduler log for ERROR jobs
ERROR_COUNT=$(python3 -c "
import json
from pathlib import Path
log_path = Path('$ALGO_LAB/research/data/scheduler_log.json')
if log_path.exists():
    log = json.load(open(log_path))
    today = '$(date +%Y-%m-%d)'
    errors = [e for e in log if e.get('started', '').startswith(today) and e.get('status') == 'ERROR']
    print(len(errors))
else:
    print(0)
" 2>/dev/null || echo 0)

if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "ALERT: $ERROR_COUNT job(s) failed today — check scheduler log" | tee -a "$LOG_FILE"
    FAILED=1
fi

# Clean old logs (keep 30 days)
find "$LOG_DIR" -name "daily_run_*.log" -mtime +30 -delete 2>/dev/null || true

echo "" | tee -a "$LOG_FILE"
if [ $FAILED -eq 0 ]; then
    echo "=== All jobs completed successfully — $(date) ===" | tee -a "$LOG_FILE"
else
    echo "=== COMPLETED WITH ERRORS — $(date) ===" | tee -a "$LOG_FILE"
    exit 1
fi
