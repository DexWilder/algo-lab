"""XB-ORB-EMA-CHANDELIER — Crossbred: ORB Breakout + EMA Slope + Chandelier Exit.

EXPERIMENTAL_FORWARD_CLOCK candidate (authorized 2026-05-28).

Archetype: PAYOFF_RATIO_WORKHORSE_FREQUENCY.

This candidate fails the standard workhorse median-trade-≥0 gate at the
full-sample level (median -$4.74 on MNQ; cross-asset family sweep confirmed
negative median on MES, MGC, M2K as well). It is NOT eligible for
paper-readiness under the existing workhorse rubric. It is forward-clocked
to determine whether FQL should codify a third archetype for payoff-ratio
strategies that operate at workhorse trade frequency.

Evidence (2026-05-28 measurement):
- net PF 1.561 on 1,211 trades over 6 years on MNQ
- cost ratio 7.7% (slip=1, comm=$0.62)
- concentration clean: top-3 14.7%, top-10 31.9%, max-year 30.0%
- 7 of 8 years positive
- walk-forward: H1 PF 1.257 (2019-2022, crisis-heavy); H2 PF 1.841 (2023-2026)

Decision rule on forward evidence: at 30 forward trades, do NOT auto-promote.
Evaluate whether a payoff-ratio archetype deserves codified gates first.

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

# Module-level params matching the 2026-05-28 measurement run.
# stop_mult=2.0 selected by the xb_orb stop-sweep study (see xb_orb_ema_ladder
# for the underlying study); the entry+filter slot is shared with the Ladder
# anchor, only the exit changes.
STOP_MULT = 2.0
TARGET_MULT = 4.0
TRAIL_MULT = 2.5
CHANDELIER_MULT = 3.0


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate ORB breakout + EMA slope + chandelier exit signals."""
    params = {
        "stop_mult": STOP_MULT,
        "target_mult": TARGET_MULT,
        "trail_mult": TRAIL_MULT,
        "chandelier_mult": CHANDELIER_MULT,
    }
    return generate_crossbred_signals(
        df,
        entry_name="orb_breakout",
        exit_name="chandelier",
        filter_name="ema_slope",
        params=params,
    )
