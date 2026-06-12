"""Cycle 2026-06-11p — Daily workhorse first batch on MNQ/MES.

Per operator #176 C amended: pivot from event-driven to daily workhorse.

Mechanism: 4 underutilized entry primitives × MNQ/MES, all with
ema_slope filter + profit_ladder exit per default doctrine.

  - abnormal_range_followup (operator queue #9 variant)
  - range_compression_break (operator queue #15)
  - stop_run_reversal (operator queue #14)
  - volatility_regime_compound (operator queue #10)

Matrix: 4 primitives × 2 assets = 8 candidates.

V1 workhorse hard gates:
  - n >= 500
  - PF >= 1.20
  - positive median
  - PASS_STRESS at 2x cost + 2 ticks slip
  - max-yr <= 50%
  - yrs+ >= 50%
  - Era3 PF >= 1.0
  - Era3 median >= 0

Daily workhorse reporting requirements per operator:
  - trade count, trades/day, % days traded, % profitable days
  - median day PnL, worst day, average losing day
  - max consecutive losing days
  - max intraday DD
  - time in market

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
    """Workhorse-archetype reporting per operator."""
    if trades.empty:
        return {"n_trades": 0, "trades_per_day": 0, "pct_days_traded": 0}
    trades = trades.copy()
    trades["entry_dt"] = pd.to_datetime(trades["entry_time"])
    trades["date"] = trades["entry_dt"].dt.date
    daily = trades.groupby("date")["pnl"].sum()
    n_days_traded = len(daily)
    pct_days_traded = n_days_traded / total_sessions * 100 if total_sessions > 0 else 0
    pct_profitable_days = (daily > 0).mean() * 100 if n_days_traded > 0 else 0
    median_day = float(daily.median())
    worst_day = float(daily.min())
    losing_days = daily[daily < 0]
    avg_losing_day = float(losing_days.mean()) if len(losing_days) > 0 else 0
    # Max consecutive losing days
    daily_sorted = daily.sort_index()
    max_consec_loss = 0; current = 0
    for v in daily_sorted.values:
        if v < 0: current += 1; max_consec_loss = max(max_consec_loss, current)
        else: current = 0
    return {
        "n_trades": len(trades), "n_days_traded": n_days_traded,
        "trades_per_day": float(len(trades) / n_days_traded) if n_days_traded > 0 else 0,
        "pct_days_traded": pct_days_traded,
        "pct_profitable_days": float(pct_profitable_days),
        "median_day_pnl": median_day, "worst_day": worst_day,
        "avg_losing_day": avg_losing_day,
        "max_consecutive_losing_days": max_consec_loss,
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
        sub = df.iloc[cuts[i]:cuts[i + 1]]
        if sub.empty: continue
        pnl = sub["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w / l) if l > 0 else float("inf")
        eras.append({"era": i + 1, "n": int(len(sub)), "pf": pf,
                     "median": float(np.median(pnl)), "net": float(pnl.sum())})
    nets = [y["net"] for y in per_year]
    total_net = sum(nets)
    max_yr_share = max(abs(n) for n in nets) / total_net * 100 if total_net > 0 else 0
    return {
        "yrs_pos": sum(1 for r in per_year if r["net"] > 0),
        "n_yrs": len(per_year), "total_net": total_net,
        "era3_pf": eras[-1]["pf"] if eras else float("nan"),
        "era3_median": eras[-1]["median"] if eras else float("nan"),
        "max_yr_share_pct": max_yr_share,
        "per_year": per_year,
    }


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


def _classify(m):
    n = m.get("n", 0); pf = m.get("pf", 0); median = m.get("median", 0)
    if n < 100: return f"KILL (n={n}, workhorse min 100)"
    if median < 0 and pf >= 1.15: return "KILL (asymmetric trap)"
    if median < 0: return "KILL (median neg)"
    if pf < 1.15: return "KILL (PF<1.15)"
    if pf >= 1.20 and median > 0: return "ESCALATE_TO_V1_AUDIT"
    return "WATCH"


def run():
    print("Cycle 2026-06-11p — Daily workhorse first batch on MNQ/MES (#176 C)\n", flush=True)
    PRIMITIVES = ["abnormal_range_followup", "range_compression_break",
                  "stop_run_reversal", "volatility_regime_compound"]

    # Count session days for "% days traded" computation
    total_sessions_by_asset = {}
    for asset in ["MNQ", "MES"]:
        df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
        df["date"] = pd.to_datetime(df["datetime"]).dt.date
        # RTH session days only (~250/year × 8 yrs)
        rth = df[(pd.to_datetime(df["datetime"]).dt.hour >= 9) &
                  (pd.to_datetime(df["datetime"]).dt.hour < 16)]
        total_sessions_by_asset[asset] = rth["date"].nunique()
        print(f"  {asset}: {total_sessions_by_asset[asset]} RTH sessions in data", flush=True)
    print()

    t_start = time.time()
    results = []
    for asset in ["MNQ", "MES"]:
        for entry in PRIMITIVES:
            label = f"WH-{asset}-{entry}-ema_slope-PL"
            t0 = time.time()
            try:
                m, trades = _run(asset, entry, "profit_ladder", "ema_slope", label)
                v = _classify(m)
                ts = None; stress_m = None; v1_gates = None; v1_verdict = None
                daily_metrics = daily_workhorse_metrics(trades, total_sessions_by_asset[asset])
                if v == "ESCALATE_TO_V1_AUDIT":
                    stress_m, _ = _run(asset, entry, "profit_ladder", "ema_slope",
                                        f"{label}-stress", cost_mult=2.0, slip_mult=3.0)
                    ts = temporal_split(trades)
                    v1_gates = evaluate_v1_workhorse_gates(m, ts, stress_m)
                    v1_verdict = "PAPER_PACKET_CANDIDATE" if all(v1_gates.values()) else \
                                  f"ARCHIVED (fails: {[k for k, v in v1_gates.items() if not v]})"
            except Exception as e:
                print(f"  {label}: ERROR {e}", flush=True)
                results.append({"label": label, "error": str(e)})
                continue
            elapsed = time.time() - t0
            extra = f" → {v1_verdict}" if v1_verdict else ""
            print(
                f"  {label:50s}: n={m['n']:5d} PF={m['pf']:.3f} "
                f"med=${m['median']:6.2f} ({daily_metrics['trades_per_day']:.1f}/day, "
                f"{daily_metrics['pct_days_traded']:.0f}% days) → {v}{extra} [{elapsed:.0f}s]",
                flush=True
            )
            results.append({
                "label": label, "asset": asset, "entry": entry,
                "metrics": {k: m.get(k) for k in ("n", "pf", "median", "net", "max_dd")},
                "verdict": v, "daily_metrics": daily_metrics,
                "v1_gates": v1_gates, "v1_verdict": v1_verdict,
                "temporal_split": ts,
                "stress_metrics": {"pf": float(stress_m["pf"]), "median": float(stress_m["median"])}
                                    if stress_m else None,
            })
    total = time.time() - t_start
    print(f"\nTotal: {total:.0f}s", flush=True)

    paper = [r for r in results if r.get("v1_verdict") == "PAPER_PACKET_CANDIDATE"]
    archived = [r for r in results if "ARCHIVED" in (r.get("v1_verdict") or "") or "KILL" in r.get("verdict", "")]
    print(f"\nV1 workhorse tier: PAPER_PACKET_CANDIDATE={len(paper)} ARCHIVED={len(archived)}", flush=True)
    if paper:
        print("\nPAPER_PACKET_CANDIDATE — needs V1 8-dim audit + family review:")
        for r in paper:
            m = r["metrics"]
            dm = r["daily_metrics"]
            print(f"  {r['label']}: PF={m['pf']:.3f} median=${m['median']:.2f}, {dm['trades_per_day']:.1f}/day, {dm['pct_days_traded']:.0f}% days traded", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-11p_daily_workhorse_first_batch.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "Daily workhorse first batch per #176 C — pivot from event to workhorse",
        "doctrine_reference": "docs/fql_forge/PACKET_STANDARD_V1_2026-06-11.md (workhorse gates)",
        "v1_tier": {"PAPER_PACKET_CANDIDATE": len(paper), "ARCHIVED": len(archived)},
        "results": results,
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
