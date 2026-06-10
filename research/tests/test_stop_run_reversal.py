"""Smoke tests for entry_stop_run_reversal primitive.

Per operator decision #118 chain + SMP-3. Validates sweep + reclaim detection,
direction logic, fail-closed behavior.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from research.crossbreeding.crossbreeding_engine import (  # noqa: E402
    ENTRY_MAP, compute_features, entry_stop_run_reversal,
    generate_crossbred_signals,
)


def _make_synthetic_df(n_days=30, bars_per_day=78, seed=42):
    """Synthetic 5-min OHLCV with sweep-and-reclaim pattern."""
    rng = np.random.default_rng(seed)
    dates, times, closes, highs, lows = [], [], [], [], []
    base = 100.0
    for d in range(n_days):
        date = pd.Timestamp("2024-01-01") + pd.Timedelta(days=d)
        for b in range(bars_per_day):
            t = pd.Timestamp("09:30") + pd.Timedelta(minutes=b * 5)
            dates.append(date)
            times.append(t.time())
            base += rng.normal(0, 0.2)
            closes.append(base)
            highs.append(base + abs(rng.normal(0.1, 0.05)))
            lows.append(base - abs(rng.normal(0.1, 0.05)))
    n = len(closes)
    df = pd.DataFrame({
        "datetime": [pd.Timestamp.combine(d, t) for d, t in zip(dates, times)],
        "open": np.array(closes) - rng.normal(0, 0.02, n),
        "high": np.array(highs),
        "low": np.array(lows),
        "close": np.array(closes),
        "volume": rng.integers(100, 1000, n),
    })
    return df


def test_entry_returns_no_signal_at_index_0():
    df = _make_synthetic_df()
    features = compute_features(df)
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    d, _, _ = entry_stop_run_reversal(features, 0, state, {})
    assert d == 0


def test_entry_no_signal_on_nan_features():
    """Early bars before dc_high_20 has values → no signal."""
    df = _make_synthetic_df(n_days=2)
    features = compute_features(df)
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    for i in range(1, 25):
        d, _, _ = entry_stop_run_reversal(features, i, state, {})
        assert d == 0, f"Early bar i={i} must not fire (NaN dc_high_20)"


def test_entry_fires_on_sweep_up_reclaim_short():
    """Construct sweep-up + reclaim → SHORT fade."""
    df = _make_synthetic_df()
    features = compute_features(df)
    feat_copy = {k: (np.array(v, copy=True) if isinstance(v, np.ndarray) else v)
                 for k, v in features.items()}
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    n = len(df)
    for i in range(30, n):
        swing_h = feat_copy["dc_high_20"][i-1]
        atr_i = feat_copy["atr"][i]
        if np.isnan(swing_h) or np.isnan(atr_i) or atr_i == 0:
            continue
        # Force sweep-up + reclaim
        feat_copy["high"][i] = swing_h + 0.5
        feat_copy["close"][i] = swing_h - 0.1
        d, stop, target = entry_stop_run_reversal(feat_copy, i, state, {})
        assert d == -1, f"Sweep-up + reclaim at i={i} should fire SHORT, got {d}"
        assert stop > feat_copy["high"][i], "SHORT stop must be above sweep high"
        assert target < feat_copy["close"][i], "SHORT target must be below close"
        return


def test_entry_fires_on_sweep_down_reclaim_long():
    """Construct sweep-down + reclaim → LONG fade."""
    df = _make_synthetic_df()
    features = compute_features(df)
    feat_copy = {k: (np.array(v, copy=True) if isinstance(v, np.ndarray) else v)
                 for k, v in features.items()}
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    n = len(df)
    for i in range(30, n):
        swing_l = feat_copy["dc_low_20"][i-1]
        atr_i = feat_copy["atr"][i]
        if np.isnan(swing_l) or np.isnan(atr_i) or atr_i == 0:
            continue
        # Force sweep-down + reclaim
        feat_copy["low"][i] = swing_l - 0.5
        feat_copy["close"][i] = swing_l + 0.1
        d, stop, target = entry_stop_run_reversal(feat_copy, i, state, {})
        assert d == 1, f"Sweep-down + reclaim at i={i} should fire LONG, got {d}"
        assert stop < feat_copy["low"][i], "LONG stop must be below sweep low"
        assert target > feat_copy["close"][i], "LONG target must be above close"
        return


def test_entry_no_signal_when_close_does_not_reclaim():
    """Sweep up but close stays above swept level → no reclaim → no signal."""
    df = _make_synthetic_df()
    features = compute_features(df)
    feat_copy = {k: (np.array(v, copy=True) if isinstance(v, np.ndarray) else v)
                 for k, v in features.items()}
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    n = len(df)
    for i in range(30, n):
        swing_h = feat_copy["dc_high_20"][i-1]
        atr_i = feat_copy["atr"][i]
        if np.isnan(swing_h) or np.isnan(atr_i) or atr_i == 0:
            continue
        # Sweep up but close ABOVE swept level (no reclaim)
        feat_copy["high"][i] = swing_h + 0.5
        feat_copy["close"][i] = swing_h + 0.3
        d, _, _ = entry_stop_run_reversal(feat_copy, i, state, {})
        assert d == 0, f"Sweep without reclaim at i={i} should not fire"
        return


def test_short_traded_today_guard():
    df = _make_synthetic_df()
    features = compute_features(df)
    feat_copy = {k: (np.array(v, copy=True) if isinstance(v, np.ndarray) else v)
                 for k, v in features.items()}
    state = {"long_traded_today": False, "short_traded_today": True, "position": 0}
    n = len(df)
    for i in range(30, n):
        swing_h = feat_copy["dc_high_20"][i-1]
        atr_i = feat_copy["atr"][i]
        if np.isnan(swing_h) or np.isnan(atr_i) or atr_i == 0:
            continue
        feat_copy["high"][i] = swing_h + 0.5
        feat_copy["close"][i] = swing_h - 0.1
        d, _, _ = entry_stop_run_reversal(feat_copy, i, state, {})
        assert d == 0, "short_traded_today=True must block SHORT"
        return


def test_entry_registered_in_entry_map():
    assert "stop_run_reversal" in ENTRY_MAP
    assert ENTRY_MAP["stop_run_reversal"] is entry_stop_run_reversal


def test_generate_crossbred_signals_end_to_end():
    df = _make_synthetic_df()
    sigs = generate_crossbred_signals(
        df, entry_name="stop_run_reversal",
        exit_name="profit_ladder", filter_name="none", params={},
    )
    assert hasattr(sigs, "__len__")


def test_no_signal_with_zero_atr():
    df = _make_synthetic_df()
    features = compute_features(df)
    feat_copy = {k: (np.array(v, copy=True) if isinstance(v, np.ndarray) else v)
                 for k, v in features.items()}
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    n = len(df)
    for i in range(30, n):
        swing_h = feat_copy["dc_high_20"][i-1]
        if np.isnan(swing_h):
            continue
        feat_copy["high"][i] = swing_h + 0.5
        feat_copy["close"][i] = swing_h - 0.1
        feat_copy["atr"][i] = 0.0
        d, _, _ = entry_stop_run_reversal(feat_copy, i, state, {})
        assert d == 0, "Zero ATR must fail-closed"
        return


def test_filter_pre_flight_compatibility():
    """#120 pre-flight: entry is REVERSAL thesis. Verify filter=none doesn't block."""
    # No filter applied → entry should fire whenever sweep+reclaim conditions met
    df = _make_synthetic_df()
    features = compute_features(df)
    feat_copy = {k: (np.array(v, copy=True) if isinstance(v, np.ndarray) else v)
                 for k, v in features.items()}
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    fired = 0
    for i in range(30, len(df)):
        swing_h = feat_copy["dc_high_20"][i-1]
        atr_i = feat_copy["atr"][i]
        if np.isnan(swing_h) or np.isnan(atr_i) or atr_i == 0:
            continue
        # Force sweep+reclaim
        feat_copy["high"][i] = swing_h + 0.5
        feat_copy["close"][i] = swing_h - 0.1
        state_copy = dict(state)
        d, _, _ = entry_stop_run_reversal(feat_copy, i, state_copy, {})
        if d == -1:
            fired += 1
            # Restore feature for next iter
            feat_copy["high"][i] = features["high"][i]
            feat_copy["close"][i] = features["close"][i]
            if fired >= 3:
                break
    assert fired >= 3, "Entry should fire on forced sweep+reclaim setups (filter pre-flight: filter=none compatible)"


if __name__ == "__main__":
    tests = [
        test_entry_returns_no_signal_at_index_0,
        test_entry_no_signal_on_nan_features,
        test_entry_fires_on_sweep_up_reclaim_short,
        test_entry_fires_on_sweep_down_reclaim_long,
        test_entry_no_signal_when_close_does_not_reclaim,
        test_short_traded_today_guard,
        test_entry_registered_in_entry_map,
        test_generate_crossbred_signals_end_to_end,
        test_no_signal_with_zero_atr,
        test_filter_pre_flight_compatibility,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception as e:
            print(f"FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(0 if failed == 0 else 1)
