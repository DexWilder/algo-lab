"""Cycle 2026-06-16o — Daily Workhorse #2 CAMPAIGN board (report-only).

Continues the WH2 hunt past MGC prior_day_break (banked frequent gold diversifier, NOT
true daily). Targeted, NOT vanity grid: it (1) CROSS-ASSETS the winning mechanism
(prior_day_break + ema_slope + profit_ladder) across non-MNQ assets to see if it
generalizes or is gold-specific, and (2) tries two new MGC mechanisms (abnormal_range_
followup, orb_breakout). Every candidate runs the SAME board incl correlation to BOTH
MNQ workhorses, with cadence tiering (true-daily / weekly-frequent / sparse) and a
hard MNQ-cousin reject rule. Report-only; NO mutation; NON-WIRED.

Order maps to operator list: A MGC abnormal_range, B MGC orb_breakout, C MYM, D MES,
E MCL, F ZN/ZF, G FX(new-mechanism prior_day_break, not retired 6J salvage).
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
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402


def _pf(p):
    a = np.asarray(p, float); w = a[a > 0].sum(); l = -a[a < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def run_xb(asset, entry, exit_name="profit_ladder", filter_name="ema_slope"):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]; costs = get_cost_params(asset)
    sigs = generate_crossbred_signals(df, entry_name=entry, exit_name=exit_name, filter_name=filter_name, params={})
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol=asset,
                       commission_per_side=costs["commission_per_side"], slippage_ticks=costs["slippage_ticks"],
                       tick_size=costs["tick_size"])
    return _metrics(res["trades_df"], f"{asset}-{entry}", costs=res["stats"]["costs"]), res["trades_df"]


def concentration(trades):
    g = trades[trades["pnl"] > 0]["pnl"].sort_values(ascending=False); gross = float(g.sum())
    t = lambda k: round(float(g.head(k).sum()) / gross * 100, 1) if gross > 0 else None
    return t(3), t(5), t(10)


def dd_dur(trades):
    eq = trades.sort_values("entry_dt")["pnl"].cumsum().to_numpy()
    peak = np.maximum.accumulate(eq); dd = eq - peak; below = dd < 0
    longest = cur = 0
    for b in below:
        cur = cur + 1 if b else 0; longest = max(longest, cur)
    return round(float(dd.min()), 0), int(longest)


def daily_corr(a, b):
    da = a.copy(); da["d"] = pd.to_datetime(da["entry_time"]).dt.date
    db = b.copy(); db["d"] = pd.to_datetime(db["entry_time"]).dt.date
    pa = da.groupby("d")["pnl"].sum(); pb = db.groupby("d")["pnl"].sum()
    al = pd.concat([pa, pb], axis=1, keys=["a", "b"]).fillna(0.0)
    return round(float(al["a"].corr(al["b"])), 3)


def board(asset, entry, mnq_orb, mnq_srr):
    try:
        m, tr = run_xb(asset, entry)
    except Exception as e:
        return {"asset": asset, "mechanism": entry, "error": str(e)[:120], "verdict": "ERROR"}
    if tr is None or tr.empty or m["n"] < 30:
        return {"asset": asset, "mechanism": entry, "n": int(m.get("n", 0)), "verdict": "KILL_no_fire"}
    tr = tr.copy(); tr["entry_dt"] = pd.to_datetime(tr["entry_time"]); tr["year"] = tr["entry_dt"].dt.year
    net = float(tr["pnl"].sum()); n_years = int(tr["year"].nunique()); tpy = round(m["n"] / max(n_years, 1), 1)
    t3, t5, t10 = concentration(tr)
    maxdd, ddur = dd_dur(tr)
    yr_excl = [round(_pf(tr[tr["year"] != y]["pnl"]), 3) for y in sorted(tr["year"].unique())]
    st = tr.sort_values("entry_dt").reset_index(drop=True); cuts = np.linspace(0, len(st), 4).astype(int)
    eras = [round(_pf(st.iloc[cuts[i]:cuts[i+1]]["pnl"]), 3) for i in range(3)]
    mx = tr["pnl"].max(); mn = tr["pnl"].min(); single = round(max(abs(mx), abs(mn)) / net * 100, 1) if net else None
    c_orb = daily_corr(tr, mnq_orb); c_srr = daily_corr(tr, mnq_srr); cmax = max(abs(c_orb), abs(c_srr))

    cadence = "true-daily" if (tpy >= 120 and m["n"] >= 500) else ("weekly-frequent" if tpy >= 30 else "sparse")

    quality = (m["pf"] > 1.2 and m["median"] >= 0 and m["h1_pf"] > 1.0 and m["h2_pf"] > 1.0
               and (t3 or 99) < 30 and (t5 or 99) < 45 and (t10 or 99) < 55
               and m["max_year_share_pct"] < 40 and (m["years_positive"] / max(m["n_years"], 1)) >= 0.75
               and all(e > 1.0 for e in eras) and min(yr_excl) > 1.15 and (single or 99) < 25)
    decorrelated = cmax < 0.3
    mnq_lite = cmax >= 0.5

    if mnq_lite and not (asset in ("MGC", "MCL", "ZN", "ZF", "6E", "6J", "6B")):
        verdict = "REJECT_MNQ_COUSIN"
    elif not quality:
        verdict = "KILL"
    elif not decorrelated:
        verdict = "WATCH_corr"  # quality ok but 0.3<=corr<0.5
    elif cadence == "true-daily":
        verdict = "PACKET_CANDIDATE"
    else:
        verdict = "FORWARD_CLOCK_CREDIBLE"

    return {"asset": asset, "mechanism": entry, "n": m["n"], "trades_per_yr": tpy, "cadence": cadence,
            "pf": round(m["pf"], 3), "net": round(net, 0), "median": round(m["median"], 2),
            "h1_pf": round(m["h1_pf"], 3), "h2_pf": round(m["h2_pf"], 3), "max_year_pct": round(m["max_year_share_pct"], 1),
            "years_pos": f"{m['years_positive']}/{m['n_years']}", "top3": t3, "top5": t5, "top10": t10,
            "max_dd": maxdd, "dd_dur": ddur, "cost_ratio_pct": m["cost_ratio_pct"], "era_pf": eras,
            "yr_excl_min": min(yr_excl), "single_event_pct": single,
            "corr_mnq_orb": c_orb, "corr_mnq_srr": c_srr, "verdict": verdict}


def run():
    print("Cycle 2026-06-16o — Daily Workhorse #2 campaign board (REPORT-ONLY)\n", flush=True)
    print("Computing MNQ workhorse reference trade sets (for correlation)...", flush=True)
    _, mnq_orb = run_xb("MNQ", "orb_breakout")
    _, mnq_srr = run_xb("MNQ", "stop_run_reversal")

    # candidate matrix: cross-asset the winning mechanism + 2 new MGC mechanisms
    candidates = [("MGC", "prior_day_break")]  # baseline re-confirm
    candidates += [("MGC", "abnormal_range_followup"), ("MGC", "orb_breakout")]  # A, B
    candidates += [(a, "prior_day_break") for a in ("MYM", "MES", "M2K", "MCL", "ZN", "ZF", "6E")]  # C-G cross-asset winner

    rows = []
    for asset, entry in candidates:
        r = board(asset, entry, mnq_orb, mnq_srr)
        rows.append(r)
        if "error" in r or r["verdict"].startswith("KILL") or r["verdict"] == "ERROR":
            print(f"  {asset:>4} {entry:<24} -> {r['verdict']} (n={r.get('n','?')})", flush=True)
        else:
            print(f"  {asset:>4} {entry:<24} -> {r['verdict']:<22} n={r['n']:>4} {r['trades_per_yr']:>5}/yr [{r['cadence']}] "
                  f"PF={r['pf']:.2f} med=${r['median']:.1f} H1/H2={r['h1_pf']:.2f}/{r['h2_pf']:.2f} "
                  f"t3/5/10={r['top3']}/{r['top5']}/{r['top10']} ddur={r['dd_dur']} cost={r['cost_ratio_pct']}% "
                  f"corr(orb/srr)={r['corr_mnq_orb']:+.2f}/{r['corr_mnq_srr']:+.2f}", flush=True)

    # ranked board
    order = {"PACKET_CANDIDATE": 0, "FORWARD_CLOCK_CREDIBLE": 1, "WATCH_corr": 2, "REJECT_MNQ_COUSIN": 3,
             "KILL": 4, "KILL_no_fire": 5, "ERROR": 6}
    ranked = sorted([r for r in rows if "verdict" in r], key=lambda r: (order.get(r["verdict"], 9), -r.get("pf", 0)))
    print("\n=== RANKED WORKHORSE #2 BOARD ===", flush=True)
    tiers = {"true-daily": [], "weekly-frequent": [], "sparse": [], "rejected/killed": []}
    for r in ranked:
        v = r["verdict"]
        if v in ("PACKET_CANDIDATE", "FORWARD_CLOCK_CREDIBLE", "WATCH_corr"):
            tiers[r.get("cadence", "sparse")].append(r)
        else:
            tiers["rejected/killed"].append(r)
    for tier, items in tiers.items():
        if items:
            print(f"\n  [{tier.upper()}]", flush=True)
            for r in items:
                tag = f"{r['asset']}-{r['mechanism']}"
                extra = f"PF {r['pf']:.2f}, {r['trades_per_yr']}/yr, corr {max(abs(r['corr_mnq_orb']),abs(r['corr_mnq_srr'])):.2f}" if "pf" in r else ""
                print(f"    {r['verdict']:<22} {tag:<32} {extra}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-16o_workhorse2_campaign.json"
    out.write_text(json.dumps({"cycle": "2026-06-16o_workhorse2_campaign",
        "mode": "Lane B report-only; targeted WH2 campaign; NON-WIRED",
        "method": "cross-asset the winning prior_day_break mechanism + 2 new MGC mechanisms; full board + MNQ correlation; cadence-tiered",
        "candidates": rows,
        "boundaries": "no activation/registry/scheduler/portfolio/order mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)
    print("(report-only; no activation/registry/scheduler/portfolio/order mutation)", flush=True)


if __name__ == "__main__":
    run()
