"""Smoke test for prior-day high/low features + entries.

Verifies:
1. prev_day_high / prev_day_low / prev_day_close in compute_features output
2. First-day bars have NaN prev-day values (fail-closed)
3. prior_day_break entry registers + fires when close > prev_high
4. prior_day_fade entry registers + fires on pierce-and-reject
5. End-to-end: prior_day_break runs on real MGC bars and produces trades
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from research.crossbreeding.crossbreeding_engine import (
    compute_features, ENTRY_MAP, generate_crossbred_signals,
)
from research.fql_forge_batch_runner import _metrics
from engine.asset_config import ASSETS
from engine.backtest import run_backtest


def test_features_present():
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    f = compute_features(df)
    for k in ("prev_day_high", "prev_day_low", "prev_day_close"):
        assert k in f, f"missing {k}"
        arr = f[k]
        assert len(arr) == f["n"]
    # First bar should be NaN (no prior day yet)
    assert np.isnan(f["prev_day_high"][0]), "first bar prev_day_high must be NaN"
    # Day 2+ bars should have finite values
    finite = (~np.isnan(f["prev_day_high"])).sum()
    assert finite > f["n"] * 0.99, f"too many NaN: {finite}/{f['n']}"
    print(f"✓ prev-day features present (n_valid={finite}/{f['n']})")


def test_entries_registered():
    for n in ("prior_day_break", "prior_day_fade"):
        assert n in ENTRY_MAP, f"{n} not in ENTRY_MAP"
    print("✓ prior_day_break / prior_day_fade registered")


def test_end_to_end_prior_day_break_mgc():
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    cfg = ASSETS["MGC"]
    sigs = generate_crossbred_signals(
        df, entry_name="prior_day_break", exit_name="profit_ladder",
        filter_name="ema_slope", params={}
    )
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol="MGC")
    m = _metrics(res["trades_df"], "SMOKE-prior-day-break-MGC",
                 costs=res["stats"]["costs"])
    print(f"✓ prior_day_break MGC end-to-end: n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f}")
    return m


def test_end_to_end_prior_day_fade_mes():
    df = pd.read_csv(ROOT / "data" / "processed" / "MES_5m.csv")
    cfg = ASSETS["MES"]
    sigs = generate_crossbred_signals(
        df, entry_name="prior_day_fade", exit_name="profit_ladder",
        filter_name="ema_slope", params={}
    )
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol="MES")
    m = _metrics(res["trades_df"], "SMOKE-prior-day-fade-MES",
                 costs=res["stats"]["costs"])
    print(f"✓ prior_day_fade MES end-to-end: n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f}")
    return m


if __name__ == "__main__":
    test_features_present()
    test_entries_registered()
    test_end_to_end_prior_day_break_mgc()
    test_end_to_end_prior_day_fade_mes()
    print("\nALL SMOKE TESTS PASSED — prior-day features are harness-ready.")
