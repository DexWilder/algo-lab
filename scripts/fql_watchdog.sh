#!/bin/bash
# FQL Watchdog — Self-healing recovery layer
# Triggered by launchd: com.fql.watchdog (every 5 minutes)
#
# Checks:
#   1. OpenClaw gateway process alive + health endpoint responsive
#   2. Claw control loop logs are fresh (within 45 minutes)
#   3. EOD audit is not stale (within 26 hours)
#   4. Scheduled research jobs ran if due
#
# Recovery actions:
#   - Restart gateway if down
#   - Kickstart claw-control-loop if stale
#   - Fire missed research jobs (with catch-up flag)
#   - Exponential backoff on repeated failures
#
# Logs: research/logs/watchdog_YYYYMMDD.log (daily rotation)

set -euo pipefail

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export HOME="/Users/chasefisher"

ALGO_LAB="/Users/chasefisher/projects/Algo Trading/algo-lab"
LOG_DIR="$ALGO_LAB/research/logs"
WATCHDOG_STATE="$LOG_DIR/.watchdog_state.json"
TODAY="$(date +%Y%m%d)"
LOG_FILE="$LOG_DIR/watchdog_${TODAY}.log"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"

GATEWAY_PORT=18789
GATEWAY_LABEL="ai.openclaw.gateway"
CLAW_LOOP_LABEL="com.fql.claw-control-loop"
DAILY_LABEL="com.fql.daily-research"
TWICE_WEEKLY_LABEL="com.fql.twice-weekly-research"
WEEKLY_LABEL="com.fql.weekly-research"

# Thresholds
CLAW_LOOP_STALE_MINUTES=45      # Control loop runs every 30m; stale if >45m
AUDIT_STALE_HOURS=26             # EOD audit should refresh daily; stale if >26h
GATEWAY_HEALTH_TIMEOUT=5         # Seconds to wait for health endpoint
MAX_CONSECUTIVE_FAILURES=5       # Stop retrying after this many consecutive failures
BACKOFF_LOCKFILE="$LOG_DIR/.watchdog_backoff.lock"

mkdir -p "$LOG_DIR"

# ---- Logging ----
log() {
    echo "[$TIMESTAMP] $*" >> "$LOG_FILE"
}

log_recovery() {
    echo "[$TIMESTAMP] RECOVERY: $*" >> "$LOG_FILE"
    # Also append to a persistent recovery audit trail
    echo "[$TIMESTAMP] $*" >> "$LOG_DIR/recovery_actions.log"
}

# ---- Backoff State ----
# Tracks consecutive failures per component to prevent restart thrashing.
# State file: JSON with {component: {failures: N, last_attempt: timestamp, backoff_until: timestamp}}

load_state() {
    if [ -f "$WATCHDOG_STATE" ]; then
        cat "$WATCHDOG_STATE"
    else
        echo '{}'
    fi
}

save_state() {
    echo "$1" > "$WATCHDOG_STATE"
}

get_failures() {
    local component="$1"
    local state
    state="$(load_state)"
    echo "$state" | python3 -c "
import json, sys
state = json.load(sys.stdin)
print(state.get('$component', {}).get('failures', 0))
" 2>/dev/null || echo 0
}

should_backoff() {
    local component="$1"
    local state
    state="$(load_state)"
    python3 -c "
import json, sys, time
state = json.load(sys.stdin)
info = state.get('$component', {})
failures = info.get('failures', 0)
backoff_until = info.get('backoff_until', 0)
if failures >= $MAX_CONSECUTIVE_FAILURES:
    print('EXHAUSTED')
elif time.time() < backoff_until:
    print('WAITING')
else:
    print('OK')
" <<< "$state" 2>/dev/null || echo "OK"
}

record_failure() {
    local component="$1"
    local state
    state="$(load_state)"
    state="$(python3 -c "
import json, sys, time
state = json.load(sys.stdin)
info = state.get('$component', {})
failures = info.get('failures', 0) + 1
# Exponential backoff: 1m, 2m, 4m, 8m, 16m
backoff_secs = min(60 * (2 ** (failures - 1)), 960)
state['$component'] = {
    'failures': failures,
    'last_attempt': time.time(),
    'backoff_until': time.time() + backoff_secs,
}
print(json.dumps(state))
" <<< "$state")"
    save_state "$state"
}

