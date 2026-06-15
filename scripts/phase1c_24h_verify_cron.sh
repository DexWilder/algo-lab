#!/bin/bash
# Phase 1C 24h post-wiring verifier — launchd wrapper.
# Runs the verification (stage-and-alert ONLY — never --execute-rollback),
# commits/pushes the verdict packet, alerts on FAIL, and self-disables on OK.
# Temporary: removes itself from LaunchAgents once PHASE1C_24H_VERIFY_OK.
set -uo pipefail

REPO="/Users/chasefisher/projects/Algo Trading/algo-lab"
LABEL="com.fql.phase1c-24h-verify"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
PY="/usr/local/bin/python3"
GIT="/usr/bin/git"

cd "$REPO" || exit 1

# Verification-only. NO --execute-rollback: a FAIL stages rollback + alerts; it
# never rewrites a truth surface unattended (human confirmation required).
OUT="$("$PY" research/phase1c_24h_verify.py 2>&1)"
echo "$OUT"
VERDICT="$(printf '%s\n' "$OUT" | grep -oE 'PHASE1C_24H_VERIFY_(OK|PENDING|FAIL)' | head -1)"

# Commit + push the verdict packet (best-effort; local commit is the source of truth).
"$GIT" add docs/fql_forge/PHASE1C_24H_VERIFY_*.md 2>/dev/null
if ! "$GIT" diff --cached --quiet 2>/dev/null; then
    "$GIT" commit -q -m "Phase 1C 24h verify: ${VERDICT:-UNKNOWN} ($(date +%Y-%m-%d))" \
        -m "Automated launchd verifier. Stage-and-alert only; no unattended rollback." || true
    "$GIT" push -q origin main 2>/dev/null || echo "WARN: push failed (commit is local); verdict packet still written."
fi

case "$VERDICT" in
    PHASE1C_24H_VERIFY_OK)
        /usr/bin/osascript -e 'display notification "Phase 1C verified OK — disabling temporary verifier." with title "FQL Phase 1C"' 2>/dev/null || true
        # Self-disable: remove from running domain + retire the plist so it won't reload.
        /bin/launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || /bin/launchctl unload "$PLIST" 2>/dev/null || true
        /bin/mv "$PLIST" "$REPO/research/logs/$LABEL.plist.retired_$(date +%Y%m%d)" 2>/dev/null || true
        echo "Phase 1C verifier self-disabled (OK)."
        ;;
    PHASE1C_24H_VERIFY_FAIL)
        /usr/bin/osascript -e 'display notification "Phase 1C 24h verify FAILED — rollback STAGED, human confirmation required." with title "⚠️ FQL Phase 1C FAIL" sound name "Basso"' 2>/dev/null || true
        echo "ALERT: PHASE1C_24H_VERIFY_FAIL — rollback staged, NOT executed. Human confirmation required."
        ;;
    *)
        echo "PENDING — awaiting live forward-runner output; verifier remains scheduled."
        ;;
esac
