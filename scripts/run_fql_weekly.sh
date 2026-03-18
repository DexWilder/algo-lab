#!/bin/bash
# FQL Weekly Research Jobs
# Triggered by launchd: com.fql.weekly-research
# Schedule: Friday at 18:30 ET (after daily pipeline)

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PYTHONUNBUFFERED=1

ALGO_LAB="/Users/chasefisher/projects/Algo Trading/algo-lab"
LOG_DIR="$ALGO_LAB/research/logs"
LOCKFILE="$LOG_DIR/.fql_weekly.lock"
TIMESTAMP="$(date +%Y%m%d_%H%M)"
LOG_FILE="$LOG_DIR/weekly_run_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"

log() {
    echo "$*" >> "$LOG_FILE"
    echo "$*"
}

# Run-lock protection
if [ -f "$LOCKFILE" ]; then
    LOCK_PID="$(cat "$LOCKFILE" 2>/dev/null || true)"
    if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
        log "$(date) - SKIPPED: weekly pipeline already running (PID $LOCK_PID)"
        exit 0
    else
        rm -f "$LOCKFILE"
    fi
fi

echo $$ > "$LOCKFILE"
cleanup() { rm -f "$LOCKFILE"; }
trap cleanup EXIT

cd "$ALGO_LAB"

log "=== FQL Weekly Research Run - $(date) ==="
log "PID: $$ | Repo: $ALGO_LAB"
log ""

python3 research/fql_research_scheduler.py --weekly >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

log ""
if [ "$EXIT_CODE" -eq 0 ]; then
    log "=== Weekly jobs completed successfully - $(date) ==="
else
    log "=== COMPLETED WITH ERRORS (exit $EXIT_CODE) - $(date) ==="
    exit 1
fi
