"""Smoke test for stacked filters (filter_name accepts list).

Verifies:
1. Single-filter behavior unchanged.
2. List of filters AND-combines correctly.
3. Stacked count ≤ each individual filter's pass count.
4. Unknown filter raises UnknownFilterError before signal generation.
5. Empty list raises.
6. End-to-end XB-BB-EMA+HurstStableMR-MGC (V5 stacked) produces Forge metrics.
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
    _resolve_filter, UnknownFilterError,
)
from research.fql_forge_batch_runner import _metrics, _verdict
from engine.backtest import run_backtest
from engine.asset_config import ASSETS


def test_single_filter_unchanged():
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    sigs1 = generate_crossbred_signals(
        df, entry_name="bb_reversion", exit_name="profit_ladder",
        filter_name="ema_slope", params={})
    sigs2 = generate_crossbred_signals(
        df, entry_name="bb_reversion", exit_name="profit_ladder",
        filter_name=["ema_slope"], params={})
    assert int((sigs1["signal"] != 0).sum()) == int((sigs2["signal"] != 0).sum()), \
        "single-element list must produce same signal count as bare string"
    print(f"✓ single-filter unchanged ({(sigs1['signal'] != 0).sum()} entries)")


def test_stacked_and_combine():
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    f = compute_features(df)
    # Apply each filter solo + the AND-stack
    rng = range(2000, 5000)
    ema_pass = sum(FILTER_MAP["ema_slope"](f, i, 1, {}) for i in rng)
    hurst_pass = sum(FILTER_MAP["hurst_stable_mr"](f, i, 1, {}) for i in rng if not np.isnan(f["hurst"][i]))
    stack = _resolve_filter(["ema_slope", "hurst_stable_mr"])
    stack_pass = sum(stack(f, i, 1, {}) for i in rng if not np.isnan(f["hurst"][i]))
    assert stack_pass <= ema_pass, "stack pass count must be ≤ ema_slope alone"
    assert stack_pass <= hurst_pass, "stack pass count must be ≤ hurst_stable_mr alone"
    print(f"✓ AND-combine ok (ema={ema_pass}, hurst={hurst_pass}, stack={stack_pass})")


def test_unknown_filter_fails_closed():
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    try:
        generate_crossbred_signals(
            df, entry_name="bb_reversion", exit_name="profit_ladder",
            filter_name="not_a_real_filter", params={})
        assert False, "should have raised on unknown single filter"
    except UnknownFilterError as e:
        assert "not_a_real_filter" in str(e)
    try:
        generate_crossbred_signals(
            df, entry_name="bb_reversion", exit_name="profit_ladder",
            filter_name=["ema_slope", "fake_filter"], params={})
        assert False, "should have raised on unknown in list"
    except UnknownFilterError as e:
        assert "fake_filter" in str(e)
    print("✓ unknown filter fails closed (single + list)")


def test_empty_list_fails():
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    try:
        generate_crossbred_signals(
            df, entry_name="bb_reversion", exit_name="profit_ladder",
            filter_name=[], params={})
        assert False, "should have raised on empty list"
    except UnknownFilterError:
        pass
    print("✓ empty list fails closed")


def test_end_to_end_xb_bb_ema_hurst_mgc():
    """V5 wired correctly this time: ema_slope ADDED hurst_stable_mr.
    Operator doctrine: Hurst as ADDITION to ema_slope, not replacement.
    """
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    cfg = ASSETS["MGC"]
    sigs = generate_crossbred_signals(
        df, entry_name="bb_reversion", exit_name="profit_ladder",
        filter_name=["ema_slope", "hurst_stable_mr"],
        params={"hurst_threshold_high": 0.50})
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol="MGC")
    m = _metrics(res["trades_df"], "XB-BB-EMA+HurstMR-MGC",
                 costs=res["stats"]["costs"])
    v = _verdict(m, "tail" if m["n"] < 500 else "workhorse")
    print(f"  XB-BB-EMA+HurstMR-MGC: n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f} "
          f"max-yr={m.get('max_year_share_pct', float('nan')):.1f}% → {v}")
    print("✓ stacked-filter V5 end-to-end ok")
    return m, v


if __name__ == "__main__":
    test_single_filter_unchanged()
    test_stacked_and_combine()
    test_unknown_filter_fails_closed()
    test_empty_list_fails()
    test_end_to_end_xb_bb_ema_hurst_mgc()
    print("\nALL SMOKE TESTS PASSED — stacked filters are harness-ready.")
