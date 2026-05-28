"""XB-ORB-EMA-ATRTRAIL — Crossbred: ORB Breakout + EMA Slope + ATR Trail.

EXPERIMENTAL_FORWARD_CLOCK candidate (Track 2, authorized 2026-05-28).

Archetype: PAYOFF_RATIO_WORKHORSE_FREQUENCY.

Third Track 2 candidate. Same entry+filter as ORB-EMA-Chandelier-MNQ but
different exit (ATR-trail vs chandelier) AND different asset (MES vs MNQ).
Tests whether the payoff-ratio shape we observed on ORB+chandelier-MNQ
generalizes to a different exit mechanism on a different asset.

Evidence (2026-05-28 Phase 3 Offensive Forge Sprint v2, upgraded screen):
- net PF 1.413 on 1,242 trades over 6 years on MES
- cost ratio (slip=1, comm=$0.62 — MES standard)
- concentration clean: top-3 11.1%, top-10 ~33%, max-year 25.4%
- walk-forward: H1 PF 1.313 (median -$11.74); H2 PF 1.509 (median +$1.51)
- median structurally negative (-$4.99), mean positive (+$23.69) — payoff-ratio

Chosen over TimeStop-MES (PF 1.36) due to higher PF and better H1/H2 stability.
Both are in the same MES+ORB+EMA cluster per correlation guard — picking 1.

Decision rule on forward evidence: at 30 forward trades, do NOT auto-promote.
Triggers archetype review per the 2026-05-28 Track 2 doctrine.

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

# Module-level params matching the 2026-05-28 sprint measurement.
STOP_MULT = 2.0
TARGET_MULT = 4.0
TRAIL_MULT = 2.5


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate ORB breakout + EMA slope + ATR-trail exit signals."""
    params = {
        "stop_mult": STOP_MULT,
        "target_mult": TARGET_MULT,
        "trail_mult": TRAIL_MULT,
    }
    return generate_crossbred_signals(
        df,
        entry_name="orb_breakout",
        exit_name="atr_trail",
        filter_name="ema_slope",
        params=params,
    )
