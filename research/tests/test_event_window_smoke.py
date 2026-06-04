"""Smoke test for the event-window Forge primitive.

Run via:
    python3 research/tests/test_event_window_smoke.py

Verifies:
1. Signal schema matches what `engine.backtest.run_backtest` consumes.
2. Synthetic event list produces the expected number of trades.
3. Long, short, and conditional direction modes all generate signals.
4. session-close exit produces same-day exits.
5. End-to-end `event_window_run` produces a metric dict identical in shape
   to `_xb_general` output (compatible with Forge `_metrics`/`_verdict`).
"""

from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from research.event_window_engine import (
    generate_event_window_signals,
    event_window_run,
)


def _synth_bars(n=200, start="2026-01-05 06:30", freq="5min"):
    """Synthesize OHLCV bars on a regular grid."""
    dts = pd.date_range(start=start, periods=n, freq=freq)
    rng = np.random.default_rng(42)
    close = 100 + np.cumsum(rng.normal(0, 0.2, n))
    df = pd.DataFrame({
        "datetime": dts,
        "open": close + rng.normal(0, 0.05, n),
        "high": close + np.abs(rng.normal(0, 0.1, n)),
        "low": close - np.abs(rng.normal(0, 0.1, n)),
        "close": close,
        "volume": rng.integers(50, 500, n),
    })
    return df


def test_schema_long_fixed_exit():
    df = _synth_bars()
    events = [df["datetime"].iloc[i] for i in (10, 50, 100, 150)]
    sigs = generate_event_window_signals(
        df, events=events,
        entry_offset_bars=1, exit_offset_bars=6,
        direction="long",
    )
    assert set(sigs.columns) >= {"signal", "exit_signal", "stop_price", "target_price"}, \
        f"missing columns: {sigs.columns.tolist()}"
    assert len(sigs) == len(df), "row count must match input bars"
    n_entries = int((sigs["signal"] == 1).sum())
    n_exits = int((sigs["exit_signal"] == 1).sum())
    assert n_entries == 4, f"expected 4 long entries, got {n_entries}"
    assert n_exits == 4, f"expected 4 long exits, got {n_exits}"
    # Entry index should be event_idx + 1 (entry_offset_bars=1)
    entry_idxs = np.where(sigs["signal"].values == 1)[0]
    assert list(entry_idxs) == [11, 51, 101, 151], f"entry idx mismatch: {entry_idxs}"
    # Exit index should be entry + 6
    exit_idxs = np.where(sigs["exit_signal"].values == 1)[0]
    assert list(exit_idxs) == [17, 57, 107, 157], f"exit idx mismatch: {exit_idxs}"
    print("✓ schema + long-fixed-exit ok")


def test_short_direction():
    df = _synth_bars()
    events = [df["datetime"].iloc[i] for i in (20, 80)]
    sigs = generate_event_window_signals(
        df, events=events,
        entry_offset_bars=0, exit_offset_bars=3,
        direction="short",
    )
    assert int((sigs["signal"] == -1).sum()) == 2, "short entries"
    assert int((sigs["exit_signal"] == -1).sum()) == 2, "short exits"
    print("✓ short direction ok")


def test_conditional_direction_callable():
    df = _synth_bars()
    events = [df["datetime"].iloc[i] for i in (15, 45, 75, 105)]
    # Alternate long/short by event index
    flipper = {events[0]: 1, events[1]: -1, events[2]: 0, events[3]: 1}
    sigs = generate_event_window_signals(
        df, events=events,
        entry_offset_bars=0, exit_offset_bars=4,
        direction=lambda dt: flipper[dt],
    )
    longs = int((sigs["signal"] == 1).sum())
    shorts = int((sigs["signal"] == -1).sum())
    assert longs == 2, f"expected 2 longs, got {longs}"
    assert shorts == 1, f"expected 1 short, got {shorts}"
    print("✓ conditional/callable direction ok")


def test_session_close_exit():
    df = _synth_bars(n=400)  # Spans multiple days at 5min freq (~33h)
    # Event at start of day 2
    day2_mask = pd.to_datetime(df["datetime"]).dt.date == pd.to_datetime(df["datetime"].iloc[200]).date()
    event_dt = df["datetime"][day2_mask].iloc[0]
    sigs = generate_event_window_signals(
        df, events=[event_dt],
        entry_offset_bars=0,
        exit_at_session_close=True,
        direction="long",
    )
    entry_idxs = np.where(sigs["signal"].values == 1)[0]
    exit_idxs = np.where(sigs["exit_signal"].values == 1)[0]
    assert len(entry_idxs) == 1 and len(exit_idxs) == 1
    # Exit must be on same calendar day as entry and at-or-after entry
    entry_dt = pd.to_datetime(df["datetime"].iloc[entry_idxs[0]])
    exit_dt = pd.to_datetime(df["datetime"].iloc[exit_idxs[0]])
    assert exit_dt.date() == entry_dt.date(), "session-close exit must be same day"
    assert exit_dt >= entry_dt, "exit must not precede entry"
    print(f"✓ session-close exit ok (entry={entry_dt}, exit={exit_dt})")


