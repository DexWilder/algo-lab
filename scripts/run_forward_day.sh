#!/bin/bash
# FQL Forward Day — daily data refresh + forward paper trading + reports
# Triggered by launchd: com.fql.forward-day
# Schedule: weekdays at 17:00 ET (before daily research pipeline at 17:30)
#
# Steps:
#   1. Update market data (fetch new bars from Databento)
#   2. Run forward paper trading engine on new bars
#   3. Refresh operator brief and alerts
#
# Logs: research/logs/forward_day_YYYYMMDD_HHMM.log

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PYTHONUNBUFFERED=1
export HOME="/Users/chasefisher"

ALGO_LAB="/Users/chasefisher/projects/Algo Trading/algo-lab"
LOG_DIR="$ALGO_LAB/research/logs"
LOCKFILE="$LOG_DIR/.forward_day.lock"
TIMESTAMP="$(date +%Y%m%d_%H%M)"
LOG_FILE="$LOG_DIR/forward_day_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"

log() {
    echo "$*" >> "$LOG_FILE"
    echo "$*"
}

# Run-lock protection
if [ -f "$LOCKFILE" ]; then
    LOCK_PID="$(cat "$LOCKFILE" 2>/dev/null || true)"
    if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
        log "$(date) - SKIPPED: forward day already running (PID $LOCK_PID)"
        exit 0
    else
        rm -f "$LOCKFILE"
    fi
fi

echo $$ > "$LOCKFILE"
cleanup() { rm -f "$LOCKFILE"; }
trap cleanup EXIT

cd "$ALGO_LAB"

log "=== FQL Forward Day - $(date) ==="
log "PID: $$ | Repo: $ALGO_LAB"
log ""

# Step 1: Update market data
log "--- Step 1: Updating market data ---"
python3 scripts/update_daily_data.py >> "$LOG_FILE" 2>&1
DATA_EXIT=$?
if [ "$DATA_EXIT" -ne 0 ]; then
    log "WARN: Data update exited with code $DATA_EXIT"
fi

# Step 2: Run forward paper trading
log ""
log "--- Step 2: Running forward paper trading ---"
python3 run_forward_paper.py >> "$LOG_FILE" 2>&1
FORWARD_EXIT=$?
if [ "$FORWARD_EXIT" -ne 0 ]; then
    log "WARN: Forward runner exited with code $FORWARD_EXIT"
fi

# Step 3: Quick report refresh (alerts + brief only, full refresh at 17:30)
log ""
log "--- Step 3: Refreshing alerts + brief ---"
python3 scripts/fql_alerts.py --save >> "$LOG_FILE" 2>&1 || true
python3 scripts/operator_brief.py --save >> "$LOG_FILE" 2>&1 || true

# Clean old logs (keep 30 days)
find "$LOG_DIR" -name "forward_day_*.log" -mtime +30 -delete 2>/dev/null || true

log ""
if [ "$DATA_EXIT" -eq 0 ] && [ "$FORWARD_EXIT" -eq 0 ]; then
    log "=== Forward day completed successfully - $(date) ==="
else
    log "=== Forward day COMPLETED WITH WARNINGS - $(date) ==="
    exit 1
fi
