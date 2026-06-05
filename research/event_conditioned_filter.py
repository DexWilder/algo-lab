"""FQL Forge — Event-Conditioned Filter Primitive (v1)

Discriminator primitive for event-window candidates. Per operator approval
2026-06-04 (#43): after 48 naive event-window candidates KILLed in a single
sweep across 6 microstructure-event families, build the discriminating filter
that looks at pre/event-bar/post-event features before allowing an entry.

**Authority:** T1 — research-grade. Lane B / report-only. No registry mutation.

**Scope (locked 2026-06-04):**
- Features computed per-event (not per-bar):
  - prior_5bar_return, prior_5bar_direction
  - prior_12bar_return, prior_12bar_direction
  - event_bar_range_pct, event_bar_atr_multiple
  - post_1bar_direction, post_1bar_range_pct
  - realized_vol_percentile_at_event
- Filter modes (composable; AND-combined):
  - fade_pre_event_move (only fire when pre-move significant; reverse direction)
  - follow_pre_event_move (only fire when pre-move significant; same direction)
  - require_event_bar_expansion (event-bar range > threshold × atr)
  - require_event_bar_compression (event-bar range < threshold × atr)
  - require_post_event_confirmation (post-1-bar in same direction as intended trade)
  - require_vol_above_percentile (atr_pctrank at event > threshold)
  - require_vol_below_percentile (atr_pctrank at event < threshold)
- Fail-closed: if any required feature is unavailable (NaN), event is excluded
- Integrates with event_window_engine via `event_filter` parameter
- Smoke-tested on synthetic event data + retested on Russell/CPI/non-equity

Not in scope:
- Multi-asset event filters (uses single-asset bar context)
- Order-flow features (no L2 data)
- Bayesian updating of feature thresholds
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class EventFeatureError(ValueError):
    """Raised when an event-conditioned filter cannot compute a required feature."""


# ─────────────────────────────────────────────────────────────────────────────
# Feature computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_event_features(df: pd.DataFrame, event_idx: int,
                            atr_period: int = 14,
                            atr_pctrank_window: int = 500) -> dict:
    """Compute pre/event/post features anchored at `event_idx`.

    Returns dict; missing features (e.g., insufficient warmup) are NaN.
    Caller decides how to handle NaN (typically fail-closed → reject event).
    """
    n = len(df)
    if event_idx < 0 or event_idx >= n:
        return {"_valid": False, "_reason": f"event_idx {event_idx} out of [0,{n})"}

    close = df["close"].values
    high = df["high"].values
    low = df["low"].values

    feat = {"_valid": True}

    # Prior N-bar return / direction
    for lookback in (5, 12):
        if event_idx - lookback < 0:
            feat[f"prior_{lookback}bar_return"] = np.nan
            feat[f"prior_{lookback}bar_direction"] = 0
        else:
            ret = (close[event_idx] - close[event_idx - lookback]) / close[event_idx - lookback]
            feat[f"prior_{lookback}bar_return"] = float(ret)
            feat[f"prior_{lookback}bar_direction"] = int(np.sign(ret))

    # Event bar features
    if event_idx == 0:
        feat["event_bar_range_pct"] = np.nan
        feat["event_bar_atr_multiple"] = np.nan
    else:
        ev_range = high[event_idx] - low[event_idx]
        feat["event_bar_range_pct"] = float(ev_range / close[event_idx])
        # Rolling ATR-14 ending at event_idx-1 (so event bar itself isn't smoothed in)
        if event_idx >= atr_period:
            prev_close = close[event_idx - atr_period - 1:event_idx - 1]
            highs = high[event_idx - atr_period:event_idx]
            lows = low[event_idx - atr_period:event_idx]
            tr = np.maximum.reduce([
                highs - lows,
                np.abs(highs - np.concatenate([[close[max(event_idx - atr_period - 1, 0)]],
                                                prev_close[:-1] if len(prev_close) > 0 else []]).flatten()[:len(highs)] if len(prev_close) > 0 else (highs - lows)),
            ])
            # Simpler/correct ATR:
            atr_window = np.zeros(atr_period)
            for k in range(atr_period):
                idx = event_idx - atr_period + k
                if idx <= 0:
                    atr_window[k] = high[idx] - low[idx]
                else:
                    pc = close[idx - 1]
                    atr_window[k] = max(high[idx] - low[idx],
                                        abs(high[idx] - pc),
                                        abs(low[idx] - pc))
            atr = float(np.mean(atr_window))
            feat["_atr_at_event"] = atr
            feat["event_bar_atr_multiple"] = float(ev_range / atr) if atr > 0 else np.nan
        else:
            feat["_atr_at_event"] = np.nan
            feat["event_bar_atr_multiple"] = np.nan

    # Post 1-bar features
    if event_idx + 1 >= n:
        feat["post_1bar_direction"] = 0
        feat["post_1bar_return"] = np.nan
        feat["post_1bar_range_pct"] = np.nan
    else:
        post_ret = (close[event_idx + 1] - close[event_idx]) / close[event_idx]
        feat["post_1bar_return"] = float(post_ret)
        feat["post_1bar_direction"] = int(np.sign(post_ret))
        post_range = high[event_idx + 1] - low[event_idx + 1]
        feat["post_1bar_range_pct"] = float(post_range / close[event_idx])

    # ATR percentile rank at event (uses prior atr values)
    if event_idx >= atr_period + atr_pctrank_window:
        atr_series = []
        for k in range(event_idx - atr_pctrank_window, event_idx):
            sub_high = high[max(k - atr_period, 0):k + 1]
            sub_low = low[max(k - atr_period, 0):k + 1]
            if len(sub_high) > 0:
                atr_series.append(np.mean(sub_high - sub_low))
        if atr_series:
            cur_atr = feat.get("_atr_at_event", np.nan)
            if not np.isnan(cur_atr):
                arr = np.array(atr_series)
                feat["realized_vol_percentile_at_event"] = float(
                    (arr <= cur_atr).mean() * 100
                )
            else:
                feat["realized_vol_percentile_at_event"] = np.nan
        else:
            feat["realized_vol_percentile_at_event"] = np.nan
    else:
        feat["realized_vol_percentile_at_event"] = np.nan

    return feat


# ─────────────────────────────────────────────────────────────────────────────
# Event filter modes
# ─────────────────────────────────────────────────────────────────────────────

def filter_fade_pre_event_move(feat: dict, intended_direction: int,
                                params: dict) -> tuple[bool, int]:
    """Only fire if pre-N-bar move is significant; return REVERSED direction.

    params:
      - prior_bars: int, default 5
      - threshold_pct: float, default 0.001 (10 bp)
    """
    lookback = params.get("prior_bars", 5)
    threshold = params.get("threshold_pct", 0.001)
    pre_ret = feat.get(f"prior_{lookback}bar_return")
    if pre_ret is None or np.isnan(pre_ret):
        return False, 0
    if abs(pre_ret) < threshold:
        return False, 0
    # Reverse the direction of pre-move
    return True, -int(np.sign(pre_ret))


def filter_follow_pre_event_move(feat: dict, intended_direction: int,
                                  params: dict) -> tuple[bool, int]:
    """Only fire if pre-N-bar move is significant; return SAME direction."""
    lookback = params.get("prior_bars", 5)
    threshold = params.get("threshold_pct", 0.001)
    pre_ret = feat.get(f"prior_{lookback}bar_return")
    if pre_ret is None or np.isnan(pre_ret):
        return False, 0
    if abs(pre_ret) < threshold:
        return False, 0
    return True, int(np.sign(pre_ret))


def filter_require_event_bar_expansion(feat: dict, intended_direction: int,
                                        params: dict) -> tuple[bool, int]:
    """Only fire if event-bar range > threshold × ATR."""
    threshold = params.get("expansion_threshold", 1.5)
    mult = feat.get("event_bar_atr_multiple")
    if mult is None or np.isnan(mult):
        return False, 0
    return mult >= threshold, intended_direction


def filter_require_event_bar_compression(feat: dict, intended_direction: int,
                                          params: dict) -> tuple[bool, int]:
    """Only fire if event-bar range < threshold × ATR (compression)."""
    threshold = params.get("compression_threshold", 0.7)
    mult = feat.get("event_bar_atr_multiple")
    if mult is None or np.isnan(mult):
        return False, 0
    return mult <= threshold, intended_direction


def filter_require_post_event_confirmation(feat: dict, intended_direction: int,
                                            params: dict) -> tuple[bool, int]:
    """Only fire if post-1-bar direction matches intended trade direction."""
    post_dir = feat.get("post_1bar_direction")
    if post_dir is None or post_dir == 0:
        return False, 0
    return post_dir == intended_direction, intended_direction


def filter_require_vol_above_percentile(feat: dict, intended_direction: int,
                                         params: dict) -> tuple[bool, int]:
    """Only fire if ATR percentile rank at event >= threshold."""
    threshold = params.get("vol_threshold", 70)
    pct = feat.get("realized_vol_percentile_at_event")
    if pct is None or np.isnan(pct):
        return False, 0
    return pct >= threshold, intended_direction


def filter_require_vol_below_percentile(feat: dict, intended_direction: int,
                                         params: dict) -> tuple[bool, int]:
    """Only fire if ATR percentile rank at event <= threshold."""
    threshold = params.get("vol_threshold", 30)
    pct = feat.get("realized_vol_percentile_at_event")
    if pct is None or np.isnan(pct):
        return False, 0
    return pct <= threshold, intended_direction


EVENT_FILTER_MAP: dict[str, Callable] = {
    "none": lambda feat, d, p: (True, d),
    "fade_pre_event_move": filter_fade_pre_event_move,
    "follow_pre_event_move": filter_follow_pre_event_move,
    "require_event_bar_expansion": filter_require_event_bar_expansion,
    "require_event_bar_compression": filter_require_event_bar_compression,
    "require_post_event_confirmation": filter_require_post_event_confirmation,
    "require_vol_above_percentile": filter_require_vol_above_percentile,
    "require_vol_below_percentile": filter_require_vol_below_percentile,
}


def resolve_event_filter(filter_name) -> Callable:
    """Resolve filter_name (str or list) into a single callable.
    Single string: returns the function directly.
    List: AND-combine; if any returns False the event is excluded; if any
    return a direction, the last non-zero direction wins (allows fade_pre
    or follow_pre to override the caller's intended direction).
    """
    if isinstance(filter_name, (list, tuple)):
        if not filter_name:
            raise EventFeatureError("event_filter list is empty")
        unknown = [n for n in filter_name if n not in EVENT_FILTER_MAP]
        if unknown:
            raise EventFeatureError(
                f"unknown event filter(s): {unknown}; registered: {sorted(EVENT_FILTER_MAP)}"
            )
        funcs = [EVENT_FILTER_MAP[n] for n in filter_name]

        def composite(feat, d, p):
            cur_dir = d
            for fn in funcs:
                ok, new_dir = fn(feat, cur_dir, p)
                if not ok:
                    return False, 0
                if new_dir != 0 and new_dir != cur_dir:
                    cur_dir = new_dir  # allow direction-modifier filters to set
            return True, cur_dir
        return composite

    if filter_name not in EVENT_FILTER_MAP:
        raise EventFeatureError(
            f"unknown event filter {filter_name!r}; registered: {sorted(EVENT_FILTER_MAP)}"
        )
    return EVENT_FILTER_MAP[filter_name]
