"""Cycle 2026-06-16q — DAILY-ELITE pressure-cooker Cycle 2 (report-only).

Track 1 continues (creative discovery never stops). Two things:
  (1) NEW untested daily mechanisms: two_day_break, prior_day_midpoint_revert,
      consecutive_close_reversion, pdh_pdl_false_sweep_reversal (Globex/level sweep proxy),
      post_large_move_followthrough, vol_shock_response.
  (2) METHODOLOGY FIX re-test: the Cycle-1 reversion mechanisms (outside_day_reversal,
      prior_close_reclaim, post_large_loss_snapback) were unfairly paired with a MOMENTUM
      exit (profit_ladder). Re-run with the thesis-matched reversion exit (midline_target)
      before they stay dead. NOT a vanity re-run — an exit-thesis correction.

Each primitive carries its own (filter, exit) per the pre-flight + exit-thesis discipline.
Full WH2 board + MNQ correlation + cadence tier + brutal kill. NO mutation; NON-WIRED.
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
import research.crossbreeding.crossbreeding_engine as ce  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from research.wh2_daily_primitives import NEW_PRIMITIVES, build_daily_map  # noqa: E402

for _name, spec in NEW_PRIMITIVES.items():
    ce.ENTRY_MAP[_name] = spec[0]

_DM = {}


def _pf(p):
    a = np.asarray(p, float); w = a[a > 0].sum(); l = -a[a < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def run_one(asset, entry, filt, exit_name, needs_dm):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]; costs = get_cost_params(asset); params = {}
    if needs_dm:
        if asset not in _DM:
            _DM[asset] = build_daily_map(df)
        params["daily_map"] = _DM[asset]
    sigs = ce.generate_crossbred_signals(df, entry_name=entry, exit_name=exit_name, filter_name=filt, params=params)
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol=asset,
                       commission_per_side=costs["commission_per_side"], slippage_ticks=costs["slippage_ticks"],
                       tick_size=costs["tick_size"])
    return _metrics(res["trades_df"], f"{asset}-{entry}", costs=res["stats"]["costs"]), res["trades_df"]


def conc(tr):
    g = tr[tr["pnl"] > 0]["pnl"].sort_values(ascending=False); gp = float(g.sum())
    t = lambda k: round(float(g.head(k).sum()) / gp * 100, 1) if gp > 0 else None
    return t(3), t(5), t(10)


def dcorr(a, b):
    a = a.copy(); a["d"] = pd.to_datetime(a["entry_time"]).dt.date
    b = b.copy(); b["d"] = pd.to_datetime(b["entry_time"]).dt.date
    al = pd.concat([a.groupby("d")["pnl"].sum(), b.groupby("d")["pnl"].sum()], axis=1, keys=["a", "b"]).fillna(0.0)
    return round(float(al["a"].corr(al["b"])), 3)


def board(asset, entry, filt, exit_name, needs_dm, mnq_orb, mnq_srr):
    try:
        m, tr = run_one(asset, entry, filt, exit_name, needs_dm)
    except Exception as e:
        return {"asset": asset, "mechanism": entry, "verdict": "ERROR", "err": str(e)[:140]}
    if tr is None or tr.empty or m["n"] < 40:
        return {"asset": asset, "mechanism": entry, "n": int(m.get("n", 0)), "verdict": "KILL_low_n"}
    tr = tr.copy(); tr["entry_dt"] = pd.to_datetime(tr["entry_time"]); tr["year"] = tr["entry_dt"].dt.year
    net = float(tr["pnl"].sum()); ny = int(tr["year"].nunique()); tpy = round(m["n"] / max(ny, 1), 1)
    t3, t5, t10 = conc(tr)
    yx = [round(_pf(tr[tr["year"] != y]["pnl"]), 3) for y in sorted(tr["year"].unique())]
    st = tr.sort_values("entry_dt").reset_index(drop=True); cuts = np.linspace(0, len(st), 4).astype(int)
    eras = [round(_pf(st.iloc[cuts[i]:cuts[i + 1]]["pnl"]), 3) for i in range(3)]
    mx = tr["pnl"].max(); mn = tr["pnl"].min(); single = round(max(abs(mx), abs(mn)) / net * 100, 1) if net else None
    c_orb = dcorr(tr, mnq_orb); c_srr = dcorr(tr, mnq_srr); cmax = max(abs(c_orb), abs(c_srr))
    cadence = "true-daily" if (tpy >= 120 and m["n"] >= 500) else ("near-daily" if tpy >= 90 else ("weekly-frequent" if tpy >= 30 else "sparse"))
    quality = (m["pf"] > 1.2 and m["median"] >= 0 and m["h1_pf"] > 1.0 and m["h2_pf"] > 1.0
               and (t3 or 99) < 30 and (t5 or 99) < 45 and (t10 or 99) < 55 and m["max_year_share_pct"] < 40
               and (m["years_positive"] / max(m["n_years"], 1)) >= 0.75 and all(e > 1.0 for e in eras)
               and min(yx) > 1.15 and (single or 99) < 25)
    decor = cmax < 0.3; lite = cmax >= 0.5
    if lite and asset in ("MES", "MYM", "M2K"):
        v = "REJECT_MNQ_COUSIN"
    elif not quality:
        v = "KILL"
    elif not decor:
        v = "WATCH_corr"
    elif cadence == "true-daily":
        v = "PACKET_CANDIDATE"
    else:
        v = "FORWARD_CLOCK_CREDIBLE"
    return {"asset": asset, "mechanism": entry, "filter": filt, "exit": exit_name, "n": m["n"], "trades_per_yr": tpy,
            "cadence": cadence, "pf": round(m["pf"], 3), "net": round(net, 0), "median": round(m["median"], 2),
            "h1_pf": round(m["h1_pf"], 3), "h2_pf": round(m["h2_pf"], 3), "max_year_pct": round(m["max_year_share_pct"], 1),
            "years_pos": f"{m['years_positive']}/{m['n_years']}", "top3": t3, "top10": t10, "era_pf": eras,
            "yr_excl_min": min(yx), "single_event_pct": single, "corr_orb": c_orb, "corr_srr": c_srr, "verdict": v}


def run():
    print("Cycle 2026-06-16q — DAILY-ELITE Cycle 2 (REPORT-ONLY)\n", flush=True)
    print("MNQ refs...", flush=True)
    _, mnq_orb = run_one("MNQ", "orb_breakout", "ema_slope", "profit_ladder", False)
    _, mnq_srr = run_one("MNQ", "stop_run_reversal", "ema_slope", "profit_ladder", False)

    ALL = ["MGC", "MES", "MYM", "MCL", "ZN", "ZF"]
    # new mechanisms + exit-thesis-corrected re-tests (all are in NEW_PRIMITIVES with their exit)
    cycle2 = ["two_day_break", "prior_day_midpoint_revert", "consecutive_close_reversion",
              "pdh_pdl_false_sweep_reversal", "post_large_move_followthrough", "vol_shock_response",
              "outside_day_reversal", "prior_close_reclaim", "post_large_loss_snapback"]
    rows = []
    for entry in cycle2:
        _fn, filt, exit_name = NEW_PRIMITIVES[entry]
        retest = " [exit-fix re-test]" if entry in ("outside_day_reversal", "prior_close_reclaim", "post_large_loss_snapback") else ""
        print(f"\n-- {entry} (filter={filt}, exit={exit_name}){retest} --", flush=True)
        for a in ALL:
            r = board(a, entry, filt, exit_name, True, mnq_orb, mnq_srr); r["tranche"] = "cycle2"; rows.append(r)
            if r["verdict"] == "ERROR" or r["verdict"].startswith("KILL"):
                print(f"  {a:>4} -> {r['verdict']} (n={r.get('n','?')})" + (f"  {r.get('err','')}" if r['verdict'] == 'ERROR' else ""), flush=True)
            else:
                print(f"  {a:>4} -> {r['verdict']:<22} n={r['n']:>4} {r['trades_per_yr']:>5}/yr [{r['cadence']}] PF={r['pf']:.2f} "
                      f"med=${r['median']:.1f} H1/H2={r['h1_pf']:.2f}/{r['h2_pf']:.2f} t3/10={r['top3']}/{r['top10']} "
                      f"corr={max(abs(r['corr_orb']),abs(r['corr_srr'])):+.2f}", flush=True)

    survivors = [r for r in rows if r["verdict"] in ("PACKET_CANDIDATE", "FORWARD_CLOCK_CREDIBLE", "WATCH_corr")]
    from collections import Counter
    tally = Counter(r["verdict"] for r in rows)
    print("\n=== CYCLE 2 SURVIVOR BOARD ===", flush=True)
    if not survivors:
        print("  (none cleared the daily-elite gauntlet)", flush=True)
    for r in sorted(survivors, key=lambda r: (r["verdict"], -r["pf"])):
        print(f"  {r['verdict']:<22} {r['asset']}-{r['mechanism']:<28} PF {r['pf']:.2f} {r['trades_per_yr']}/yr "
              f"corr {max(abs(r['corr_orb']),abs(r['corr_srr'])):.2f}", flush=True)
    print(f"\n  TALLY: {dict(tally)} (total {len(rows)})", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-16q_daily_elite_cycle2.json"
    out.write_text(json.dumps({"cycle": "2026-06-16q_daily_elite_cycle2",
        "mode": "Lane B report-only; daily-elite cycle 2; NON-WIRED",
        "note": "new daily mechanisms + exit-thesis-corrected re-test of cycle-1 reversion kills",
        "screened": rows, "survivors": survivors, "tally": dict(tally),
        "boundaries": "no activation/registry/scheduler/portfolio/order mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)
    print("(report-only; no activation/registry/scheduler/portfolio/order mutation)", flush=True)


if __name__ == "__main__":
    run()
