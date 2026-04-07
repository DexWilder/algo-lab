"""XB-ORB-EMA-LADDER — Crossbred: ORB Breakout + EMA Slope + Profit Ladder.

Phase 12 crossbreeding candidate #1.
Entry: ORB-style breakout (price breaks opening range high/low).
Filter: Daily EMA slope (longs in uptrend, shorts in downtrend).
Exit: Profit ladder (ratcheting stops at 1R/2R/3R milestones).

Best raw result: MNQ-short, PF=1.92, Sharpe=3.80, 117 trades, 59-bar hold.
Strategic value: Trend-follower DNA (59-bar hold), multi-asset profitable.

PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals

TICK_SIZE = 0.25  # Patched per asset by runner

# Module-level params (perturbable by validation battery)
# Upgraded 2026-04-07 from 0.5 to 2.0 after stop-sweep study (see
# research/data/xb_orb_stop_sweep_results.json). stop=2.0 was the best
# variant by both avg PF (1.548 vs 1.454) and avg drawdown duration
# (250d vs 314d) across 4-asset cross-validation (MNQ/MES/MGC/M2K).
# The upgrade sits inside a broad stability plateau (10/10 clean variants
# across stop_mult 0.1-3.0), so this is a baseline selection, not a fit.
#
# NOTE: TARGET_MULT and TRAIL_MULT are currently IGNORED by
# exit_profit_ladder (fixed 1R/2R/3R ratchets). Queued as research item
# "exit_profit_ladder bug" — fixing will unlock a new optimization surface.
STOP_MULT = 2.0
TARGET_MULT = 4.0
TRAIL_MULT = 2.5


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate ORB breakout + EMA slope + profit ladder signals."""
    params = {
        "stop_mult": STOP_MULT,
        "target_mult": TARGET_MULT,
        "trail_mult": TRAIL_MULT,
    }
    return generate_crossbred_signals(
        df,
        entry_name="orb_breakout",
        exit_name="profit_ladder",
        filter_name="ema_slope",
        params=params,
    )
