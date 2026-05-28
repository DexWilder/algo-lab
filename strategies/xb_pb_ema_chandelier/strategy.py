"""XB-PB-EMA-CHANDELIER — Crossbred: PB Pullback + EMA Slope + Chandelier Exit.

EXPERIMENTAL_FORWARD_CLOCK candidate (Track 2, authorized 2026-05-28).

Archetype: PAYOFF_RATIO_WORKHORSE_FREQUENCY.

Second Track 2 candidate. Different entry family (pullback) than the first
Track 2 candidate (XB-ORB-EMA-Chandelier-MNQ, ORB entry). Tests whether the
payoff-ratio shape we observed on ORB+chandelier generalizes across entry
families on the same asset.

Evidence (2026-05-28 Offensive Forge Sprint v1, upgraded screen):
- net PF 1.341 on 1,478 trades over 6 years on MNQ
- cost ratio 12.2% (slip=1, comm=$0.62)
- concentration clean: top-3 10.9%, top-10 31.4%, max-year 35.8%
- 7 of 8 years positive
- walk-forward: H1 PF 1.201 (median -$13.74); H2 PF 1.469 (median -$13.74)
- median structurally negative, mean positive — confirms payoff-ratio shape

Sample is larger than ORB-Chandelier (1478 vs 1211) and PF is lower (1.34 vs
1.56). The PB entry generates more setups but with worse per-trade PnL
distribution. Concentration and walk-forward halves both above gate.

Decision rule on forward evidence: at 30 forward trades, do NOT auto-promote.
Triggers archetype review per the 2026-05-28 doctrine.

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
CHANDELIER_MULT = 3.0
PB_PROXIMITY = 0.5


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate PB pullback + EMA slope + chandelier exit signals."""
    params = {
        "stop_mult": STOP_MULT,
        "target_mult": TARGET_MULT,
        "trail_mult": TRAIL_MULT,
        "chandelier_mult": CHANDELIER_MULT,
        "pb_proximity": PB_PROXIMITY,
    }
    return generate_crossbred_signals(
        df,
        entry_name="pb_pullback",
        exit_name="chandelier",
        filter_name="ema_slope",
        params=params,
    )
