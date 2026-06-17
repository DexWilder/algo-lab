"""Cycle 2026-06-17b — screen Claw testable-now lead #T2: Dual-Thrust non-equity (report-only).

From the 878-note backlog triage, the top in-house testable-now / distinct-driver / daily
mechanism: DUAL-THRUST breakout (asymmetric prior-day thresholds), distinct from ORB
(opening-range) and donchian (N-day high). Apply to NON-equity (ZN rates, MCL crude) where
the driver differs from equity momentum; MGC/MES for reference. Full WH2 board + MNQ corr.

Dual-thrust (prior-day variant): upper = prev_close + K1*(prev_high - prev_close),
lower = prev_close - K2*(prev_close - prev_low). Break upper -> long, break lower -> short,
one/day, engine flattens intraday. NO mutation; NON-WIRED.
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


def entry_dual_thrust(f, i, state, params):
    if not f["entry_ok"][i]:
        return 0, 0, 0
    pc = f["prev_day_close"][i]; ph = f["prev_day_high"][i]; pl = f["prev_day_low"][i]; atr = f["atr"][i]
    if pc is None or np.isnan(pc) or np.isnan(ph) or np.isnan(pl) or not atr or np.isnan(atr) or atr <= 0:
        return 0, 0, 0
    k1 = params.get("k1", 0.5); k2 = params.get("k2", 0.5)
    upper = pc + k1 * (ph - pc); lower = pc - k2 * (pc - pl)
    c = f["close"][i]; cp = f["close"][i - 1] if i > 0 else c
    sm = params.get("stop_mult", 1.5); tm = params.get("target_mult", 2.0)
    if cp <= upper and c > upper and not state["long_traded_today"]:
        return 1, c - atr * sm, c + atr * tm
    if cp >= lower and c < lower and not state["short_traded_today"]:
        return -1, c + atr * sm, c - atr * tm
    return 0, 0, 0


ce.ENTRY_MAP["dual_thrust"] = entry_dual_thrust


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def run_xb(asset, entry, filt):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv"); cfg = ASSETS[asset]; c = get_cost_params(asset)
    s = ce.generate_crossbred_signals(df, entry_name=entry, exit_name="profit_ladder", filter_name=filt, params={})
    return _metrics((r := run_backtest(df, s, mode="both", point_value=cfg["point_value"], symbol=asset,
                                       commission_per_side=c["commission_per_side"], slippage_ticks=c["slippage_ticks"],
                                       tick_size=c["tick_size"]))["trades_df"], f"{asset}-{entry}", costs=r["stats"]["costs"]), r["trades_df"]


def dcorr(a, b):
    a = a.copy(); a["d"] = pd.to_datetime(a["entry_time"]).dt.date
    b = b.copy(); b["d"] = pd.to_datetime(b["entry_time"]).dt.date
    al = pd.concat([a.groupby("d")["pnl"].sum(), b.groupby("d")["pnl"].sum()], axis=1, keys=["a", "b"]).fillna(0.0)
    return round(float(al["a"].corr(al["b"])), 3)


def board(asset, filt, mnq_orb, mnq_srr):
    try:
        m, tr = run_xb(asset, "dual_thrust", filt)
    except Exception as e:
        return {"asset": asset, "filter": filt, "verdict": "ERROR", "err": str(e)[:120]}
    if tr is None or tr.empty or m["n"] < 40:
        return {"asset": asset, "filter": filt, "n": int(m.get("n", 0)), "verdict": "KILL_low_n"}
    tr = tr.copy(); tr["dt"] = pd.to_datetime(tr["entry_time"]); tr["y"] = tr["dt"].dt.year
    net = float(tr["pnl"].sum()); ny = int(tr["y"].nunique()); tpy = round(m["n"] / max(ny, 1), 1)
    g = tr[tr["pnl"] > 0]["pnl"].sort_values(ascending=False); gp = float(g.sum())
    t3 = round(float(g.head(3).sum()) / gp * 100, 1) if gp > 0 else None
    t10 = round(float(g.head(10).sum()) / gp * 100, 1) if gp > 0 else None
    yx = [round(_pf(tr[tr["y"] != y]["pnl"]), 3) for y in sorted(tr["y"].unique())]
    st = tr.sort_values("dt").reset_index(drop=True); cuts = np.linspace(0, len(st), 4).astype(int)
    eras = [round(_pf(st.iloc[cuts[i]:cuts[i + 1]]["pnl"]), 3) for i in range(3)]
    c_orb = dcorr(tr, mnq_orb); c_srr = dcorr(tr, mnq_srr); cmax = max(abs(c_orb), abs(c_srr))
    cadence = "true-daily" if (tpy >= 120 and m["n"] >= 500) else ("near-daily" if tpy >= 90 else ("weekly-frequent" if tpy >= 30 else "sparse"))
    quality = (m["pf"] > 1.2 and m["median"] >= 0 and m["h1_pf"] > 1.0 and m["h2_pf"] > 1.0
               and (t3 or 99) < 30 and (t10 or 99) < 55 and m["max_year_share_pct"] < 40
               and (m["years_positive"] / max(m["n_years"], 1)) >= 0.75 and all(e > 1.0 for e in eras) and min(yx) > 1.15)
    v = ("REJECT_MNQ_COUSIN" if cmax >= 0.5 and asset in ("MES", "MYM", "M2K")
         else ("KILL" if not quality else ("WATCH_corr" if cmax >= 0.3
               else ("PACKET_CANDIDATE" if cadence == "true-daily" else "FORWARD_CLOCK_CREDIBLE"))))
    return {"asset": asset, "filter": filt, "n": m["n"], "trades_per_yr": tpy, "cadence": cadence, "pf": round(m["pf"], 3),
            "net": round(net, 0), "median": round(m["median"], 2), "h1_pf": round(m["h1_pf"], 3), "h2_pf": round(m["h2_pf"], 3),
            "max_year_pct": round(m["max_year_share_pct"], 1), "top3": t3, "top10": t10, "era_pf": eras, "yr_excl_min": min(yx),
            "corr_orb": c_orb, "corr_srr": c_srr, "verdict": v}


def run():
    print("Cycle 2026-06-17b — Dual-Thrust non-equity (Claw lead #T2) (REPORT-ONLY)\n", flush=True)
    _, mnq_orb = run_xb("MNQ", "orb_breakout", "ema_slope"); _, mnq_srr = run_xb("MNQ", "stop_run_reversal", "ema_slope")
    rows = []
    for asset in ("ZN", "MCL", "MGC", "MES", "ZF"):
        for filt in ("none", "ema_slope"):
            r = board(asset, filt, mnq_orb, mnq_srr); rows.append(r)
            if r["verdict"] == "ERROR" or r["verdict"].startswith("KILL"):
                print(f"  {asset:>4} dual_thrust [{filt:<9}] -> {r['verdict']} (n={r.get('n','?')})", flush=True)
            else:
                print(f"  {asset:>4} dual_thrust [{filt:<9}] -> {r['verdict']:<22} n={r['n']:>4} {r['trades_per_yr']:>5}/yr "
                      f"[{r['cadence']}] PF={r['pf']:.2f} med=${r['median']:.1f} H1/H2={r['h1_pf']:.2f}/{r['h2_pf']:.2f} "
                      f"t3/10={r['top3']}/{r['top10']} corr={max(abs(r['corr_orb']),abs(r['corr_srr'])):+.2f}", flush=True)
    surv = [r for r in rows if r["verdict"] in ("PACKET_CANDIDATE", "FORWARD_CLOCK_CREDIBLE", "WATCH_corr")]
    print(f"\n  SURVIVORS: {[(r['asset'], r['filter'], r['pf']) for r in surv] or 'none'}", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-17b_dual_thrust.json"
    out.write_text(json.dumps({"cycle": "2026-06-17b_dual_thrust", "mode": "Lane B report-only; Claw lead #T2; NON-WIRED",
        "screened": rows, "survivors": surv, "boundaries": "no activation/registry/scheduler/portfolio/order mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
