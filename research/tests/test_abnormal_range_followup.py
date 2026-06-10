"""Smoke tests for entry_abnormal_range_followup primitive.

Per operator decision #127. Validates abnormal-range detection, direction
classification, continuation/fade modes, session-open detection, fail-closed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from research.crossbreeding.crossbreeding_engine import (  # noqa: E402
    ENTRY_MAP, compute_features, entry_abnormal_range_followup,
    generate_crossbred_signals,
)


def _make_synthetic_df(n_days=80, bars_per_day=78, seed=42, abnormal_day_idx=70,
                       abnormal_bullish=True):
    """Synthetic 5-min OHLCV with abnormal day at index `abnormal_day_idx`.

    Pre-RTH bars 08:00-09:30 (18 bars), RTH bars 09:30-15:45 (75 bars).
    """
    rng = np.random.default_rng(seed)
    rows = []
    base = 100.0
    for d in range(n_days):
        date = pd.Timestamp("2024-01-02") + pd.Timedelta(days=d)
        day_high_target = base + 1.0
        day_low_target = base - 1.0
        # If abnormal day, expand range significantly
        if d == abnormal_day_idx:
            day_high_target = base + 5.0
            day_low_target = base - 2.0 if abnormal_bullish else base - 5.0
            target_close = base + 4.5 if abnormal_bullish else base - 4.5
        else:
            target_close = base + rng.normal(0, 0.3)
        # Pre-RTH bars (18)
        for b in range(18):
            t = pd.Timestamp("08:00") + pd.Timedelta(minutes=b * 5)
            base += rng.normal(0, 0.05)
            rows.append((pd.Timestamp.combine(date, t.time()), base))
        # RTH bars (75) - drive toward target close
        rth_open = base
        if d == abnormal_day_idx:
            step = (target_close - rth_open) / 75
            for b in range(75):
                t = pd.Timestamp("09:30") + pd.Timedelta(minutes=b * 5)
                base = rth_open + step * (b + 1) + rng.normal(0, 0.3)
                rows.append((pd.Timestamp.combine(date, t.time()), base))
        else:
            for b in range(75):
                t = pd.Timestamp("09:30") + pd.Timedelta(minutes=b * 5)
                base += rng.normal(0, 0.15)
                rows.append((pd.Timestamp.combine(date, t.time()), base))
    df = pd.DataFrame(rows, columns=["datetime", "close"])
    rng2 = np.random.default_rng(seed + 1)
    n = len(df)
    df["open"] = df["close"] - rng2.normal(0, 0.02, n)
    df["high"] = df["close"] + np.abs(rng2.normal(0, 0.1, n))
    df["low"] = df["close"] - np.abs(rng2.normal(0, 0.1, n))
    df["volume"] = rng2.integers(100, 1000, n)
    return df


def test_entry_returns_no_signal_at_index_0():
    df = _make_synthetic_df()
    features = compute_features(df)
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    d, _, _ = entry_abnormal_range_followup(features, 0, state, {})
    assert d == 0


def test_entry_no_signal_outside_session():
    df = _make_synthetic_df()
    features = compute_features(df)
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    for i in range(1, len(df)):
        if not features["in_session"][i]:
            d, _, _ = entry_abnormal_range_followup(features, i, state, {})
            assert d == 0, f"Outside session i={i} must not fire"
            return


def test_features_computed():
    """Verify prev_day_range, prev_day_midpoint, prev_day_range_pctrank_60 in features."""
    df = _make_synthetic_df()
    features = compute_features(df)
    assert "prev_day_range" in features
    assert "prev_day_midpoint" in features
    assert "prev_day_range_pctrank_60" in features
    # At least some bars should have valid pctrank (after warm-up)
    valid = ~np.isnan(features["prev_day_range_pctrank_60"])
    assert valid.sum() > 0, "Expected at least one valid pctrank value"


def test_entry_no_signal_when_range_not_abnormal():
    """Bars where pctrank < threshold → no signal."""
    df = _make_synthetic_df()
    features = compute_features(df)
    feat_copy = {k: (np.array(v, copy=True) if isinstance(v, np.ndarray) else v)
                 for k, v in features.items()}
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    # Find a session-opening bar with low pctrank
    for i in range(1500, len(df)):
        if not feat_copy["in_session"][i] or feat_copy["in_session"][i-1]:
            continue
        pctrank = feat_copy["prev_day_range_pctrank_60"][i]
        if np.isnan(pctrank) or pctrank >= 80:
            continue
        d, _, _ = entry_abnormal_range_followup(feat_copy, i, state, {})
        assert d == 0, f"Non-abnormal day at i={i} pctrank={pctrank:.1f} must not fire"
        return


def test_entry_fires_continuation_long_after_abnormal_bullish():
    """Abnormal bullish day → continuation mode → LONG next day."""
    df = _make_synthetic_df(abnormal_day_idx=70, abnormal_bullish=True)
    features = compute_features(df)
    feat_copy = {k: (np.array(v, copy=True) if isinstance(v, np.ndarray) else v)
                 for k, v in features.items()}
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    # Find first session-opening bar after the abnormal day
    fired = 0
    for i in range(2000, len(df)):
        if not feat_copy["in_session"][i] or feat_copy["in_session"][i-1]:
            continue
        pctrank = feat_copy["prev_day_range_pctrank_60"][i]
        prev_close = feat_copy["prev_day_close"][i]
        prev_mid = feat_copy["prev_day_midpoint"][i]
        if np.isnan(pctrank) or np.isnan(prev_close) or np.isnan(prev_mid):
            continue
        if pctrank < 80:
            continue
        # Force a bullish abnormal day
        feat_copy["prev_day_close"][i] = feat_copy["prev_day_midpoint"][i] + 0.5
        d, _, _ = entry_abnormal_range_followup(
            feat_copy, i, state, {"mode": "continuation"})
        if d != 0:
            assert d == 1, f"Continuation+bullish should fire LONG, got {d}"
            fired += 1
            break
    assert fired >= 1, "Expected at least one fire for continuation+bullish"


def test_entry_fires_fade_short_after_abnormal_bullish():
    """Abnormal bullish day → fade mode → SHORT next day."""
    df = _make_synthetic_df(abnormal_day_idx=70, abnormal_bullish=True)
    features = compute_features(df)
    feat_copy = {k: (np.array(v, copy=True) if isinstance(v, np.ndarray) else v)
                 for k, v in features.items()}
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    fired = 0
    for i in range(2000, len(df)):
        if not feat_copy["in_session"][i] or feat_copy["in_session"][i-1]:
            continue
        pctrank = feat_copy["prev_day_range_pctrank_60"][i]
        prev_close = feat_copy["prev_day_close"][i]
        prev_mid = feat_copy["prev_day_midpoint"][i]
        if np.isnan(pctrank) or np.isnan(prev_close) or np.isnan(prev_mid):
            continue
        if pctrank < 80:
            continue
        # Force bullish
        feat_copy["prev_day_close"][i] = feat_copy["prev_day_midpoint"][i] + 0.5
        d, _, _ = entry_abnormal_range_followup(
            feat_copy, i, state, {"mode": "fade"})
        if d != 0:
            assert d == -1, f"Fade+bullish should fire SHORT, got {d}"
            fired += 1
            break
    assert fired >= 1, "Expected at least one fire for fade+bullish"


def test_long_traded_today_guard():
    df = _make_synthetic_df()
    features = compute_features(df)
    feat_copy = {k: (np.array(v, copy=True) if isinstance(v, np.ndarray) else v)
                 for k, v in features.items()}
    state = {"long_traded_today": True, "short_traded_today": False, "position": 0}
    for i in range(2000, len(df)):
        if not feat_copy["in_session"][i] or feat_copy["in_session"][i-1]:
            continue
        pctrank = feat_copy["prev_day_range_pctrank_60"][i]
        if np.isnan(pctrank) or pctrank < 80:
            continue
        feat_copy["prev_day_close"][i] = feat_copy["prev_day_midpoint"][i] + 0.5
        d, _, _ = entry_abnormal_range_followup(
            feat_copy, i, state, {"mode": "continuation"})
        assert d == 0, "long_traded_today=True must block LONG"
        return


def test_entry_registered_in_entry_map():
    assert "abnormal_range_followup" in ENTRY_MAP
    assert ENTRY_MAP["abnormal_range_followup"] is entry_abnormal_range_followup


def test_generate_crossbred_signals_end_to_end():
    df = _make_synthetic_df()
    sigs = generate_crossbred_signals(
        df, entry_name="abnormal_range_followup",
        exit_name="profit_ladder", filter_name="none",
        params={"mode": "continuation"},
    )
    assert hasattr(sigs, "__len__")


def test_no_signal_with_zero_atr():
    df = _make_synthetic_df()
    features = compute_features(df)
    feat_copy = {k: (np.array(v, copy=True) if isinstance(v, np.ndarray) else v)
                 for k, v in features.items()}
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    for i in range(2000, len(df)):
        if not feat_copy["in_session"][i] or feat_copy["in_session"][i-1]:
            continue
        pctrank = feat_copy["prev_day_range_pctrank_60"][i]
        if np.isnan(pctrank) or pctrank < 80:
            continue
        feat_copy["prev_day_close"][i] = feat_copy["prev_day_midpoint"][i] + 0.5
        feat_copy["atr"][i] = 0.0
        d, _, _ = entry_abnormal_range_followup(
            feat_copy, i, state, {"mode": "continuation"})
        assert d == 0, "Zero ATR must fail-closed"
        return


def test_unknown_mode_no_signal():
    """Unknown mode value → no signal (fail-closed)."""
    df = _make_synthetic_df()
    features = compute_features(df)
    feat_copy = {k: (np.array(v, copy=True) if isinstance(v, np.ndarray) else v)
                 for k, v in features.items()}
    state = {"long_traded_today": False, "short_traded_today": False, "position": 0}
    for i in range(2000, len(df)):
        if not feat_copy["in_session"][i] or feat_copy["in_session"][i-1]:
            continue
        pctrank = feat_copy["prev_day_range_pctrank_60"][i]
        if np.isnan(pctrank) or pctrank < 80:
            continue
        feat_copy["prev_day_close"][i] = feat_copy["prev_day_midpoint"][i] + 0.5
        d, _, _ = entry_abnormal_range_followup(
            feat_copy, i, state, {"mode": "garbage"})
        assert d == 0, "Unknown mode must fail-closed"
        return


if __name__ == "__main__":
    tests = [
        test_entry_returns_no_signal_at_index_0,
        test_entry_no_signal_outside_session,
        test_features_computed,
        test_entry_no_signal_when_range_not_abnormal,
        test_entry_fires_continuation_long_after_abnormal_bullish,
        test_entry_fires_fade_short_after_abnormal_bullish,
        test_long_traded_today_guard,
        test_entry_registered_in_entry_map,
        test_generate_crossbred_signals_end_to_end,
        test_no_signal_with_zero_atr,
        test_unknown_mode_no_signal,
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
