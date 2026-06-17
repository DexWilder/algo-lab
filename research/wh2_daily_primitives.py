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
    # 2-day high/low (of the two prior days, no lookahead — computed from completed bars)
    d["two_day_high"] = d["h"].rolling(2).max()
    d["two_day_low"] = d["l"].rolling(2).min()
    d["range_pctrank60"] = d["range"].rolling(60).apply(lambda x: (x.iloc[-1] >= x).mean(), raw=False)
    # consecutive same-direction daily-close streak (signed): +k = k up-closes, -k = k down-closes
    sign = np.sign(d["c"].diff().fillna(0.0))
    streak = np.zeros(len(d)); run = 0; last = 0.0
    for k in range(len(d)):
        s = sign.iloc[k]
        run = (run + 1) if (s != 0 and s == last) else (1 if s != 0 else 0)
        streak[k] = run * s; last = s if s != 0 else last
    d["streak"] = streak
    m = {}
    for i in range(1, len(d)):
        prev = d.iloc[i - 1]
        m[d.iloc[i]["date"]] = {
            "prev_inside": bool(prev["inside"]), "prev_outside": bool(prev["outside"]),
            "prev_nr7": bool(prev["nr7"]), "prev_down_close": bool(prev["down_close"]),
            "prev_ret_z": float(prev["ret_z"]) if pd.notna(prev["ret_z"]) else 0.0,
            "prev_high": float(prev["h"]), "prev_low": float(prev["l"]),
            "two_day_high": float(prev["two_day_high"]) if pd.notna(prev["two_day_high"]) else float(prev["h"]),
            "two_day_low": float(prev["two_day_low"]) if pd.notna(prev["two_day_low"]) else float(prev["l"]),
            "prev_range_pctrank": float(prev["range_pctrank60"]) if pd.notna(prev["range_pctrank60"]) else 0.5,
            "prev_streak": float(prev["streak"]),
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


def entry_two_day_break(f, i, state, params):
    dm = params.get("daily_map", {}).get(f["dates"][i])
    if not dm or not f["entry_ok"][i]:
        return 0, 0, 0
    c = f["close"][i]; atr = _atr(f, i); sm = params.get("stop_mult", 1.5); tm = params.get("target_mult", 2.0)
    if atr <= 0:
        return 0, 0, 0
    if c > dm["two_day_high"] and not state["long_traded_today"]:
        return 1, c - atr * sm, c + atr * tm
    if c < dm["two_day_low"] and not state["short_traded_today"]:
        return -1, c + atr * sm, c - atr * tm
    return 0, 0, 0


def entry_prior_day_midpoint_revert(f, i, state, params):
    if not f["entry_ok"][i]:
        return 0, 0, 0
    mid = f["prev_day_midpoint"][i]; atr = _atr(f, i)
    if mid is None or np.isnan(mid) or atr <= 0:
        return 0, 0, 0
    c = f["close"][i]; dist = (c - mid) / atr; k = params.get("ext", 1.5); sm = params.get("stop_mult", 1.5)
    if dist > k and not state["short_traded_today"]:       # extended above prior midpoint -> revert short
        return -1, c + atr * sm, mid
    if dist < -k and not state["long_traded_today"]:
        return 1, c - atr * sm, mid
    return 0, 0, 0


def entry_consecutive_close_reversion(f, i, state, params):
    dm = params.get("daily_map", {}).get(f["dates"][i])
    if not dm or not f["entry_ok"][i]:
        return 0, 0, 0
    streak = dm["prev_streak"]; thr = params.get("streak_thr", 3); c = f["close"][i]; atr = _atr(f, i)
    sm = params.get("stop_mult", 1.5); tm = params.get("target_mult", 1.5)
    if atr <= 0:
        return 0, 0, 0
    if streak >= thr and not state["short_traded_today"]:   # N up-closes -> fade short
        return -1, c + atr * sm, c - atr * tm
    if streak <= -thr and not state["long_traded_today"]:   # N down-closes -> fade long
        return 1, c - atr * sm, c + atr * tm
    return 0, 0, 0


def entry_pdh_pdl_false_sweep_reversal(f, i, state, params):
    """Prior-day high/low FALSE sweep: take out PDH/PDL then close back inside -> reverse.
    Behavioral: stop-runs resting liquidity at prior-day extremes, then mean-reverts."""
    if not f["entry_ok"][i] or i < 1:
        return 0, 0, 0
    pdh = f["prev_day_high"][i]; pdl = f["prev_day_low"][i]; atr = _atr(f, i)
    if pdh is None or np.isnan(pdh) or atr <= 0:
        return 0, 0, 0
    c = f["close"][i]; cp = f["close"][i - 1]; sm = params.get("stop_mult", 1.0); tm = params.get("target_mult", 1.5)
    if cp > pdh and c < pdh and not state["short_traded_today"]:   # swept PDH then reclaimed below
        return -1, pdh + atr * sm, c - atr * tm
    if cp < pdl and c > pdl and not state["long_traded_today"]:    # swept PDL then reclaimed above
        return 1, pdl - atr * sm, c + atr * tm
    return 0, 0, 0


def entry_post_large_move_followthrough(f, i, state, params):
    dm = params.get("daily_map", {}).get(f["dates"][i])
    if not dm or not f["entry_ok"][i]:
        return 0, 0, 0
    z = dm["prev_ret_z"]; thr = params.get("z_thresh", 1.5); c = f["close"][i]; atr = _atr(f, i)
    sm = params.get("stop_mult", 1.5); tm = params.get("target_mult", 2.0)
    if atr <= 0:
        return 0, 0, 0
    if z >= thr and not state["long_traded_today"]:        # big up day -> continue long
        return 1, c - atr * sm, c + atr * tm
    if z <= -thr and not state["short_traded_today"]:      # big down day -> continue short
        return -1, c + atr * sm, c - atr * tm
    return 0, 0, 0


def entry_vol_shock_response(f, i, state, params):
    """After a high-range (vol-shock) prior day, trade the next-day breakout continuation."""
    dm = params.get("daily_map", {}).get(f["dates"][i])
    if not dm or not f["entry_ok"][i] or dm["prev_range_pctrank"] < params.get("rank_thr", 0.85):
        return 0, 0, 0
    c = f["close"][i]; atr = _atr(f, i); sm = params.get("stop_mult", 1.5); tm = params.get("target_mult", 2.0)
    if atr <= 0:
        return 0, 0, 0
    if c > dm["prev_high"] and not state["long_traded_today"]:
        return 1, c - atr * sm, c + atr * tm
    if c < dm["prev_low"] and not state["short_traded_today"]:
        return -1, c + atr * sm, c - atr * tm
    return 0, 0, 0


# name -> (entry_fn, recommended_filter, recommended_exit)
# reversion -> filter 'none' + exit 'midline_target' (exit-thesis match); momentum -> 'ema_slope' + 'profit_ladder'
NEW_PRIMITIVES = {
    "inside_day_expansion": (entry_inside_day_expansion, "ema_slope", "profit_ladder"),
    "narrow_range_expansion": (entry_narrow_range_expansion, "ema_slope", "profit_ladder"),
    "outside_day_reversal": (entry_outside_day_reversal, "none", "midline_target"),
    "prior_close_reclaim": (entry_prior_close_reclaim, "none", "midline_target"),
    "post_large_loss_snapback": (entry_post_large_loss_snapback, "none", "midline_target"),
    "two_day_break": (entry_two_day_break, "ema_slope", "profit_ladder"),
    "prior_day_midpoint_revert": (entry_prior_day_midpoint_revert, "none", "midline_target"),
    "consecutive_close_reversion": (entry_consecutive_close_reversion, "none", "midline_target"),
    "pdh_pdl_false_sweep_reversal": (entry_pdh_pdl_false_sweep_reversal, "none", "midline_target"),
    "post_large_move_followthrough": (entry_post_large_move_followthrough, "ema_slope", "profit_ladder"),
    "vol_shock_response": (entry_vol_shock_response, "ema_slope", "profit_ladder"),
}
