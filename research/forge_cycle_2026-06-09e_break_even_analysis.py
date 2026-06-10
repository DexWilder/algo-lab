"""Cycle 2026-06-09e — Break-even cost analysis on OBSERVATIONAL inventory.

Per no-idle rule + cost-fragility hypothesis (5/5 new primitives = ARCHIVED).
Instead of building another speculative primitive, produce actionable data:
for each cost-sensitive OBSERVATIONAL candidate with positive baseline median,
find the EXACT break-even round-trip cost. Rank by cost-sensitivity.

This directly informs operator's prop-cost rate sheet decision: shows
which candidates would unlock at which verified RT cost.

Authority: Lane B research-only. NO asset_config changes. NO cost
assumption changes. Operator-verified data still required for any
asset_config update.
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
    generate_crossbred_signals,
)
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def make_runner(spec):
    """Runner that caches signal generation; re-runs backtest on cost change."""
    _cache = {}
    def runner(commission_per_side, slippage_ticks):
        cfg = ASSETS[spec["asset"]]
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
            commission_per_side=commission_per_side,
            slippage_ticks=slippage_ticks,
            tick_size=ASSETS[spec["asset"]]["tick_size"],
        )
    return runner


def rt_cost_dollar(commission_per_side, slippage_ticks, tick_value_dollar):
    """Round-trip cost in dollars."""
    return 2 * (commission_per_side + slippage_ticks * tick_value_dollar)


def find_break_even_rt(spec):
    """Sweep cost levels to find exact break-even RT cost (where median → 0).

    Method: binary search on commission_per_side with slippage_ticks held at
    base value (1 or 2 per asset). Returns the RT cost at which median trade
    crosses zero, along with key reference points.
    """
    cfg = ASSETS[spec["asset"]]
    tick_value = cfg["tick_size"] * cfg["point_value"]
    base_costs = get_cost_params(spec["asset"])
    runner = make_runner(spec)

    # Sample at multiple stress rungs to characterize curve
    samples = []
    for cost_mult in [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0]:
        comm = base_costs["commission_per_side"] * cost_mult
        slip = base_costs["slippage_ticks"]  # hold slip constant at base
        res = runner(comm, slip)
        m = _metrics(res["trades_df"], f"{spec['label']}-{cost_mult}x",
                     costs=res["stats"]["costs"])
        rt = rt_cost_dollar(comm, slip, tick_value)
        samples.append({
            "cost_mult": cost_mult,
            "commission_per_side": float(comm),
            "slippage_ticks": int(slip),
            "rt_cost_dollar": rt,
            "n": int(m["n"]),
            "pf": float(m["pf"]) if np.isfinite(m["pf"]) else None,
            "median": float(m["median"]),
            "net": float(m["net"]),
        })

    # Find break-even by interpolation between adjacent samples
    break_even_rt = None
    break_even_cost_mult = None
    for i in range(len(samples) - 1):
        if samples[i]["median"] > 0 and samples[i+1]["median"] <= 0:
            # Linear interp
            x0, x1 = samples[i]["rt_cost_dollar"], samples[i+1]["rt_cost_dollar"]
            y0, y1 = samples[i]["median"], samples[i+1]["median"]
            # y = y0 + (y1-y0)/(x1-x0) * (x - x0) = 0 → x = x0 - y0*(x1-x0)/(y1-y0)
            if y1 != y0:
                break_even_rt = x0 - y0 * (x1 - x0) / (y1 - y0)
            else:
                break_even_rt = (x0 + x1) / 2
            # Same interp on cost_mult
            x0m, x1m = samples[i]["cost_mult"], samples[i+1]["cost_mult"]
            if y1 != y0:
                break_even_cost_mult = x0m - y0 * (x1m - x0m) / (y1 - y0)
            else:
                break_even_cost_mult = (x0m + x1m) / 2
            break

    return {
        "spec": spec,
        "base_rt_cost_dollar": rt_cost_dollar(
            base_costs["commission_per_side"], base_costs["slippage_ticks"],
            tick_value),
        "base_median": next(s["median"] for s in samples if s["cost_mult"] == 1.0),
        "base_pf": next(s["pf"] for s in samples if s["cost_mult"] == 1.0),
        "base_n": next(s["n"] for s in samples if s["cost_mult"] == 1.0),
        "break_even_rt_dollar": break_even_rt,
        "break_even_cost_mult": break_even_cost_mult,
        "samples": samples,
    }


# OBSERVATIONAL candidates worth break-even analysis
# Each must have a positive baseline median (otherwise no break-even exists)
CANDIDATES = [
    # MCL probation siblings (REPLACEMENT_CANDIDATE_LIKELY pending prop-cost #85)
    {"label": "MCL-Short-PL (XB-ORB)", "asset": "MCL", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "short"},
    {"label": "MCL-Short-FR2 (XB-ORB)", "asset": "MCL", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "fixed_ratio",
     "params": {"ratio": 2.0}, "mode": "short"},

    # BB-Keltner-MNQ (best cost-sensitive near-miss from 5-mechanism scoreboard)
    {"label": "BBKC-MNQ-Both-PL", "asset": "MNQ", "entry": "bb_keltner_squeeze",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "both"},

    # RCB-MES-Both-PL (compression on MES)
    {"label": "RCB-MES-Both-PL", "asset": "MES", "entry": "range_compression_break",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "both"},

    # RCB-MGC-Both-PL (compression on MGC)
    {"label": "RCB-MGC-Both-PL", "asset": "MGC", "entry": "range_compression_break",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "both"},

    # RCB15-MES-Both-PL (tighter compression — improved median)
    {"label": "RCB15-MES-Both-PL", "asset": "MES", "entry": "range_compression_break",
     "filter": "ema_slope", "exit": "profit_ladder",
     "params": {"compression_pct_max": 15}, "mode": "both"},

    # MES PORTFOLIO_COMPLEMENT candidates (PASS_STRESS but family overlap)
    {"label": "DIR-MES-ORB-Short-PL", "asset": "MES", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "short"},
    {"label": "DIR-MES-ORB-Long-PL", "asset": "MES", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "long"},
]


def run():
    print(f"Cycle 2026-06-09e — Break-even cost analysis on OBSERVATIONAL inventory", flush=True)
    print(f"Per no-idle rule + 5/5 new-primitive scoreboard. Producing actionable cost-sensitivity data.", flush=True)
    print(f"Boundaries: report-only Lane B. NO asset_config change. NO cost-assumption change.\n", flush=True)
    t_start = time.time()
    results = []
    for i, spec in enumerate(CANDIDATES, 1):
        t0 = time.time()
        try:
            res = find_break_even_rt(spec)
        except Exception as e:
            print(f"  [{i}] {spec['label']}: ERROR {e}", flush=True)
            results.append({"spec": spec, "error": str(e)})
            continue
        elapsed = time.time() - t0
        base_rt = res["base_rt_cost_dollar"]
        base_med = res["base_median"]
        be_rt = res["break_even_rt_dollar"]
        be_mult = res["break_even_cost_mult"]
        be_str = (f"${be_rt:.2f} RT (mult {be_mult:.2f}x)"
                  if be_rt is not None else "beyond test range")
        print(
            f"  [{i}] {spec['label']:32s}: base RT ${base_rt:.2f}, "
            f"base med=${base_med:7.2f}, BE RT={be_str} [{elapsed:.0f}s]",
            flush=True
        )
        results.append(res)
    total = time.time() - t_start
    print(f"\nTotal: {total:.0f}s", flush=True)

    # Build cost-sensitivity ranking
    ranked = []
    for r in results:
        if "error" in r: continue
        be = r["break_even_rt_dollar"]
        base_rt = r["base_rt_cost_dollar"]
        if be is None:
            margin = float("inf")
        else:
            margin = be - base_rt
        ranked.append((margin, r))
    ranked.sort(key=lambda x: x[0])

    print("\n=== Cost-sensitivity ranking (smaller margin = more cost-sensitive) ===", flush=True)
    for margin, r in ranked:
        margin_str = f"${margin:.2f}" if margin != float("inf") else "beyond test"
        be = r["break_even_rt_dollar"]
        be_str = f"${be:.2f}" if be is not None else "beyond"
        print(
            f"  {r['spec']['label']:32s}: base ${r['base_rt_cost_dollar']:.2f} RT, "
            f"BE {be_str}, margin {margin_str}",
            flush=True
        )

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-09e_break_even_analysis.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "Break-even cost analysis on OBSERVATIONAL inventory (cost-fragility hypothesis empirical mapping)",
        "boundaries": "report-only Lane B; no asset_config change; no cost-assumption change",
        "method": "Sweep commission multiplier 0.25x-4.0x at base slippage; linear interp between adjacent samples to find median=0",
        "results": results,
        "cost_sensitivity_ranking": [
            {"margin_dollar": (m if m != float('inf') else None),
             "label": r["spec"]["label"],
             "base_rt": r["base_rt_cost_dollar"],
             "break_even_rt": r["break_even_rt_dollar"]}
            for m, r in ranked
        ],
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
