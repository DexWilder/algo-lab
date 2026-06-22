"""Cycle 2026-06-22j — P-SLEEVE: bench-construction report (report-only EVIDENCE MAPPING).

NOT portfolio approval. Quantify whether banked event/tail/overlay finds improve the TOTAL bench:
pairwise daily-PnL correlation, bad-day overlap (do sleeves offset incumbents' worst days?), combined
drawdown sequencing. NO promotion/sizing/wiring. Cadence caveat: sparse sleeves trade few days ->
correlations near 0 trivially; the decision metric is bad-day-offset + combined-DD, not raw corr.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import get_cost_params, run_backtest  # noqa: E402
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals as gcs  # noqa: E402
from research.forge_fomc_calendar_official import build_official_fomc_calendar  # noqa: E402


def _maxdd(d):
    c = d.sort_index().cumsum(); return float((c - c.cummax()).min())


def xb_daily(asset, entry):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv"); cfg = ASSETS[asset]; cp = get_cost_params(asset)
    s = gcs(df, entry_name=entry, exit_name="profit_ladder", filter_name="ema_slope", params={})
    tr = run_backtest(df, s, mode="both", point_value=cfg["point_value"], symbol=asset,
                      commission_per_side=cp["commission_per_side"], slippage_ticks=cp["slippage_ticks"], tick_size=cp["tick_size"])["trades_df"]
    d = pd.to_datetime(tr["entry_time"]).dt.normalize(); g = tr.assign(d=d).groupby("d")["pnl"].sum()
    g.index = pd.to_datetime(g.index); return g[g.index.year >= 2019]


def daily_close(a):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{a}_5m.csv"); dt = pd.to_datetime(df["datetime"])
    s = df.assign(date=dt.dt.normalize()).groupby("date")["close"].last(); s.index = pd.to_datetime(s.index); return s


def fomc_week_zn():
    s = daily_close("ZN"); s = s[s.index.year >= 2019]; days = list(s.index); dset = set(days)
    pv = ASSETS["ZN"]["point_value"]; cp = get_cost_params("ZN"); rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
    rows = {}
    for c in build_official_fomc_calendar():
        f = pd.Timestamp(c["actual_date"]).normalize()
        while f not in dset and f < days[-1]:
            f += pd.Timedelta(days=1)
        if f not in dset:
            continue
        i = days.index(f)
        if i - 2 < 0 or i + 2 >= len(days):
            continue
        rows[days[i + 2]] = (s.loc[days[i + 2]] - s.loc[days[i - 2]]) * pv - rt
    return pd.Series(rows)


def preholiday(asset):
    from pandas.tseries.holiday import USFederalHolidayCalendar, GoodFriday
    fed = USFederalHolidayCalendar().holidays("2019-01-01", "2026-12-31")
    drop = set(d.normalize() for d in fed if (d.month == 10 and d.weekday() == 0 and 8 <= d.day <= 14) or (d.month == 11 and d.day in (10, 11, 12)))
    hol = (set(d.normalize() for d in fed) - drop) | set(pd.Timestamp(d).normalize() for d in GoodFriday.dates("2019-01-01", "2026-12-31"))
    s = daily_close(asset); s = s[s.index.year >= 2019]; days = list(s.index); pv = ASSETS[asset]["point_value"]
    cp = get_cost_params(asset); rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
    rows = {}
    for h in sorted(hol):
        prior = [d for d in days if d.normalize() < h]
        if not prior or (h - prior[-1].normalize()).days > 4:
            continue
        pre = prior[-1]; i = days.index(pre)
        if i < 1:
            continue
        rows[pre] = (s.loc[pre] - s.iloc[i - 1]) * pv - rt
    return pd.Series(rows)


def run():
    print("Cycle 2026-06-22j — P-SLEEVE bench-construction (REPORT-ONLY evidence mapping)\n", flush=True)
    books = {
        "MNQ-ORB(inc)": xb_daily("MNQ", "orb_breakout"),
        "MNQ-stoprun(inc)": xb_daily("MNQ", "stop_run_reversal"),
        "MGC-ORB(inc)": xb_daily("MGC", "orb_breakout"),
        "MGC-priorday(cand)": xb_daily("MGC", "prior_day_break"),
        "FOMCwk-ZN(tail)": fomc_week_zn(),
        "preholiday-M2K(tail)": preholiday("M2K"),
    }
    for k, v in books.items():
        print(f"  {k:<22} days={len(v)} net=${v.sum():.0f} maxDD=${_maxdd(v):.0f}", flush=True)

    mat = pd.concat(books, axis=1).fillna(0.0)
    print("\n  PAIRWISE daily-PnL correlation (union dates, fill0; sparse->near0 trivially):", flush=True)
    corr = mat.corr().round(2)
    print(corr.to_string(), flush=True)

    # bad-day offset: incumbent-portfolio worst-20 days, what do tails/cands do?
    inc = books["MNQ-ORB(inc)"].add(books["MNQ-stoprun(inc)"], fill_value=0).add(books["MGC-ORB(inc)"], fill_value=0)
    worst = inc.sort_values().head(20).index
    print("\n  BAD-DAY OFFSET (sum on incumbents' worst-20 days; >0 offsets):", flush=True)
    for k in ("MGC-priorday(cand)", "FOMCwk-ZN(tail)", "preholiday-M2K(tail)"):
        v = books[k].reindex(worst).fillna(0.0)
        print(f"    {k:<22} sum=${v.sum():.0f} mean=${v.mean():.0f} %pos={float((v>0).mean())*100:.0f}%", flush=True)

    # combined DD: incumbents vs incumbents+each
    inc_dd = _maxdd(inc)
    print(f"\n  COMBINED max-DD: incumbents-only=${inc_dd:.0f}", flush=True)
    add = {}
    for k in ("MGC-priorday(cand)", "FOMCwk-ZN(tail)", "preholiday-M2K(tail)"):
        comb = inc.add(books[k], fill_value=0)
        add[k] = {"combined_net": round(float(comb.sum()), 0), "combined_dd": round(_maxdd(comb), 0),
                  "dd_delta": round(_maxdd(comb) - inc_dd, 0)}
        print(f"    +{k:<22} net=${comb.sum():.0f} maxDD=${_maxdd(comb):.0f} (DD {'better' if _maxdd(comb)>inc_dd else 'worse'} by ${abs(_maxdd(comb)-inc_dd):.0f})", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-22j_sleeve_construction.json"
    out.write_text(json.dumps({"cycle": "2026-06-22j_sleeve_construction", "mode": "report-only evidence mapping; NOT portfolio approval; NON-WIRED",
        "books": {k: {"days": int(len(v)), "net": round(float(v.sum()), 0), "max_dd": round(_maxdd(v), 0)} for k, v in books.items()},
        "correlation": corr.to_dict(), "incumbent_dd": round(inc_dd, 0), "additions": add,
        "boundaries": "no promotion/sizing/wiring/mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; bench evidence; no mutation)", flush=True)


if __name__ == "__main__":
    run()