record_success() {
    local component="$1"
    local state
    state="$(load_state)"
    state="$(python3 -c "
import json, sys
state = json.load(sys.stdin)
if '$component' in state:
    del state['$component']
print(json.dumps(state))
" <<< "$state")"
    save_state "$state"
}

# ---- Check 1: OpenClaw Gateway ----
check_gateway() {
    log "CHECK: OpenClaw gateway..."

    # Check if process exists
    local pid
    pid="$(launchctl list | grep "$GATEWAY_LABEL" | awk '{print $1}')"
    if [ "$pid" = "-" ] || [ -z "$pid" ]; then
        log "  FAIL: Gateway process not running (no PID)"
        return 1
    fi

    # Check health endpoint
    local health
    health="$(curl -s --max-time "$GATEWAY_HEALTH_TIMEOUT" "http://localhost:${GATEWAY_PORT}/health" 2>/dev/null || echo "")"
    if echo "$health" | grep -q '"ok":true'; then
        log "  OK: Gateway alive (PID $pid), health endpoint responsive"
        record_success "gateway"
        return 0
    else
        log "  FAIL: Gateway process exists (PID $pid) but health check failed: $health"
        return 1
    fi
}

recover_gateway() {
    local backoff
    backoff="$(should_backoff gateway)"
    if [ "$backoff" = "EXHAUSTED" ]; then
        log "  SKIP: Gateway recovery exhausted ($MAX_CONSECUTIVE_FAILURES consecutive failures). Manual intervention required."
        return 1
    elif [ "$backoff" = "WAITING" ]; then
        log "  SKIP: Gateway recovery in backoff period."
        return 1
    fi

    log_recovery "Restarting OpenClaw gateway..."
    launchctl kickstart -k "gui/$(id -u)/$GATEWAY_LABEL" 2>/dev/null || true
    sleep 3

    # Verify recovery
    local health
    health="$(curl -s --max-time "$GATEWAY_HEALTH_TIMEOUT" "http://localhost:${GATEWAY_PORT}/health" 2>/dev/null || echo "")"
    if echo "$health" | grep -q '"ok":true'; then
        log_recovery "Gateway recovered successfully."
        record_success "gateway"
        return 0
    else
        log_recovery "Gateway recovery FAILED. Health: $health"
        record_failure "gateway"
        return 1
    fi
}

# ---- Check 2: Claw Control Loop Freshness ----
check_claw_loop() {
    log "CHECK: Claw control loop freshness..."

    # Find the most recent claw_loop log
    local latest_log
    latest_log="$(ls -t "$LOG_DIR"/claw_loop_*.log 2>/dev/null | head -1)"
    if [ -z "$latest_log" ]; then
        log "  FAIL: No claw_loop logs found"
        return 1
    fi

    # Check age of most recent log
    local log_age_minutes
    log_age_minutes="$(python3 -c "
import os, time
mtime = os.path.getmtime('$latest_log')
age = (time.time() - mtime) / 60
print(int(age))
" 2>/dev/null || echo 9999)"

    if [ "$log_age_minutes" -le "$CLAW_LOOP_STALE_MINUTES" ]; then
        log "  OK: Latest claw log is ${log_age_minutes}m old (threshold: ${CLAW_LOOP_STALE_MINUTES}m) — $latest_log"
        record_success "claw_loop"
        return 0
    else
        log "  FAIL: Latest claw log is ${log_age_minutes}m old (threshold: ${CLAW_LOOP_STALE_MINUTES}m)"
        return 1
    fi
}

