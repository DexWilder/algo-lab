#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
#  daily_runner.sh — Automated daily lab operations
#
#  Runs after market close (recommended: 4:30 PM ET via cron/launchd)
#
#  Steps:
#    1. Forward validation run (data update + paper trading + monitor)
#    2. Daily health report
#    3. Forward scorecard (drift check)
#    4. Auto-review report (daily mode)
#
#  Usage:
#      ./schedulers/daily_runner.sh              # full daily run
#      ./schedulers/daily_runner.sh --skip-forward  # skip forward run, analysis only
#
#  Cron example (4:30 PM ET weekdays):
#      30 16 * * 1-5 /path/to/algo-lab/schedulers/daily_runner.sh >> /path/to/algo-lab/logs/scheduler.log 2>&1
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SKIP_FORWARD=false
for arg in "$@"; do
    case "$arg" in
        --skip-forward) SKIP_FORWARD=true ;;
        *)              echo "Unknown flag: $arg"; exit 1 ;;
    esac
done

DATE=$(date '+%Y-%m-%d')
TIME=$(date '+%H:%M:%S')

echo ""
echo "======================================================================"
echo "  DAILY LAB RUNNER — $DATE $TIME"
echo "======================================================================"

# ── Step 1: Forward validation run ──────────────────────────────────
if [ "$SKIP_FORWARD" = false ]; then
    echo ""
    echo "  [1/4] Forward validation run..."
    echo "  ────────────────────────────────────────"
    if ! bash scripts/start_forward_day.sh; then
        echo "  WARNING: Forward run had errors. Continuing with analysis."
    fi
else
    echo ""
    echo "  [1/4] Skipping forward run (--skip-forward)"
fi

# ── Step 2: Health report ───────────────────────────────────────────
echo ""
echo "  [2/4] Health report..."
echo "  ────────────────────────────────────────"
python3 scripts/forward_health_report.py 2>/dev/null || echo "  WARNING: Health report failed"

# ── Step 3: Forward scorecard ───────────────────────────────────────
echo ""
echo "  [3/4] Forward scorecard..."
echo "  ────────────────────────────────────────"
python3 scripts/forward_scorecard.py 2>/dev/null || echo "  WARNING: Scorecard failed"

# ── Step 4: Auto-review report ──────────────────────────────────────
echo ""
echo "  [4/4] Daily review report..."
echo "  ────────────────────────────────────────"
if [ -f "$ROOT/research/auto_review_report.py" ]; then
    python3 research/auto_review_report.py --daily --save 2>/dev/null || echo "  WARNING: Auto-review failed"
else
    echo "  (auto_review_report.py not yet available)"
fi

# ── Summary ─────────────────────────────────────────────────────────
echo ""
echo "======================================================================"
echo "  DAILY RUN COMPLETE — $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================================================"
echo ""
