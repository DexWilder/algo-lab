"""FQL Forge — Monthly Rebalance Harness (v1)

Reusable harness for FX-carry, cross-asset value/carry, and other monthly
rebalance candidates. Generates `signal` / `exit_signal` columns aligned to
bar-level OHLCV data from a month-end signal series, then plugs into the
existing `engine.backtest.run_backtest` → `research.fql_forge_batch_runner._metrics`
pipeline.

**Authority:** T1 — research-grade. Lane B / report-only. No registry mutation.

**Scope (locked 2026-06-02 per operator approval):**
- monthly rebalance (last business day of month → first bar of next month)
- flat / long / short monthly signal
- month-end entry; exit at next month's rebalance bar
- volatility sizing OPTIONAL in v1 (not required; contracts=1 default)
- metrics output goes through standard Forge `_metrics`; max-year concentration,
  positive-year fraction, drawdown duration come for free from the existing
  cheap-screen metric block
- minimum viable; no data-fetch (FRED/BoJ) built here — caller supplies the
  signal series

Unlocks:
- Spec C: CRY-Policy-Rate-Differential-6J (FRED Fed Funds − BoJ policy rate
  monthly spread → 6J short/flat signal)
- Future cross-asset value/carry monthly rebalance candidates
- Templates monthly rebalancing for any single-leg asset; spread/pairs is a
  later extension.
"""

from __future__ import annotations

from typing import Union
import numpy as np
import pandas as pd


SignalT = Union[pd.Series, dict]  # month-end date → -1/0/1


def _normalize_signal_series(signal: SignalT) -> pd.Series:
    """Coerce dict / Series into a sorted Series indexed by pd.Timestamp."""
    if isinstance(signal, dict):
        s = pd.Series(signal)
    elif isinstance(signal, pd.Series):
        s = signal.copy()
    else:
        raise TypeError(f"signal must be Series or dict, got {type(signal).__name__}")
    s.index = pd.to_datetime(s.index)
    s = s.sort_index()
    # Coerce to ints; allow nan to mean flat
    s = s.fillna(0).astype(int)
    bad = s[~s.isin([-1, 0, 1])]
    if len(bad):
        raise ValueError(f"signal values must be -1, 0, or 1; got: {bad.head().to_dict()}")
    return s


def _first_bar_on_or_after(dts: pd.Series, ts: pd.Timestamp) -> int | None:
    """Return row index of first bar with datetime >= ts, or None."""
    mask = dts.values >= ts.to_datetime64()
    if not mask.any():
        return None
    return int(np.argmax(mask))


def generate_monthly_rebalance_signals(
    df: pd.DataFrame,
    signal: SignalT,
) -> pd.DataFrame:
    """Build (signal, exit_signal) on a bar grid from monthly signals.

    Behavior:
    - Each non-zero monthly signal becomes a long/short entry at the first bar
      with datetime >= signal's index timestamp.
    - The entry is closed at the entry bar of the next non-flat-or-zero signal
      OR the first bar of the next month (whichever comes first). v1: exit at
      next signal's entry bar regardless of value, then immediately re-enter
      if next signal is non-zero on a different bar.
    - The final signal exits at the last bar in `df` (no orphan position).

    Parameters
    ----------
    df : DataFrame
        OHLCV bars with a 'datetime' column.
    signal : Series or dict
        Map of month-end (or arbitrary rebalance) timestamps → {-1, 0, 1}.

    Returns
    -------
    DataFrame with columns (signal, exit_signal, stop_price, target_price)
    aligned to df. stop/target are NaN — monthly rebalance candidates do not
    use stop-loss in v1.
    """
    s = _normalize_signal_series(signal)
    n = len(df)
    sig_arr = np.zeros(n, dtype=int)
    exit_arr = np.zeros(n, dtype=int)
    if n == 0 or len(s) == 0:
        return pd.DataFrame({
            "signal": sig_arr, "exit_signal": exit_arr,
            "stop_price": np.full(n, np.nan), "target_price": np.full(n, np.nan),
        })

    dts = pd.to_datetime(df["datetime"]).reset_index(drop=True)

    # Map each rebalance timestamp → bar index it lands on
    rebal_bars = []
    for ts, val in s.items():
        idx = _first_bar_on_or_after(dts, ts)
        rebal_bars.append((idx, val))

    # Walk through rebalances, emitting entry at this bar & exit at next bar
    open_pos = 0  # current sign
    open_bar = None
    for k, (idx, val) in enumerate(rebal_bars):
        if idx is None:
            # rebalance timestamp later than all bars — close any open position now
            break

        # Close any open position at this bar (next rebalance arrived)
        if open_pos != 0 and open_bar is not None and idx > open_bar:
            exit_arr[idx] = open_pos
            open_pos = 0
            open_bar = None

        # Open new position if val is non-zero
        if val != 0:
            # If something is already open at this bar (shouldn't happen given
            # exit just above), skip — v1 is non-overlapping monthly.
            if sig_arr[idx] == 0:
                sig_arr[idx] = val
                open_pos = val
                open_bar = idx

    # Close trailing position at last bar
    if open_pos != 0 and open_bar is not None:
        last = n - 1
        if last > open_bar:
            exit_arr[last] = open_pos

    return pd.DataFrame({
        "signal": sig_arr,
        "exit_signal": exit_arr,
        "stop_price": np.full(n, np.nan),
        "target_price": np.full(n, np.nan),
    })


def monthly_rebalance_run(
    asset: str,
    signal: SignalT,
    label: str = "MONTHLY-rebal",
    mode: str = "both",
    contracts: int = 1,
):
    """Run a single monthly-rebalance candidate end-to-end.

    Returns the run_backtest dict (with trades_df, stats, equity_curve) so the
    Forge runner can wrap _metrics around it identically to _xb_general.
    """
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

    sigs = generate_monthly_rebalance_signals(df, signal=signal)
    res = run_backtest(
        df, sigs, mode=mode,
        point_value=cfg["point_value"], symbol=asset,
        contracts=contracts,
    )
    return res


# ─────────────────────────────────────────────────────────────────────────────
# Convenience: build a Fed-vs-BoJ policy-rate-differential signal series given
# rate inputs. This is the Spec C carry rule (canonical FX carry):
#     spread_t = fed_funds_t - boj_policy_t
#     signal_t = -1 if spread_t > median_12m(spread) AND Δspread_t >= 0
#     else 0
# Caller supplies the two rate series indexed by month-end timestamps.
# ─────────────────────────────────────────────────────────────────────────────


def build_policy_differential_signal(
    fed_funds: pd.Series,
    boj_rate: pd.Series,
    lookback_months: int = 12,
) -> pd.Series:
    """Build month-end signal series for the Fed-BoJ carry rule.

    -1 (short 6J): when spread > trailing median AND spread Δ ≥ 0
     0 (flat):    otherwise
    Never goes long in v1 (canonical rule per harvest note).
    """
    fed = fed_funds.copy()
    boj = boj_rate.copy()
    fed.index = pd.to_datetime(fed.index)
    boj.index = pd.to_datetime(boj.index)
    # Align on common month-end index
    spread = (fed - boj).dropna().sort_index()
    if len(spread) < lookback_months + 1:
        return pd.Series(dtype=int)
    median_tr = spread.rolling(lookback_months, min_periods=lookback_months).median()
    delta = spread.diff()
    sig = pd.Series(0, index=spread.index, dtype=int)
    cond = (spread > median_tr) & (delta >= 0)
    sig.loc[cond] = -1
    # Drop rows where median is NaN (warmup)
    sig = sig.loc[median_tr.notna()]
    return sig
