"""Cycle 2026-06-12c — Test first_impulse_pullback primitive on MNQ/MES.

Per operator #187 A: continue to NEEDS_PRIMITIVE #6 immediately.

New primitive: entry_first_impulse_pullback (added to crossbreeding_engine.py).

Mechanism: after ORB completes, track impulse direction; on 50% pullback +
reversal, enter in impulse direction (continuation).

Test matrix: 2 assets × ema_slope filter × profit_ladder exit = 2 candidates.

V1 workhorse hard gates + family review vs existing inventory.

Boundaries: report-only Lane B.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def _run(asset, entry, exit_name, filter_name, label, cost_mult=1.0, slip_mult=1.0):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    costs = get_cost_params(asset)
    sigs = generate_crossbred_signals(df, entry_name=entry, exit_name=exit_name,
                                       filter_name=filter_name, params={})
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol=asset,
                       commission_per_side=costs["commission_per_side"] * cost_mult,
                       slippage_ticks=int(np.ceil(costs["slippage_ticks"] * slip_mult)),
                       tick_size=costs["tick_size"])
    return _metrics(res["trades_df"], label, costs=res["stats"]["costs"]), res["trades_df"]


def daily_workhorse_metrics(trades, total_sessions):
    if trades.empty: return {"n_trades": 0, "trades_per_day": 0, "pct_days_traded": 0}
    trades = trades.copy()
    trades["entry_dt"] = pd.to_datetime(trades["entry_time"])
    trades["date"] = trades["entry_dt"].dt.date
    daily = trades.groupby("date")["pnl"].sum()
    return {
        "n_trades": len(trades), "n_days_traded": len(daily),
        "trades_per_day": float(len(trades) / len(daily)) if len(daily) > 0 else 0,
        "pct_days_traded": float(len(daily) / total_sessions * 100) if total_sessions > 0 else 0,
        "pct_profitable_days": float((daily > 0).mean() * 100),
    }


def temporal_split(trades):
    if trades.empty: return None
    df = trades.copy()
    df["entry_dt"] = pd.to_datetime(df["entry_time"])
    df["year"] = df["entry_dt"].dt.year
    per_year = []
    for y, g in df.groupby("year"):
        pnl = g["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w / l) if l > 0 else float("inf")
        per_year.append({"year": int(y), "n": int(len(g)), "pf": pf,
                         "median": float(np.median(pnl)), "net": float(pnl.sum())})
    df = df.sort_values("entry_dt").reset_index(drop=True)
    cuts = np.linspace(0, len(df), 4).astype(int)
    eras = []
    for i in range(3):
        sub = df.iloc[cuts[i]:cuts[i+1]]
        if sub.empty: continue
        pnl = sub["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w / l) if l > 0 else float("inf")
        eras.append({"era": i+1, "n": int(len(sub)), "pf": pf,
                     "median": float(np.median(pnl)), "net": float(pnl.sum())})
    nets = [y["net"] for y in per_year]
    total_net = sum(nets)
    max_yr = max(abs(n) for n in nets) / total_net * 100 if total_net > 0 else 0
    return {"yrs_pos": sum(1 for r in per_year if r["net"] > 0),
            "n_yrs": len(per_year),
            "era3_pf": eras[-1]["pf"] if eras else float("nan"),
            "era3_median": eras[-1]["median"] if eras else float("nan"),
            "max_yr_share_pct": max_yr, "per_year": per_year, "eras": eras}


def evaluate_v1_workhorse_gates(m, ts, stress_m):
    return {
        "n_>=_500": m["n"] >= 500,
        "PF_>=_1.20": m["pf"] >= 1.20,
        "positive_median": m["median"] > 0,
        "PASS_STRESS": stress_m["median"] > 0,
        "max_yr_<=_50pct": ts["max_yr_share_pct"] <= 50.0,
        "yrs_pos_>=_50pct": ts["yrs_pos"] / ts["n_yrs"] >= 0.5,
        "Era3_PF_>=_1.0": ts["era3_pf"] >= 1.0,
        "Era3_median_>=_0": ts["era3_median"] >= 0,
    }


def family_corr(trades_a, trades_b):
    if trades_a.empty or trades_b.empty: return float("nan")
    da = trades_a.copy(); da["entry_dt"] = pd.to_datetime(da["entry_time"]); da["date"] = da["entry_dt"].dt.date
    db = trades_b.copy(); db["entry_dt"] = pd.to_datetime(db["entry_time"]); db["date"] = db["entry_dt"].dt.date
    pa = da.groupby("date")["pnl"].sum(); pb = db.groupby("date")["pnl"].sum()
    aligned = pd.concat([pa, pb], axis=1, keys=["a", "b"]).fillna(0.0)
    return float(aligned["a"].corr(aligned["b"]))


def _classify(m):
    n = m.get("n", 0); pf = m.get("pf", 0); median = m.get("median", 0)
    if n < 100: return f"KILL (n={n}, workhorse min 100)"
    if median < 0 and pf >= 1.15: return "KILL (asymmetric trap)"
    if median < 0: return "KILL (median neg)"
    if pf < 1.15: return "KILL (PF<1.15)"
    if pf >= 1.20 and median > 0: return "ESCALATE_TO_V1_AUDIT"
    return "WATCH"


def run():
    print("Cycle 2026-06-12c — first_impulse_pullback primitive test on MNQ/MES\n", flush=True)

    sessions = {}
    for asset in ["MNQ", "MES"]:
        df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
        df["date"] = pd.to_datetime(df["datetime"]).dt.date
        rth = df[(pd.to_datetime(df["datetime"]).dt.hour >= 9) &
                  (pd.to_datetime(df["datetime"]).dt.hour < 16)]
        sessions[asset] = rth["date"].nunique()

    t_start = time.time()
    results = []
    for asset in ["MNQ", "MES"]:
        label = f"WH-{asset}-first_impulse_pullback-ema_slope-PL"
        t0 = time.time()
        try:
            m, trades = _run(asset, "first_impulse_pullback", "profit_ladder", "ema_slope", label)
            v = _classify(m)
            daily = daily_workhorse_metrics(trades, sessions[asset])
            ts = None; stress_m = None; v1_gates = None; v1_verdict = None
            if v == "ESCALATE_TO_V1_AUDIT":
                stress_m, _ = _run(asset, "first_impulse_pullback", "profit_ladder", "ema_slope",
                                    f"{label}-stress", cost_mult=2.0, slip_mult=3.0)
                ts = temporal_split(trades)
                v1_gates = evaluate_v1_workhorse_gates(m, ts, stress_m)
                v1_verdict = "PAPER_PACKET_CANDIDATE" if all(v1_gates.values()) else \
                              f"ARCHIVED (fails: {[k for k, v in v1_gates.items() if not v]})"
        except Exception as e:
            import traceback; traceback.print_exc()
            print(f"  {label}: ERROR {e}", flush=True)
            results.append({"label": label, "error": str(e)})
            continue
        elapsed = time.time() - t0
        extra = f" → {v1_verdict}" if v1_verdict else ""
        print(
            f"  {label:55s}: n={m['n']:5d} PF={m['pf']:.3f} "
            f"med=${m['median']:6.2f} ({daily['trades_per_day']:.1f}/day, "
            f"{daily['pct_days_traded']:.0f}% days) → {v}{extra} [{elapsed:.0f}s]",
            flush=True
        )
        results.append({
            "label": label, "asset": asset,
            "metrics": {k: m.get(k) for k in ("n", "pf", "median", "net", "max_dd")},
            "daily_metrics": daily, "verdict": v,
            "v1_gates": v1_gates, "v1_verdict": v1_verdict,
            "temporal_split": ts,
            "stress_metrics": {"pf": float(stress_m["pf"]), "median": float(stress_m["median"])}
                                if stress_m else None,
            "trades_for_family": trades,
        })

    print(f"\nTotal: {time.time() - t_start:.0f}s", flush=True)

    # Family review on any PAPER_PACKET_CANDIDATE
    print(f"\n--- Family review ---", flush=True)
    for r in results:
        if "error" in r or r.get("v1_verdict") != "PAPER_PACKET_CANDIDATE": continue
        _, t_orb_prob = _run("MNQ", "orb_breakout", "profit_ladder", "ema_slope", "ref")
        _, t_stop_run = _run("MNQ", "stop_run_reversal", "profit_ladder", "ema_slope", "ref")
        _, t_range = _run("MNQ", "range_compression_break", "profit_ladder", "ema_slope", "ref")
        _, t_orb_fail = _run("MNQ", "orb_failure_reversal", "profit_ladder", "ema_slope", "ref")
        fam = {
            "vs_XB_ORB_MNQ": family_corr(r["trades_for_family"], t_orb_prob),
            "vs_WH_stop_run": family_corr(r["trades_for_family"], t_stop_run),
            "vs_WH_range_compression": family_corr(r["trades_for_family"], t_range),
            "vs_WH_orb_failure_reversal": family_corr(r["trades_for_family"], t_orb_fail),
        }
        print(f"  {r['label']}:", flush=True)
        for k, v in fam.items():
            print(f"    {k}: corr={v:+.3f}", flush=True)
        r["family_review"] = fam

    for r in results:
        r.pop("trades_for_family", None)

    paper = [r for r in results if r.get("v1_verdict") == "PAPER_PACKET_CANDIDATE"]
    archived = [r for r in results if "ARCHIVED" in (r.get("v1_verdict") or "") or "KILL" in r.get("verdict", "")]
    print(f"\nV1 tier: PAPER_PACKET_CANDIDATE={len(paper)} ARCHIVED={len(archived)}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-12c_first_impulse_pullback_test.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "Test first_impulse_pullback primitive (NEEDS_PRIMITIVE #6) on MNQ/MES",
        "v1_tier": {"PAPER_PACKET_CANDIDATE": len(paper), "ARCHIVED": len(archived)},
        "results": results,
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
