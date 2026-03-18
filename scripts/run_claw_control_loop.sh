#!/bin/bash
# FQL Claw Control Loop — Claude-side directive refresh + audit
# Triggered by launchd: com.fql.claw-control-loop
#
# Schedule: Daily at 06:00 ET (morning directives) and 20:00 ET (EOD audit)
# Logs: research/logs/claw_loop_YYYYMMDD_HHMM.log

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PYTHONUNBUFFERED=1

ALGO_LAB="/Users/chasefisher/projects/Algo Trading/algo-lab"
LOG_DIR="$ALGO_LAB/research/logs"
LOCKFILE="$LOG_DIR/.claw_loop.lock"
TIMESTAMP="$(date +%Y%m%d_%H%M)"
LOG_FILE="$LOG_DIR/claw_loop_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"

log() {
    echo "$*" >> "$LOG_FILE"
    echo "$*"
}

# Run-lock protection
if [ -f "$LOCKFILE" ]; then
    LOCK_PID="$(cat "$LOCKFILE" 2>/dev/null || true)"
    if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
        log "$(date) - SKIPPED: Claw control loop already running (PID $LOCK_PID)"
        exit 0
    else
        rm -f "$LOCKFILE"
    fi
fi

echo $$ > "$LOCKFILE"
cleanup() { rm -f "$LOCKFILE"; }
trap cleanup EXIT

cd "$ALGO_LAB"

log "=== Claw Control Loop - $(date) ==="
log "PID: $$ | Repo: $ALGO_LAB"
log ""

python3 scripts/claw_control_loop.py >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

# Clean old logs (keep 30 days)
find "$LOG_DIR" -name "claw_loop_*.log" -mtime +30 -delete 2>/dev/null || true

log ""
if [ "$EXIT_CODE" -eq 0 ]; then
    log "=== Control loop completed successfully - $(date) ==="
else
    log "=== COMPLETED WITH ERRORS (exit $EXIT_CODE) - $(date) ==="
    exit 1
fi
