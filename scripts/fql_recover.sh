#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
#  fql_recover.sh — Post-restart recovery inspection
#
#  Run after a Mac/launchd restart to confirm the FQL platform came back
#  up clean. Inspect-only: no mutations, no loads/reloads, no runtime
#  actions. Hold-compliant.
#
#  Steps:
#    1. Repo path check
#    2. git status (summary)
#    3. launchd job presence (FQL + OpenClaw)
#    4. Treasury rolldown stdout/stderr sanity
#    5. Watchdog state summary
#
#  Allowlisted carve-outs (do not fail the run):
#    - watchdog WARN: "Stale data: ES_5m" — reference symbol; live runner
#      universe is micros (MES, not ES).
#
#  Exit codes:
#    0 — OK, or only allowlisted warnings
#    1 — real issue surfaced
#
#  Usage: ./scripts/fql_recover.sh
# ──────────────────────────────────────────────────────────────────────
set -uo pipefail
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

ROOT="/Users/chasefisher/projects/Algo Trading/algo-lab"
WATCHDOG_STATE="$ROOT/research/data/watchdog_state.json"
TREAS_OUT="$ROOT/research/logs/treasury_rolldown_monthly_stdout.log"
TREAS_ERR="$ROOT/research/logs/treasury_rolldown_monthly_stderr.log"

EXPECTED_FQL_JOBS=(
  com.fql.claw-control-loop
  com.fql.source-helpers
  com.fql.operator-digest
  com.fql.watchdog
  com.fql.weekly-research
  com.fql.forward-day
  com.fql.treasury-rolldown-monthly
  com.fql.daily-research
  com.fql.twice-weekly-research
)
EXPECTED_OPENCLAW="ai.openclaw.gateway"

FAIL=0
WARN_ALLOWLISTED=0

section() { printf "\n── %s ──\n" "$1"; }
ok()      { printf "  OK    %s\n" "$1"; }
warn()    { printf "  WARN  %s\n" "$1"; WARN_ALLOWLISTED=1; }
fail()    { printf "  FAIL  %s\n" "$1"; FAIL=1; }

# 1. repo path
section "repo"
if [ -d "$ROOT/.git" ]; then
  ok "$ROOT"
  cd "$ROOT"
else
  fail "not a git repo: $ROOT"
  echo; echo "FAIL"; exit 1
fi

# 2. git status
section "git"
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
DIRTY="$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
ok "branch=$BRANCH dirty=$DIRTY files"

# 3. launchd presence
section "launchd"
LIST="$(launchctl list 2>/dev/null)"
for j in "${EXPECTED_FQL_JOBS[@]}"; do
  if printf "%s\n" "$LIST" | awk '{print $3}' | grep -qx "$j"; then
    ok "$j"
  else
    fail "missing: $j"
  fi
done
if printf "%s\n" "$LIST" | awk '{print $3}' | grep -qx "$EXPECTED_OPENCLAW"; then
  GW_PID="$(printf "%s\n" "$LIST" | awk -v n="$EXPECTED_OPENCLAW" '$3==n {print $1}')"
  if [ "$GW_PID" = "-" ]; then
    fail "$EXPECTED_OPENCLAW registered but not running"
  else
    ok "$EXPECTED_OPENCLAW (PID $GW_PID)"
  fi
else
  fail "missing: $EXPECTED_OPENCLAW"
fi

# 4. treasury rolldown logs
section "treasury rolldown"
if [ ! -f "$TREAS_OUT" ]; then
  fail "stdout missing: $TREAS_OUT"
elif grep -q "Traceback" "$TREAS_OUT"; then
  fail "stdout contains Traceback"
else
  ok "stdout clean ($(wc -l <"$TREAS_OUT" | tr -d ' ') lines)"
fi
if [ ! -f "$TREAS_ERR" ]; then
  fail "stderr missing: $TREAS_ERR"
elif [ -s "$TREAS_ERR" ]; then
  fail "stderr non-empty ($(wc -l <"$TREAS_ERR" | tr -d ' ') lines)"
else
  ok "stderr empty"
fi

# 5. watchdog state
section "watchdog"
if [ ! -f "$WATCHDOG_STATE" ]; then
  fail "watchdog state missing: $WATCHDOG_STATE"
else
  python3 - "$WATCHDOG_STATE" <<'PY'
import json, sys
state = json.load(open(sys.argv[1]))
overall = state.get("overall", "UNKNOWN")
ts      = state.get("timestamp", "?")
safe    = state.get("safe_mode", None)
print(f"  ts={ts} overall={overall} safe_mode={safe}")
ALLOWLIST_SUBSTR = "Stale data: ES_5m"
exit_code = 0   # 0 ok, 1 warn-allowlisted, 2 real fail
for name, c in state.get("checks", {}).items():
    s = c.get("status", "?")
    d = c.get("detail", "")
    if s == "OK":
        print(f"  OK    {name}: {d}")
    elif s == "WARN":
        if ALLOWLIST_SUBSTR in d:
            print(f"  WARN  {name}: {d}  [allowlisted]")
            exit_code = max(exit_code, 1)
        else:
            print(f"  FAIL  {name}: {d}  [unallowlisted WARN]")
            exit_code = max(exit_code, 2)
    else:
        print(f"  FAIL  {name}: {s} {d}")
        exit_code = max(exit_code, 2)
sys.exit(exit_code)
PY
  rc=$?
  [ "$rc" -eq 2 ] && FAIL=1
  [ "$rc" -eq 1 ] && WARN_ALLOWLISTED=1
fi

# summary
echo
if [ "$FAIL" -eq 1 ]; then
  echo "FAIL"
  exit 1
elif [ "$WARN_ALLOWLISTED" -eq 1 ]; then
  echo "WARN (allowlisted)"
  exit 0
else
  echo "OK"
  exit 0
fi
