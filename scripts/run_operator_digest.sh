#!/bin/bash
# FQL Operator Digest — automated daily intelligence
# Triggered by launchd: com.fql.operator-digest
# Schedule: Weekdays at 18:00 ET (after daily-research at 17:30)
#
# Chain: forward-day (17:00) -> daily-research (17:30) -> operator-digest (18:00)

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PYTHONUNBUFFERED=1

ALGO_LAB="/Users/chasefisher/projects/Algo Trading/algo-lab"
LOG_DIR="$ALGO_LAB/research/logs"
LOCKFILE="$LOG_DIR/.fql_digest.lock"
TIMESTAMP="$(date +%Y%m%d_%H%M)"
LOG_FILE="$LOG_DIR/digest_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"

log() {
    echo "$*" >> "$LOG_FILE"
    echo "$*"
}

# Run-lock protection
if [ -f "$LOCKFILE" ]; then
    LOCK_PID="$(cat "$LOCKFILE" 2>/dev/null || true)"
    if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
        log "$(date) - SKIPPED: digest already running (PID $LOCK_PID)"
        exit 0
    else
        rm -f "$LOCKFILE"
    fi
fi

echo $$ > "$LOCKFILE"
cleanup() { rm -f "$LOCKFILE"; }
trap cleanup EXIT

cd "$ALGO_LAB"

log "=== FQL Operator Digest - $(date) ==="
log "PID: $$ | Repo: $ALGO_LAB"
log ""

# Step 1: Refresh alerts (in case daily pipeline was slow)
log "--- Refreshing alerts ---"
python3 scripts/fql_alerts.py --save >> "$LOG_FILE" 2>&1 || true

# Step 2: Health check
log "--- Health check ---"
python3 scripts/fql_doctor.py --save >> "$LOG_FILE" 2>&1 || true

# Step 3: Generate digest
log "--- Generating operator digest ---"
python3 scripts/operator_digest.py --save >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

log ""
if [ "$EXIT_CODE" -eq 0 ]; then
    log "=== Digest completed successfully - $(date) ==="
else
    log "=== Digest FAILED (exit $EXIT_CODE) - $(date) ==="
    exit 1
fi

# Clean old digest logs (keep 30 days)
find "$LOG_DIR" -name "digest_*.log" -mtime +30 -delete 2>/dev/null || true
