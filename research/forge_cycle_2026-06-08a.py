"""Cycle 2026-06-08a — Directional asymmetry expansion + PL vs FR2 fragility study.

Per operator decisions 2026-06-08:
  #85 OK C (prop-cost verification → separate note artifact)
  #86 OK continue (directional asymmetry: MES/MYM/ZN ORB long vs short)
  #87 OK investigate (PL vs FR2 cost-fragility; do NOT codify yet)

Boundaries:
  - Report-only Lane B research.
  - No registry mutation, no scheduler change, no portfolio change, no paper/live promotion.
  - Every WATCH gets prop-stress immediately.
  - Stress failure = OBSERVATIONAL.
  - Same-family subset = insight, not packet.
  - Median-negative PF>1.2 = KILL.
  - Short data window = OBSERVATIONAL only.
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
    if median < 0 and pf >= 1.2:
        return "KILL (asymmetric trap: PF>1.2, median<0)"
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
    """Runner that caches sigs after first call; only re-runs backtest on cost change."""
    _cache = {}
    def runner(commission_mult, slippage_mult):
        cfg = ASSETS[spec["asset"]]
        base_costs = get_cost_params(spec["asset"])
        if "sigs" not in _cache:
            df = pd.read_csv(ROOT / "data" / "processed" / f"{spec['asset']}_5m.csv")
            sigs = generate_crossbred_signals(
                df, entry_name=spec["entry"], exit_name=spec["exit"],
                filter_name=spec["filter"], params=spec.get("params", {}),
            )
            _cache["df"] = df
            _cache["sigs"] = sigs
        df = _cache["df"]
        sigs = _cache["sigs"]
        mode = spec.get("mode", "both")
        res = run_backtest(
            df, sigs, mode=mode, point_value=cfg["point_value"],
            symbol=spec["asset"],
            commission_per_side=base_costs["commission_per_side"] * commission_mult,
            slippage_ticks=int(np.ceil(base_costs["slippage_ticks"] * slippage_mult)),
            tick_size=base_costs["tick_size"],
        )
        return res
    return runner


def run_one(spec, stress_on_watch=True):
    runner = make_runner(spec)
    res = runner(1.0, 1.0)
    m = _metrics(res["trades_df"], spec["label"], costs=res["stats"]["costs"])
    vc = _classify(m)
    ts = temporal_split(res["trades_df"]) if vc == "TEMPORAL_SPLIT_REQUIRED" else None
    v, delta = _doctrine(m, ts, m.get("median", 0))
    stress = None
    if stress_on_watch and "WATCH" in v:
        stress = prop_stress_screen(runner, spec["label"])
    return m, ts, v, delta, stress, runner


def stress_break_even(runner, label):
    """5-rung break-even diagnostic for cost-fragility study.

    Returns rung list with (rung_name, commission_mult, slippage_mult, median, pf).
    """
    ladder = [
        ("1x baseline", 1.0, 1.0),
        ("1.5x cost + 1 tick slip", 1.5, 2.0),
        ("2x cost + 1 tick slip", 2.0, 2.0),
        ("2x cost + 2 ticks slip", 2.0, 3.0),
        ("4x cost + 2 ticks slip", 4.0, 3.0),
    ]
    rows = []
    for rung, cm, sm in ladder:
        res = runner(cm, sm)
        m = _metrics(res["trades_df"], f"{label}-{rung}", costs=res["stats"]["costs"])
        wins = res["trades_df"][res["trades_df"]["pnl"] > 0]["pnl"]
        losses = res["trades_df"][res["trades_df"]["pnl"] < 0]["pnl"]
        rows.append({
            "rung": rung,
            "commission_mult": cm,
            "slippage_mult": sm,
            "n": int(m["n"]),
            "pf": float(m["pf"]),
            "median": float(m["median"]),
            "mean": float(m["mean"]) if "mean" in m else float(res["trades_df"]["pnl"].mean()),
            "win_rate": float(len(wins) / len(res["trades_df"])) if len(res["trades_df"]) > 0 else 0.0,
            "avg_win": float(wins.mean()) if len(wins) > 0 else 0.0,
            "avg_loss": float(losses.mean()) if len(losses) > 0 else 0.0,
        })
    return rows


def find_break_even(rows):
    """Linear-interpolate between rungs to find median-zero round-trip-cost rung."""
    for i in range(len(rows) - 1):
        if rows[i]["median"] > 0 and rows[i+1]["median"] <= 0:
            return {
                "between": (rows[i]["rung"], rows[i+1]["rung"]),
                "high_median": rows[i]["median"],
                "low_median": rows[i+1]["median"],
            }
    if rows[-1]["median"] > 0:
        return {"between": (rows[-1]["rung"], "beyond"), "high_median": rows[-1]["median"], "low_median": None}
    return {"between": ("before baseline", rows[0]["rung"]), "high_median": None, "low_median": rows[0]["median"]}


# --- TRACK B: Directional asymmetry expansion ---
DIRECTIONAL_SPECS = [
    # MES — moderate liquidity micros
    {"label": "DIR-MES-ORB-Long-PL", "asset": "MES", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "long"},
    {"label": "DIR-MES-ORB-Short-PL", "asset": "MES", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "short"},

    # MYM — lowest-volume equity micro; conservative slip already in cost config
    {"label": "DIR-MYM-ORB-Long-PL", "asset": "MYM", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "long"},
    {"label": "DIR-MYM-ORB-Short-PL", "asset": "MYM", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "short"},

    # ZN — treasury micro
    {"label": "DIR-ZN-ORB-Long-PL", "asset": "ZN", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "long"},
    {"label": "DIR-ZN-ORB-Short-PL", "asset": "ZN", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "short"},

    # ZF / ZB — only if reasonable data; conservative
    {"label": "DIR-ZF-ORB-Long-PL", "asset": "ZF", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "long"},
    {"label": "DIR-ZF-ORB-Short-PL", "asset": "ZF", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "short"},
]

# --- TRACK C: PL vs FR2 fragility comparison ---
# Select pairs of (same asset, entry, filter, mode) with PL and FR2 exits.
FRAGILITY_PAIRS = [
    # Known MCL Short pair (control — established break-evens)
    [{"label": "FRAG-MCL-Short-PL", "asset": "MCL", "entry": "orb_breakout",
      "filter": "ema_slope", "exit": "profit_ladder", "mode": "short"},
     {"label": "FRAG-MCL-Short-FR2", "asset": "MCL", "entry": "orb_breakout",
      "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 2.0}, "mode": "short"}],
    # MGC ORB Short pair
    [{"label": "FRAG-MGC-Short-PL", "asset": "MGC", "entry": "orb_breakout",
      "filter": "ema_slope", "exit": "profit_ladder", "mode": "short"},
     {"label": "FRAG-MGC-Short-FR2", "asset": "MGC", "entry": "orb_breakout",
      "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 2.0}, "mode": "short"}],
    # MGC ORB Long pair (for cross-direction control)
    [{"label": "FRAG-MGC-Long-PL", "asset": "MGC", "entry": "orb_breakout",
      "filter": "ema_slope", "exit": "profit_ladder", "mode": "long"},
     {"label": "FRAG-MGC-Long-FR2", "asset": "MGC", "entry": "orb_breakout",
      "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 2.0}, "mode": "long"}],
    # MGC PriorDayBreak Long pair
    [{"label": "FRAG-PDB-MGC-Long-PL", "asset": "MGC", "entry": "prior_day_break",
      "filter": "ema_slope", "exit": "profit_ladder", "mode": "long"},
     {"label": "FRAG-PDB-MGC-Long-FR2", "asset": "MGC", "entry": "prior_day_break",
      "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 2.0}, "mode": "long"}],
    # MCL DC Short pair
    [{"label": "FRAG-DC-MCL-Short-PL", "asset": "MCL", "entry": "donchian_breakout",
      "filter": "ema_slope", "exit": "profit_ladder", "mode": "short"},
     {"label": "FRAG-DC-MCL-Short-FR2", "asset": "MCL", "entry": "donchian_breakout",
      "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 2.0}, "mode": "short"}],
]


def run():
    print(f"Cycle 2026-06-08a — Directional expansion + PL/FR2 fragility study", flush=True)
    print(f"Boundaries: report-only Lane B. No registry/portfolio/scheduler/promotion mutation.\n", flush=True)
    print(f"Feature cache: {feature_cache_stats()}\n", flush=True)

    t_start = time.time()
    directional_results = []
    fragility_results = []

    # --- TRACK B: Directional asymmetry expansion ---
    print(f"--- TRACK B: Directional asymmetry expansion ({len(DIRECTIONAL_SPECS)} candidates) ---", flush=True)
    for i, spec in enumerate(DIRECTIONAL_SPECS, 1):
        t0 = time.time()
        try:
            m, ts, v, delta, stress, _ = run_one(spec, stress_on_watch=True)
        except Exception as e:
            print(f"  [{i}] {spec['label']}: ERROR {e}", flush=True)
            directional_results.append({"spec": spec, "error": str(e)})
            continue
        elapsed = time.time() - t0
        max_yr = m.get("max_year_share_pct", float("nan"))
        n_yrs = ts["n_yrs"] if ts else m.get("n_years", "?")
        yrs_pos = ts["yrs_pos"] if ts else m.get("years_positive", "?")
        era3 = ts["era3_pf"] if ts else float("nan")
        delta_str = f" [{delta}]" if delta else ""
        stress_str = f" stress={stress['verdict'].split()[0]}" if stress else ""
        print(
            f"  [{i}] {spec['label']:30s} ({spec['mode']:5s}): n={m['n']:5d} PF={m['pf']:.3f} "
            f"median=${m['median']:7.2f} max-yr={max_yr:.1f}% yrs+={yrs_pos}/{n_yrs} Era3={era3:.2f} → {v}{delta_str}{stress_str} [{elapsed:.0f}s]",
            flush=True
        )
        directional_results.append({
            "spec": spec,
            "metrics": {k: m.get(k) for k in (
                "n", "pf", "median", "net", "max_dd",
                "max_year_share_pct", "top3_share_pct",
                "h1_pf", "h2_pf", "years_positive", "n_years",
            )},
            "temporal_split": ts, "doctrine_verdict": v,
            "era3_delta": delta, "prop_stress": stress,
            "elapsed_seconds": elapsed,
        })

    # --- TRACK C: PL vs FR2 fragility comparison ---
    print(f"\n--- TRACK C: PL vs FR2 cost-fragility comparison ({len(FRAGILITY_PAIRS)} pairs) ---", flush=True)
    for j, pair in enumerate(FRAGILITY_PAIRS, 1):
        pl_spec, fr2_spec = pair
        pl_runner = make_runner(pl_spec)
        fr2_runner = make_runner(fr2_spec)
        t0 = time.time()
        try:
            pl_rows = stress_break_even(pl_runner, pl_spec["label"])
            fr2_rows = stress_break_even(fr2_runner, fr2_spec["label"])
        except Exception as e:
            print(f"  [{j}] {pl_spec['asset']}-{pl_spec['mode']}: ERROR {e}", flush=True)
            fragility_results.append({"pair": pair, "error": str(e)})
            continue
        elapsed = time.time() - t0
        pl_be = find_break_even(pl_rows)
        fr2_be = find_break_even(fr2_rows)
        # Compute cost-tolerance gap (PL break-even rung vs FR2 break-even rung)
        rung_order = ["1x baseline", "1.5x cost + 1 tick slip", "2x cost + 1 tick slip",
                      "2x cost + 2 ticks slip", "4x cost + 2 ticks slip", "beyond"]
        def rung_idx(name):
            try: return rung_order.index(name)
            except ValueError: return -1
        pl_be_rung = pl_be["between"][1]
        fr2_be_rung = fr2_be["between"][1]
        gap_rungs = rung_idx(pl_be_rung) - rung_idx(fr2_be_rung)
        print(
            f"  [{j}] {pl_spec['asset']}-{pl_spec['entry'][:3]}-{pl_spec['mode']:5s}:"
            f" PL n={pl_rows[0]['n']} PF1x={pl_rows[0]['pf']:.3f} med1x=${pl_rows[0]['median']:6.2f} BE@{pl_be_rung[:18]:<18s}"
            f" || FR2 n={fr2_rows[0]['n']} PF1x={fr2_rows[0]['pf']:.3f} med1x=${fr2_rows[0]['median']:6.2f} BE@{fr2_be_rung[:18]:<18s}"
            f" Δrungs={gap_rungs} [{elapsed:.0f}s]",
            flush=True
        )
        fragility_results.append({
            "pair_label": f"{pl_spec['asset']}-{pl_spec['entry']}-{pl_spec['mode']}",
            "pl_spec": pl_spec, "fr2_spec": fr2_spec,
            "pl_rows": pl_rows, "fr2_rows": fr2_rows,
            "pl_break_even": pl_be, "fr2_break_even": fr2_be,
            "rung_gap_pl_vs_fr2": gap_rungs,
            "elapsed_seconds": elapsed,
        })

    total = time.time() - t_start
    print(f"\nTotal: {total:.0f}s. Feature cache: {feature_cache_stats()}", flush=True)

    # 3-tier classification of directional results
    paper_packet, portfolio_complement, observational, kill = [], [], [], []
    for r in directional_results:
        if "error" in r:
            continue
        v = r["doctrine_verdict"]; s = r["prop_stress"]
        if "KILL" in v or "ARCHITECTURAL_REJECT" in v:
            kill.append(r)
        elif "WATCH_FOR_DEEP_SCREEN" in v:
            if s and s["verdict"] == "PASS_STRESS":
                paper_packet.append(r)
            else:
                observational.append(r)
        elif "WATCH" in v:
            observational.append(r)
    print(f"\nTrack B tier classification: PAPER_PACKET={len(paper_packet)} "
          f"PORTFOLIO_COMPLEMENT={len(portfolio_complement)} "
          f"OBSERVATIONAL={len(observational)} KILL={len(kill)}", flush=True)
    if paper_packet:
        print("\nPAPER_PACKET tier (passes prop-stress):")
        for r in paper_packet:
            m = r["metrics"]
            print(f"  {r['spec']['label']}: PF={m['pf']:.3f} median=${m['median']:.2f}", flush=True)

    # Fragility pattern summary
    pl_more_robust = sum(1 for r in fragility_results if r.get("rung_gap_pl_vs_fr2", 0) > 0)
    fr2_more_robust = sum(1 for r in fragility_results if r.get("rung_gap_pl_vs_fr2", 0) < 0)
    tied = sum(1 for r in fragility_results if r.get("rung_gap_pl_vs_fr2", 0) == 0)
    print(f"\nTrack C fragility pattern: PL_more_robust={pl_more_robust} "
          f"FR2_more_robust={fr2_more_robust} TIED={tied} (of {len(fragility_results)} pairs)", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-08a.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "approvals": "OK C (#85), OK continue (#86), OK investigate (#87)",
        "boundaries": "report-only Lane B; no registry/portfolio/scheduler/promotion mutation",
        "track_B_directional": {
            "tier_classification": {
                "PAPER_PACKET": len(paper_packet),
                "PORTFOLIO_COMPLEMENT": len(portfolio_complement),
                "OBSERVATIONAL": len(observational),
                "KILL": len(kill),
            },
            "results": directional_results,
        },
        "track_C_fragility": {
            "pl_more_robust": pl_more_robust,
            "fr2_more_robust": fr2_more_robust,
            "tied": tied,
            "n_pairs": len(fragility_results),
            "results": fragility_results,
        },
        "feature_cache_stats_final": feature_cache_stats(),
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
