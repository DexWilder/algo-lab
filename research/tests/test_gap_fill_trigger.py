"""Smoke tests for entry_gap_fill_trigger primitive.

Per operator decision #116. Validates fade direction, session-open detection,
fail-closed behavior.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from research.crossbreeding.crossbreeding_engine import (  # noqa: E402
    ENTRY_MAP, compute_features, entry_gap_fill_trigger,
    generate_crossbred_signals,
)


def _make_synthetic_df(n_days=10, bars_per_day=78, gap_size=2.0, seed=42):
    """Synthetic 5-min OHLCV with gap at session open on day 5+.

    Each "day" = 78 bars covering 09:30 → 22:00 in 5-min increments.
    in_session = times in [09:30, 15:45). Gap injected at session open of day 5+.
    """
    rng = np.random.default_rng(seed)
    rows = []
    base = 100.0
    for d in range(n_days):
        date = pd.Timestamp("2024-01-02") + pd.Timedelta(days=d)
        # Pre-RTH bars (08:00-09:30, 18 bars)
        for b in range(18):
            t = pd.Timestamp("08:00") + pd.Timedelta(minutes=b * 5)
            base += rng.normal(0, 0.05)
            rows.append((pd.Timestamp.combine(date, t.time()), base))
        # GAP at RTH open of day 5+
        if d >= 5:
            base += gap_size  # large up-gap
        # RTH bars (09:30-15:45 = 75 bars)
        for b in range(75):
            t = pd.Timestamp("09:30") + pd.Timedelta(minutes=b * 5)
            base += rng.normal(0, 0.1)
            rows.append((pd.Timestamp.combine(date, t.time()), base))
    df = pd.DataFrame(rows, columns=["datetime", "close"])
    rng2 = np.random.default_rng(seed + 1)
    n = len(df)
    df["open"] = df["close"] - rng2.normal(0, 0.02, n)
    df["high"] = df["close"] + np.abs(rng2.normal(0, 0.05, n))
    df["low"] = df["close"] - np.abs(rng2.normal(0, 0.05, n))
    df["volume"] = rng2.integers(100, 1000, n)
    return df


def test_entry_returns_no_signal_at_index_0():
    df = _make_synthetic_df()
    features = compute_features(df)
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    d, _, _ = entry_gap_fill_trigger(features, 0, state, {})
    assert d == 0


def test_entry_no_signal_outside_session():
    """Pre-RTH bars (08:00-09:30) should not fire."""
    df = _make_synthetic_df()
    features = compute_features(df)
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    for i in range(1, len(df)):
        if not features["in_session"][i]:
            d, _, _ = entry_gap_fill_trigger(features, i, state, {})
            assert d == 0, f"Outside session i={i} must not fire"
            return


def test_entry_fires_on_gap_up_short_fade():
    """Gap UP at session open → SHORT fade."""
    df = _make_synthetic_df(gap_size=3.0)
    features = compute_features(df)
    state_template = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    n = len(df)
    fired = 0
    for i in range(20, n):
        if not features["entry_ok"][i]:
            continue
        if i == 0 or features["entry_ok"][i-1]:
            continue  # not session-opening bar
        # i is session-open bar; check gap
        prev_close = features["prev_day_close"][i]
        if np.isnan(prev_close):
            continue
        close = features["close"][i]
        atr_i = features["atr"][i]
        if np.isnan(atr_i) or atr_i == 0:
            continue
        gap = close - prev_close
        if gap > 0.5 * atr_i:
            state = dict(state_template)
            direction, stop, target = entry_gap_fill_trigger(features, i, state, {})
            if direction == -1:
                fired += 1
                # Verify stop > close (short stop above)
                assert stop > close
                # Verify target is prev_close
                assert target == prev_close
                break
    assert fired >= 1, "Up-gap setup should fire SHORT at least once"


def test_entry_fires_on_gap_down_long_fade():
    """Gap DOWN at session open → LONG fade."""
    df = _make_synthetic_df(gap_size=-3.0)
    features = compute_features(df)
    n = len(df)
    fired = 0
    for i in range(20, n):
        if not features["entry_ok"][i]:
            continue
        if i == 0 or features["entry_ok"][i-1]:
            continue
        prev_close = features["prev_day_close"][i]
        if np.isnan(prev_close):
            continue
        close = features["close"][i]
        atr_i = features["atr"][i]
        if np.isnan(atr_i) or atr_i == 0:
            continue
        gap = close - prev_close
        if gap < -0.5 * atr_i:
            state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
            direction, stop, target = entry_gap_fill_trigger(features, i, state, {})
            if direction == 1:
                fired += 1
                assert stop < close
                assert target == prev_close
                break
    assert fired >= 1, "Down-gap setup should fire LONG at least once"


def test_long_traded_today_guard():
    df = _make_synthetic_df(gap_size=-3.0)
    features = compute_features(df)
    state = {"long_traded_today": True, "short_traded_today": False, "position": 0}
    n = len(df)
    for i in range(20, n):
        if not features["entry_ok"][i]:
            continue
        if i == 0 or features["entry_ok"][i-1]:
            continue
        prev_close = features["prev_day_close"][i]
        if np.isnan(prev_close):
            continue
        gap = features["close"][i] - prev_close
        atr_i = features["atr"][i]
        if not np.isnan(atr_i) and gap < -0.5 * atr_i:
            d, _, _ = entry_gap_fill_trigger(features, i, state, {})
            assert d == 0, "long_traded_today=True must block LONG"
            return


def test_no_signal_when_gap_too_small():
    """If gap < min_gap_atr * ATR, no signal. Direct feature-manipulation test."""
    df = _make_synthetic_df(gap_size=3.0)
    features = compute_features(df)
    feat_copy = {k: (np.array(v, copy=True) if isinstance(v, np.ndarray) else v)
                 for k, v in features.items()}
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    n = len(df)
    # Find a session-opening bar with valid prev_close and ATR
    for i in range(20, n):
        if not feat_copy["entry_ok"][i]:
            continue
        if i == 0 or feat_copy["entry_ok"][i-1]:
            continue
        prev_close = feat_copy["prev_day_close"][i]
        atr_i = feat_copy["atr"][i]
        if np.isnan(prev_close) or np.isnan(atr_i) or atr_i == 0:
            continue
        # Force tiny gap: close = prev_close + 0.01*ATR (below 0.5*ATR threshold)
        feat_copy["close"][i] = prev_close + 0.01 * atr_i
        d, _, _ = entry_gap_fill_trigger(feat_copy, i, state, {})
        assert d == 0, f"Tiny gap at i={i} (0.01*ATR) must not fire"
        return


def test_no_signal_beyond_session_open_bars():
    """Bars deeper into session (beyond session_open_bars) should not fire."""
    df = _make_synthetic_df(gap_size=3.0)
    features = compute_features(df)
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    n = len(df)
    for i in range(20, n):
        if not features["in_session"][i]:
            continue
        # Find bar that's deep into session
        n_consec = 0
        j = i
        while j >= 0 and features["in_session"][j]:
            n_consec += 1; j -= 1
        if n_consec > 3:
            d, _, _ = entry_gap_fill_trigger(features, i, state, {})
            assert d == 0, f"Bar deep in session (n_consec={n_consec}) should not fire"
            return


def test_entry_registered_in_entry_map():
    assert "gap_fill_trigger" in ENTRY_MAP
    assert ENTRY_MAP["gap_fill_trigger"] is entry_gap_fill_trigger


def test_generate_crossbred_signals_end_to_end():
    df = _make_synthetic_df(gap_size=3.0)
    sigs = generate_crossbred_signals(
        df, entry_name="gap_fill_trigger",
        exit_name="profit_ladder", filter_name="ema_slope", params={},
    )
    assert hasattr(sigs, "__len__")


def test_no_signal_with_zero_atr():
    df = _make_synthetic_df(gap_size=3.0)
    features = compute_features(df)
    feat_copy = {k: (np.array(v, copy=True) if isinstance(v, np.ndarray) else v)
                 for k, v in features.items()}
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    n = len(df)
    for i in range(20, n):
        if not feat_copy["entry_ok"][i]:
            continue
        if i == 0 or feat_copy["entry_ok"][i-1]:
            continue
        feat_copy["atr"][i] = 0.0
        d, _, _ = entry_gap_fill_trigger(feat_copy, i, state, {})
        assert d == 0
        return


if __name__ == "__main__":
    tests = [
        test_entry_returns_no_signal_at_index_0,
        test_entry_no_signal_outside_session,
        test_entry_fires_on_gap_up_short_fade,
        test_entry_fires_on_gap_down_long_fade,
        test_long_traded_today_guard,
        test_no_signal_when_gap_too_small,
        test_no_signal_beyond_session_open_bars,
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
