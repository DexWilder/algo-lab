"""Cycle 2026-06-18d — COT-as-FILTER on live edges (priority #2, report-only).

Standalone COT reversal died (18c); COT-as-filter is the more plausible use. Partition the LIVE
edges' trades by COT positioning regime (as-of prior Fri release, no-lookahead) and see if a regime
materially + robustly improves the edge WITHOUT just slashing trades.
  Edge A: MGC prior_day_break (gold-cap-gated addition; 405 trades)  x COT GOLD regime
  Edge B: FOMC-week ZN sleeve (entry -2td / exit +2td, $1200 stop)   x COT 10Y regime
Discipline: no-lookahead Fri-release lag; overfit guard (retention floor 40%, n>=120 for A);
per-year stability; classify COT_FILTER_IMPROVES / NO_IMPROVEMENT / OVERFIT_RISK. No sweep, no mutation.
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


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def daily_close(a):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{a}_5m.csv"); dt = pd.to_datetime(df["datetime"])
    s = df.assign(date=dt.dt.normalize()).groupby("date")["close"].last(); s.index = pd.to_datetime(s.index).astype("datetime64[ns]"); return s


def cot_state(sym):
    c = pd.read_csv(ROOT / "data" / "feeds" / "cot.csv", parse_dates=["date"])
    c = c[c["sym"] == sym].sort_values("open_interest_all", ascending=False).drop_duplicates(["date"]).sort_values("date")
    c["z"] = (c["spec_net"] - c["spec_net"].rolling(52, min_periods=26).mean()) / c["spec_net"].rolling(52, min_periods=26).std()
    c["release"] = (c["date"] + pd.Timedelta(days=3)).astype("datetime64[ns]")
    return c.dropna(subset=["z"])


def attach(trades_dates, c):
    td = pd.DataFrame({"date": pd.to_datetime(trades_dates).astype("datetime64[ns]")}).sort_values("date")
    m = pd.merge_asof(td, c[["release", "z", "comm_net"]].dropna().sort_values("release"),
                      left_on="date", right_on="release", direction="backward", allow_exact_matches=False)
    assert int((m["release"] >= m["date"]).sum()) == 0, "LOOKAHEAD"
    return m.set_index("date")


def board(pnl):
    p = np.asarray(pnl, float)
    if len(p) < 12:
        return {"n": len(p), "pf": None}
    return {"n": len(p), "pf": round(_pf(p), 3), "net": round(float(p.sum()), 0), "median": round(float(np.median(p)), 2)}


def evaluate(name, trades, c, n_floor):
    """trades: df with date,pnl. Partition by COT regime; overfit-guarded."""
    base = board(trades["pnl"])
    st = attach(trades["date"], c)
    trades = trades.copy(); trades["z"] = st["z"].reindex(pd.to_datetime(trades["date"]).astype("datetime64[ns]")).values
    trades["comm"] = st["comm_net"].reindex(pd.to_datetime(trades["date"]).astype("datetime64[ns]")).values
    trades["yr"] = pd.to_datetime(trades["date"]).dt.year
    parts = {
        "specs_not_extreme_long(z<=0.5)": trades[trades["z"] <= 0.5],
        "specs_extreme_long(z>0.5)": trades[trades["z"] > 0.5],
        "comm_net_long": trades[trades["comm"] > 0],
        "comm_net_short": trades[trades["comm"] <= 0],
    }
    print(f"  {name}: baseline PF={base['pf']} n={base['n']}", flush=True)
    best = None
    for tag, sub in parts.items():
        if len(sub) < 12:
            print(f"    {tag:<32} n={len(sub)} (too few)", flush=True); continue
        b = board(sub["pnl"]); retain = round(len(sub) / base["n"] * 100, 1)
        yp = sub.groupby("yr")["pnl"].sum(); yrs_pos = f"{int((yp>0).sum())}/{int(yp.shape[0])}"
        improves = (b["pf"] or 0) >= (base["pf"] or 0) + 0.15
        ok_retain = retain >= 40 and len(sub) >= n_floor
        verdict = "IMPROVES" if (improves and ok_retain) else ("OVERFIT_RISK" if improves else "no-edge")
        print(f"    {tag:<32} n={len(sub)} ({retain}%) PF={b['pf']} net=${b['net']} yrs+={yrs_pos} -> {verdict}", flush=True)
        if verdict == "IMPROVES":
            best = (tag, b, retain)
    return {"baseline": base, "improving_partition": ({"tag": best[0], **best[1], "retain_pct": best[2]} if best else None),
            "verdict": "COT_FILTER_IMPROVES" if best else "NO_IMPROVEMENT"}


def run():
    print("Cycle 2026-06-18d — COT-as-FILTER on live edges (priority #2) (REPORT-ONLY)\n", flush=True)
    results = {}

    # Edge A: MGC prior_day_break x COT GOLD
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv"); cfg = ASSETS["MGC"]; cp = get_cost_params("MGC")
    sig = gcs(df, entry_name="prior_day_break", exit_name="profit_ladder", filter_name="ema_slope", params={})
    tr = run_backtest(df, sig, mode="both", point_value=cfg["point_value"], symbol="MGC",
                      commission_per_side=cp["commission_per_side"], slippage_ticks=cp["slippage_ticks"], tick_size=cp["tick_size"])["trades_df"]
    tA = pd.DataFrame({"date": pd.to_datetime(tr["entry_time"]).dt.normalize(), "pnl": tr["pnl"].values})
    tA = tA[tA["date"].dt.year >= 2019]
    results["A_MGC_priorday_x_GOLDcot"] = evaluate("A MGC-prior_day_break x COT-GOLD", tA, cot_state("GOLD"), 120)

    # Edge B: FOMC-week ZN (entry -2td exit +2td, $1200 stop) x COT 10Y
    s = daily_close("ZN"); days = list(s.index); pv = ASSETS["ZN"]["point_value"]; c2 = get_cost_params("ZN")
    rt = 2 * (c2["commission_per_side"] + c2["slippage_ticks"] * c2["tick_size"] * pv)
    fomc = [pd.Timestamp(x["actual_date"]).normalize() for x in build_official_fomc_calendar()]
    rows = []
    dset = set(days)
    for f in fomc:
        fd = f
        while fd not in dset and fd < days[-1]:
            fd += pd.Timedelta(days=1)
        if fd not in dset:
            continue
        i = days.index(fd); ei, xi = i - 2, i + 2
        if ei < 0 or xi >= len(days):
            continue
        rows.append({"date": days[ei], "pnl": float((s.loc[days[xi]] - s.loc[days[ei]]) * pv - rt)})
    tB = pd.DataFrame(rows)
    results["B_FOMCwk_ZN_x_10Ycot"] = evaluate("B FOMC-week-ZN x COT-10Y (small n)", tB, cot_state("10Y"), 12)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-18d_cot_filter.json"
    out.write_text(json.dumps({"cycle": "2026-06-18d_cot_filter", "mode": "Lane 1 report-only; COT-as-filter; NON-WIRED",
        "results": results, "boundaries": "overfit-guarded; no-lookahead Fri-release; no sweep/mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; COT-as-filter; no mutation)", flush=True)


if __name__ == "__main__":
    run()
