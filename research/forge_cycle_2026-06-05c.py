"""Consolidated cycle 2026-06-05c — MCL family review + stress break-even
diagnostic + DC directional batch + MGC PriorDayBreak Long fixed-ratio.

Per operator approvals 2026-06-05c (#81 MCL family review, #82 doc, #83 A+C,
#84 strict stress + break-even reporting).
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Reuse family-review framework
_spec = importlib.util.spec_from_file_location(
    "mnq_review_lib", ROOT / "research" / "forge_mnq_family_review.py"
)
_lib = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lib)
trade_overlap_analysis = _lib.trade_overlap_analysis
pnl_correlation = _lib.pnl_correlation
daily_pnl_series = _lib.daily_pnl_series
portfolio_metrics = _lib.portfolio_metrics
controller_combined_series = _lib.controller_combined_series
classify_family_review = _lib.classify_family_review

from research.crossbreeding.crossbreeding_engine import (  # noqa: E402
    generate_crossbred_signals, feature_cache_stats,
)
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from research.prop_stress_screen import prop_stress_screen  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def _classify(m):
    n = m.get("n", 0); pf = m.get("pf", 0); median = m.get("median", 0)
    max_yr = m.get("max_year_share_pct", 100)
    if n < 30:
        return f"KILL (n={n})"
    if median < 0:
        return "KILL (median neg)"
    if pf < 1.15:
        return "KILL (PF<1.15)"
    if max_yr >= 50:
        return "TEMPORAL_SPLIT_REQUIRED"
    if pf >= 1.30 and median > 0:
        return "WATCH_FOR_DEEP_SCREEN"
    return "WATCH"


def temporal_split(trades):
    if trades.empty:
        return None
    df = trades.copy()
    df["entry_dt"] = pd.to_datetime(df["entry_time"])
    df["year"] = df["entry_dt"].dt.year
    per_year = []
    for y, g in df.groupby("year"):
        pnl = g["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w/l) if l > 0 else float("inf")
        per_year.append({"year": int(y), "n": int(len(g)),
                         "pf": pf, "median": float(np.median(pnl)),
                         "net": float(pnl.sum())})
    df = df.sort_values("entry_dt").reset_index(drop=True)
    cuts = np.linspace(0, len(df), 4).astype(int)
    eras = []
    for i in range(3):
        sub = df.iloc[cuts[i]:cuts[i+1]]
        if sub.empty: continue
        pnl = sub["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w/l) if l > 0 else float("inf")
        eras.append({"era": i+1, "n": int(len(sub)), "pf": pf,
                     "median": float(np.median(pnl)),
                     "net": float(pnl.sum())})
    return {"per_year": per_year, "eras": eras,
            "yrs_pos": sum(1 for r in per_year if r["net"] > 0),
            "n_yrs": len(per_year),
            "era3_pf": eras[-1]["pf"] if eras else float("nan"),
            "era3_median": eras[-1]["median"] if eras else float("nan")}


def _doctrine(m, ts, full_median):
    v = _classify(m)
    if v != "TEMPORAL_SPLIT_REQUIRED" or ts is None:
        return v, None
    if ts["yrs_pos"] < ts["n_yrs"] * 0.5:
        return "ARCHITECTURAL_REJECT (<50% yrs+)", None
    if any(e["pf"] < 1.0 and np.isfinite(e["pf"]) for e in ts["eras"]):
        return "ARCHITECTURAL_REJECT (losing era)", None
    era3 = ts.get("era3_pf", 1.0)
    if np.isfinite(era3) and era3 < 1.0:
        return "ARCHITECTURAL_REJECT (Era-3 regime-wall fail)", None
    era3_med = ts.get("era3_median", full_median)
    delta = None
    if full_median > 0:
        if era3_med > full_median * 2:
            delta = "RECENT_IMPROVEMENT_SIGNAL"
        elif era3_med < full_median * 0.5 or era3_med < 0:
            delta = "CURRENT_REGIME_WARNING"
    if m["pf"] >= 1.30 and m["median"] > 0 and ts["yrs_pos"] >= ts["n_yrs"] * 0.75:
        return "WATCH_FOR_DEEP_SCREEN (temporal+Era3)", delta
    return "WATCH (temporal)", delta


def make_runner(spec):
    _cache = {}
    def runner(cm, sm):
        cfg = ASSETS[spec["asset"]]
        bc = get_cost_params(spec["asset"])
        if "sigs" not in _cache:
            df = pd.read_csv(ROOT / "data" / "processed" / f"{spec['asset']}_5m.csv")
            sigs = generate_crossbred_signals(
                df, entry_name=spec["entry"], exit_name=spec["exit"],
                filter_name=spec["filter"], params=spec.get("params", {}),
            )
            _cache["df"] = df
            _cache["sigs"] = sigs
        res = run_backtest(
            _cache["df"], _cache["sigs"], mode=spec.get("mode", "both"),
            point_value=cfg["point_value"], symbol=spec["asset"],
            commission_per_side=bc["commission_per_side"] * cm,
            slippage_ticks=int(np.ceil(bc["slippage_ticks"] * sm)),
            tick_size=bc["tick_size"],
        )
        return res
    return runner


def run_with_stress(spec):
    runner = make_runner(spec)
    res = runner(1.0, 1.0)
    m = _metrics(res["trades_df"], spec["label"], costs=res["stats"]["costs"])
    vc = _classify(m)
    ts = temporal_split(res["trades_df"]) if vc == "TEMPORAL_SPLIT_REQUIRED" else None
    v, delta = _doctrine(m, ts, m.get("median", 0))
    stress = None
    if "WATCH" in v:
        stress = prop_stress_screen(runner, spec["label"])
    return m, ts, v, delta, stress


def stress_break_even(spec):
    """Per-#84: report median across ladder for OBSERVATIONAL candidates."""
    runner = make_runner(spec)
    rows = []
    for label, cm, sm in [
        ("1x baseline", 1.0, 1.0),
        ("1.5x cost + 1 tick", 1.5, 2.0),
        ("2x cost + 1 tick", 2.0, 2.0),
        ("2x cost + 2 ticks", 2.0, 3.0),
        ("4x cost + 2 ticks", 4.0, 3.0),
    ]:
        res = runner(cm, sm)
        m = _metrics(res["trades_df"], f"{spec['label']}-{label}",
                     costs=res["stats"]["costs"])
        rows.append({"stress": label, "cm": cm, "sm": sm,
                     "n": int(m["n"]), "pf": float(m["pf"]),
                     "median": float(m["median"]), "net": float(m["net"])})
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Part 1: MCL family review (#81)
# ─────────────────────────────────────────────────────────────────────────────

def family_review(label_a, runner_spec_a, label_b, runner_spec_b):
    """Run both candidates' trades and apply 5-test family review."""
    def _build_trades(spec):
        runner = make_runner(spec)
        res = runner(1.0, 1.0)
        trades = res["trades_df"].copy()
        if not trades.empty:
            trades["entry_dt"] = pd.to_datetime(trades["entry_time"])
            trades["entry_date"] = trades["entry_dt"].dt.date
        return trades

    t_a = _build_trades(runner_spec_a)
    t_b = _build_trades(runner_spec_b)
    overlap = trade_overlap_analysis(t_a, t_b, label_a, label_b)
    corr = pnl_correlation(t_a, t_b)
    all_dates = pd.to_datetime(
        sorted(set(t_a["entry_date"]) | set(t_b["entry_date"]))
    )
    pnl_a = daily_pnl_series(t_a, all_dates)
    pnl_b = daily_pnl_series(t_b, all_dates)
    configs = {
        "A_baseline_alone": portfolio_metrics(pnl_a, f"{label_a} alone"),
        "B_new_alone": portfolio_metrics(pnl_b, f"{label_b} alone"),
        "C_both_full": portfolio_metrics(pnl_a + pnl_b, "Both full"),
        "D_both_half": portfolio_metrics((pnl_a + pnl_b) / 2, "Both half"),
        "E_replacement_new": portfolio_metrics(pnl_b.copy(), f"{label_b} replaces {label_a}"),
        "F_controller": portfolio_metrics(
            controller_combined_series(t_a, t_b, all_dates),
            f"{label_b} when fires else {label_a}"
        ),
    }
    verdict, notes = classify_family_review(
        configs["A_baseline_alone"], configs["B_new_alone"],
        configs["C_both_full"], configs["D_both_half"],
        configs["F_controller"], overlap, corr,
    )
    # Add REPLACEMENT mode check: if B alone has higher Sharpe AND lower DD AND >= 90% PnL of baseline
    replace_better = False
    a = configs["A_baseline_alone"]
    b = configs["B_new_alone"]
    if (b.get("sharpe_est", 0) >= a.get("sharpe_est", 0) * 0.95
            and abs(b.get("max_drawdown", 0)) <= abs(a.get("max_drawdown", 0)) * 1.05
            and b.get("total_pnl", 0) >= a.get("total_pnl", 0) * 0.90):
        replace_better = True
    if replace_better and verdict in ("INCONCLUSIVE / WATCH_FOR_LONGER_OBSERVATION", "PARALLEL_COMPLEMENT_CANDIDATE"):
        verdict = "REPLACEMENT_CANDIDATE_LIKELY (B Sharpe ≥ 95% A AND DD ≤ 105% A AND PnL ≥ 90% A)"
    return {"label_a": label_a, "label_b": label_b,
            "overlap": overlap, "correlation": corr,
            "configs": configs, "verdict": verdict, "notes": notes}


MCL_BASELINE = {"label": "XB-ORB-EMA-Ladder-MCL", "asset": "MCL",
                "entry": "orb_breakout", "filter": "ema_slope",
                "exit": "profit_ladder", "mode": "both"}

MCL_SHORT_PL = {"label": "P1-MCL-ORB-Short-PL", "asset": "MCL",
                "entry": "orb_breakout", "filter": "ema_slope",
                "exit": "profit_ladder", "mode": "short"}

MCL_SHORT_FR2 = {"label": "P1-MCL-ORB-Short-FR2", "asset": "MCL",
                 "entry": "orb_breakout", "filter": "ema_slope",
                 "exit": "fixed_ratio", "params": {"ratio": 2.0},
                 "mode": "short"}


# ─────────────────────────────────────────────────────────────────────────────
# Part 2: Diagnostic batch
# ─────────────────────────────────────────────────────────────────────────────

DIAGNOSTIC_SPECS = [
    # A. DC short-bias diagnostic on MGC/MCL
    {"label": "DC-MGC-Long-PL", "asset": "MGC", "entry": "donchian_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "long"},
    {"label": "DC-MGC-Short-PL", "asset": "MGC", "entry": "donchian_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "short"},
    {"label": "DC-MGC-Short-FR2", "asset": "MGC", "entry": "donchian_breakout",
     "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 2.0},
     "mode": "short"},
    {"label": "DC-MCL-Long-PL", "asset": "MCL", "entry": "donchian_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "long"},
    {"label": "DC-MCL-Short-PL", "asset": "MCL", "entry": "donchian_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "short"},
    {"label": "DC-MCL-Short-FR2", "asset": "MCL", "entry": "donchian_breakout",
     "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 2.0},
     "mode": "short"},

    # C. MGC PriorDayBreak Long fixed-ratio variants (bounded)
    {"label": "PDB-MGC-Long-FR2", "asset": "MGC", "entry": "prior_day_break",
     "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 2.0},
     "mode": "long"},
    {"label": "PDB-MGC-Long-FR3", "asset": "MGC", "entry": "prior_day_break",
     "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 3.0},
     "mode": "long"},
]


def run():
    t_start = time.time()
    print("=" * 78, flush=True)
    print("Forge Cycle 2026-06-05c — MCL family review + diagnostics + stress break-even", flush=True)
    print("=" * 78, flush=True)

    # ─── Part 1: MCL family reviews ─────────────────────────────────────────
    print("\n[Part 1] MCL family reviews (#81)\n", flush=True)
    fam1 = family_review(MCL_BASELINE["label"], MCL_BASELINE,
                          MCL_SHORT_PL["label"], MCL_SHORT_PL)
    print(f"  vs Short-PL  — VERDICT: {fam1['verdict']}", flush=True)
    print(f"    daily corr: {fam1['correlation']['daily_corr']:.3f}", flush=True)
    print(f"    same-day overlap B-pct: {fam1['overlap']['same_day_pct_of_b']:.1f}%", flush=True)
    print(f"    config A baseline: total ${fam1['configs']['A_baseline_alone']['total_pnl']:.0f}, DD ${fam1['configs']['A_baseline_alone']['max_drawdown']:.0f}", flush=True)
    print(f"    config B short-only: total ${fam1['configs']['B_new_alone']['total_pnl']:.0f}, DD ${fam1['configs']['B_new_alone']['max_drawdown']:.0f}", flush=True)
    print(f"    config E replacement (B alone): same as B above", flush=True)

    fam2 = family_review(MCL_BASELINE["label"], MCL_BASELINE,
                          MCL_SHORT_FR2["label"], MCL_SHORT_FR2)
    print(f"\n  vs Short-FR2 — VERDICT: {fam2['verdict']}", flush=True)
    print(f"    daily corr: {fam2['correlation']['daily_corr']:.3f}", flush=True)
    print(f"    same-day overlap B-pct: {fam2['overlap']['same_day_pct_of_b']:.1f}%", flush=True)
    print(f"    config B (FR2 alone): total ${fam2['configs']['B_new_alone']['total_pnl']:.0f}, DD ${fam2['configs']['B_new_alone']['max_drawdown']:.0f}", flush=True)

    # ─── Part 2: Stress break-even on MCL Short candidates ──────────────────
    print("\n[Part 2] Stress break-even (#84) on MCL Short candidates\n", flush=True)
    print("\nP1-MCL-ORB-Short-PL break-even:", flush=True)
    be_pl = stress_break_even(MCL_SHORT_PL)
    for r in be_pl:
        print(f"  {r['stress']:25s}: n={r['n']} PF={r['pf']:.3f} netMed=${r['median']:.2f}", flush=True)

    print("\nP1-MCL-ORB-Short-FR2 break-even:", flush=True)
    be_fr2 = stress_break_even(MCL_SHORT_FR2)
    for r in be_fr2:
        print(f"  {r['stress']:25s}: n={r['n']} PF={r['pf']:.3f} netMed=${r['median']:.2f}", flush=True)

    # ─── Part 3: Diagnostic batch (DC directional + PriorDayBreak Long FR) ──
    print("\n[Part 3] Diagnostic batch (#83 A+C)\n", flush=True)
    diag_results = []
    for spec in DIAGNOSTIC_SPECS:
        t0 = time.time()
        m, ts, v, delta, stress = run_with_stress(spec)
        elapsed = time.time() - t0
        max_yr = m.get("max_year_share_pct", float("nan"))
        n_yrs = ts["n_yrs"] if ts else m.get("n_years", "?")
        yrs_pos = ts["yrs_pos"] if ts else m.get("years_positive", "?")
        era3 = ts["era3_pf"] if ts else float("nan")
        delta_str = f" [{delta}]" if delta else ""
        stress_str = f" stress={stress['verdict'].split()[0]}" if stress else ""
        print(f"  {spec['label']:25s} ({spec['mode']:5s}): n={m['n']:5d} PF={m['pf']:.3f} "
              f"median=${m['median']:7.2f} max-yr={max_yr:.1f}% "
              f"yrs+={yrs_pos}/{n_yrs} Era3={era3:.2f} → {v}{delta_str}{stress_str} [{elapsed:.0f}s]", flush=True)
        diag_results.append({
            "spec": spec,
            "metrics": {k: m.get(k) for k in (
                "n", "pf", "median", "net", "max_dd",
                "max_year_share_pct", "top3_share_pct",
                "h1_pf", "h2_pf", "years_positive", "n_years",
            )},
            "temporal": ts, "verdict": v, "era3_delta": delta,
            "prop_stress": stress,
        })

    total = time.time() - t_start
    print(f"\nTotal cycle: {total:.0f}s. Feature cache: {feature_cache_stats()}", flush=True)

    # Save
    out_dir = ROOT / "research" / "data" / "fql_forge" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_iso = date.today().isoformat() + "c"
    payload = {
        "date": date.today().isoformat(),
        "cycle": "c",
        "approvals": ["#81 MCL family review", "#82 MCL insight doc",
                      "#83 A+C diagnostic", "#84 strict stress + break-even"],
        "mcl_family_review": {"vs_Short_PL": fam1, "vs_Short_FR2": fam2},
        "mcl_stress_break_even": {"Short_PL": be_pl, "Short_FR2": be_fr2},
        "diagnostic_batch": diag_results,
        "feature_cache_stats": feature_cache_stats(),
    }
    (out_dir / f"forge_cycle_2026-06-05c.json").write_text(
        json.dumps(payload, indent=2, default=str)
    )
    print(f"\nWrote: {out_dir / f'forge_cycle_2026-06-05c.json'}", flush=True)


if __name__ == "__main__":
    run()
