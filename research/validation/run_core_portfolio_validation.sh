#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
#  Run extended-history validation battery on all 6 core portfolio strategies.
#
#  Purpose: Verify that our backbone/enhancer/probation edges are
#  structural (survive 6.7 years of data) — not recent-regime illusions.
#
#  Usage:
#      ./research/validation/run_core_portfolio_validation.sh
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

VENV="python3"
BATTERY="${ROOT}/research/validation/run_validation_battery.py"

echo "═══════════════════════════════════════════════════════════════"
echo "  FQL Core Portfolio Extended-History Validation"
echo "  Data: 6.7 years (2019-07 → 2026-03)"
echo "  Date: $(date '+%Y-%m-%d %H:%M')"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Strategy 1: VWAP-MNQ-Long (backbone — 41.7% of trades, 32.4% of PnL)
echo "▸ [1/6] VWAP-MNQ-Long (backbone)"
$VENV "$BATTERY" --strategy vwap_trend --asset MNQ --mode long 2>&1 | tail -5
echo ""

# Strategy 2: XB-PB-EMA-MES-Short (backbone — 22.5% of trades, 15.5% of PnL)
echo "▸ [2/6] XB-PB-EMA-MES-Short (backbone)"
$VENV "$BATTERY" --strategy xb_pb_ema_timestop --asset MES --mode short 2>&1 | tail -5
echo ""

# Strategy 3: ORB-MGC-Long (core — 15.9% of trades, 16.9% of PnL)
echo "▸ [3/6] ORB-MGC-Long (core)"
$VENV "$BATTERY" --strategy orb_009 --asset MGC --mode long 2>&1 | tail -5
echo ""

# Strategy 4: Donchian-MNQ-Long-GRINDING (probation — 12.0% of trades, 13.9% of PnL)
echo "▸ [4/6] Donchian-MNQ-Long-GRINDING (probation)"
$VENV "$BATTERY" --strategy donchian_trend --asset MNQ --mode long --grinding --exit-variant profit_ladder 2>&1 | tail -5
echo ""

# Strategy 5: BB-EQ-MGC-Long (enhancer/tail — 5.6% of trades, 16.6% of PnL)
echo "▸ [5/6] BB-EQ-MGC-Long (enhancer/tail)"
$VENV "$BATTERY" --strategy bb_equilibrium --asset MGC --mode long 2>&1 | tail -5
echo ""

# Strategy 6: PB-MGC-Short (core — 2.3% of trades, 4.8% of PnL)
echo "▸ [6/6] PB-MGC-Short (core)"
$VENV "$BATTERY" --strategy pb_trend --asset MGC --mode short 2>&1 | tail -5
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "  All 6 core validations complete."
echo "  Results: research/validation/*_validation.json"
echo "═══════════════════════════════════════════════════════════════"
