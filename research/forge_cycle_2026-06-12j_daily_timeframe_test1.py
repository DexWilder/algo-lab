"""Cycle 2026-06-12j — Daily-Timeframe Test 1: prior_day_break + prior_day_fade × MNQ/MES.

Per operator #200 A: viability probe of existing daily-referencing primitives.

Test matrix:
  - prior_day_break × MNQ × ema_slope × profit_ladder
  - prior_day_break × MES × ema_slope × profit_ladder
  - prior_day_fade × MNQ × ema_slope × profit_ladder
  - prior_day_fade × MES × ema_slope × profit_ladder

V1 archetype-correct gates:
  - n >= 500 → workhorse gates (PF>=1.20, etc.)
  - n < 500 → tail-engine gates (PF>=1.30, etc.)

Daily-specific instrumentation:
  - Average bars per trade
  - Overnight exposure fraction
  - DOW / month patterns

Important framing: if all 4 fail, only the DIRECT EXISTING-PRIMITIVES thesis
archived. Daily-timeframe lane remains valid for NEW primitives (failed daily
breakout, weekly range compression, 3-day momentum, inside-day expansion).

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


def daily_instrumentation(trades, total_sessions):
    """Daily-specific metrics per methodology."""
    if trades.empty:
        return {"n_trades": 0, "trades_per_day": 0, "pct_days_traded": 0,
                "avg_hold_bars": 0, "overnight_pct": 0}
    trades = trades.copy()
    trades["entry_dt"] = pd.to_datetime(trades["entry_time"])
    trades["exit_dt"] = pd.to_datetime(trades["exit_time"])
    trades["date"] = trades["entry_dt"].dt.date
    daily = trades.groupby("date")["pnl"].sum()
    # Average hold time in 5-min bars
    trades["hold_minutes"] = (trades["exit_dt"] - trades["entry_dt"]).dt.total_seconds() / 60
    trades["hold_bars"] = trades["hold_minutes"] / 5
    avg_hold_bars = float(trades["hold_bars"].mean())
    # Overnight exposure
    trades["overnight"] = (trades["exit_dt"].dt.date != trades["entry_dt"].dt.date).astype(int)
    overnight_pct = float(trades["overnight"].mean() * 100)
    # DOW distribution
    trades["dow"] = trades["entry_dt"].dt.day_name()
    dow_dist = trades["dow"].value_counts().to_dict()
    return {
        "n_trades": len(trades),
        "n_days_traded": len(daily),
        "trades_per_day": float(len(trades) / len(daily)) if len(daily) > 0 else 0,
        "pct_days_traded": float(len(daily) / total_sessions * 100) if total_sessions > 0 else 0,
        "pct_profitable_days": float((daily > 0).mean() * 100),
        "avg_hold_bars": avg_hold_bars,
        "avg_hold_minutes": float(trades["hold_minutes"].mean()),
        "overnight_pct": overnight_pct,
        "dow_distribution": dow_dist,
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
    nets_arr = np.array(nets)
    instance_cv = float(nets_arr.std() / nets_arr.mean()) if nets_arr.mean() != 0 else float("inf")
    return {"yrs_pos": sum(1 for r in per_year if r["net"] > 0),
            "n_yrs": len(per_year),
            "era3_pf": eras[-1]["pf"] if eras else float("nan"),
            "era3_median": eras[-1]["median"] if eras else float("nan"),
            "max_yr_share_pct": max_yr, "instance_cv": instance_cv,
            "positive_instance_fraction": sum(1 for r in per_year if r["net"] > 0) / len(per_year) if per_year else 0,
            "per_year": per_year, "eras": eras}


def evaluate_workhorse_gates(m, ts, stress_m):
    return {
        "n_>=_500": m["n"] >= 500,
        "PF_>=_1.20": m["pf"] >= 1.20,
        "positive_median": m["median"] > 0,
        "PASS_STRESS": stress_m["median"] > 0,
        "max_yr_<=_50pct": ts["max_yr_share_pct"] <= 50.0,
        "yrs_pos_>=_50pct": ts["positive_instance_fraction"] >= 0.5,
        "Era3_PF_>=_1.0": ts["era3_pf"] >= 1.0,
        "Era3_median_>=_0": ts["era3_median"] >= 0,
    }


def evaluate_tail_engine_gates(m, ts, stress_m):
    return {
        "n_>=_20": m["n"] >= 20,
        "PF_>=_1.30": m["pf"] >= 1.30,
        "PASS_STRESS_PF_>=_1.30": stress_m["pf"] >= 1.30,
        "max_instance_<=_35pct": ts["max_yr_share_pct"] <= 35.0,
        "positive_instance_frac_>=_60pct": ts["positive_instance_fraction"] >= 0.6,
        "instance_CV_<=_3.0": ts["instance_cv"] <= 3.0,
        "Era3_PF_>=_1.0": ts["era3_pf"] >= 1.0,
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
    if n < 20: return f"KILL (n={n}, below tail-engine min 20)"
    if median < 0 and pf >= 1.15: return "KILL (asymmetric trap)"
    if median < 0: return "KILL (median neg)"
    if pf < 1.15: return "KILL (PF<1.15)"
    if pf >= 1.20 and median > 0: return "ESCALATE_TO_V1_AUDIT"
    return "WATCH"


def run():
    print("Cycle 2026-06-12j — Daily-Timeframe Test 1 (#200 A)\n", flush=True)
    print("Viability probe: prior_day_break + prior_day_fade × MNQ/MES.\n", flush=True)

    sessions = {}
    for asset in ["MNQ", "MES"]:
        df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
        rth = df[(pd.to_datetime(df["datetime"]).dt.hour >= 9) &
                  (pd.to_datetime(df["datetime"]).dt.hour < 16)]
        sessions[asset] = pd.to_datetime(rth["datetime"]).dt.date.nunique()
    print(f"  MNQ sessions: {sessions['MNQ']}, MES sessions: {sessions['MES']}\n", flush=True)

    t_start = time.time()
    results = []
    for entry in ["prior_day_break", "prior_day_fade"]:
        for asset in ["MNQ", "MES"]:
            label = f"WH-{asset}-{entry}-ema_slope-PL"
            t0 = time.time()
            try:
                m, trades = _run(asset, entry, "profit_ladder", "ema_slope", label)
                v = _classify(m)
                daily = daily_instrumentation(trades, sessions[asset])
                ts = None; stress_m = None; gates = None; v1_verdict = None
                archetype = "WORKHORSE" if m["n"] >= 500 else "TAIL_ENGINE"
                if v == "ESCALATE_TO_V1_AUDIT":
                    stress_m, _ = _run(asset, entry, "profit_ladder", "ema_slope",
                                        f"{label}-stress", cost_mult=2.0, slip_mult=3.0)
                    ts = temporal_split(trades)
                    if archetype == "WORKHORSE":
                        gates = evaluate_workhorse_gates(m, ts, stress_m)
                    else:
                        gates = evaluate_tail_engine_gates(m, ts, stress_m)
                    v1_verdict = "PAPER_PACKET_CANDIDATE" if all(gates.values()) else \
                                  f"ARCHIVED (fails: {[k for k, v in gates.items() if not v]})"
            except Exception as e:
                import traceback; traceback.print_exc()
                print(f"  {label}: ERROR {e}", flush=True)
                results.append({"label": label, "error": str(e)})
                continue
            elapsed = time.time() - t0
            extra = f" → {v1_verdict}" if v1_verdict else ""
            print(
                f"  {label:55s}: n={m['n']:5d} PF={m['pf']:.3f} "
                f"med=${m['median']:6.2f} ({archetype}) "
                f"hold={daily['avg_hold_bars']:.1f} bars, overnight={daily['overnight_pct']:.0f}% → {v}{extra} [{elapsed:.0f}s]",
                flush=True
            )
            results.append({
                "label": label, "asset": asset, "entry": entry, "archetype": archetype,
                "metrics": {k: m.get(k) for k in ("n", "pf", "median", "net", "max_dd")},
                "daily_instrumentation": daily,
                "verdict": v, "v1_gates": gates, "v1_verdict": v1_verdict,
                "temporal_split": ts,
                "stress_metrics": {"pf": float(stress_m["pf"]), "median": float(stress_m["median"])}
                                    if stress_m else None,
                "trades_for_family": trades,
            })

    print(f"\nTotal: {time.time() - t_start:.0f}s", flush=True)

    # Family review on PAPER_PACKET_CANDIDATEs (vs all Lane A candidates)
    print(f"\n--- Family review on any PAPER_PACKET_CANDIDATE (vs Lane A) ---", flush=True)
    for r in results:
        if "error" in r or r.get("v1_verdict") != "PAPER_PACKET_CANDIDATE": continue
        _, t_stop = _run("MNQ", "stop_run_reversal", "profit_ladder", "ema_slope", "ref")
        _, t_range = _run("MNQ", "range_compression_break", "profit_ladder", "ema_slope", "ref")
        _, t_fip = _run("MNQ", "first_impulse_pullback", "profit_ladder", "ema_slope", "ref")
        _, t_orb = _run("MNQ", "orb_breakout", "profit_ladder", "ema_slope", "ref")
        fam = {
            "vs_LaneA_stop_run": family_corr(r["trades_for_family"], t_stop),
            "vs_LaneA_range_compression": family_corr(r["trades_for_family"], t_range),
            "vs_LaneA_first_impulse": family_corr(r["trades_for_family"], t_fip),
            "vs_XB_ORB_MNQ_probation": family_corr(r["trades_for_family"], t_orb),
        }
        print(f"  {r['label']}:", flush=True)
        for k, v in fam.items():
            print(f"    {k}: corr={v:+.3f}", flush=True)
        r["family_review"] = fam

    for r in results:
        r.pop("trades_for_family", None)

    paper = [r for r in results if r.get("v1_verdict") == "PAPER_PACKET_CANDIDATE"]
    archived = [r for r in results if "ARCHIVED" in (r.get("v1_verdict") or "") or "KILL" in r.get("verdict", "")]
    watch = [r for r in results if r.get("verdict") == "WATCH"]
    print(f"\nV1 tier: PAPER_PACKET_CANDIDATE={len(paper)} WATCH={len(watch)} ARCHIVED={len(archived)}", flush=True)

    print(f"\nViability assessment:", flush=True)
    if len(paper) > 0:
        print(f"  POSITIVE — daily-mechanism lane shows life. Proceed to Test 2 with NEW primitives if family review independent.", flush=True)
    elif len(watch) > 0 or any(r.get("metrics", {}).get("median", -999) > 0 for r in results):
        print(f"  BORDERLINE — direct daily primitives don't pass strict gates but show positive medians. NEW daily primitives (Test 2) still warranted.", flush=True)
    else:
        print(f"  NEGATIVE on existing primitives — but per operator framing, daily-timeframe LANE remains valid for NEW primitives.", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-12j_daily_timeframe_test1.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "Daily-Timeframe Test 1 (viability probe) per #200 A",
        "framing": "if all fail, archive only direct existing-primitives thesis; daily-timeframe lane remains valid for NEW primitives",
        "v1_tier": {"PAPER_PACKET_CANDIDATE": len(paper), "WATCH": len(watch), "ARCHIVED": len(archived)},
        "results": results,
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
