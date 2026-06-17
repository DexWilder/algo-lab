"""Cross-asset confirmation/divergence harness — NO-LOOKAHEAD as a first-class requirement.

Report-only research. The cardinal rule: a trade on date D may only use a confirming
asset's state derived from data through STRICTLY PRIOR trading days. We enforce this with
merge_asof(direction='backward', allow_exact_matches=False) — the matched state date is
guaranteed < trade date — plus an explicit assertion in prove_no_lookahead().

Lookahead pitfalls this guards against:
  - using today's close to filter an earlier intraday trade today (we lag to prior day)
  - later-settled market confirming an earlier signal (strictly-prior only)
  - mismatched timestamps / stale sessions (we align on normalized trading dates)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def daily_closes(asset: str) -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    dt = pd.to_datetime(df["datetime"])
    d = df.assign(date=dt.dt.normalize()).groupby("date").agg(c=("close", "last")).reset_index()
    return d  # columns: date, c


def trend_state(asset: str, lookback: int = 42) -> pd.DataFrame:
    """State KNOWN AS OF that date's close: sign of close-vs-close[lookback ago] + raw ret."""
    d = daily_closes(asset)
    d["ret"] = (d["c"] - d["c"].shift(lookback)) / d["c"].shift(lookback)
    d["state"] = np.sign(d["ret"]).fillna(0.0)
    return d[["date", "ret", "state"]].rename(columns={"ret": f"{asset}_ret", "state": f"{asset}_state"})


def dollar_state(lookback: int = 42, legs=("6E", "6J", "6B")) -> pd.DataFrame:
    """USD-strength proxy from FX basket: 6E/6J/6B are USD-quoted (leg up => USD down),
    so dollar strength = -mean(leg lookback returns). State known as of that date's close."""
    frames = []
    for a in legs:
        d = daily_closes(a); d[a] = (d["c"] - d["c"].shift(lookback)) / d["c"].shift(lookback)
        frames.append(d[["date", a]])
    m = frames[0]
    for f in frames[1:]:
        m = m.merge(f, on="date", how="inner")
    m["usd_ret"] = -m[list(legs)].mean(axis=1)
    m["usd_state"] = np.sign(m["usd_ret"]).fillna(0.0)
    return m[["date", "usd_ret", "usd_state"]]


def attribute_by_state(trades: pd.DataFrame, state_df: pd.DataFrame, state_col: str) -> pd.DataFrame:
    """Attach the confirming state as-of the STRICTLY-PRIOR trading day to each trade.
    NO-LOOKAHEAD enforced by allow_exact_matches=False (matched state date < trade date)."""
    t = trades.copy()
    t["trade_date"] = pd.to_datetime(t["entry_time"]).dt.normalize()
    t = t.sort_values("trade_date").reset_index(drop=True)
    s = state_df[["date", state_col]].dropna().sort_values("date").reset_index(drop=True)
    merged = pd.merge_asof(t, s.rename(columns={"date": "state_date"}), left_on="trade_date",
                           right_on="state_date", direction="backward", allow_exact_matches=False)
    return merged


def prove_no_lookahead(merged: pd.DataFrame) -> dict:
    """Assert every used state_date is STRICTLY before its trade_date."""
    ok = merged.dropna(subset=["state_date"])
    violations = int((ok["state_date"] >= ok["trade_date"]).sum())
    assert violations == 0, f"LOOKAHEAD LEAK: {violations} trades used same/future state"
    gaps = (ok["trade_date"] - ok["state_date"]).dt.days
    return {"trades_checked": int(len(ok)), "violations": violations,
            "min_lag_days": int(gaps.min()) if len(gaps) else None,
            "median_lag_days": float(gaps.median()) if len(gaps) else None,
            "unmatched_no_prior_state": int(merged["state_date"].isna().sum())}


def overlap_ranges(assets) -> dict:
    out = {}
    for a in assets:
        try:
            d = daily_closes(a)
            out[a] = {"start": str(d["date"].min().date()), "end": str(d["date"].max().date()), "days": int(len(d))}
        except Exception as e:
            out[a] = {"error": str(e)[:80]}
    return out
