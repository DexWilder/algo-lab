#!/bin/bash
# FQL Recovery Status — compact at-a-glance health report
# Usage: bash scripts/fql_recovery_status.sh
#
# Writes to: ~/openclaw-intake/inbox/_recovery_status.md
# Also prints to stdout.

set -uo pipefail
# Note: -e omitted intentionally. ls|head triggers SIGPIPE with pipefail
# which would kill the script. We handle errors explicitly instead.

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export HOME="/Users/chasefisher"

ALGO_LAB="/Users/chasefisher/projects/Algo Trading/algo-lab"
LOG_DIR="$ALGO_LAB/research/logs"
STATE_FILE="$LOG_DIR/.watchdog_state.json"
RECOVERY_LOG="$LOG_DIR/recovery_actions.log"
OUTPUT="$HOME/openclaw-intake/inbox/_recovery_status.md"
NOW="$(date '+%Y-%m-%d %H:%M:%S')"

# ---- Gather data ----

# Gateway
GW_PID="$(launchctl list 2>/dev/null | grep ai.openclaw.gateway | awk '{print $1}')"
GW_HEALTH="$(curl -s --max-time 3 http://localhost:18789/health 2>/dev/null || echo '{}')"
if echo "$GW_HEALTH" | grep -q '"ok":true'; then
    GW_STATUS="HEALTHY (PID $GW_PID)"
else
    GW_STATUS="DOWN"
fi

# Claw loop
LATEST_CLAW="$(ls -t "$LOG_DIR"/claw_loop_*.log 2>/dev/null | head -1)"
if [ -n "$LATEST_CLAW" ]; then
    CLAW_AGE="$(python3 -c "import os,time; print(f'{(time.time()-os.path.getmtime(\"$LATEST_CLAW\"))/60:.0f}m')" 2>/dev/null || echo "?")"
    CLAW_FILE="$(basename "$LATEST_CLAW")"
    if [ "${CLAW_AGE%m}" -le 45 ] 2>/dev/null; then
        CLAW_STATUS="FRESH ($CLAW_AGE ago)"
    else
        CLAW_STATUS="STALE ($CLAW_AGE ago)"
    fi
else
    CLAW_STATUS="NO LOGS"
    CLAW_FILE="none"
    CLAW_AGE="?"
fi

# Watchdog
LATEST_WD="$(ls -t "$LOG_DIR"/watchdog_*.log 2>/dev/null | head -1)"
if [ -n "$LATEST_WD" ]; then
    WD_LAST="$(tail -1 "$LATEST_WD" | grep -o '^\[[^]]*\]' | tr -d '[]')"
    WD_RESULT="$(tail -1 "$LATEST_WD")"
else
    WD_LAST="never"
    WD_RESULT="no watchdog logs"
fi

# Last recovery action
if [ -f "$RECOVERY_LOG" ] && [ -s "$RECOVERY_LOG" ]; then
    LAST_RECOVERY="$(tail -1 "$RECOVERY_LOG")"
    RECOVERY_COUNT="$(wc -l < "$RECOVERY_LOG" | tr -d ' ')"
else
    LAST_RECOVERY="none"
    RECOVERY_COUNT="0"
fi

# Backoff state
if [ -f "$STATE_FILE" ]; then
    FAILURES="$(python3 -c "
import json
state = json.load(open('$STATE_FILE'))
if not state:
    print('0 (clean)')
else:
    parts = []
    for comp, info in state.items():
        f = info.get('failures', 0)
        if f > 0:
            parts.append(f'{comp}={f}')
    if parts:
        print(', '.join(parts))
    else:
        print('0 (clean)')
" 2>/dev/null || echo "?")"
else
    FAILURES="0 (clean)"
fi

# Scheduled jobs
TODAY="$(date +%Y%m%d)"
DAILY_LOG="$(ls -t "$LOG_DIR"/daily_run_${TODAY}*.log 2>/dev/null | head -1)"
DAILY_STATUS="$([ -n "$DAILY_LOG" ] && echo "RAN ($(basename "$DAILY_LOG"))" || echo "NOT YET")"

# Service counts
SVC_COUNT="$(launchctl list 2>/dev/null | grep -c 'com.fql\|ai.openclaw' || echo 0)"

# ---- Format report ----

REPORT="# FQL Recovery Status
*Generated: $NOW*

| Component | Status |
|-----------|--------|
| **Gateway** | $GW_STATUS |
| **Claw loop** | $CLAW_STATUS — \`$CLAW_FILE\` |
| **Watchdog** | Last: $WD_LAST |
| **Daily research** | $DAILY_STATUS |
| **Services loaded** | $SVC_COUNT |

## Recovery History

| Metric | Value |
|--------|-------|
| Total recovery actions | $RECOVERY_COUNT |
| Last recovery | $LAST_RECOVERY |
| Consecutive failures | $FAILURES |

## Launchd Services

\`\`\`
$(launchctl list 2>/dev/null | grep 'com.fql\|ai.openclaw' | awk '{printf "  %-6s %-4s %s\n", $1, $2, $3}')
\`\`\`
"

echo "$REPORT" > "$OUTPUT"
echo "$REPORT"
