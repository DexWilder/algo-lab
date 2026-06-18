"""Cycle 2026-06-17l — Lane 2: MNQ workhorse IMPROVEMENT screen (report-only).

NOT a WH2 search (MNQ stays equity exposure). Evaluate candidate MNQ entries as
REPLACEMENT / ADDITION / OVERLAY vs the INCUMBENT MNQ books:
  incumbents: orb_breakout (XB-ORB-EMA-Ladder-MNQ), stop_run_reversal (WH-MNQ-stop_run_reversal)
Each candidate: full workhorse board + daily-PnL correlation to each incumbent + same-day signal
overlap + bad-day overlap + portfolio contribution (does incumbents+candidate beat incumbents-only
on combined PF / max-DD / worst-day?). Classify:
  KILL (not workhorse-quality) / REDUNDANT (corr>=0.7 to an incumbent = duplicate exposure) /
  REPLACEMENT (quality AND clearly beats weaker incumbent on netPF+OOS+DD) /
  ADDITION (quality AND corr<0.5 to BOTH AND improves combined portfolio).
No WH2 label. No sweep, no synthetic fill, no mutation.
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
from research.fql_forge_batch_runner import _metrics  # noqa: E402

INCUMBENTS = ["orb_breakout", "stop_run_reversal"]
CANDIDATES = ["range_compression_break", "donchian_breakout", "first_impulse_pullback", "pb_pullback", "vwap_continuation"]


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def trades(entry):
    df = pd.read_csv(ROOT / "data" / "processed" / "MNQ_5m.csv"); cfg = ASSETS["MNQ"]; c = get_cost_params("MNQ")
    s = gcs(df, entry_name=entry, exit_name="profit_ladder", filter_name="ema_slope", params={})
    res = run_backtest(df, s, mode="both", point_value=cfg["point_value"], symbol="MNQ",
                       commission_per_side=c["commission_per_side"], slippage_ticks=c["slippage_ticks"], tick_size=c["tick_size"])
    m = _metrics(res["trades_df"], f"MNQ-{entry}", costs=res["stats"]["costs"])
    tr = res["trades_df"].copy(); tr["date"] = pd.to_datetime(tr["entry_time"]).dt.normalize().astype("datetime64[ns]")
    return m, tr


def board(m, tr):
    if tr is None or m["n"] < 100:
        return {"n": int(m.get("n", 0)), "quality": False}
    p = tr["pnl"].to_numpy(); net = float(p.sum())
    g = tr[tr["pnl"] > 0]["pnl"].sort_values(ascending=False); gp = float(g.sum())
    top3 = round(float(g.head(3).sum()) / gp * 100, 1) if gp > 0 else None
    daily = tr.groupby("date")["pnl"].sum().sort_index()
    eq = daily.cumsum().to_numpy(); dd = float((eq - np.maximum.accumulate(eq)).min())
    worst = float(daily.min())
    quality = (m["pf"] > 1.2 and m["median"] >= 0 and m["h1_pf"] > 1.0 and m["h2_pf"] > 1.0
               and (top3 or 99) < 30 and m["max_year_share_pct"] < 40 and (m["years_positive"] / max(m["n_years"], 1)) >= 0.75)
    return {"n": m["n"], "pf": round(m["pf"], 3), "net": round(net, 0), "median": round(m["median"], 2),
            "h1_pf": round(m["h1_pf"], 3), "h2_pf": round(m["h2_pf"], 3), "top3_pct": top3,
            "max_year_pct": round(m["max_year_share_pct"], 1), "max_dd": round(dd, 0), "worst_day": round(worst, 0),
            "yrs_pos": f"{m['years_positive']}/{m['n_years']}", "quality": bool(quality)}


def daily_pnl(tr):
    return tr.groupby("date")["pnl"].sum()


def overlap(a, b):
    da = set(a["date"]); db = set(b["date"])
    return round(len(da & db) / len(da) * 100, 1) if da else 0.0


def run():
    print("Cycle 2026-06-17l — Lane 2: MNQ workhorse IMPROVEMENT vs incumbents (REPORT-ONLY)\n", flush=True)
    inc = {}
    for e in INCUMBENTS:
        m, tr = trades(e); inc[e] = {"board": board(m, tr), "tr": tr, "daily": daily_pnl(tr)}
        b = inc[e]["board"]
        print(f"  INCUMBENT {e:<22} PF={b['pf']} net=${b['net']} med=${b['median']} maxDD=${b['max_dd']} worstday=${b['worst_day']} n={b['n']}", flush=True)
    inc_combined = (inc["orb_breakout"]["daily"].add(inc["stop_run_reversal"]["daily"], fill_value=0)).sort_index()
    ic_pf = round(_pf(inc_combined.values), 3); ic_dd = round(float((inc_combined.cumsum() - inc_combined.cumsum().cummax()).min()), 0)
    print(f"  INCUMBENTS COMBINED: PF={ic_pf} maxDD=${ic_dd} worstday=${round(float(inc_combined.min()),0)}\n", flush=True)

    results = {}
    for e in CANDIDATES:
        m, tr = trades(e); bd = board(m, tr)
        if not bd.get("quality"):
            results[e] = {"board": bd, "verdict": "KILL"}
            print(f"  {e:<24} -> KILL (quality fail; PF={bd.get('pf')} n={bd.get('n')})", flush=True)
            continue
        dpc = daily_pnl(tr)
        c_orb = round(float(pd.concat([dpc.rename('a'), inc['orb_breakout']['daily'].rename('b')], axis=1).fillna(0)['a'].corr(
            pd.concat([dpc.rename('a'), inc['orb_breakout']['daily'].rename('b')], axis=1).fillna(0)['b'])), 3)
        c_srr = round(float(pd.concat([dpc.rename('a'), inc['stop_run_reversal']['daily'].rename('b')], axis=1).fillna(0)['a'].corr(
            pd.concat([dpc.rename('a'), inc['stop_run_reversal']['daily'].rename('b')], axis=1).fillna(0)['b'])), 3)
        ov_orb = overlap(tr, inc['orb_breakout']['tr']); ov_srr = overlap(tr, inc['stop_run_reversal']['tr'])
        # portfolio contribution: incumbents + candidate
        comb = inc_combined.add(dpc, fill_value=0).sort_index()
        comb_pf = round(_pf(comb.values), 3); comb_dd = round(float((comb.cumsum() - comb.cumsum().cummax()).min()), 0)
        # risk-reducing addition: PF not materially worse AND combined DD shallower (less negative)
        improves = (comb_pf >= ic_pf - 0.02) and (comb_dd > ic_dd)
        cmax = max(abs(c_orb), abs(c_srr))
        # beats weaker incumbent? (replacement)
        weaker = min(inc.values(), key=lambda x: x["board"]["pf"])["board"]
        beats_weaker = bd["pf"] >= weaker["pf"] + 0.1 and bd["h2_pf"] > 1.0 and bd["max_dd"] >= weaker["max_dd"]
        if cmax >= 0.7:
            verdict = "REDUNDANT_duplicate_exposure"
        elif beats_weaker:
            verdict = "REPLACEMENT_CANDIDATE"
        elif cmax < 0.5 and improves:
            verdict = "ADDITION_CANDIDATE"
        else:
            verdict = "NEUTRAL_no_improvement"
        results[e] = {"board": bd, "corr_orb": c_orb, "corr_srr": c_srr, "overlap_orb_pct": ov_orb, "overlap_srr_pct": ov_srr,
                      "combined_pf": comb_pf, "combined_dd": comb_dd, "improves_portfolio": improves, "verdict": verdict}
        print(f"  {e:<24} PF={bd['pf']} net=${bd['net']} maxDD=${bd['max_dd']} | corr(orb/srr)={c_orb}/{c_srr} "
              f"overlap={ov_orb}/{ov_srr}% | +portfolio PF {ic_pf}->{comb_pf} DD {ic_dd}->{comb_dd} -> {verdict}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-17l_mnq_improvement.json"
    out.write_text(json.dumps({"cycle": "2026-06-17l_mnq_improvement", "mode": "Lane 2 report-only; MNQ improvement vs incumbents; NON-WIRED",
        "incumbents": {e: inc[e]["board"] for e in INCUMBENTS}, "incumbents_combined": {"pf": ic_pf, "max_dd": ic_dd},
        "candidates": {e: {k: v for k, v in r.items() if k != "tr"} for e, r in results.items()},
        "note": "MNQ = equity exposure; NOT WH2 regardless of result. Classification replacement/addition/overlay/redundant only.",
        "boundaries": "no sweep/synthetic-fill/mutation/promotion"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; Lane 2 MNQ improvement; not WH2; no mutation)", flush=True)


if __name__ == "__main__":
    run()
