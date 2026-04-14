#!/bin/bash
# FQL Guarded Forward Runner -- Morning paper trading automation
# Triggered by launchd: com.fql.forward-trading (DISABLED BY DEFAULT)
#
# IMPORTANT: This script uses PAID Databento API calls for data updates.
# Do not enable the launchd agent without understanding the cost implications.
# Typical cost: ~$0.10-0.50 per daily update across all active assets.
#
# Schedule: Weekdays at 06:25 ET (before market open)
#
# Safety features:
#   - Enable/disable switch (FORWARD_ENABLED flag below)
#   - Pre-flight data integrity checks
#   - Lockfile protection
#   - Watchdog check before running
#   - Detailed logging
#   - Non-zero exit on any failure

# ---- ENABLE/DISABLE SWITCH ----
# Set to "true" to allow automated forward runs.
# Set to "false" to block execution even if launchd triggers it.
FORWARD_ENABLED="false"

# ---- Environment ----
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PYTHONUNBUFFERED=1

ALGO_LAB="/Users/chasefisher/projects/Algo Trading/algo-lab"
LOG_DIR="$ALGO_LAB/research/logs"
LOCKFILE="$LOG_DIR/.fql_forward.lock"
TIMESTAMP="$(date +%Y%m%d_%H%M)"
LOG_FILE="$LOG_DIR/forward_run_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"

log() {
    echo "$*" >> "$LOG_FILE"
    echo "$*"
}

# ---- Enable check ----
if [ "$FORWARD_ENABLED" != "true" ]; then
    log "$(date) - Forward runner is DISABLED (FORWARD_ENABLED=false)"
    log "To enable, edit scripts/run_fql_forward.sh and set FORWARD_ENABLED=true"
    exit 0
fi

# ---- Run-lock protection ----
if [ -f "$LOCKFILE" ]; then
    LOCK_PID="$(cat "$LOCKFILE" 2>/dev/null || true)"
    if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
        log "$(date) - SKIPPED: forward runner already running (PID $LOCK_PID)"
        exit 0
    else
        rm -f "$LOCKFILE"
    fi
fi

echo $$ > "$LOCKFILE"
cleanup() { rm -f "$LOCKFILE"; }
trap cleanup EXIT

cd "$ALGO_LAB"

log "=== FQL Forward Trading Run - $(date) ==="
log "PID: $$ | Repo: $ALGO_LAB"
log ""

# ---- Pre-flight: Watchdog check ----
# Reads the cached SAFE_MODE verdict from research/data/watchdog_state.json.
# That file is refreshed by daily_system_watchdog in fql_research_scheduler
# (priority 0). If the daily scheduler has not run recently, the verdict
# here will be stale. See research/system_watchdog.py for the full
# relationship between this gate, the shell recovery watchdog, and the
# 60-point fql_health_check.
log "--- Pre-flight: watchdog check ---"
WATCHDOG_RESULT="$(python3 research/system_watchdog.py --safe-mode 2>&1)"
if [ $? -ne 0 ]; then
    log "ABORT: System is in SAFE_MODE — $WATCHDOG_RESULT"
    log "Fix underlying issues before running forward trading."
    exit 1
fi
log "Watchdog: $WATCHDOG_RESULT"

# ---- Pre-flight: Data directory check ----
DATA_FILES="$(ls "$ALGO_LAB/data/processed/"*_5m.csv 2>/dev/null | wc -l | tr -d ' ')"
if [ "$DATA_FILES" -lt 3 ]; then
    log "ABORT: Only $DATA_FILES data files found (need at least 3)"
    exit 1
fi
log "Data files: $DATA_FILES assets available"

# ---- Step 1: Update data (PAID API CALL) ----
log ""
log "--- Step 1: Updating market data (Databento API) ---"
python3 scripts/update_daily_data.py >> "$LOG_FILE" 2>&1
DATA_EXIT=$?

if [ "$DATA_EXIT" -ne 0 ]; then
    log "WARNING: Data update failed (exit $DATA_EXIT)"
    log "Continuing with existing data (may be stale)"
fi

# ---- Step 2: Run forward paper trading ----
log ""
log "--- Step 2: Running forward paper trading ---"
python3 run_forward_paper.py >> "$LOG_FILE" 2>&1
FORWARD_EXIT=$?

log ""
log "--- Forward runner exited with code $FORWARD_EXIT ---"

# ---- Final status ----
log ""
if [ "$FORWARD_EXIT" -eq 0 ]; then
    log "=== Forward trading completed successfully - $(date) ==="
else
    log "=== FORWARD TRADING COMPLETED WITH ERRORS - $(date) ==="
    exit 1
fi
