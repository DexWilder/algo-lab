"""Self-contained DAILY-STRUCTURE primitives for the daily-elite pressure-cooker.

REPORT-ONLY research primitives. NOT added to the production crossbreeding engine —
they are injected into a copy of ENTRY_MAP at runtime by the screening script, so they
run through the SAME validated generate_crossbred_signals -> run_backtest path (same
exits, filters, stops, session flatten) without mutating production code.

Entry signature matches the engine: fn(f, i, state, params) -> (signal, stop, target).
Daily-bar context (inside/outside/NR7/prev-return-z/prev hi-lo) is precomputed per asset
and passed in via params["daily_map"][date].
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def build_daily_map(df: pd.DataFrame) -> dict:
    dt = pd.to_datetime(df["datetime"])
    d = df.assign(date=dt.dt.normalize().dt.date).groupby("date").agg(
        o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last")).reset_index()
    d["range"] = d["h"] - d["l"]
    d["ret"] = d["c"].pct_change()
    d["inside"] = (d["h"] < d["h"].shift(1)) & (d["l"] > d["l"].shift(1))
    d["outside"] = (d["h"] > d["h"].shift(1)) & (d["l"] < d["l"].shift(1))
    d["nr7"] = d["range"] == d["range"].rolling(7).min()
    mu = d["ret"].rolling(20).mean(); sd = d["ret"].rolling(20).std()
    d["ret_z"] = (d["ret"] - mu) / sd
    d["down_close"] = d["c"] < d["o"]
    m = {}
    for i in range(1, len(d)):
        prev = d.iloc[i - 1]
        m[d.iloc[i]["date"]] = {
            "prev_inside": bool(prev["inside"]), "prev_outside": bool(prev["outside"]),
            "prev_nr7": bool(prev["nr7"]), "prev_down_close": bool(prev["down_close"]),
            "prev_ret_z": float(prev["ret_z"]) if pd.notna(prev["ret_z"]) else 0.0,
            "prev_high": float(prev["h"]), "prev_low": float(prev["l"]),
        }
    return m


def _atr(f, i):
    a = f["atr"][i]
    return a if (a and not np.isnan(a)) else 0.0


def entry_inside_day_expansion(f, i, state, params):
    dm = params.get("daily_map", {}).get(f["dates"][i])
    if not dm or not dm["prev_inside"] or not f["entry_ok"][i]:
        return 0, 0, 0
    c = f["close"][i]; atr = _atr(f, i); sm = params.get("stop_mult", 1.5); tm = params.get("target_mult", 2.0)
    if atr <= 0:
        return 0, 0, 0
    if c > dm["prev_high"] and not state["long_traded_today"]:
        return 1, c - atr * sm, c + atr * tm
    if c < dm["prev_low"] and not state["short_traded_today"]:
        return -1, c + atr * sm, c - atr * tm
    return 0, 0, 0


def entry_narrow_range_expansion(f, i, state, params):
    dm = params.get("daily_map", {}).get(f["dates"][i])
    if not dm or not dm["prev_nr7"] or not f["entry_ok"][i]:
        return 0, 0, 0
    c = f["close"][i]; atr = _atr(f, i); sm = params.get("stop_mult", 1.5); tm = params.get("target_mult", 2.0)
    if atr <= 0:
        return 0, 0, 0
    if c > dm["prev_high"] and not state["long_traded_today"]:
        return 1, c - atr * sm, c + atr * tm
    if c < dm["prev_low"] and not state["short_traded_today"]:
        return -1, c + atr * sm, c - atr * tm
    return 0, 0, 0


def entry_outside_day_reversal(f, i, state, params):
    dm = params.get("daily_map", {}).get(f["dates"][i])
    if not dm or not dm["prev_outside"] or not f["entry_ok"][i]:
        return 0, 0, 0
    if state["long_traded_today"] or state["short_traded_today"]:
        return 0, 0, 0
    c = f["close"][i]; atr = _atr(f, i); sm = params.get("stop_mult", 1.5); tm = params.get("target_mult", 2.0)
    if atr <= 0:
        return 0, 0, 0
    if dm["prev_down_close"]:   # prior outside day closed down -> revert long
        return 1, c - atr * sm, c + atr * tm
    return -1, c + atr * sm, c - atr * tm   # closed up -> revert short


def entry_prior_close_reclaim(f, i, state, params):
    if not f["entry_ok"][i] or i < 1:
        return 0, 0, 0
    pc = f["prev_day_close"][i]
    if pc is None or np.isnan(pc):
        return 0, 0, 0
    c = f["close"][i]; cp = f["close"][i - 1]; atr = _atr(f, i)
    sm = params.get("stop_mult", 1.5); tm = params.get("target_mult", 2.0)
    if atr <= 0:
        return 0, 0, 0
    if cp < pc and c > pc and not state["long_traded_today"]:     # reclaim from below
        return 1, c - atr * sm, c + atr * tm
    if cp > pc and c < pc and not state["short_traded_today"]:    # reject from above
        return -1, c + atr * sm, c - atr * tm
    return 0, 0, 0


def entry_post_large_loss_snapback(f, i, state, params):
    dm = params.get("daily_map", {}).get(f["dates"][i])
    if not dm or not f["entry_ok"][i] or state["long_traded_today"]:
        return 0, 0, 0
    if dm["prev_ret_z"] <= params.get("z_thresh", -1.5):    # prior day a large down move
        c = f["close"][i]; atr = _atr(f, i)
        if atr <= 0:
            return 0, 0, 0
        return 1, c - atr * params.get("stop_mult", 1.5), c + atr * params.get("target_mult", 2.0)
    return 0, 0, 0


# name -> (entry_fn, recommended_filter)  [reversion uses 'none' per filter pre-flight rule]
NEW_PRIMITIVES = {
    "inside_day_expansion": (entry_inside_day_expansion, "ema_slope"),
    "narrow_range_expansion": (entry_narrow_range_expansion, "ema_slope"),
    "outside_day_reversal": (entry_outside_day_reversal, "none"),
    "prior_close_reclaim": (entry_prior_close_reclaim, "none"),
    "post_large_loss_snapback": (entry_post_large_loss_snapback, "none"),
}
