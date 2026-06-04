"""Smoke test for the vol-regime FILTER_MAP primitives.

Verifies:
1. atr_pctrank appears in compute_features output and is in [0, 100] when not NaN.
2. filter_vol_regime correctly gates by params.
3. New filter names registered in FILTER_MAP.
4. End-to-end: apply ema_slope_vol_high vs baseline ema_slope on XB-BB-MGC.
   Goal: demonstrate the filter PASSES through the harness; concentration
   impact is reported as evidence.
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


def test_atr_pctrank_in_features():
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    f = compute_features(df)
    assert "atr_pctrank" in f, "atr_pctrank must be in features dict"
    pct = f["atr_pctrank"]
    valid = pct[~np.isnan(pct)]
    assert len(valid) > 0, "should have some valid percentile entries"
    assert valid.min() >= 0 and valid.max() <= 100, f"out of range: [{valid.min()}, {valid.max()}]"
    print(f"✓ atr_pctrank in features (valid n={len(valid)}, range [{valid.min():.1f}, {valid.max():.1f}])")


def test_filter_registered():
    for name in ("vol_regime", "ema_slope_vol_high", "ema_slope_vol_low"):
        assert name in FILTER_MAP, f"{name} not in FILTER_MAP"
    print("✓ vol_regime / ema_slope_vol_high / ema_slope_vol_low registered")


def test_filter_gating():
    """vol_regime with vr_low_pct=99 must zero almost all signals."""
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    f = compute_features(df)
    fn = FILTER_MAP["vol_regime"]
    # Default params (no restriction) pass all
    pass_all = sum(fn(f, i, 1, {}) for i in range(2000, 3000) if not np.isnan(f["atr_pctrank"][i]))
    # Very restrictive: only top-1% vol
    pass_top1 = sum(fn(f, i, 1, {"vr_low_pct": 99}) for i in range(2000, 3000) if not np.isnan(f["atr_pctrank"][i]))
    assert pass_all > pass_top1, f"restrictive params must reduce pass count; all={pass_all}, top1={pass_top1}"
    # Bottom-1%
    pass_bot1 = sum(fn(f, i, 1, {"vr_high_pct": 1}) for i in range(2000, 3000) if not np.isnan(f["atr_pctrank"][i]))
    assert pass_all > pass_bot1, "bottom-1% must reduce pass count"
    print(f"✓ vol_regime gating ok (pass_all={pass_all}, pass_top1={pass_top1}, pass_bot1={pass_bot1})")


def _run_xb(asset, entry, filter_name, exit_name, params=None, label=""):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    sigs = generate_crossbred_signals(df, entry_name=entry, exit_name=exit_name,
                                       filter_name=filter_name, params=params or {})
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol=asset)
    m = _metrics(res["trades_df"], label, costs=res["stats"]["costs"])
    return m


def test_end_to_end_xb_bb_mgc_concentration_mutation():
    """Apply the new vol-regime filter to XB-BB-MGC. Baseline ema_slope reported
    PF 1.502 / max-year 87.8% (today's fire). Plan B asks: does vol-regime
    overlay normalize concentration? Test both high-vol and low-vol cuts."""
    base = _run_xb("MGC", "bb_reversion", "ema_slope", "profit_ladder",
                   label="XB-BB-MGC-baseline")
    high = _run_xb("MGC", "bb_reversion", "ema_slope_vol_high", "profit_ladder",
                   params={"vr_threshold": 70}, label="XB-BB-MGC-volhi70")
    low = _run_xb("MGC", "bb_reversion", "ema_slope_vol_low", "profit_ladder",
                   params={"vr_threshold": 30}, label="XB-BB-MGC-vollo30")
    print()
    print(f"  baseline:     n={base['n']:4d} PF={base['pf']:.3f} median={base['median']:.2f} max-yr={base.get('max_year_share_pct', float('nan')):.1f}% top3={base.get('top3_share_pct', float('nan')):.1f}% top10={base.get('top10_share_pct', float('nan')):.1f}% → {_verdict(base, 'workhorse')}")
    print(f"  vol-high(70): n={high['n']:4d} PF={high['pf']:.3f} median={high['median']:.2f} max-yr={high.get('max_year_share_pct', float('nan')):.1f}% top3={high.get('top3_share_pct', float('nan')):.1f}% top10={high.get('top10_share_pct', float('nan')):.1f}% → {_verdict(high, 'workhorse')}")
    print(f"  vol-low(30):  n={low['n']:4d} PF={low['pf']:.3f} median={low['median']:.2f} max-yr={low.get('max_year_share_pct', float('nan')):.1f}% top3={low.get('top3_share_pct', float('nan')):.1f}% top10={low.get('top10_share_pct', float('nan')):.1f}% → {_verdict(low, 'workhorse')}")
    print("✓ end-to-end vol-regime mutation comparison ok")
    return base, high, low


if __name__ == "__main__":
    test_atr_pctrank_in_features()
    test_filter_registered()
    test_filter_gating()
    base, high, low = test_end_to_end_xb_bb_mgc_concentration_mutation()
    print("\nALL SMOKE TESTS PASSED — vol-regime filter is harness-ready.")
