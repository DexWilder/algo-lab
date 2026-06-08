"""Smoke tests for entry_volatility_regime_compound primitive.

Per operator decision #106 (Hybrid D-A-2). Validates fail-closed behavior
and the regime-shift mechanism actually fires.

Run: python3 research/tests/test_volatility_regime_compound.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from research.crossbreeding.crossbreeding_engine import (  # noqa: E402
    ENTRY_MAP, compute_features, entry_volatility_regime_compound,
    generate_crossbred_signals,
)


def _make_synthetic_df(n_days=60, bars_per_day=78, seed=42):
    """Synthetic 5-min OHLCV with sharp vol-regime shift:
    Days 1-40: quiet/tight (low vol).
    Day 41: extreme vol expansion.
    Days 42-60: high-vol regime sustained.

    Long pre-window allows vol_of_vol_pctrank to fully stabilize at LOW
    before the shift. Sharp shift drives post-shift bars to HIGH pctrank
    within the 5-bar transition window.
    """
    rng = np.random.default_rng(seed)
    dates, times, closes = [], [], []
    base = 100.0
    for d in range(n_days):
        date = pd.Timestamp("2024-01-01") + pd.Timedelta(days=d)
        for b in range(bars_per_day):
            t = pd.Timestamp("09:30") + pd.Timedelta(minutes=b * 5)
            dates.append(date)
            times.append(t.time())
            if d < 40:
                base += rng.normal(0, 0.02)  # very low vol
            elif d < 42:
                base += rng.normal(0, 2.0)   # extreme shift
            else:
                base += rng.normal(0, 0.6)   # sustained high vol
            closes.append(base)
    n = len(closes)
    closes = np.array(closes)
    df = pd.DataFrame({
        "datetime": [pd.Timestamp.combine(d, t) for d, t in zip(dates, times)],
        "open": closes - rng.normal(0, 0.02, n),
        "high": closes + np.abs(rng.normal(0, 0.08, n)),
        "low": closes - np.abs(rng.normal(0, 0.08, n)),
        "close": closes,
        "volume": rng.integers(100, 1000, n),
    })
    return df


def test_entry_returns_no_signal_at_index_0():
    df = _make_synthetic_df(n_days=5)
    features = compute_features(df)
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    direction, _, _ = entry_volatility_regime_compound(features, 0, state, {})
    assert direction == 0, "Index 0 must return 0 (i < 1 guard)"


def test_entry_fail_closed_on_nan_pctrank():
    """Early bars before pctrank warmup → no signal."""
    df = _make_synthetic_df(n_days=2)  # Too few bars for 120-min pctrank
    features = compute_features(df)
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    n = len(df)
    for i in range(1, min(50, n)):
        d, _, _ = entry_volatility_regime_compound(features, i, state, {})
        assert d == 0, f"Early bars (i={i}) must produce no signal"


def test_entry_no_signal_when_current_vol_regime_not_high():
    """Current bar with vol_of_vol_pctrank < 75 → no signal."""
    df = _make_synthetic_df(n_days=30)
    features = compute_features(df)
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    # Find a bar where current vol_of_vol_pctrank is LOW
    for i in range(150, len(df)):
        pct_now = features["vol_of_vol_pctrank"][i]
        if not np.isnan(pct_now) and pct_now < 50:
            direction, _, _ = entry_volatility_regime_compound(features, i, state, {})
            assert direction == 0, f"At i={i} pct={pct_now:.1f} should not fire"
            return
    print("WARN: no LOW vol-pctrank bar found in test_no_signal test")


def test_entry_fires_on_regime_shift():
    """Find a bar with high vol_of_vol_pctrank that had a low prior bar → fires."""
    df = _make_synthetic_df(n_days=30)
    features = compute_features(df)
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    n = len(df)
    fired = 0
    for i in range(150, n):
        pct_now = features["vol_of_vol_pctrank"][i]
        if np.isnan(pct_now) or pct_now < 75:
            continue
        # Check for low-vol bar within last 5
        was_low = False
        for j in range(max(0, i - 5), i):
            pct_j = features["vol_of_vol_pctrank"][j]
            if not np.isnan(pct_j) and pct_j <= 25:
                was_low = True
                break
        if not was_low:
            continue
        if (np.isnan(features["atr"][i]) or features["atr"][i] == 0 or
            np.isnan(features["ema21"][i]) or np.isnan(features["ema50"][i])):
            continue
        # Should fire (direction depends on ema21 vs ema50)
        state_copy = {"long_traded_today": False, "short_traded_today": False, "position": 0}
        direction, stop, target = entry_volatility_regime_compound(features, i, state_copy, {})
        if direction != 0:
            fired += 1
            close_i = features["close"][i]
            atr_i = features["atr"][i]
            # Verify shape
            if direction == 1:
                assert stop < close_i, "LONG stop must be below close"
                assert target > close_i, "LONG target must be above close"
                assert abs((close_i - stop) / atr_i - 1.5) < 0.01
                assert abs((target - close_i) / atr_i - 3.0) < 0.01
            else:
                assert stop > close_i, "SHORT stop must be above close"
                assert target < close_i, "SHORT target must be below close"
            break
    assert fired >= 1, "Regime-shift setup should fire at least once in synthetic data"


def test_long_traded_today_guard():
    df = _make_synthetic_df(n_days=30)
    features = compute_features(df)
    state = {"long_traded_today": True, "short_traded_today": True, "position": 0}
    n = len(df)
    for i in range(150, n):
        pct_now = features["vol_of_vol_pctrank"][i]
        if np.isnan(pct_now) or pct_now < 75:
            continue
        was_low = False
        for j in range(max(0, i - 5), i):
            pct_j = features["vol_of_vol_pctrank"][j]
            if not np.isnan(pct_j) and pct_j <= 25:
                was_low = True
                break
        if not was_low:
            continue
        direction, _, _ = entry_volatility_regime_compound(features, i, state, {})
        assert direction == 0, "Both traded_today guards must block fire"
        return
    print("WARN: no qualifying bar found in traded_today guard test")


def test_entry_registered_in_entry_map():
    assert "volatility_regime_compound" in ENTRY_MAP
    assert ENTRY_MAP["volatility_regime_compound"] is entry_volatility_regime_compound


def test_generate_crossbred_signals_end_to_end():
    df = _make_synthetic_df(n_days=30)
    sigs = generate_crossbred_signals(
        df, entry_name="volatility_regime_compound",
        exit_name="profit_ladder", filter_name="ema_slope", params={},
    )
    assert hasattr(sigs, "__len__")


def test_no_signal_with_zero_atr():
    """Construct features where atr=0 at the candidate bar → no signal."""
    df = _make_synthetic_df(n_days=30)
    features = compute_features(df)
    feat_copy = {k: (np.array(v, copy=True) if isinstance(v, np.ndarray) else v)
                 for k, v in features.items()}
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    n = len(df)
    for i in range(150, n):
        pct_now = feat_copy["vol_of_vol_pctrank"][i]
        if np.isnan(pct_now) or pct_now < 75:
            continue
        was_low = False
        for j in range(max(0, i - 5), i):
            pct_j = feat_copy["vol_of_vol_pctrank"][j]
            if not np.isnan(pct_j) and pct_j <= 25:
                was_low = True
                break
        if not was_low:
            continue
        # Force atr = 0
        feat_copy["atr"][i] = 0.0
        d, _, _ = entry_volatility_regime_compound(feat_copy, i, state, {})
        assert d == 0, "Zero ATR must fail-closed"
        return


if __name__ == "__main__":
    tests = [
        test_entry_returns_no_signal_at_index_0,
        test_entry_fail_closed_on_nan_pctrank,
        test_entry_no_signal_when_current_vol_regime_not_high,
        test_entry_fires_on_regime_shift,
        test_long_traded_today_guard,
        test_entry_registered_in_entry_map,
        test_generate_crossbred_signals_end_to_end,
        test_no_signal_with_zero_atr,
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
