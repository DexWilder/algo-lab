"""Smoke tests for entry_bb_keltner_squeeze primitive.

Per operator decision #111 (Hybrid D-A-3). Validates squeeze detection,
release-fire mechanism, fail-closed behavior, direction logic.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from research.crossbreeding.crossbreeding_engine import (  # noqa: E402
    ENTRY_MAP, compute_features, entry_bb_keltner_squeeze,
    generate_crossbred_signals,
)


def _make_synthetic_df(n_days=30, bars_per_day=78, seed=42):
    """Synthetic 5-min OHLCV with a squeeze: days 5-15 quiet vol, day 16 release."""
    rng = np.random.default_rng(seed)
    dates, times, closes = [], [], []
    base = 100.0
    for d in range(n_days):
        date = pd.Timestamp("2024-01-01") + pd.Timedelta(days=d)
        for b in range(bars_per_day):
            t = pd.Timestamp("09:30") + pd.Timedelta(minutes=b * 5)
            dates.append(date)
            times.append(t.time())
            if 5 <= d <= 15:
                base += rng.normal(0, 0.03)  # squeeze period — very quiet
            elif d == 16:
                base += rng.normal(0.5, 0.3)  # release
            else:
                base += rng.normal(0, 0.2)
            closes.append(base)
    n = len(closes)
    closes = np.array(closes)
    df = pd.DataFrame({
        "datetime": [pd.Timestamp.combine(d, t) for d, t in zip(dates, times)],
        "open": closes - rng.normal(0, 0.02, n),
        "high": closes + np.abs(rng.normal(0, 0.05, n)),
        "low": closes - np.abs(rng.normal(0, 0.05, n)),
        "close": closes,
        "volume": rng.integers(100, 1000, n),
    })
    return df


def test_entry_returns_no_signal_at_index_0():
    df = _make_synthetic_df(n_days=5)
    features = compute_features(df)
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    d, _, _ = entry_bb_keltner_squeeze(features, 0, state, {})
    assert d == 0


def test_entry_no_signal_when_squeeze_never_was_on():
    """If squeeze_on never True in last min_squeeze_bars, no signal."""
    df = _make_synthetic_df(n_days=30)
    features = compute_features(df)
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    # Find bar where squeeze_on[i-1] is False
    for i in range(50, len(df)):
        if not features["squeeze_on"][i-1]:
            d, _, _ = entry_bb_keltner_squeeze(features, i, state, {})
            assert d == 0, f"At i={i} squeeze_off → no signal"
            return


def test_entry_fires_on_squeeze_release():
    """Find a release-bar (squeeze_on transition True→False) → fires."""
    df = _make_synthetic_df(n_days=30)
    features = compute_features(df)
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    fired = 0
    for i in range(50, len(df)):
        sq_now = features["squeeze_on"][i]
        sq_prev = features["squeeze_on"][i-1]
        if np.isnan(sq_now) or np.isnan(sq_prev):
            continue
        if not (sq_prev and not sq_now):
            continue
        # Verify min_squeeze_bars satisfied
        on_count = 0
        for j in range(max(0, i - 3), i):
            sj = features["squeeze_on"][j]
            if not np.isnan(sj) and sj:
                on_count += 1
        if on_count < 3:
            continue
        if (np.isnan(features["atr"][i]) or features["atr"][i] == 0
            or np.isnan(features["ema20"][i])):
            continue
        state_copy = {"long_traded_today": False, "short_traded_today": False, "position": 0}
        direction, stop, target = entry_bb_keltner_squeeze(features, i, state_copy, {})
        if direction != 0:
            fired += 1
            close_i = features["close"][i]
            atr_i = features["atr"][i]
            if direction == 1:
                assert stop < close_i
                assert target > close_i
                assert abs((close_i - stop) / atr_i - 1.5) < 0.01
                assert abs((target - close_i) / atr_i - 3.0) < 0.01
            else:
                assert stop > close_i
                assert target < close_i
            break
    assert fired >= 1, "Squeeze-release setup should fire at least once in synthetic data"


def test_long_traded_today_guard():
    df = _make_synthetic_df(n_days=30)
    features = compute_features(df)
    state = {"long_traded_today": True, "short_traded_today": True, "position": 0}
    for i in range(50, len(df)):
        sq_now = features["squeeze_on"][i]
        sq_prev = features["squeeze_on"][i-1]
        if np.isnan(sq_now) or np.isnan(sq_prev):
            continue
        if sq_prev and not sq_now:
            d, _, _ = entry_bb_keltner_squeeze(features, i, state, {})
            assert d == 0
            return


def test_entry_registered_in_entry_map():
    assert "bb_keltner_squeeze" in ENTRY_MAP
    assert ENTRY_MAP["bb_keltner_squeeze"] is entry_bb_keltner_squeeze


def test_generate_crossbred_signals_end_to_end():
    df = _make_synthetic_df(n_days=30)
    sigs = generate_crossbred_signals(
        df, entry_name="bb_keltner_squeeze",
        exit_name="profit_ladder", filter_name="ema_slope", params={},
    )
    assert hasattr(sigs, "__len__")


def test_no_signal_with_zero_atr():
    df = _make_synthetic_df(n_days=30)
    features = compute_features(df)
    feat_copy = {k: (np.array(v, copy=True) if isinstance(v, np.ndarray) else v)
                 for k, v in features.items()}
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    for i in range(50, len(df)):
        sq_now = feat_copy["squeeze_on"][i]
        sq_prev = feat_copy["squeeze_on"][i-1]
        if np.isnan(sq_now) or np.isnan(sq_prev):
            continue
        if sq_prev and not sq_now:
            feat_copy["atr"][i] = 0.0
            d, _, _ = entry_bb_keltner_squeeze(feat_copy, i, state, {})
            assert d == 0, "Zero ATR must fail-closed"
            return


def test_squeeze_state_is_computed():
    """squeeze_on is a boolean array in features."""
    df = _make_synthetic_df(n_days=30)
    features = compute_features(df)
    assert "squeeze_on" in features
    assert "kc_upper" in features
    assert "kc_lower" in features
    # Squeeze_on must have at least one True (synthetic data has squeeze period)
    n_squeezed = int(np.sum(features["squeeze_on"] == True))  # noqa: E712
    assert n_squeezed > 0, f"Expected at least one squeezed bar in synthetic data; got {n_squeezed}"


if __name__ == "__main__":
    tests = [
        test_entry_returns_no_signal_at_index_0,
        test_entry_no_signal_when_squeeze_never_was_on,
        test_entry_fires_on_squeeze_release,
        test_long_traded_today_guard,
        test_entry_registered_in_entry_map,
        test_generate_crossbred_signals_end_to_end,
        test_no_signal_with_zero_atr,
        test_squeeze_state_is_computed,
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
