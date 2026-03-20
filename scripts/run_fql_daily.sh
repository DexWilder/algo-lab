#!/bin/bash
# FQL Daily Research Scheduler - runs after market close
# Triggered by launchd: com.fql.daily-research
#
# Schedule: weekdays at 17:30 ET (after market close)
# Logs: research/logs/daily_run_YYYYMMDD_HHMM.log  (detailed per-run)
#        research/logs/launchd_stdout.log            (launchd capture)
# Alert: exits nonzero if any job fails

# ---- Explicit environment (launchd provides minimal env) ----
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PYTHONUNBUFFERED=1

ALGO_LAB="/Users/chasefisher/projects/Algo Trading/algo-lab"
LOG_DIR="$ALGO_LAB/research/logs"
LOCKFILE="$LOG_DIR/.fql_daily.lock"
TIMESTAMP="$(date +%Y%m%d_%H%M)"
LOG_FILE="$LOG_DIR/daily_run_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"

# Helper: write to both per-run log and stdout (launchd captures stdout)
log() {
    echo "$*" >> "$LOG_FILE"
    echo "$*"
}

# ---- Run-lock protection (prevent duplicate runs) ----
if [ -f "$LOCKFILE" ]; then
    LOCK_PID="$(cat "$LOCKFILE" 2>/dev/null || true)"
    if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
        log "$(date) - SKIPPED: FQL daily pipeline already running (PID $LOCK_PID)"
        exit 0
    else
        log "$(date) - Removing stale lockfile (PID $LOCK_PID no longer running)"
        rm -f "$LOCKFILE"
    fi
fi

# Write our PID and ensure cleanup on exit
echo $$ > "$LOCKFILE"
cleanup() { rm -f "$LOCKFILE"; }
trap cleanup EXIT

# ---- Begin pipeline ----
cd "$ALGO_LAB"

log "=== FQL Daily Research Run - $(date) ==="
log "PID: $$ | Repo: $ALGO_LAB"
log "Python: $(which python3) ($(python3 --version 2>&1))"
log ""

# Run the daily pipeline (includes health, half-life, contribution,
# activation matrix, decision report, and drift monitor)
log "--- Starting daily pipeline ---"
python3 research/fql_research_scheduler.py --daily >> "$LOG_FILE" 2>&1
PIPELINE_EXIT=$?
log "--- Daily pipeline exited with code $PIPELINE_EXIT ---"

# ---- Check for failures ----
FAILED=0
if [ "$PIPELINE_EXIT" -ne 0 ]; then
    log "ALERT: Daily pipeline exited with code $PIPELINE_EXIT"
    FAILED=1
fi

# Check scheduler log for ERROR jobs today
ERROR_COUNT="$(python3 -c "
import json, pathlib, sys
log_path = pathlib.Path('$ALGO_LAB/research/data/scheduler_log.json')
if not log_path.exists():
    print(0); sys.exit()
log = json.loads(log_path.read_text())
today = '$(date +%Y-%m-%d)'
errors = [e for e in log if e.get('started', '').startswith(today) and e.get('status') == 'ERROR']
print(len(errors))
" 2>/dev/null || echo 0)"

if [ "$ERROR_COUNT" -gt 0 ]; then
    log "ALERT: $ERROR_COUNT job(s) failed today - check scheduler log"
    FAILED=1
fi

# ---- Rates challenger review (lightweight, non-blocking) ----
log "--- Generating rates challenger review ---"
python3 scripts/rates_challenger_review.py --save >> "$LOG_FILE" 2>&1 || true

# Clean old per-run logs (keep 30 days)
find "$LOG_DIR" -name "daily_run_*.log" -mtime +30 -delete 2>/dev/null || true

# ---- Final status ----
log ""
if [ "$FAILED" -eq 0 ]; then
    log "=== All jobs completed successfully - $(date) ==="
else
    log "=== COMPLETED WITH ERRORS - $(date) ==="
    exit 1
fi
