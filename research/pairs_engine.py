"""FQL Forge — Cross-Asset Pairs Harness (v1)

Reusable harness for 2-asset spread / pairs candidates. Computes the spread
series from two bar streams, generates z-score signals, runs a per-trade
PnL accounting that handles both legs cost-aware, and emits a `trades_df` +
metric dict in the same shape `engine.backtest.run_backtest` does so the
output flows through the standard `research.fql_forge_batch_runner._metrics`
→ `_verdict` pipeline unchanged.

**Authority:** T1 — research-grade. Lane B / report-only. No registry mutation.

**Scope (locked 2026-06-03 per operator approval):**
- Two assets (single pair)
- Spread = z-score of (normalized return A − normalized return B) over rolling window
- Signals: long spread (long A, short B) when z < -threshold; short when z > +threshold
- Hedge ratio: 1:1 contracts (v1) OR volatility-adjusted (v1 option)
- Rebalance frequency: monthly ("M") or daily ("D"); both supported
- Cost-aware: both legs charged via engine.asset_config
- Output: trades_df + stats compatible with `_metrics`

Unlocks (per V2/V3 etc.):
- V2: EQ-TY-YieldGap-MES-ZN (yield-gap value pair)
- Most VALUE/CARRY spread/pair specs in the harvest backlog (~40-60%)
- Future commodity calendar spreads, basis pairs, intra-asset-class pairs

Not in scope here:
- N>2 portfolio optimization (rotation harness is a separate later build)
- Cointegration regression / Kalman state — z-score MVP only
- Live execution; pure research backtest
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal, Union

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _resample_close(df: pd.DataFrame, freq: str) -> pd.Series:
    """Resample OHLCV to {freq} closes. freq in {'M','D'}."""
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime").sort_index()
    if freq.upper() == "M":
        return df["close"].resample("ME").last().dropna()
    if freq.upper() == "D":
        return df["close"].resample("1D").last().dropna()
    raise ValueError(f"unsupported freq {freq!r}; use 'M' or 'D'")


def _rolling_vol(series: pd.Series, window: int) -> pd.Series:
    """Rolling std of log-returns, used for vol-adjusted hedge."""
    rets = np.log(series / series.shift(1))
    return rets.rolling(window).std(ddof=0)


class PairSignalError(ValueError):
    """Raised when pair signal-class inputs are inconsistent / missing.
    Fail-closed per FQL Evidence Law."""


SIGNAL_CLASSES = ("return_z", "level_z", "yield_z", "fundamental_z")


def generate_pairs_signal(
    series_a: pd.Series,
    series_b: pd.Series,
    lookback: int = 12,
    z_threshold: float = 2.0,
    exit_z: float = 0.5,
    signal_class: str = "return_z",
) -> pd.Series:
    """Generate spread-z-score signals on a common date index.

    Signal classes (added 2026-06-04 per operator approval #19):
      - `return_z` (default; v1 behavior): z-score of (return_a − return_b)
        using rolling stats of each return series. Best for price-driven
        relative-value where neither series has a natural level interpretation.
      - `level_z`: rolling z-score of the level spread (series_a − series_b).
        Best when both series are mean-reverting around a common level
        (e.g., calendar spreads, well-cointegrated commodities).
      - `yield_z`: same math as level_z, but expects yield series as inputs
        (caller passes yields via override args in pairs_backtest). Distinct
        name for reporting clarity on curve trades.
      - `fundamental_z`: same math as level_z, but expects a fundamentals
        series (earnings yield, term premium, etc.) — typically loaded via
        fundamentals_cache. Distinct name for reporting clarity on macro pairs.

    -1 / 0 / +1 → short / flat / long spread (long = long A, short B).
    Entry when |z| > z_threshold. Stays in position until z crosses
    `exit_z` toward zero, then re-evaluates.
    """
    if signal_class not in SIGNAL_CLASSES:
        raise PairSignalError(
            f"signal_class={signal_class!r} not in {SIGNAL_CLASSES}"
        )

    idx = series_a.index.intersection(series_b.index)
    if len(idx) == 0:
        raise PairSignalError("series A and B share no common index after intersection")
    a = series_a.reindex(idx).sort_index()
    b = series_b.reindex(idx).sort_index()

    if signal_class == "return_z":
        ra = np.log(a / a.shift(1))
        rb = np.log(b / b.shift(1))
        mu_a = ra.rolling(lookback).mean()
        sd_a = ra.rolling(lookback).std(ddof=0)
        mu_b = rb.rolling(lookback).mean()
        sd_b = rb.rolling(lookback).std(ddof=0)
        za = (ra - mu_a) / sd_a.replace(0, np.nan)
        zb = (rb - mu_b) / sd_b.replace(0, np.nan)
        z_spread = za - zb
    else:
        # level_z / yield_z / fundamental_z all use the same math: rolling
        # z-score of the level spread. The named distinction is documentation,
        # not different mechanics — caller controls what series are passed in.
        spread = a - b
        mu_s = spread.rolling(lookback).mean()
        sd_s = spread.rolling(lookback).std(ddof=0)
        z_spread = (spread - mu_s) / sd_s.replace(0, np.nan)

    sig = pd.Series(0, index=idx, dtype=int)
    pos = 0
    for i in range(len(idx)):
        v = z_spread.iloc[i]
        if np.isnan(v):
            sig.iloc[i] = pos
            continue
        if pos == 1 and v >= -exit_z:
            pos = 0
        elif pos == -1 and v <= exit_z:
            pos = 0
        if pos == 0:
            if v < -z_threshold:
                pos = 1
            elif v > z_threshold:
                pos = -1
        sig.iloc[i] = pos
    return sig


def _hedge_contracts(price_a: float, price_b: float, pv_a: float, pv_b: float,
                     vol_a: float | None, vol_b: float | None,
                     hedge: str) -> tuple[float, float]:
    """Return (contracts_a, contracts_b) for a 1-unit long-spread position.
    Sign convention: long spread → contracts_a > 0, contracts_b < 0.
    """
    if hedge == "1:1":
        return 1.0, -1.0
    if hedge == "vol_adjusted":
        if vol_a is None or vol_b is None or vol_a == 0 or vol_b == 0:
            return 1.0, -1.0  # fallback
        # Equal dollar-vol contribution: contracts ∝ 1 / (vol * notional)
        nom_a = price_a * pv_a * vol_a
        nom_b = price_b * pv_b * vol_b
        ratio = nom_a / nom_b if nom_b != 0 else 1.0
        return 1.0, -ratio
    if hedge == "notional":
        nom_a = price_a * pv_a
        nom_b = price_b * pv_b
        ratio = nom_a / nom_b if nom_b != 0 else 1.0
        return 1.0, -ratio
    raise ValueError(f"unknown hedge {hedge!r}")


def pairs_backtest(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    asset_a: str,
    asset_b: str,
    freq: Literal["M", "D"] = "M",
    lookback: int = 12,
    z_threshold: float = 2.0,
    exit_z: float = 0.5,
    hedge: Literal["1:1", "vol_adjusted", "notional"] = "1:1",
    label: str = "PAIR",
    signal_class: str = "return_z",
    series_a_override: pd.Series | None = None,
    series_b_override: pd.Series | None = None,
):
    """End-to-end pair backtest. Returns dict with trades_df + stats.

    Signal-class adapter (added 2026-06-04):
      - `signal_class` selects how the spread z-score is computed.
      - `series_a_override` / `series_b_override`: if provided, these series
        drive signal generation (e.g., yields for curve trades, fundamentals
        for value pairs). Price data df_a/df_b is still used for PnL accounting.
      - `level_z`, `yield_z`, `fundamental_z` require overrides on both sides
        OR a single-side override (e.g., a yield series for asset A and the
        same conversion for asset B). Fail-closed if signal_class is not
        `return_z` and no overrides are supplied — we don't silently fall back.
    """
    from engine.asset_config import ASSETS
    from engine.backtest import get_cost_params

    cfg_a, cfg_b = ASSETS[asset_a], ASSETS[asset_b]
    pv_a, pv_b = cfg_a["point_value"], cfg_b["point_value"]
    costs_a = get_cost_params(asset_a)
    costs_b = get_cost_params(asset_b)

    # Price closes always come from df_a / df_b — PnL is in price space.
    a_px = _resample_close(df_a, freq)
    b_px = _resample_close(df_b, freq)

    # Signal-generation series can be overridden per signal_class
    if signal_class == "return_z":
        a_sig, b_sig = a_px, b_px
    else:
        if series_a_override is None or series_b_override is None:
            raise PairSignalError(
                f"signal_class={signal_class!r} requires both series_a_override and "
                f"series_b_override (fail-closed; no silent fallback to price)"
            )
        a_sig = series_a_override.copy()
        b_sig = series_b_override.copy()
        # Align signal series to price index frequency (resample to freq)
        try:
            a_sig.index = pd.to_datetime(a_sig.index)
            b_sig.index = pd.to_datetime(b_sig.index)
        except Exception as e:
            raise PairSignalError(f"override series index not date-parseable: {e}")

    sig = generate_pairs_signal(a_sig, b_sig, lookback=lookback,
                                z_threshold=z_threshold, exit_z=exit_z,
                                signal_class=signal_class)
    # Align everything to a common index (intersection of price series + signal).
    # The PnL walk uses positional .iloc, so a / b / sig must share length.
    common_idx = a_px.index.intersection(b_px.index).intersection(sig.index)
    if len(common_idx) == 0:
        raise PairSignalError("no common index between price A, price B, and signal series")
    a = a_px.reindex(common_idx).sort_index()
    b = b_px.reindex(common_idx).sort_index()
    sig = sig.reindex(common_idx).fillna(0).astype(int)

    # Vol estimates for hedge sizing (computed AFTER alignment so they share index)
    vol_a = _rolling_vol(a, lookback) if hedge == "vol_adjusted" else None
    vol_b = _rolling_vol(b, lookback) if hedge == "vol_adjusted" else None

    # Walk signals → trades
    trades = []
    pos = 0
    entry_idx = None
    entry_ca = entry_cb = 0.0  # contracts
    entry_pa = entry_pb = 0.0  # entry prices
    for i in range(len(sig)):
        s = int(sig.iloc[i])
        if s != pos:
            # Close prior position if any
            if pos != 0 and entry_idx is not None:
                exit_pa = a.iloc[i]
                exit_pb = b.iloc[i]
                # PnL per contract
                pnl_a = (exit_pa - entry_pa) * pv_a * entry_ca
                pnl_b = (exit_pb - entry_pb) * pv_b * entry_cb
                # Round-trip commissions + slip on both legs
                comm_a = costs_a["commission_per_side"] * 2 * abs(entry_ca)
                comm_b = costs_b["commission_per_side"] * 2 * abs(entry_cb)
                slip_a = costs_a["slippage_ticks"] * costs_a["tick_size"] * pv_a * abs(entry_ca) * 2
                slip_b = costs_b["slippage_ticks"] * costs_b["tick_size"] * pv_b * abs(entry_cb) * 2
                gross = pnl_a + pnl_b
                friction = comm_a + comm_b + slip_a + slip_b
                pnl = gross - friction
                trades.append({
                    "entry_time": a.index[entry_idx],
                    "exit_time": a.index[i],
                    "side": "long_spread" if pos == 1 else "short_spread",
                    "entry_price_a": entry_pa,
                    "exit_price_a": exit_pa,
                    "entry_price_b": entry_pb,
                    "exit_price_b": exit_pb,
                    "contracts_a": entry_ca,
                    "contracts_b": entry_cb,
                    "gross": gross,
                    "friction": friction,
                    "pnl": pnl,
                })
            # Open new position if non-zero
            if s != 0:
                va = float(vol_a.iloc[i]) if vol_a is not None and not np.isnan(vol_a.iloc[i]) else None
                vb = float(vol_b.iloc[i]) if vol_b is not None and not np.isnan(vol_b.iloc[i]) else None
                ca, cb = _hedge_contracts(a.iloc[i], b.iloc[i], pv_a, pv_b, va, vb, hedge)
                # Short spread flips signs
                if s == -1:
                    ca, cb = -ca, -cb
                entry_ca, entry_cb = ca, cb
                entry_pa, entry_pb = a.iloc[i], b.iloc[i]
                entry_idx = i
                pos = s
            else:
                pos = 0
                entry_idx = None
    # Close trailing position
    if pos != 0 and entry_idx is not None and entry_idx < len(sig) - 1:
        i = len(sig) - 1
        exit_pa, exit_pb = a.iloc[i], b.iloc[i]
        pnl_a = (exit_pa - entry_pa) * pv_a * entry_ca
        pnl_b = (exit_pb - entry_pb) * pv_b * entry_cb
        comm_a = costs_a["commission_per_side"] * 2 * abs(entry_ca)
        comm_b = costs_b["commission_per_side"] * 2 * abs(entry_cb)
        slip_a = costs_a["slippage_ticks"] * costs_a["tick_size"] * pv_a * abs(entry_ca) * 2
        slip_b = costs_b["slippage_ticks"] * costs_b["tick_size"] * pv_b * abs(entry_cb) * 2
        gross = pnl_a + pnl_b
        friction = comm_a + comm_b + slip_a + slip_b
        trades.append({
            "entry_time": a.index[entry_idx], "exit_time": a.index[i],
            "side": "long_spread" if pos == 1 else "short_spread",
            "entry_price_a": entry_pa, "exit_price_a": exit_pa,
            "entry_price_b": entry_pb, "exit_price_b": exit_pb,
            "contracts_a": entry_ca, "contracts_b": entry_cb,
            "gross": gross, "friction": friction, "pnl": gross - friction,
        })

    trades_df = pd.DataFrame(trades)

    # Build a synthetic stats / costs block compatible with _metrics
    total_comm = sum(t["friction"] for t in trades) if trades else 0.0
    cost_tier = "VALIDATED" if (costs_a["cost_tier"] == "VALIDATED"
                                and costs_b["cost_tier"] == "VALIDATED") else "EXPLORATION_TIER"
    cost_block = {
        "commission_per_side": (costs_a["commission_per_side"] + costs_b["commission_per_side"]) / 2,
        "slippage_ticks": max(costs_a["slippage_ticks"], costs_b["slippage_ticks"]),
        "tick_size": min(costs_a["tick_size"], costs_b["tick_size"]),
        "total_commission": total_comm * 0.4,  # rough commission share
        "total_slippage": total_comm * 0.6,
        "total_friction": total_comm,
        "cost_tier": cost_tier,
        "symbol": f"{asset_a}/{asset_b}",
    }
    stats = {"costs": cost_block, "n_trades": len(trades_df)}
    return {
        "trades_df": trades_df,
        "stats": stats,
        "signal_series": sig,
        "label": label,
        "signal_class": signal_class,
        "used_overrides": series_a_override is not None or series_b_override is not None,
    }


def pairs_metrics(res: dict, label: str | None = None) -> dict:
    """Compute Forge-compatible metric dict from a pairs_backtest result.

    Equivalent to `_metrics` for single-asset XB results, but skips the
    archetype routing (pairs are by definition tail-like / event-like;
    archetype is computed independently here).
    """
    from research.fql_forge_batch_runner import _metrics
    trades = res["trades_df"]
    m = _metrics(trades, label or res.get("label", "PAIR"), costs=res["stats"]["costs"])
    return m
