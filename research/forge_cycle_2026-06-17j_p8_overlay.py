"""Cycle 2026-06-17j — Lane 2: P8 real-rate gate as an OVERLAY on the combined MGC sleeve.

NOT a WH2 test. Question: does the P8 real-rate state (favorable = DFII10 below its 60d mean,
lagged 1d) improve the COMBINED gold sleeve (MGC-ORB + MGC-prior_day_break) as an overlay/
enhancer? Compare baseline vs gated on net/PF/median/OOS/max-DD/worst-days/concentration/
trade-count(retention)/exposure-overlap. Overfit guard: predeclared retention floor. Classify
GOLD_SLEEVE_OVERLAY_CANDIDATE only if it improves risk profile WITHOUT just slashing trades;
never WH2 (it stays gold exposure). Report-only; no mutation.
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

RETAIN_FLOOR = 50.0  # predeclared: an overlay that keeps <50% of sleeve trades is over-cutting


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def sleeve_trades(entry):
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv"); cfg = ASSETS["MGC"]; c = get_cost_params("MGC")
    s = gcs(df, entry_name=entry, exit_name="profit_ladder", filter_name="ema_slope", params={})
    tr = run_backtest(df, s, mode="both", point_value=cfg["point_value"], symbol="MGC",
                      commission_per_side=c["commission_per_side"], slippage_ticks=c["slippage_ticks"], tick_size=c["tick_size"])["trades_df"]
    tr = tr.copy(); tr["date"] = pd.to_datetime(tr["entry_time"]).dt.normalize().astype("datetime64[ns]")
    return tr[["date", "pnl"]]


def metrics(tr):
    if tr is None or len(tr) < 30:
        return {"n": len(tr) if tr is not None else 0, "net": 0, "pf": None, "median": 0,
                "h1_pf": None, "h2_pf": None, "max_dd": 0, "worst_day": 0, "top3_pct": None, "yrs_pos": "0/0"}
    p = tr["pnl"].to_numpy(); n = len(p); net = float(p.sum())
    s = tr.set_index("date")["pnl"]; per_yr = s.groupby(s.index.year).sum()
    daily = s.groupby(s.index).sum().sort_index()
    eq = daily.cumsum().to_numpy(); dd = float((eq - np.maximum.accumulate(eq)).min())
    worst = float(daily.min())
    g = tr[tr["pnl"] > 0]["pnl"].sort_values(ascending=False); gp = float(g.sum())
    top3 = round(float(g.head(3).sum()) / gp * 100, 1) if gp > 0 else None
    h = n // 2
    return {"n": n, "net": round(net, 0), "pf": round(_pf(p), 3), "median": round(float(np.median(p)), 2),
            "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3), "max_dd": round(dd, 0),
            "worst_day": round(worst, 0), "top3_pct": top3, "yrs_pos": f"{int((per_yr>0).sum())}/{int(per_yr.shape[0])}"}


def run():
    print("Cycle 2026-06-17j — Lane 2: P8 real-rate OVERLAY on combined MGC sleeve (REPORT-ONLY)\n", flush=True)
    orb = sleeve_trades("orb_breakout"); pdb = sleeve_trades("prior_day_break")
    sleeve = pd.concat([orb, pdb], ignore_index=True).sort_values("date").reset_index(drop=True)
    sleeve = sleeve[sleeve["date"].dt.year >= 2019].reset_index(drop=True)
    print(f"Combined MGC sleeve (ORB + prior_day_break): n={len(sleeve)} trades", flush=True)

    rr = pd.read_csv(ROOT / "data" / "feeds" / "real_rates.csv", parse_dates=["date"])
    rr["date"] = pd.to_datetime(rr["date"]).astype("datetime64[ns]")
    # P8 gate: real yield below its 60d mean. FIX: compute the rolling mean on the GAP-CLEANED
    # series (dfii10 has holiday NaN; rolling(60) over raw -> NaN-poisoned mean -> false regime).
    rr = rr.sort_values("date").dropna(subset=["dfii10"]).reset_index(drop=True)
    rr["dfii10_mean60"] = rr["dfii10"].rolling(60).mean()
    rr["favorable"] = (rr["dfii10"] < rr["dfii10_mean60"]).astype(float)
    rr = rr.dropna(subset=["dfii10_mean60"])
    print(f"  [fix] favorable-regime fraction (clean): {round(float(rr[rr['date'].dt.year>=2019]['favorable'].mean()),3)}", flush=True)
    # attach as-of STRICTLY PRIOR day
    s = sleeve.sort_values("date")
    m = pd.merge_asof(s, rr[["date", "favorable"]].dropna().rename(columns={"date": "rdate"}),
                      left_on="date", right_on="rdate", direction="backward", allow_exact_matches=False)
    assert int((m["rdate"] >= m["date"]).sum()) == 0, "LOOKAHEAD"
    m = m.dropna(subset=["favorable"])

    base = metrics(m[["date", "pnl"]])
    gated = metrics(m[m["favorable"] == 1.0][["date", "pnl"]])
    retain = round(gated["n"] / base["n"] * 100, 1) if base.get("n") else 0
    print(f"\n  BASELINE sleeve : n={base['n']} net=${base['net']} PF={base['pf']} med=${base['median']} "
          f"maxDD=${base['max_dd']} worstday=${base['worst_day']} top3={base['top3_pct']}% H1/H2={base['h1_pf']}/{base['h2_pf']} yrs+={base['yrs_pos']}", flush=True)
    print(f"  P8-GATED sleeve : n={gated['n']} ({retain}% retained) net=${gated['net']} PF={gated['pf']} med=${gated['median']} "
          f"maxDD=${gated['max_dd']} worstday=${gated['worst_day']} top3={gated['top3_pct']}% H1/H2={gated['h1_pf']}/{gated['h2_pf']} yrs+={gated['yrs_pos']}", flush=True)

    # overlay value judgment (predeclared): improves PF AND (maxDD better OR worst-day better) AND retains >= floor
    improves_pf = gated.get("pf", 0) >= base.get("pf", 0) + 0.1
    improves_risk = (gated.get("max_dd", -9e9) > base.get("max_dd", -9e9)) or (gated.get("worst_day", -9e9) > base.get("worst_day", -9e9))
    enough = retain >= RETAIN_FLOOR
    if not enough:
        verdict = "REJECT_OVERLAY_overcuts"
    elif improves_pf and improves_risk:
        verdict = "GOLD_SLEEVE_OVERLAY_CANDIDATE"
    elif improves_pf or improves_risk:
        verdict = "MARGINAL_OVERLAY_watch"
    else:
        verdict = "REJECT_OVERLAY_no_improvement"
    print(f"\n  retention {retain}% (floor {RETAIN_FLOOR}%); PF lift {round(gated.get('pf',0)-base.get('pf',0),3)}; "
          f"maxDD {base['max_dd']}->{gated['max_dd']}; worstday {base['worst_day']}->{gated['worst_day']}", flush=True)
    print(f"\n  VERDICT: {verdict}  (gold-sleeve overlay only; NOT WH2 — still gold exposure)", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-17j_p8_overlay.json"
    out.write_text(json.dumps({"cycle": "2026-06-17j_p8_overlay", "mode": "Lane 2 report-only; gold-sleeve overlay eval; NON-WIRED",
        "baseline": base, "p8_gated": gated, "retention_pct": retain, "verdict": verdict,
        "note": "overlay on existing gold sleeve; stays gold exposure; NOT a WH2/diversifier",
        "boundaries": "no mutation/promotion/activation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; Lane 2 overlay; no mutation)", flush=True)


if __name__ == "__main__":
    run()
