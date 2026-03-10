"""XB-PB-SQUEEZE-CHAND — Crossbred: PB Pullback + BB Squeeze + Chandelier Exit.

Phase 12 crossbreeding candidate #14.
Entry: PB-style pullback to fast EMA in trend direction.
Filter: BB bandwidth squeeze (only trade when volatility is compressed).
Exit: Chandelier exit (highest high / lowest low - ATR × mult).

Best raw result: MGC-long, PF=1.80, Sharpe=2.73, 193 trades, 19-bar hold.
Strategic value: Volatility compression specialist, fills genome gap, high trade count.

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

PARAMS = {
    "stop_mult": 1.5,
    "target_mult": 3.0,
    "chandelier_mult": 3.0,
    "pb_proximity": 0.5,
    "bw_threshold": 40,
}


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate PB pullback + squeeze + chandelier signals."""
    return generate_crossbred_signals(
        df,
        entry_name="pb_pullback",
        exit_name="chandelier",
        filter_name="bandwidth_squeeze",
        params=PARAMS,
    )
