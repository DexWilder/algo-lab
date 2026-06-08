"""Cycle 2026-06-08b — MNQ directional split + PL vs FR2 fragility n+5 extension.

Per operator decisions 2026-06-08:
  #89 OK run MNQ directional split (diagnostic only)
  #90 OK n+5 — extend PL vs FR2 study to n=10 with 5 new pairs
       Codify if PL wins/ties 8+/10 as daily-workhorse heuristic.

Boundaries:
  - Report-only Lane B research.
  - No registry mutation, no scheduler change, no portfolio change, no paper/live promotion.
  - MNQ directional = DIAGNOSTIC only (per #89; not packet candidate unless
    family review proves independent which is unlikely).
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


# Helpers inlined from cycle 2026-06-08a (hyphenated filenames break Python import)
def _classify(m):
    n = m.get("n", 0); pf = m.get("pf", 0); median = m.get("median", 0)
    max_yr = m.get("max_year_share_pct", 100)
    if n < 30: return f"KILL (n={n})"
    if median < 0 and pf >= 1.2: return "KILL (asymmetric trap: PF>1.2, median<0)"
    if median < 0: return "KILL (median neg)"
    if pf < 1.15: return "KILL (PF<1.15)"
    if max_yr >= 50: return "TEMPORAL_SPLIT_REQUIRED"
    if pf >= 1.30 and median > 0: return "WATCH_FOR_DEEP_SCREEN"
    return "WATCH"


def temporal_split(trades):
    if trades.empty: return None
    df = trades.copy()
    df["entry_dt"] = pd.to_datetime(df["entry_time"])
    df["year"] = df["entry_dt"].dt.year
    per_year = []
    for y, g in df.groupby("year"):
        pnl = g["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w/l) if l > 0 else float("inf")
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
        pf = float(w/l) if l > 0 else float("inf")
        eras.append({"era": i+1, "n": int(len(sub)), "pf": pf,
                     "median": float(np.median(pnl)), "net": float(pnl.sum())})
    return {"per_year": per_year, "eras": eras,
            "yrs_pos": sum(1 for r in per_year if r["net"] > 0),
            "n_yrs": len(per_year),
            "era3_pf": eras[-1]["pf"] if eras else float("nan"),
            "era3_median": eras[-1]["median"] if eras else float("nan")}


def _doctrine(m, ts, full_median):
    v = _classify(m)
    if v != "TEMPORAL_SPLIT_REQUIRED" or ts is None: return v, None
    if ts["yrs_pos"] < ts["n_yrs"] * 0.5: return "ARCHITECTURAL_REJECT (<50% yrs+)", None
    if any(e["pf"] < 1.0 and np.isfinite(e["pf"]) for e in ts["eras"]):
        return "ARCHITECTURAL_REJECT (losing era)", None
    era3 = ts.get("era3_pf", 1.0)
    if np.isfinite(era3) and era3 < 1.0:
        return "ARCHITECTURAL_REJECT (Era-3 regime-wall fail)", None
    era3_med = ts.get("era3_median", full_median)
    delta = None
    if full_median > 0:
        if era3_med > full_median * 2: delta = "RECENT_IMPROVEMENT_SIGNAL"
        elif era3_med < full_median * 0.5 or era3_med < 0: delta = "CURRENT_REGIME_WARNING"
    if m["pf"] >= 1.30 and m["median"] > 0 and ts["yrs_pos"] >= ts["n_yrs"] * 0.75:
        return "WATCH_FOR_DEEP_SCREEN (temporal+Era3)", delta
    return "WATCH (temporal)", delta


def make_runner(spec):
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
            _cache["df"] = df; _cache["sigs"] = sigs
        df = _cache["df"]; sigs = _cache["sigs"]
        mode = spec.get("mode", "both")
        return run_backtest(
            df, sigs, mode=mode, point_value=cfg["point_value"],
            symbol=spec["asset"],
            commission_per_side=base_costs["commission_per_side"] * commission_mult,
            slippage_ticks=int(np.ceil(base_costs["slippage_ticks"] * slippage_mult)),
            tick_size=base_costs["tick_size"],
        )
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
            "rung": rung, "commission_mult": cm, "slippage_mult": sm,
            "n": int(m["n"]), "pf": float(m["pf"]),
            "median": float(m["median"]),
            "win_rate": float(len(wins) / len(res["trades_df"])) if len(res["trades_df"]) > 0 else 0.0,
            "avg_win": float(wins.mean()) if len(wins) > 0 else 0.0,
            "avg_loss": float(losses.mean()) if len(losses) > 0 else 0.0,
        })
    return rows


def find_break_even(rows):
    for i in range(len(rows) - 1):
        if rows[i]["median"] > 0 and rows[i+1]["median"] <= 0:
            return {"between": (rows[i]["rung"], rows[i+1]["rung"])}
    if rows[-1]["median"] > 0:
        return {"between": (rows[-1]["rung"], "beyond")}
    return {"between": ("before baseline", rows[0]["rung"])}


# --- Track A: MNQ directional split diagnostic (#89) ---
MNQ_DIAGNOSTIC_SPECS = [
    {"label": "DIR-MNQ-ORB-Long-PL", "asset": "MNQ", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "long"},
    {"label": "DIR-MNQ-ORB-Short-PL", "asset": "MNQ", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "short"},
]

# --- Track B: PL vs FR2 fragility n+5 extension (#90) ---
FRAGILITY_PAIRS_N5 = [
    # MES — new asset, equity index (paired with cross-asset cousin findings)
    [{"label": "FRAG-MES-ORB-Long-PL", "asset": "MES", "entry": "orb_breakout",
      "filter": "ema_slope", "exit": "profit_ladder", "mode": "long"},
     {"label": "FRAG-MES-ORB-Long-FR2", "asset": "MES", "entry": "orb_breakout",
      "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 2.0}, "mode": "long"}],
    # MYM — symmetric asset; tests fragility on a symmetric-edge case
    [{"label": "FRAG-MYM-ORB-Both-PL", "asset": "MYM", "entry": "orb_breakout",
      "filter": "ema_slope", "exit": "profit_ladder", "mode": "both"},
     {"label": "FRAG-MYM-ORB-Both-FR2", "asset": "MYM", "entry": "orb_breakout",
      "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 2.0}, "mode": "both"}],
    # DC-MGC Long — different entry family on already-tested asset
    [{"label": "FRAG-DC-MGC-Long-PL", "asset": "MGC", "entry": "donchian_breakout",
      "filter": "ema_slope", "exit": "profit_ladder", "mode": "long"},
     {"label": "FRAG-DC-MGC-Long-FR2", "asset": "MGC", "entry": "donchian_breakout",
      "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 2.0}, "mode": "long"}],
    # PDB-MGC-Short — different direction on existing entry family
    [{"label": "FRAG-PDB-MGC-Short-PL", "asset": "MGC", "entry": "prior_day_break",
      "filter": "ema_slope", "exit": "profit_ladder", "mode": "short"},
     {"label": "FRAG-PDB-MGC-Short-FR2", "asset": "MGC", "entry": "prior_day_break",
      "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 2.0}, "mode": "short"}],
    # MGC-ORB-Both — symmetric direction control
    [{"label": "FRAG-MGC-ORB-Both-PL", "asset": "MGC", "entry": "orb_breakout",
      "filter": "ema_slope", "exit": "profit_ladder", "mode": "both"},
     {"label": "FRAG-MGC-ORB-Both-FR2", "asset": "MGC", "entry": "orb_breakout",
      "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 2.0}, "mode": "both"}],
]


# Re-include the prior n=5 results so we can tally n=10
PRIOR_N5_RESULTS = [
    {"pair_label": "MCL-orb-short", "pl_break_even_rung": "2x cost + 2 ticks slip",
     "fr2_break_even_rung": "1.5x cost + 1 tick slip", "delta_rungs": 2, "winner": "PL"},
    {"pair_label": "MGC-orb-short", "pl_break_even_rung": "beyond",
     "fr2_break_even_rung": "beyond", "delta_rungs": 0, "winner": "TIED"},
    {"pair_label": "MGC-orb-long", "pl_break_even_rung": "2x cost + 2 ticks slip",
     "fr2_break_even_rung": "2x cost + 2 ticks slip", "delta_rungs": 0, "winner": "TIED"},
    {"pair_label": "MGC-prior_day_break-long", "pl_break_even_rung": "2x cost + 2 ticks slip",
     "fr2_break_even_rung": "1.5x cost + 1 tick slip", "delta_rungs": 2, "winner": "PL"},
    {"pair_label": "MCL-donchian_breakout-short", "pl_break_even_rung": "1.5x cost + 1 tick slip",
     "fr2_break_even_rung": "1x baseline", "delta_rungs": 1, "winner": "PL"},
]


def family_review_mnq_subset(asset, mode_split, mode_baseline):
    """Compute trade-day overlap and PnL correlation for MNQ directional subset."""
    cfg = ASSETS[asset]
    costs = get_cost_params(asset)
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    sigs = generate_crossbred_signals(
        df, entry_name="orb_breakout", exit_name="profit_ladder",
        filter_name="ema_slope", params={},
    )

    def bt(mode):
        return run_backtest(
            df, sigs, mode=mode, point_value=cfg["point_value"], symbol=asset,
            commission_per_side=costs["commission_per_side"],
            slippage_ticks=costs["slippage_ticks"],
            tick_size=costs["tick_size"],
        )["trades_df"]

    split_trades = bt(mode_split)
    baseline_trades = bt(mode_baseline)

    if split_trades.empty or baseline_trades.empty:
        return None

    days_split = set(pd.to_datetime(split_trades["entry_time"]).dt.date)
    days_baseline = set(pd.to_datetime(baseline_trades["entry_time"]).dt.date)
    overlap = len(days_split & days_baseline)

    daily_split = split_trades.copy()
    daily_split["entry_dt"] = pd.to_datetime(daily_split["entry_time"])
    daily_split["date"] = daily_split["entry_dt"].dt.date
    pnl_split = daily_split.groupby("date")["pnl"].sum()

    daily_baseline = baseline_trades.copy()
    daily_baseline["entry_dt"] = pd.to_datetime(daily_baseline["entry_time"])
    daily_baseline["date"] = daily_baseline["entry_dt"].dt.date
    pnl_baseline = daily_baseline.groupby("date")["pnl"].sum()

    aligned = pd.concat([pnl_split, pnl_baseline], axis=1, keys=["s", "b"]).fillna(0.0)
    corr = float(aligned["s"].corr(aligned["b"]))

    return {
        "split_n_trades": int(len(split_trades)),
        "baseline_n_trades": int(len(baseline_trades)),
        "split_net": float(split_trades["pnl"].sum()),
        "baseline_net": float(baseline_trades["pnl"].sum()),
        "split_pf": float(split_trades[split_trades["pnl"] > 0]["pnl"].sum() /
                          (-split_trades[split_trades["pnl"] < 0]["pnl"].sum()))
                          if (split_trades["pnl"] < 0).any() else float("inf"),
        "split_median": float(np.median(split_trades["pnl"])),
        "n_days_split": len(days_split),
        "n_days_baseline": len(days_baseline),
        "n_days_overlap": overlap,
        "overlap_pct_of_split": overlap / len(days_split) * 100 if days_split else 0.0,
        "daily_pnl_corr": corr,
    }


def run():
    print("Cycle 2026-06-08b — MNQ directional + PL/FR2 n+5", flush=True)
    print(f"Boundaries: report-only Lane B. No registry/portfolio/scheduler/promotion mutation.\n", flush=True)
    print(f"Feature cache: {feature_cache_stats()}\n", flush=True)
    t_start = time.time()

    # --- Track A: MNQ directional split ---
    print(f"--- Track A: MNQ directional split diagnostic ({len(MNQ_DIAGNOSTIC_SPECS)} candidates) ---", flush=True)
    mnq_results = []
    for i, spec in enumerate(MNQ_DIAGNOSTIC_SPECS, 1):
        t0 = time.time()
        try:
            m, ts, v, delta, stress, _ = run_one(spec, stress_on_watch=True)
        except Exception as e:
            print(f"  [{i}] {spec['label']}: ERROR {e}", flush=True)
            mnq_results.append({"spec": spec, "error": str(e)})
            continue
        elapsed = time.time() - t0
        max_yr = m.get("max_year_share_pct", float("nan"))
        n_yrs = ts["n_yrs"] if ts else m.get("n_years", "?")
        yrs_pos = ts["yrs_pos"] if ts else m.get("years_positive", "?")
        era3 = ts["era3_pf"] if ts else float("nan")
        stress_str = f" stress={stress['verdict'].split()[0]}" if stress else ""
        print(
            f"  [{i}] {spec['label']:30s} ({spec['mode']:5s}): n={m['n']:5d} PF={m['pf']:.3f} "
            f"median=${m['median']:7.2f} max-yr={max_yr:.1f}% yrs+={yrs_pos}/{n_yrs} Era3={era3:.2f} → {v}{stress_str} [{elapsed:.0f}s]",
            flush=True
        )
        mnq_results.append({
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

    # Family review for each MNQ subset
    print("\nFamily review: MNQ directional subset vs MNQ-both probation...", flush=True)
    mnq_long_review = family_review_mnq_subset("MNQ", "long", "both")
    mnq_short_review = family_review_mnq_subset("MNQ", "short", "both")
    print(f"  MNQ-long vs MNQ-both: corr={mnq_long_review['daily_pnl_corr']:.3f} day-overlap={mnq_long_review['overlap_pct_of_split']:.1f}%", flush=True)
    print(f"  MNQ-short vs MNQ-both: corr={mnq_short_review['daily_pnl_corr']:.3f} day-overlap={mnq_short_review['overlap_pct_of_split']:.1f}%", flush=True)

    # --- Track B: PL vs FR2 n+5 extension ---
    print(f"\n--- Track B: PL vs FR2 fragility n+5 extension ({len(FRAGILITY_PAIRS_N5)} new pairs) ---", flush=True)
    new_fragility = []
    for j, pair in enumerate(FRAGILITY_PAIRS_N5, 1):
        pl_spec, fr2_spec = pair
        pl_runner = make_runner(pl_spec)
        fr2_runner = make_runner(fr2_spec)
        t0 = time.time()
        try:
            pl_rows = stress_break_even(pl_runner, pl_spec["label"])
            fr2_rows = stress_break_even(fr2_runner, fr2_spec["label"])
        except Exception as e:
            print(f"  [{j}] {pl_spec['asset']}-{pl_spec['mode']}: ERROR {e}", flush=True)
            new_fragility.append({"pair": pair, "error": str(e)})
            continue
        elapsed = time.time() - t0
        pl_be = find_break_even(pl_rows)
        fr2_be = find_break_even(fr2_rows)
        rung_order = ["before baseline", "1x baseline", "1.5x cost + 1 tick slip",
                      "2x cost + 1 tick slip", "2x cost + 2 ticks slip",
                      "4x cost + 2 ticks slip", "beyond"]
        def rung_idx(name):
            try: return rung_order.index(name)
            except ValueError: return -1
        pl_be_rung = pl_be["between"][1]
        fr2_be_rung = fr2_be["between"][1]
        gap_rungs = rung_idx(pl_be_rung) - rung_idx(fr2_be_rung)
        print(
            f"  [{j}] {pl_spec['asset']}-{pl_spec['entry'][:3]}-{pl_spec['mode']:5s}:"
            f" PL PF1x={pl_rows[0]['pf']:.3f} med1x=${pl_rows[0]['median']:6.2f} BE@{pl_be_rung[:18]:<18s}"
            f" || FR2 PF1x={fr2_rows[0]['pf']:.3f} med1x=${fr2_rows[0]['median']:6.2f} BE@{fr2_be_rung[:18]:<18s}"
            f" Δrungs={gap_rungs} [{elapsed:.0f}s]",
            flush=True
        )
        new_fragility.append({
            "pair_label": f"{pl_spec['asset']}-{pl_spec['entry']}-{pl_spec['mode']}",
            "pl_spec": pl_spec, "fr2_spec": fr2_spec,
            "pl_rows": pl_rows, "fr2_rows": fr2_rows,
            "pl_break_even_rung": pl_be["between"][1],
            "fr2_break_even_rung": fr2_be["between"][1],
            "rung_gap_pl_vs_fr2": gap_rungs,
            "winner": "PL" if gap_rungs > 0 else ("FR2" if gap_rungs < 0 else "TIED"),
            "elapsed_seconds": elapsed,
        })

    total = time.time() - t_start
    print(f"\nTotal: {total:.0f}s. Feature cache: {feature_cache_stats()}", flush=True)

    # Aggregate n=10 fragility tally
    all_pairs = PRIOR_N5_RESULTS + [
        {"pair_label": r["pair_label"],
         "pl_break_even_rung": r["pl_break_even_rung"],
         "fr2_break_even_rung": r["fr2_break_even_rung"],
         "delta_rungs": r["rung_gap_pl_vs_fr2"],
         "winner": r["winner"]}
        for r in new_fragility if "error" not in r
    ]
    pl_wins = sum(1 for r in all_pairs if r["winner"] == "PL")
    fr2_wins = sum(1 for r in all_pairs if r["winner"] == "FR2")
    ties = sum(1 for r in all_pairs if r["winner"] == "TIED")
    pl_or_tied = pl_wins + ties
    print(f"\nAGGREGATE n={len(all_pairs)}: PL_wins={pl_wins}, FR2_wins={fr2_wins}, TIED={ties}, PL_or_tied={pl_or_tied}/{len(all_pairs)}", flush=True)

    codify = (pl_or_tied >= 8 and fr2_wins == 0)
    print(f"\nCODIFICATION DECISION: {'CODIFY (PL≥8 with no FR2 wins)' if codify else 'DO NOT CODIFY (threshold not met)'}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-08b.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "approvals": "OK run MNQ (#89), OK n+5 (#90)",
        "boundaries": "report-only Lane B; no registry/portfolio/scheduler/promotion mutation",
        "track_A_mnq_diagnostic": {
            "results": mnq_results,
            "mnq_long_vs_both_family_review": mnq_long_review,
            "mnq_short_vs_both_family_review": mnq_short_review,
            "classification": "DIRECTIONAL_INSIGHT_DIAGNOSTIC_ONLY (per #89; subsets of existing probation)",
        },
        "track_B_fragility_n_extended": {
            "prior_n5": PRIOR_N5_RESULTS,
            "new_n5": new_fragility,
            "all_pairs_summary": all_pairs,
            "pl_wins": pl_wins,
            "fr2_wins": fr2_wins,
            "ties": ties,
            "pl_or_tied_of_n": f"{pl_or_tied}/{len(all_pairs)}",
            "codify": codify,
            "codification_rule": "≥8 PL_or_tied AND 0 FR2_wins → codify",
        },
        "feature_cache_stats_final": feature_cache_stats(),
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
