"""FQL Forge — Event-Window Signal Primitive (v1)

Reusable harness adapter for event-driven candidates. Generates signal /
exit_signal columns in the same schema as
`research/crossbreeding/crossbreeding_engine.py::generate_crossbred_signals`
so the output plugs into the existing `engine/backtest.run_backtest` →
`research/fql_forge_batch_runner._metrics` pipeline unchanged.

**Authority:** T1 — research-grade. Lane B / report-only. No registry mutation.

**Scope (locked 2026-06-02 per operator approval):**
- accepts event timestamp list
- supports entry offset (bars relative to event)
- supports exit offset (fixed holding window in bars) OR session-close exit
- supports long / short / conditional direction (callable for per-event)
- emits the same DataFrame schema as crossbred signals
- minimum viable; no event-data ingestion built here
- unit/smoke-test on synthetic event list before any real candidate fires

Unlocks (future work, not in scope here):
- Treasury auction calendar candidates (Spec A)
- EIA inventory release candidates (Spec B, also needs M2 spread data)
- OPEC conference drift candidates (Spec D, also needs outcome list)
- FOMC drift / CPI / NFP / roll-day / structural event candidates
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Iterable, Union

import numpy as np
import pandas as pd


DirectionT = Union[int, str, Callable[[pd.Timestamp], int]]


def _resolve_direction(direction: DirectionT, event_dt: pd.Timestamp) -> int:
    """Map direction spec → signal int (1 long, -1 short, 0 skip)."""
    if callable(direction):
        v = int(direction(event_dt))
        if v not in (-1, 0, 1):
            raise ValueError(f"direction callable returned {v}; must be -1, 0, or 1")
        return v
    if isinstance(direction, str):
        s = direction.lower()
        if s == "long":
            return 1
        if s == "short":
            return -1
        if s in ("flat", "skip", "none"):
            return 0
        raise ValueError(f"unknown direction string: {direction!r}")
    if isinstance(direction, int):
        if direction in (-1, 0, 1):
            return direction
        raise ValueError(f"direction int must be -1, 0, or 1; got {direction}")
    raise TypeError(f"direction must be int / str / callable; got {type(direction).__name__}")


def _first_bar_at_or_after(dts: pd.Series, event_dt: pd.Timestamp) -> int | None:
    """Return row index of first bar with datetime >= event_dt, or None."""
    mask = dts.values >= event_dt.to_datetime64()
    if not mask.any():
        return None
    return int(np.argmax(mask))


def generate_event_window_signals(
    df: pd.DataFrame,
    events: Iterable[Union[str, pd.Timestamp]],
    entry_offset_bars: int = 0,
    exit_offset_bars: int | None = None,
    exit_at_session_close: bool = False,
    session_close_hour: int | None = None,
    direction: DirectionT = "long",
) -> pd.DataFrame:
    """Build (signal, exit_signal) frame from an event timestamp list.

    Parameters
    ----------
    df : DataFrame
        OHLCV bars with a 'datetime' column (parseable to pandas datetime).
    events : iterable of datetimes
        Event timestamps. Each one triggers at-most-one entry.
    entry_offset_bars : int, default 0
        Bars after the event-aligned bar to enter. Negative permitted (enter
        before event).
    exit_offset_bars : int or None, default None
        If set, exit N bars after entry. Must be > 0.
    exit_at_session_close : bool, default False
        Mutually exclusive with exit_offset_bars. If True, exit at the last
        bar whose datetime's hour == `session_close_hour` (UTC of the bar
        timestamps in df). Falls back to end of entry day if not given.
    session_close_hour : int or None
        Hour value for session-close exit. Optional.
    direction : int / str / callable
        1 / "long" → long entry; -1 / "short" → short; 0 / "flat" → skip;
        callable(event_dt) → -1/0/1 for per-event conditional direction.

    Returns
    -------
    DataFrame with columns (signal, exit_signal, stop_price, target_price)
    aligned to `df`'s row order. stop/target are NaN — event-window candidates
    do not use stop-loss in v1 (held through event window).

    Notes
    -----
    Same schema as `generate_crossbred_signals`. Plug directly into
    `run_backtest(df, sigs, mode='both', point_value=..., symbol=...)`.
    """
    if exit_offset_bars is not None and exit_at_session_close:
        raise ValueError("Specify exit_offset_bars OR exit_at_session_close, not both.")
    if exit_offset_bars is None and not exit_at_session_close:
        raise ValueError("Specify one exit rule: exit_offset_bars OR exit_at_session_close.")
    if exit_offset_bars is not None and exit_offset_bars <= 0:
        raise ValueError("exit_offset_bars must be positive.")

    n = len(df)
    signals = np.zeros(n, dtype=int)
    exits = np.zeros(n, dtype=int)

    if n == 0:
        return pd.DataFrame({
            "signal": signals, "exit_signal": exits,
            "stop_price": np.full(n, np.nan), "target_price": np.full(n, np.nan),
        })

    dts = pd.to_datetime(df["datetime"]).reset_index(drop=True)

    for ev in events:
        event_dt = pd.to_datetime(ev)
        ev_idx = _first_bar_at_or_after(dts, event_dt)
        if ev_idx is None:
            continue

        entry_idx = ev_idx + int(entry_offset_bars)
        if entry_idx < 0 or entry_idx >= n:
            continue

        sig = _resolve_direction(direction, event_dt)
        if sig == 0:
            continue

        # Prevent overlap: if an entry is already pending at this bar, skip
        # (later improvement: a position-state machine; v1 is event-disjoint).
        if signals[entry_idx] != 0:
            continue

        # Resolve exit
        if exit_offset_bars is not None:
            exit_idx = entry_idx + int(exit_offset_bars)
            if exit_idx >= n:
                # Truncate: don't open a trade we can't close
                continue
        else:
            # Session-close exit
            entry_date = dts.iloc[entry_idx].date()
            if session_close_hour is not None:
                same_day_close = (
                    (dts.dt.date == entry_date)
                    & (dts.dt.hour == int(session_close_hour))
                )
            else:
                same_day_close = dts.dt.date == entry_date
            close_idxs = np.where(same_day_close.values)[0]
            close_idxs = close_idxs[close_idxs >= entry_idx]
            if len(close_idxs) == 0:
                continue
            exit_idx = int(close_idxs[-1])
            if exit_idx <= entry_idx:
                continue

        signals[entry_idx] = sig
        exits[exit_idx] = sig

    out = pd.DataFrame({
        "signal": signals,
        "exit_signal": exits,
        "stop_price": np.full(n, np.nan),
        "target_price": np.full(n, np.nan),
    })
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Thin Forge candidate wrapper — analogous to research.fql_forge_batch_runner._xb_general
# Lives here (not in batch_runner) to keep the primitive importable for tests
# without dragging the whole batch_runner module.
# ─────────────────────────────────────────────────────────────────────────────


def event_window_run(
    asset: str,
    events: Iterable,
    entry_offset_bars: int = 0,
    exit_offset_bars: int | None = None,
    exit_at_session_close: bool = False,
    session_close_hour: int | None = None,
    direction: DirectionT = "long",
    label: str = "EVT-window",
    mode: str = "both",
):
    """Run a single event-window candidate end-to-end.

    Returns the same metric dict shape as `_xb_general` so the Forge runner can
    consume it identically. Costs are cost-aware via asset_config.
    """
    # Imports kept inside to avoid heavy module load at primitive import time
    from pathlib import Path
    import sys
    ROOT = Path(__file__).resolve().parent.parent
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from engine.asset_config import ASSETS
    from engine.backtest import run_backtest

    asset_path = ROOT / "data" / "processed" / f"{asset}_5m.csv"
    df = pd.read_csv(asset_path)
    cfg = ASSETS[asset]

    sigs = generate_event_window_signals(
        df,
        events=events,
        entry_offset_bars=entry_offset_bars,
        exit_offset_bars=exit_offset_bars,
        exit_at_session_close=exit_at_session_close,
        session_close_hour=session_close_hour,
        direction=direction,
    )
    res = run_backtest(
        df, sigs, mode=mode,
        point_value=cfg["point_value"], symbol=asset,
    )
    return res
