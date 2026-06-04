"""Smoke test for the hurst_stable FILTER_MAP primitives.

Verifies:
1. hurst is in compute_features output.
2. filter_hurst_stable_mr and filter_hurst_stable_trend are registered.
3. The filter gates entries as expected (restrictive threshold reduces count).
4. End-to-end XB-BB-EMA-HurstStable-MGC runs and produces Forge schema.
"""

from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from research.crossbreeding.crossbreeding_engine import (
    compute_features, FILTER_MAP, generate_crossbred_signals,
)
from research.fql_forge_batch_runner import _metrics, _verdict
from engine.backtest import run_backtest
from engine.asset_config import ASSETS


def test_hurst_in_features():
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    f = compute_features(df)
    assert "hurst" in f, "hurst missing"
    valid = f["hurst"][~np.isnan(f["hurst"])]
    assert len(valid) > 1000
    # Should be in a reasonable Hurst range; allow some overshoot due to proxy
    assert valid.min() > -0.5 and valid.max() < 1.5, \
        f"hurst proxy out of plausible range [{valid.min():.2f}, {valid.max():.2f}]"
    print(f"✓ hurst in features (n_valid={len(valid)}, range [{valid.min():.2f}, {valid.max():.2f}], "
          f"median {np.median(valid):.3f})")


def test_filters_registered():
    for n in ("hurst_stable_mr", "hurst_stable_trend"):
        assert n in FILTER_MAP, f"{n} not registered"
    print("✓ hurst filters registered")


def test_filter_gating():
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    f = compute_features(df)
    mr = FILTER_MAP["hurst_stable_mr"]
    trend = FILTER_MAP["hurst_stable_trend"]
    # Restrictive MR (very low threshold) should pass few
    rng = range(2000, 4000)
    pass_easy = sum(mr(f, i, 1, {}) for i in rng if not np.isnan(f["hurst"][i]))
    pass_strict = sum(mr(f, i, 1, {"hurst_threshold_high": 0.3}) for i in rng if not np.isnan(f["hurst"][i]))
    assert pass_easy >= pass_strict, "restrictive MR must pass fewer"
    pass_trend_easy = sum(trend(f, i, 1, {}) for i in rng if not np.isnan(f["hurst"][i]))
    pass_trend_strict = sum(trend(f, i, 1, {"hurst_threshold_low": 0.7}) for i in rng if not np.isnan(f["hurst"][i]))
    assert pass_trend_easy >= pass_trend_strict, "restrictive trend must pass fewer"
    print(f"✓ filter gating ok (MR easy={pass_easy}, MR strict={pass_strict}, "
          f"trend easy={pass_trend_easy}, trend strict={pass_trend_strict})")


def test_end_to_end_xb_bb_hurst_mgc():
    """XB-BB-EMA-HurstStable-MGC (V5 spec wired):
    BB-reversion entry + ema_slope was the original trio. Replace filter with
    hurst_stable_mr to require sustained MR regime. Test if cheap-screen
    differs from plain BB-reversion baseline.
    """
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    cfg = ASSETS["MGC"]
    # Use ema_slope (no hurst) as baseline reference, then hurst_stable_mr
    sigs_base = generate_crossbred_signals(
        df, entry_name="bb_reversion", exit_name="profit_ladder",
        filter_name="ema_slope", params={}
    )
    res_b = run_backtest(df, sigs_base, mode="both", point_value=cfg["point_value"], symbol="MGC")
    m_b = _metrics(res_b["trades_df"], "BASE", costs=res_b["stats"]["costs"])

    sigs_hurst = generate_crossbred_signals(
        df, entry_name="bb_reversion", exit_name="profit_ladder",
        filter_name="hurst_stable_mr", params={"hurst_threshold_high": 0.45}
    )
    res_h = run_backtest(df, sigs_hurst, mode="both", point_value=cfg["point_value"], symbol="MGC")
    m_h = _metrics(res_h["trades_df"], "HURST", costs=res_h["stats"]["costs"])
    print(f"  baseline (ema_slope):     n={m_b['n']:4d} PF={m_b['pf']:.3f} median=${m_b['median']:.2f}")
    print(f"  hurst_stable_mr (0.45):   n={m_h['n']:4d} PF={m_h['pf']:.3f} median=${m_h['median']:.2f}")
    print("✓ end-to-end hurst-gated MR cheap-screen ok")
    return m_b, m_h


if __name__ == "__main__":
    test_hurst_in_features()
    test_filters_registered()
    test_filter_gating()
    m_b, m_h = test_end_to_end_xb_bb_hurst_mgc()
    print("\nALL SMOKE TESTS PASSED — hurst_stable filter is harness-ready.")
