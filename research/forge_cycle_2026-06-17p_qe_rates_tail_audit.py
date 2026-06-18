"""Cycle 2026-06-17p — TAIL-ENGINE AUDIT: quarter-end rates settlement flow (report-only).

STRUCTURE_FOUND (17o) had only ~28 events -> mandatory audit before any belief. Checks:
  1. Instance contribution: max-single, top-3, top-5, max-year (% of gross profit).
  2. Stability: per-year + per-quarter (Q1/Q2/Q3/Q4) breakdown.
  3. Robustness: ZF vs ZN; K=2/3/4 mechanical windows (minimal, no broad tuning).
  4. Cost/slippage 1x/2x/3x.
  5. Risk: worst event, worst single-day-in-hold (prop daily-loss), drawdown path.
  6. Overlap with Rates-FOMC-week sleeve (don't double-count rates-event).
  7. Calendar integrity: quarter-end dates mechanically generated, no lookahead.
Classify PASS_tail / WATCH_tail / KILL. Report-only; no mutation. NOT daily WH2 (event/tail).
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
from engine.backtest import get_cost_params  # noqa: E402
from research.forge_fomc_calendar_official import build_official_fomc_calendar  # noqa: E402


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def daily_close(a):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{a}_5m.csv")
    dt = pd.to_datetime(df["datetime"])
    s = df.assign(date=dt.dt.normalize()).groupby("date")["close"].last(); s.index = pd.to_datetime(s.index); return s


def qe_events(asset, K):
    s = daily_close(asset); s = s[s.index.year >= 2019]
    pv = ASSETS[asset]["point_value"]; cp = get_cost_params(asset)
    rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
    days = list(s.index); dfd = pd.DataFrame({"date": days}); dfd["y"] = dfd["date"].dt.year; dfd["m"] = dfd["date"].dt.month
    rows = []
    for (y, m), g in dfd[dfd["m"].isin([3, 6, 9, 12])].groupby([dfd["y"], dfd["m"]]):
        gd = list(g["date"])
        if len(gd) < K + 1:
            continue
        qe = gd[-1]; entry_day = gd[-1 - K]
        # within-hold daily PnL (for worst single day / prop daily-loss)
        hold_days = [d for d in days if entry_day < d <= qe]
        if not hold_days:
            continue
        prev = s.loc[entry_day]; worst_day = 0.0
        for d in hold_days:
            wd = (s.loc[d] - prev) * pv; worst_day = min(worst_day, wd); prev = s.loc[d]
        pnl = (s.loc[qe] - s.loc[entry_day]) * pv - rt
        rows.append({"qe": qe, "entry": entry_day, "pnl": float(pnl), "year": int(y), "quarter": (m // 3),
                     "worst_day_in_hold": float(worst_day)})
    return pd.DataFrame(rows), rt


def audit(asset, K):
    tr, rt = qe_events(asset, K)
    if len(tr) < 12:
        return {"asset": asset, "K": K, "n": len(tr), "verdict": "KILL_low_n"}
    p = tr["pnl"].to_numpy(); net = float(p.sum()); pf = _pf(p)
    gross = float(p[p > 0].sum())
    g = np.sort(p[p > 0])[::-1]
    maxsingle = round(float(g[0]) / gross * 100, 1) if gross > 0 else None
    top3 = round(float(g[:3].sum()) / gross * 100, 1) if gross > 0 else None
    top5 = round(float(g[:5].sum()) / gross * 100, 1) if gross > 0 else None
    per_y = tr.groupby("year")["pnl"].sum(); maxyr = round(float(per_y.abs().max() / net * 100), 1) if net else None
    yrs_pos = f"{int((per_y>0).sum())}/{int(per_y.shape[0])}"
    per_q = tr.groupby("quarter")["pnl"].agg(["sum", "count"]).to_dict("index")
    worst_event = round(float(p.min()), 0); worst_day = round(float(tr["worst_day_in_hold"].min()), 0)
    return {"asset": asset, "K": K, "n": len(tr), "pf": round(pf, 3), "net": round(net, 0),
            "median": round(float(np.median(p)), 2), "pos_frac": round(float((p > 0).mean()), 2),
            "max_single_pct": maxsingle, "top3_pct": top3, "top5_pct": top5, "max_year_pct": maxyr, "yrs_pos": yrs_pos,
            "per_quarter": {int(k): {"net": round(v["sum"], 0), "n": int(v["count"])} for k, v in per_q.items()},
            "worst_event": worst_event, "worst_day_in_hold": worst_day, "trades": tr}


def run():
    print("Cycle 2026-06-17p — TAIL-ENGINE AUDIT: quarter-end rates flow (REPORT-ONLY)\n", flush=True)

    print("7. CALENDAR INTEGRITY: QE = mechanical last-trading-day of Mar/Jun/Sep/Dec; entry = K td prior; "
          "exit at QE close; uses only past closes -> no lookahead (windows fixed by calendar, not outcome).", flush=True)

    print("\n1+2+5. ZF (primary) & ZN (confirm), K=3 — contribution / stability / risk:", flush=True)
    main = {}
    for a in ("ZF", "ZN"):
        r = audit(a, 3); main[a] = r
        print(f"  {a}-K3: n={r['n']} PF={r['pf']} net=${r['net']} pos={r['pos_frac']} | max-single={r['max_single_pct']}% "
              f"top3={r['top3_pct']}% top5={r['top5_pct']}% max-year={r['max_year_pct']}% yrs+={r['yrs_pos']}", flush=True)
        print(f"        per-quarter: {r['per_quarter']} | worst-event=${r['worst_event']} worst-day-in-hold=${r['worst_day_in_hold']}", flush=True)

    print("\n3. WINDOW ROBUSTNESS (K=2/3/4, minimal — no broad tuning):", flush=True)
    for a in ("ZF", "ZN"):
        line = []
        for K in (2, 3, 4):
            r = audit(a, K); line.append(f"K{K}:PF={r.get('pf')}/n={r.get('n')}")
        print(f"  {a}: {'  '.join(line)}", flush=True)

    print("\n4. COST/SLIPPAGE (ZF-K3; rebuild cost in qe_events uses 1x; here scale):", flush=True)
    # cost sensitivity: recompute net at higher slippage by subtracting extra rt per event
    cp = get_cost_params("ZF"); pv = ASSETS["ZF"]["point_value"]
    base_tr, rt1 = qe_events("ZF", 3)
    for sm in (1.0, 2.0, 3.0):
        rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * sm * cp["tick_size"] * pv)
        adj = base_tr["pnl"].to_numpy() - (rt - rt1)  # add extra slippage
        print(f"   slip={sm}x: PF={_pf(adj):.3f} net=${adj.sum():.0f}", flush=True)

    print("\n6. OVERLAP with Rates-FOMC-week sleeve:", flush=True)
    fomc = [pd.Timestamp(c["actual_date"]) for c in build_official_fomc_calendar()]
    zf = main["ZF"]["trades"]; ov = 0
    for _, e in zf.iterrows():
        win_lo = e["entry"]; win_hi = e["qe"]
        if any(win_lo - pd.Timedelta(days=2) <= f <= win_hi + pd.Timedelta(days=2) for f in fomc):
            ov += 1
    print(f"   ZF-K3 events overlapping a FOMC window (±2d): {ov}/{len(zf)} "
          f"({'low overlap -> distinct from FOMC sleeve' if ov/len(zf) < 0.25 else 'material overlap -> may double-count'})", flush=True)

    # classification (ZF primary)
    r = main["ZF"]
    pass_tail = (r["pf"] >= 1.3 and (r["max_single_pct"] or 99) < 35 and (r["top3_pct"] or 99) < 60
                 and (r["max_year_pct"] or 99) < 50 and r["pos_frac"] >= 0.6 and r["worst_day_in_hold"] > -2000)
    watch = r["pf"] >= 1.2 and (r["top3_pct"] or 99) < 70
    verdict = "PASS_tail" if pass_tail else ("WATCH_tail" if watch else "KILL")
    print(f"\n  VERDICT (ZF-K3 primary): {verdict}", flush=True)
    print(f"   (PF {r['pf']}; max-single {r['max_single_pct']}%; top3 {r['top3_pct']}%; max-year {r['max_year_pct']}%; "
          f"pos {r['pos_frac']}; worst-day-in-hold ${r['worst_day_in_hold']}; n={r['n']} small)", flush=True)
    print("   LABEL: structural event/tail diversifier (rates), NOT daily WH2.", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-17p_qe_rates_tail_audit.json"
    save = {a: {k: v for k, v in main[a].items() if k != "trades"} for a in main}
    out.write_text(json.dumps({"cycle": "2026-06-17p_qe_rates_tail_audit", "mode": "Lane 1 tail audit; report-only; NON-WIRED",
        "zf_zn_K3": save, "fomc_overlap": f"{ov}/{len(zf)}", "verdict": verdict,
        "boundaries": "no sweep beyond K2/3/4; no mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; tail audit; no mutation)", flush=True)


if __name__ == "__main__":
    run()
