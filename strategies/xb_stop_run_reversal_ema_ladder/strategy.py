"""XB-STOP-RUN-REVERSAL-EMA-LADDER — Crossbred: Stop-Run Reversal + EMA Slope + Profit Ladder.

Lane A Wave 1 PRIMARY daily workhorse (validated 2026-06-12 batch).
Registry strategy_id (proposed, confirmed at Phase 1C wiring):
    WH-MNQ-stop_run_reversal-ema_slope-PL

Entry:  stop_run_reversal — liquidity sweep + reclaim, traded in the REVERSAL
        direction (sweep-up+reclaim -> SHORT, sweep-down+reclaim -> LONG).
Filter: ema_slope — daily EMA20 slope (longs in uptrend, shorts in downtrend).
Exit:   profit_ladder — ratcheting stops at 1R/2R/3R milestones ("classic").

PORT FIDELITY NOTE (Phase 1A, 2026-06-13):
    This production module is a thin adapter. It calls the EXACT research
    primitive `generate_crossbred_signals` with the EXACT validated arguments
    used by the DATA_AUDIT_GREEN harness (cycle 2026-06-12a,
    `regenerate_candidate("MNQ", "xb", entry="stop_run_reversal")`):

        generate_crossbred_signals(
            df,
            entry_name="stop_run_reversal",
            exit_name="profit_ladder",
            filter_name="ema_slope",
            params={},          # <-- ALL DEFAULTS: sweep_buffer=0.0, stop_mult=1.5,
        )                       #     target_mult=3.0, ladder_style="classic"

    Because the signal/exit logic is the same code path as the validated
    research run, logic divergence is impossible by construction. The only
    surface that can diverge is the live-execution adapter (how the runner
    feeds bars and calls run_backtest), which is verified empirically by
    research/forge_cycle_2026-06-13_phase1a_port_verification.py against:
      (a) the canonical audit path, and
      (b) the committed cycle-11r baseline (n=1414, PF 1.477, median +$15.51).

    DATA_AUDIT_GREEN proved reproducibility WITHIN the current feed. It does
    NOT prove independent feed correctness. Clean enough to paper. Not yet
    clean enough for capital (live/prop gated by DSCL §7).

    IMPORTANT: When this strategy is wired (Phase 1C), its registry
    execution_config MUST set exit_variant=None so the forward runner routes
    signal generation through THIS module's generate_signals(). The runner's
    `exit_variant == "profit_ladder"` branch is a legacy donchian-entry path
    and would silently replace stop_run_reversal entries with donchian ones.

PLATFORM-AGNOSTIC: Pure signal logic only. Asset-independent (the primitive
operates on any 5-min OHLCV df); cost/point_value are applied by run_backtest
from the canonical engine/asset_config.py via symbol.
"""

import sys
from pathlib import Path

import numpy as np  # noqa: F401  (kept for parity with incumbent module shape)
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals

TICK_SIZE = 0.25  # Patched per asset by runner (vestigial for the crossbred path)

# Validated baseline used params={} (all primitive defaults). Mirrored here as
# an explicit, auditable record. Passing this dict is identical to passing {}
# because every value equals the primitive's documented default.
ENTRY_NAME = "stop_run_reversal"
EXIT_NAME = "profit_ladder"
FILTER_NAME = "ema_slope"
PARAMS: dict = {}  # sweep_buffer=0.0, stop_mult=1.5, target_mult=3.0, ladder_style="classic"


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate stop-run-reversal + ema_slope + profit_ladder signals.

    Faithful port: delegates to the same generate_crossbred_signals primitive
    and arguments that produced the validated, DATA_AUDIT_GREEN baseline.
    """
    return generate_crossbred_signals(
        df,
        entry_name=ENTRY_NAME,
        exit_name=EXIT_NAME,
        filter_name=FILTER_NAME,
        params=PARAMS,
    )
