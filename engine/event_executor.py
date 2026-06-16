"""Shared EVENT EXECUTOR scaffold (report-only, NON-WIRED).

Converts the banked event-driven candidates (Rates-FOMC-week ZN/ZF + FOMC-MNQ
Phase 1D) from research-bench toward activation-ready infrastructure WITHOUT any
activation. This module is PURE decision/replay logic — it does NOT:
  - touch the live forward runner, fql_research_scheduler JOBS, or launchd agents
  - read/write the registry, portfolio, allocation, or trade logs
  - place orders or enable any paper/live/prop path

It is the out-of-band analog of the daily forward runner (cf. Treasury-Rolldown's
out-of-band monthly path), expressed as a spec + a dry-run replay so executor
FIDELITY can be proven against the validated backtests before any wiring is ever
authorized. Wiring (scheduler/registry/order routing) is a SEPARATE, gated step.

One spec shape serves BOTH:
  - daily td-window events (ZN/ZF FOMC-week: enter Ntd pre, exit Mtd post, $ stop)
  - intraday bar-window events (FOMC-MNQ-Long-1h: enter +1 bar, hold 12 bars)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class EventStrategySpec:
    name: str
    instrument: str
    calendar: str                 # e.g. "FOMC_official"
    timeframe: str                # "daily" | "intraday_5m"
    direction: int                # +1 long, -1 short
    entry_offset: int             # daily: trading-days rel to event; intraday: bars rel to event-aligned bar
    exit_offset: int              # daily: trading-days held; intraday: bars held
    point_value: float
    commission_per_side: float
    slippage_ticks: float
    tick_size: float
    stop_usd: Optional[float] = None
    event_time_et: str = "14:00:00"   # intraday alignment (FOMC 14:00 ET)
    exit_at_session_close: bool = False
    session_close_hour: Optional[int] = None
    archetype: str = "EVENT_TAIL"

    @property
    def round_trip_cost(self) -> float:
        per_side = self.commission_per_side + self.slippage_ticks * self.tick_size * self.point_value
        return 2 * per_side


def _daily_frame(df5: pd.DataFrame) -> pd.DataFrame:
    dt = pd.to_datetime(df5["datetime"])
    g = df5.assign(date=dt.dt.date).groupby("date").agg(
        o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last")).reset_index()
    return g


def replay(spec: EventStrategySpec, df5: pd.DataFrame, events: Iterable) -> pd.DataFrame:
    """Dry-run the executor over history; emit the trades it WOULD have taken.

    Pure: returns a trades DataFrame (entry_time, exit_time, pnl, exit_reason).
    No side effects. This is the live-decision logic in replay form.
    """
    events = [pd.Timestamp(e) for e in events]
    rows = []
    if spec.timeframe == "daily":
        g = _daily_frame(df5)
        gd = list(g["date"]); c = g["c"].values; lo = g["l"].values; hi = g["h"].values
        n = len(gd)
        for ev in events:
            # Daily timeframe: align on the event DATE (normalize away intraday time)
            # so the event day maps to itself; otherwise a 14:00 event vs midnight-keyed
            # daily bars shifts the window +1 day. (Fidelity check caught this.)
            ev_date = pd.Timestamp(ev).normalize()
            af = [i for i, d in enumerate(gd) if pd.Timestamp(d) >= ev_date]
            if not af:
                continue
            i = af[0]
            ei, xi = i + spec.entry_offset, i + spec.entry_offset + spec.exit_offset
            if ei < 0 or xi >= n or xi <= ei:
                continue
            entry = c[ei]; exit_px = None; reason = "time"
            if spec.stop_usd:
                sp = entry - spec.direction * spec.stop_usd / spec.point_value
                for j in range(ei + 1, xi + 1):
                    hit = lo[j] <= sp if spec.direction == 1 else hi[j] >= sp
                    if hit:
                        exit_px = sp; reason = "stop"; break
            if exit_px is None:
                exit_px = c[xi]
            pnl = spec.direction * (exit_px - entry) * spec.point_value - spec.round_trip_cost
            rows.append({"entry_time": pd.Timestamp(gd[ei]), "exit_time": pd.Timestamp(gd[xi]),
                         "pnl": pnl, "exit_reason": reason})
    elif spec.timeframe == "intraday_5m":
        df = df5.copy(); df["dt"] = pd.to_datetime(df["datetime"])
        dts = df["dt"].values; c = df["close"].values; n = len(df)
        for ev in events:
            # event-aligned bar = first bar at/after the event timestamp
            pos = int(np.searchsorted(dts, np.datetime64(ev)))
            if pos >= n:
                continue
            ei = pos + spec.entry_offset
            if ei < 0 or ei >= n:
                continue
            if spec.exit_at_session_close and spec.session_close_hour is not None:
                # last bar on entry day at/just before session_close_hour
                eday = pd.Timestamp(dts[ei]).date()
                xs = [k for k in range(ei + 1, n)
                      if pd.Timestamp(dts[k]).date() == eday and pd.Timestamp(dts[k]).hour <= spec.session_close_hour]
                xi = xs[-1] if xs else min(ei + 1, n - 1)
            else:
                xi = min(ei + spec.exit_offset, n - 1)
            if xi <= ei:
                continue
            entry = c[ei]; exit_px = c[xi]
            pnl = spec.direction * (exit_px - entry) * spec.point_value - spec.round_trip_cost
            rows.append({"entry_time": pd.Timestamp(dts[ei]), "exit_time": pd.Timestamp(dts[xi]),
                         "pnl": pnl, "exit_reason": "time"})
    else:
        raise ValueError(f"unknown timeframe {spec.timeframe!r}")
    return pd.DataFrame(rows)


def summarize(trades: pd.DataFrame) -> dict:
    if trades is None or trades.empty:
        return {"n": 0}
    p = trades["pnl"].to_numpy()
    g = p[p > 0].sum(); b = -p[p < 0].sum()
    pf = float(g / b) if b > 0 else float("inf")
    return {"n": int(len(p)), "pf": round(pf, 3), "median": round(float(np.median(p)), 2),
            "net": round(float(p.sum()), 2), "largest_loss": round(float(p.min()), 2),
            "stops": int((trades["exit_reason"] == "stop").sum())}
