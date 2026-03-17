#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
#  start_forward_day.sh — One-command morning workflow
#
#  Runs the full daily forward paper trading pipeline:
#    1. Update data (fetch new bars from Databento)
#    2. Run forward paper trading engine
#    3. Display monitoring dashboard
#
#  Usage:
#      ./scripts/start_forward_day.sh              # normal run
#      ./scripts/start_forward_day.sh --cost-only   # check data cost only
#      ./scripts/start_forward_day.sh --skip-update  # skip data fetch
#      ./scripts/start_forward_day.sh --reset        # reset account state
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# ── Parse flags ───────────────────────────────────────────────────────
COST_ONLY=false
SKIP_UPDATE=false
RESET_FLAG=""

for arg in "$@"; do
    case "$arg" in
        --cost-only)   COST_ONLY=true ;;
        --skip-update) SKIP_UPDATE=true ;;
        --reset)       RESET_FLAG="--reset" ;;
        *)             echo "Unknown flag: $arg"; exit 1 ;;
    esac
done

# ── Startup banner ────────────────────────────────────────────────────
echo ""
echo "======================================================================"
echo "  FORWARD PAPER TRADING — DAILY WORKFLOW"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================================================"

# ── Pre-flight checks ────────────────────────────────────────────────
echo ""
echo "  Pre-flight checks..."

# Python available
if ! command -v python3 &>/dev/null; then
    echo "  FATAL: python3 not found"
    exit 1
fi

# Data directory exists
if [ ! -d "$ROOT/data/processed" ]; then
    echo "  FATAL: data/processed/ not found — run initial data fetch first"
    exit 1
fi

# Check that at least one data file exists
DATA_FILES=$(ls "$ROOT/data/processed/"*_5m.csv 2>/dev/null | wc -l | tr -d ' ')
if [ "$DATA_FILES" -eq 0 ]; then
    echo "  FATAL: No *_5m.csv files in data/processed/"
    exit 1
fi

# Show current account state if it exists
if [ -f "$ROOT/state/account_state.json" ]; then
    EQUITY=$(python3 -c "import json; s=json.load(open('$ROOT/state/account_state.json')); print(f\"\${s['equity']:,.2f}\")")
    RUNS=$(python3 -c "import json; s=json.load(open('$ROOT/state/account_state.json')); print(s.get('run_count', 0))")
    LAST=$(python3 -c "import json; s=json.load(open('$ROOT/state/account_state.json')); print(s.get('last_run', 'never'))")
    echo "  Account: equity=$EQUITY | runs=$RUNS | last=$LAST"
else
    echo "  Account: fresh start (no prior state)"
fi

echo "  Data files: $DATA_FILES assets"
echo "  Pre-flight: OK"

# ── Cost-only mode ────────────────────────────────────────────────────
if [ "$COST_ONLY" = true ]; then
    echo ""
    echo "----------------------------------------------------------------------"
    echo "  STEP 1: Checking data update cost"
    echo "----------------------------------------------------------------------"
    python3 scripts/update_daily_data.py --cost-only
    echo ""
    echo "  (Cost-only mode — no data fetched, no trading run)"
    exit 0
fi

# ── Step 1: Update data ──────────────────────────────────────────────
if [ "$SKIP_UPDATE" = false ]; then
    echo ""
    echo "----------------------------------------------------------------------"
    echo "  STEP 1/3: Updating market data"
    echo "----------------------------------------------------------------------"
    echo ""

    if ! python3 scripts/update_daily_data.py; then
        echo ""
        echo "  FATAL: Data update failed. Aborting."
        echo "  Fix the data issue and re-run, or use --skip-update to bypass."
        exit 1
    fi

    # Verify data integrity — check that all CSVs have recent data
    echo ""
    echo "  Verifying data integrity..."
    INTEGRITY_OK=true
    for CSV in "$ROOT/data/processed/"*_5m.csv; do
        BASENAME=$(basename "$CSV")
        LINES=$(wc -l < "$CSV" | tr -d ' ')
        if [ "$LINES" -lt 100 ]; then
            echo "  WARNING: $BASENAME has only $LINES lines"
            INTEGRITY_OK=false
        fi
    done

    if [ "$INTEGRITY_OK" = false ]; then
        echo "  FATAL: Data integrity check failed. Aborting."
        exit 1
    fi
    echo "  Data integrity: OK"
else
    echo ""
    echo "  (Skipping data update — using existing data)"
fi

# ── Step 2: Run forward paper trading ─────────────────────────────────
echo ""
echo "----------------------------------------------------------------------"
echo "  STEP 2/3: Running forward paper trading engine"
echo "----------------------------------------------------------------------"
echo ""

if ! python3 run_forward_paper.py $RESET_FLAG; then
    echo ""
    echo "  ERROR: Forward runner failed."
    echo "  Check logs/ for details."
    exit 1
fi

# ── Step 3: Display monitor ──────────────────────────────────────────
echo ""
echo "----------------------------------------------------------------------"
echo "  STEP 3/3: Daily monitoring dashboard"
echo "----------------------------------------------------------------------"

python3 scripts/monitor.py --history 7

# ── End-of-day summary ────────────────────────────────────────────────
echo ""
echo "======================================================================"
echo "  DAILY WORKFLOW COMPLETE — $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================================================"
echo ""
echo "  Next steps:"
echo "    - Review the monitor output above"
echo "    - Check logs/ for detailed trade and signal data"
echo "    - Run again tomorrow: ./scripts/start_forward_day.sh"
echo ""
