"""XB-PB-EMA-TIMESTOP — Crossbred: PB Pullback + EMA Slope + Time Stop.

Phase 12 crossbreeding candidate #15.
Entry: PB-style pullback to fast EMA in trend direction.
Filter: Daily EMA slope (longs in uptrend, shorts in downtrend).
Exit: Time stop (max 30 bars) with ATR trail fallback.

Best raw result: MES-short, PF=1.82, Sharpe=3.56, 123 trades, 10-bar hold.
Strategic value: Fills MES parent gap in portfolio.

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
STOP_MULT = 1.5
TARGET_MULT = 2.5
TRAIL_MULT = 2.0
MAX_BARS = 30
PB_PROXIMITY = 0.5


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate PB pullback + EMA slope + time stop signals."""
    params = {
        "stop_mult": STOP_MULT,
        "target_mult": TARGET_MULT,
        "trail_mult": TRAIL_MULT,
        "max_bars": MAX_BARS,
        "pb_proximity": PB_PROXIMITY,
    }
    return generate_crossbred_signals(
        df,
        entry_name="pb_pullback",
        exit_name="time_stop",
        filter_name="ema_slope",
        params=params,
    )