recover_claw_loop() {
    local backoff
    backoff="$(should_backoff claw_loop)"
    if [ "$backoff" = "EXHAUSTED" ]; then
        log "  SKIP: Claw loop recovery exhausted. Manual intervention required."
        return 1
    elif [ "$backoff" = "WAITING" ]; then
        log "  SKIP: Claw loop recovery in backoff period."
        return 1
    fi

    log_recovery "Kickstarting claw control loop..."
    launchctl kickstart -k "gui/$(id -u)/$CLAW_LOOP_LABEL" 2>/dev/null || true
    sleep 5

    # Verify: check if a new log appeared
    local latest_log
    latest_log="$(ls -t "$LOG_DIR"/claw_loop_*.log 2>/dev/null | head -1)"
    local log_age_minutes
    log_age_minutes="$(python3 -c "
import os, time
mtime = os.path.getmtime('$latest_log')
age = (time.time() - mtime) / 60
print(int(age))
" 2>/dev/null || echo 9999)"

    if [ "$log_age_minutes" -le 2 ]; then
        log_recovery "Claw loop recovered — fresh log at $latest_log"
        record_success "claw_loop"
        return 0
    else
        log_recovery "Claw loop recovery FAILED — log still ${log_age_minutes}m old"
        record_failure "claw_loop"
        return 1
    fi
}

# ---- Check 3: EOD Audit Freshness ----
check_audit() {
    log "CHECK: EOD audit freshness..."

    local audit_dir="$ALGO_LAB/research/data/claw_audits"
    local latest_audit
    latest_audit="$(ls -t "$audit_dir"/audit_*.md "$audit_dir"/brief_*.md 2>/dev/null | head -1)"
    if [ -z "$latest_audit" ]; then
        log "  WARN: No audit files found in $audit_dir"
        return 1
    fi

    local audit_age_hours
    audit_age_hours="$(python3 -c "
import os, time
mtime = os.path.getmtime('$latest_audit')
age = (time.time() - mtime) / 3600
print(f'{age:.1f}')
" 2>/dev/null || echo 999)"

    local age_int
    age_int="${audit_age_hours%%.*}"

    if [ "$age_int" -le "$AUDIT_STALE_HOURS" ]; then
        log "  OK: Latest audit is ${audit_age_hours}h old (threshold: ${AUDIT_STALE_HOURS}h) — $(basename "$latest_audit")"
        return 0
    else
        log "  WARN: Latest audit is ${audit_age_hours}h old (threshold: ${AUDIT_STALE_HOURS}h)"
        return 1
    fi
}

# ---- Check 4: Missed Research Jobs Catch-Up ----
check_missed_jobs() {
    log "CHECK: Scheduled research job freshness..."

    local now_epoch
    now_epoch="$(date +%s)"
    local dow
    dow="$(date +%u)"  # 1=Monday ... 7=Sunday
    local hour
    hour="$(date +%H)"

    local missed=""

    # Forward day: should have run today (weekday) by 17:30 if it's past 17:45
    if [ "$dow" -le 5 ] && [ "$hour" -ge 18 ]; then
        local fwd_log
        fwd_log="$(ls -t "$LOG_DIR"/forward_day_${TODAY}*.log 2>/dev/null | head -1)"
        if [ -z "$fwd_log" ]; then
            missed="$missed forward_day"
            log "  MISS: Forward day has not run today (expected by 17:00)"
        else
            log "  OK: Forward day ran today — $(basename "$fwd_log")"
        fi
    fi

    # Daily research: should have run today (weekday) by 18:00 if it's past 18:30
    if [ "$dow" -le 5 ] && [ "$hour" -ge 18 ]; then
        local daily_log
        daily_log="$(ls -t "$LOG_DIR"/daily_run_${TODAY}*.log 2>/dev/null | head -1)"
        if [ -z "$daily_log" ]; then
            missed="$missed daily"
            log "  MISS: Daily research has not run today (expected by 17:30)"
        else
            log "  OK: Daily research ran today — $(basename "$daily_log")"
        fi
    fi

    # Twice-weekly: Tuesday (dow=2) and Thursday (dow=4), should run by 18:30
    if { [ "$dow" -eq 2 ] || [ "$dow" -eq 4 ]; } && [ "$hour" -ge 19 ]; then
        local tw_log
        tw_log="$(ls -t "$LOG_DIR"/twice_weekly_run_${TODAY}*.log 2>/dev/null | head -1)"
        if [ -z "$tw_log" ]; then
            missed="$missed twice_weekly"
            log "  MISS: Twice-weekly research has not run today (expected by 18:00)"
        else
            log "  OK: Twice-weekly research ran today — $(basename "$tw_log")"
        fi
    fi

    # Weekly: Friday (dow=5), should run by 19:30
    if [ "$dow" -eq 5 ] && [ "$hour" -ge 20 ]; then
        local weekly_log
        weekly_log="$(ls -t "$LOG_DIR"/weekly_run_${TODAY}*.log 2>/dev/null | head -1)"
        if [ -z "$weekly_log" ]; then
            missed="$missed weekly"
            log "  MISS: Weekly research has not run today (expected by 18:30)"
        else
            log "  OK: Weekly research ran today — $(basename "$weekly_log")"
        fi
    fi

    if [ -n "$missed" ]; then
        echo "$missed"
        return 1
    fi
    return 0
}