def test_overlap_protection():
    """Two events on the same entry bar — only one entry counts."""
    df = _synth_bars()
    same_dt = df["datetime"].iloc[50]
    sigs = generate_event_window_signals(
        df, events=[same_dt, same_dt],
        entry_offset_bars=0, exit_offset_bars=5,
        direction="long",
    )
    assert int((sigs["signal"] == 1).sum()) == 1, "overlap should collapse to 1"
    print("✓ overlap protection ok")


def test_event_outside_bar_range():
    """Events outside the bar range are handled gracefully (no crash).

    Semantics: too_late (no bar >= event_dt) → dropped.
    too_early (bar 0 is first bar >= too_early) → snaps to bar 0 if there's
    room to satisfy the exit.
    """
    df = _synth_bars()
    too_late = df["datetime"].iloc[-1] + pd.Timedelta("1h")
    too_early = df["datetime"].iloc[0] - pd.Timedelta("1h")
    # too_late alone: no entry
    sigs_late = generate_event_window_signals(
        df, events=[too_late],
        entry_offset_bars=0, exit_offset_bars=3,
        direction="long",
    )
    assert int(sigs_late["signal"].sum()) == 0, "too-late event must not produce entry"
    # too_early alone with valid exit room: snaps to bar 0
    sigs_early = generate_event_window_signals(
        df, events=[too_early],
        entry_offset_bars=0, exit_offset_bars=3,
        direction="long",
    )
    assert int((sigs_early["signal"] == 1).sum()) == 1, "too-early should snap to bar 0"
    # too_early with no exit room (offset > remaining bars): dropped
    sigs_no_room = generate_event_window_signals(
        df, events=[df["datetime"].iloc[-2]],
        entry_offset_bars=0, exit_offset_bars=10,
        direction="long",
    )
    assert int(sigs_no_room["signal"].sum()) == 0, "no exit room → dropped"
    print("✓ event-range handling ok")


def test_validation_errors():
    df = _synth_bars()
    try:
        generate_event_window_signals(
            df, events=[df["datetime"].iloc[10]],
            exit_offset_bars=5, exit_at_session_close=True,
            direction="long",
        )
        assert False, "should have raised on dual exit rules"
    except ValueError:
        pass
    try:
        generate_event_window_signals(
            df, events=[df["datetime"].iloc[10]],
            direction="long",
        )
        assert False, "should have raised on no exit rule"
    except ValueError:
        pass
    print("✓ validation errors ok")


def test_end_to_end_with_real_data():
    """Run the full event_window_run pipeline against real MCL bars + a
    synthetic event list (5 random EIA-Wed-like timestamps in 2025).
    Verifies the metric dict shape matches what _xb_general returns."""
    import sys as _sys
    _sys.path.insert(0, str(ROOT))
    from research.event_window_engine import event_window_run
    from research.fql_forge_batch_runner import _metrics

    # Construct 5 fake event timestamps — Wed 10:30 ET = ~14:30 UTC, but the
    # bars in this repo are in some local tz; we just pick 5 bars from MCL
    # that exist as event proxies.
    mcl_path = ROOT / "data" / "processed" / "MCL_5m.csv"
    df_mcl = pd.read_csv(mcl_path)
    rng = np.random.default_rng(7)
    sample_idxs = rng.choice(len(df_mcl) - 50, size=20, replace=False)
    sample_idxs.sort()
    events = pd.to_datetime(df_mcl["datetime"].iloc[sample_idxs]).tolist()

    res = event_window_run(
        asset="MCL",
        events=events,
        entry_offset_bars=1, exit_offset_bars=6,
        direction="long",
        label="SMOKE-EVT-MCL",
    )
    assert "trades_df" in res, "missing trades_df"
    assert "stats" in res, "missing stats"
    assert "costs" in res["stats"], "missing costs block (cost-aware)"
    m = _metrics(res["trades_df"], "SMOKE-EVT-MCL", costs=res["stats"]["costs"])
    # Must contain the Forge metric keys
    for k in ("label", "n", "net", "pf", "median", "max_dd", "archetype", "gate_verdict"):
        assert k in m, f"metric dict missing {k}"
    print(f"✓ end-to-end MCL smoke: n={m['n']} PF={m['pf']:.3f} net=${m['net']:.0f} median=${m['median']:.2f} archetype={m['archetype']} gate={m['gate_verdict']}")


if __name__ == "__main__":
    test_schema_long_fixed_exit()
    test_short_direction()
    test_conditional_direction_callable()
    test_session_close_exit()
    test_overlap_protection()
    test_event_outside_bar_range()
    test_validation_errors()
    test_end_to_end_with_real_data()
    print("\nALL SMOKE TESTS PASSED — event-window primitive is harness-ready.")
