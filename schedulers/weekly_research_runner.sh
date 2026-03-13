#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
#  weekly_research_runner.sh — Automated weekly research diagnostics
#
#  Runs once per week (recommended: Saturday morning via cron/launchd)
#
#  Steps:
#    1. Strategy contribution analysis
#    2. Portfolio correlation matrix
#    3. Trade duration analysis
#    4. Edge decay monitor
#    5. Opportunity scanner
#    6. Weekly review report
#
#  Usage:
#      ./schedulers/weekly_research_runner.sh
#
#  Cron example (Saturday 9 AM):
#      0 9 * * 6 /path/to/algo-lab/schedulers/weekly_research_runner.sh >> /path/to/algo-lab/logs/scheduler.log 2>&1
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DATE=$(date '+%Y-%m-%d')
TIME=$(date '+%H:%M:%S')

echo ""
echo "======================================================================"
echo "  WEEKLY RESEARCH RUNNER — $DATE $TIME"
echo "======================================================================"

# ── Step 1: Strategy contribution ───────────────────────────────────
echo ""
echo "  [1/6] Strategy contribution analysis..."
echo "  ────────────────────────────────────────"
python3 research/strategy_contribution_analyzer.py 2>/dev/null || echo "  WARNING: Contribution analyzer failed"

# ── Step 2: Correlation matrix ──────────────────────────────────────
echo ""
echo "  [2/6] Portfolio correlation matrix..."
echo "  ────────────────────────────────────────"
python3 research/portfolio_correlation_matrix.py --include-probation --save 2>/dev/null || echo "  WARNING: Correlation matrix failed"

# ── Step 3: Trade duration ──────────────────────────────────────────
echo ""
echo "  [3/6] Trade duration analysis..."
echo "  ────────────────────────────────────────"
python3 research/trade_duration_analysis.py 2>/dev/null || echo "  WARNING: Duration analysis failed"

# ── Step 4: Edge decay ──────────────────────────────────────────────
echo ""
echo "  [4/6] Edge decay monitor..."
echo "  ────────────────────────────────────────"
python3 research/edge_decay_monitor.py --save 2>/dev/null || echo "  WARNING: Edge decay monitor failed"

# ── Step 5: Opportunity scanner ─────────────────────────────────────
echo ""
echo "  [5/6] Opportunity scanner..."
echo "  ────────────────────────────────────────"
if [ -f "$ROOT/research/opportunity_scanner.py" ]; then
    python3 research/opportunity_scanner.py --save 2>/dev/null || echo "  WARNING: Opportunity scanner failed"
else
    echo "  (opportunity_scanner.py not yet available)"
fi

# ── Step 6: Weekly review report ────────────────────────────────────
echo ""
echo "  [6/6] Weekly review report..."
echo "  ────────────────────────────────────────"
if [ -f "$ROOT/research/auto_review_report.py" ]; then
    python3 research/auto_review_report.py --weekly --save 2>/dev/null || echo "  WARNING: Weekly review failed"
else
    echo "  (auto_review_report.py not yet available)"
fi

# ── Summary ─────────────────────────────────────────────────────────
echo ""
echo "======================================================================"
echo "  WEEKLY RESEARCH COMPLETE — $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================================================"
echo ""
echo "  Reports saved to:"
echo "    - research/portfolio_correlation_results.json"
echo "    - research/edge_decay_report.json"
echo "    - research/opportunity_scan_results.json"
echo "    - reports/weekly_$DATE.md"
echo ""