recover_missed_jobs() {
    local missed="$1"
    for job in $missed; do
        local backoff
        backoff="$(should_backoff "job_$job")"
        if [ "$backoff" != "OK" ]; then
            log "  SKIP: $job catch-up in backoff or exhausted."
            continue
        fi

        case "$job" in
            forward_day)
                log_recovery "Firing catch-up: forward day (data + trading)..."
                launchctl kickstart "gui/$(id -u)/com.fql.forward-day" 2>/dev/null || true
                ;;
            daily)
                log_recovery "Firing catch-up: daily research..."
                launchctl kickstart "gui/$(id -u)/$DAILY_LABEL" 2>/dev/null || true
                ;;
            twice_weekly)
                log_recovery "Firing catch-up: twice-weekly research..."
                launchctl kickstart "gui/$(id -u)/$TWICE_WEEKLY_LABEL" 2>/dev/null || true
                ;;
            weekly)
                log_recovery "Firing catch-up: weekly research..."
                launchctl kickstart "gui/$(id -u)/$WEEKLY_LABEL" 2>/dev/null || true
                ;;
        esac

        # Give the job time to create its log file
        sleep 10

        # Verify
        local verify_log
        case "$job" in
            forward_day) verify_log="$(ls -t "$LOG_DIR"/forward_day_${TODAY}*.log 2>/dev/null | head -1)" ;;
            daily) verify_log="$(ls -t "$LOG_DIR"/daily_run_${TODAY}*.log 2>/dev/null | head -1)" ;;
            twice_weekly) verify_log="$(ls -t "$LOG_DIR"/twice_weekly_run_${TODAY}*.log 2>/dev/null | head -1)" ;;
            weekly) verify_log="$(ls -t "$LOG_DIR"/weekly_run_${TODAY}*.log 2>/dev/null | head -1)" ;;
        esac

        if [ -n "$verify_log" ]; then
            log_recovery "$job catch-up fired successfully — $(basename "$verify_log")"
            record_success "job_$job"
        else
            log_recovery "$job catch-up FAILED — no log produced"
            record_failure "job_$job"
        fi
    done
}

# ---- Main ----
log "=== FQL Watchdog Run ==="

ISSUES=0

# Check 1: Gateway
if ! check_gateway; then
    recover_gateway || true
    ISSUES=$((ISSUES + 1))
fi

# Check 2: Claw loop freshness
if ! check_claw_loop; then
    recover_claw_loop || true
    ISSUES=$((ISSUES + 1))
fi

# Check 3: Audit freshness (informational — no auto-recovery)
if ! check_audit; then
    log "  NOTE: Stale audit is informational. Claw loop recovery should fix this."
    ISSUES=$((ISSUES + 1))
fi

# Check 4: Missed research jobs
missed_jobs=""
if ! missed_jobs="$(check_missed_jobs)"; then
    if [ -n "$missed_jobs" ]; then
        recover_missed_jobs "$missed_jobs"
        ISSUES=$((ISSUES + 1))
    fi
fi

if [ "$ISSUES" -eq 0 ]; then
    log "=== All checks passed ==="
else
    log "=== Completed with $ISSUES issue(s) ==="
fi

# Generate compact recovery status report
bash "$ALGO_LAB/scripts/fql_recovery_status.sh" > /dev/null 2>&1 || true

# Clean old watchdog logs (keep 14 days)
find "$LOG_DIR" -name "watchdog_*.log" -mtime +14 -delete 2>/dev/null || true
find "$LOG_DIR" -name "recovery_actions.log" -size +1M -exec sh -c 'tail -500 "$1" > "$1.tmp" && mv "$1.tmp" "$1"' _ {} \; 2>/dev/null || true
