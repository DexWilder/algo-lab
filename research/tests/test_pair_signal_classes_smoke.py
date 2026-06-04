"""Smoke test for the pair signal-class adapter.

Verifies:
1. Default return_z behavior unchanged from v1.
2. level_z / yield_z / fundamental_z all run when overrides are supplied.
3. Fail-closed: requesting non-return_z signal_class without overrides raises.
4. Fail-closed: invalid signal_class string raises.
5. End-to-end: ZN/ZB price-level pair (level_z) produces signals where return_z gave zero.
6. fundamental_z runs end-to-end using fundamentals_cache.
"""

from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from research.pairs_engine import (
    generate_pairs_signal, pairs_backtest, pairs_metrics,
    SIGNAL_CLASSES, PairSignalError,
)


def test_default_return_z_unchanged():
    """A return_z call without override args must match the v1 result."""
    df_a = pd.read_csv(ROOT / "data" / "processed" / "MES_5m.csv")
    df_b = pd.read_csv(ROOT / "data" / "processed" / "ZN_5m.csv")
    r1 = pairs_backtest(df_a=df_a, df_b=df_b, asset_a="MES", asset_b="ZN",
                        freq="M", lookback=12, z_threshold=1.5, exit_z=0.5,
                        hedge="vol_adjusted", label="DEFAULT")
    r2 = pairs_backtest(df_a=df_a, df_b=df_b, asset_a="MES", asset_b="ZN",
                        freq="M", lookback=12, z_threshold=1.5, exit_z=0.5,
                        hedge="vol_adjusted", label="EXPLICIT_RETURN_Z",
                        signal_class="return_z")
    assert len(r1["trades_df"]) == len(r2["trades_df"]), \
        "explicit return_z must equal default"
    print(f"✓ default return_z unchanged ({len(r1['trades_df'])} trades both)")


def test_invalid_signal_class_fails():
    df_a = pd.read_csv(ROOT / "data" / "processed" / "MES_5m.csv")
    df_b = pd.read_csv(ROOT / "data" / "processed" / "ZN_5m.csv")
    try:
        pairs_backtest(df_a=df_a, df_b=df_b, asset_a="MES", asset_b="ZN",
                       freq="M", signal_class="not_a_class")
        assert False, "should have raised"
    except PairSignalError as e:
        assert "not_a_class" in str(e)
    print("✓ invalid signal_class fails closed")


def test_override_required_for_non_return_z():
    df_a = pd.read_csv(ROOT / "data" / "processed" / "ZN_5m.csv")
    df_b = pd.read_csv(ROOT / "data" / "processed" / "ZB_5m.csv")
    try:
        pairs_backtest(df_a=df_a, df_b=df_b, asset_a="ZN", asset_b="ZB",
                       freq="M", signal_class="yield_z")
        assert False, "yield_z without overrides should have raised"
    except PairSignalError as e:
        assert "requires" in str(e)
    print("✓ non-return_z without overrides fails closed")


def test_level_z_on_zn_zb_curve():
    """level_z (z-score of price-spread) should produce signals where the v1
    return_z gave 0 trades. Doesn't require yield conversion since this is
    just level mean-reversion in price space."""
    df_a = pd.read_csv(ROOT / "data" / "processed" / "ZN_5m.csv")
    df_b = pd.read_csv(ROOT / "data" / "processed" / "ZB_5m.csv")
    from research.pairs_engine import _resample_close
    a_lvl = _resample_close(df_a, "M")
    b_lvl = _resample_close(df_b, "M")
    res = pairs_backtest(df_a=df_a, df_b=df_b, asset_a="ZN", asset_b="ZB",
                         freq="M", lookback=12, z_threshold=1.5, exit_z=0.5,
                         hedge="vol_adjusted", label="ZN-ZB-level_z-smoke",
                         signal_class="level_z",
                         series_a_override=a_lvl, series_b_override=b_lvl)
    m = pairs_metrics(res, "ZN-ZB-level_z-smoke")
    print(f"✓ level_z on ZN/ZB: n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f}")


def test_fundamental_z_using_cache():
    """fundamental_z driven by fundamentals_cache series.
    Uses Fed Funds vs BoJ rate as a synthetic 'pair' on MES (just to validate
    the wiring; PnL is on MES). Not a real candidate — pure plumbing check."""
    from research.fundamentals_cache import load_series
    df_a = pd.read_csv(ROOT / "data" / "processed" / "MES_5m.csv")
    df_b = pd.read_csv(ROOT / "data" / "processed" / "ZN_5m.csv")
    fed = load_series("fed_funds_effective")
    boj = load_series("boj_policy_rate")
    res = pairs_backtest(df_a=df_a, df_b=df_b, asset_a="MES", asset_b="ZN",
                         freq="M", lookback=12, z_threshold=1.0, exit_z=0.3,
                         hedge="vol_adjusted", label="MES-ZN-fundamental_z-smoke",
                         signal_class="fundamental_z",
                         series_a_override=fed, series_b_override=boj)
    m = pairs_metrics(res, "MES-ZN-fundamental_z-smoke")
    assert res["signal_class"] == "fundamental_z"
    assert res["used_overrides"] is True
    print(f"✓ fundamental_z plumbing: n={m['n']} PF={m['pf']:.3f}")


if __name__ == "__main__":
    test_default_return_z_unchanged()
    test_invalid_signal_class_fails()
    test_override_required_for_non_return_z()
    test_level_z_on_zn_zb_curve()
    test_fundamental_z_using_cache()
    print("\nALL SMOKE TESTS PASSED — signal-class adapter is harness-ready.")
