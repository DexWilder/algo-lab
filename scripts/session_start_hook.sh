#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
#  session_start_hook.sh — preload FQL state into Claude session context
#
#  Invoked by the SessionStart hook in .claude/settings.json. Runs the
#  read-only recovery inspection + tails the latest operator digest log,
#  then emits the combined output as the SessionStart additionalContext
#  so Claude has FQL state at session open without operator typing.
#
#  Strictly read-only: no mutations, no restarts, no auto-decisions,
#  no auto-commits. Hold-compliant.
# ──────────────────────────────────────────────────────────────────────
set -uo pipefail
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

REPO="/Users/chasefisher/projects/Algo Trading/algo-lab"

if ! cd "$REPO" 2>/dev/null; then
  jq -nc --arg msg "(fql session-start hook: cannot cd to $REPO)" \
    '{suppressOutput:true,hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$msg}}'
  exit 0
fi

OUTPUT=$(
  echo "=== fql_recover.sh ==="
  ./scripts/fql_recover.sh 2>&1
  echo
  echo "=== Latest operator digest ==="
  LATEST=$(ls -t research/logs/digest_*.log 2>/dev/null | head -1)
  if [ -n "$LATEST" ]; then
    echo "(file: $LATEST)"
    tail -30 "$LATEST"
  else
    echo "(no operator digest log found)"
  fi
)

jq -nc --arg c "$OUTPUT" \
  '{suppressOutput:true,systemMessage:"FQL state preloaded into context",hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$c}}'
