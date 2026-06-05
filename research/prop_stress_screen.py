"""Prop-firm stress screen — early filter for WATCH candidates.

Per operator approval 2026-06-04 (#67). Minimum viable stress ladder:
  - baseline cost
  - 2x cost + 1 tick slip
  - 2x cost + 2 ticks slip
  - 4x cost + 2 ticks slip

Hard rule: if median collapses to near-zero (< $1) under moderate stress
(2x cost + 2 tick slip), candidate cannot be packet-grade. May be kept as
OBSERVATIONAL if portfolio contribution strong, but NOT escalated.

Reusable module — pass any candidate-runner callable to `prop_stress_screen()`.
Authority: T1 / Lane B / report-only.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def prop_stress_screen(
    runner: Callable,
    label: str = "candidate",
    median_collapse_threshold: float = 1.0,
) -> dict:
    """Run a stress ladder on a candidate.

    `runner` must be a callable that accepts (commission_mult, slippage_mult)
    and returns a dict with at minimum the keys `trades_df` and `stats` (cost
    block). See `engine.backtest.run_backtest` return shape.

    Returns
    -------
    dict with `rows` (per-stress metrics), `verdict` (`PASS_STRESS` /
    `KNIFE_EDGE` / `FAIL_STRESS`), and `headline_reason`.
    """
    from research.fql_forge_batch_runner import _metrics

    ladder = [
        ("baseline (1x)", 1.0, 1.0),
        ("2x cost + 1 tick slip", 2.0, 2.0),
        ("2x cost + 2 ticks slip", 2.0, 3.0),
        ("4x cost + 2 ticks slip", 4.0, 3.0),
    ]
    rows = []
    for stress_label, cm, sm in ladder:
        res = runner(cm, sm)
        m = _metrics(res["trades_df"], f"{label}-{stress_label}",
                     costs=res["stats"]["costs"])
        rows.append({
            "stress": stress_label,
            "commission_mult": cm,
            "slippage_mult": sm,
            "n": int(m["n"]),
            "pf": float(m["pf"]),
            "net_median": float(m["median"]),
            "net_pnl": float(m["net"]),
            "max_dd": float(m["max_dd"]),
        })
    moderate = next(r for r in rows if r["stress"] == "2x cost + 2 ticks slip")
    extreme = next(r for r in rows if r["stress"] == "4x cost + 2 ticks slip")
    # Hard rule
    if moderate["net_median"] <= 0:
        verdict = "FAIL_STRESS (median ≤ 0 at 2x cost + 2 ticks)"
        reason = f"At 2x cost + 2 ticks slip: median ${moderate['net_median']:.2f} (≤ 0)"
    elif moderate["net_median"] < median_collapse_threshold:
        verdict = "KNIFE_EDGE (median collapses near 0 at moderate stress)"
        reason = (
            f"At 2x cost + 2 ticks slip: median ${moderate['net_median']:.2f} "
            f"(< ${median_collapse_threshold:.2f} threshold)"
        )
    elif extreme["net_median"] <= 0:
        verdict = "KNIFE_EDGE (passes moderate but fails 4x stress)"
        reason = f"At 4x cost + 2 ticks: median ${extreme['net_median']:.2f}"
    else:
        verdict = "PASS_STRESS"
        reason = (
            f"Survives 4x cost + 2 ticks: median ${extreme['net_median']:.2f}, "
            f"PF {extreme['pf']:.3f}"
        )
    return {
        "label": label,
        "rows": rows,
        "verdict": verdict,
        "headline_reason": reason,
        "moderate_median": moderate["net_median"],
        "extreme_median": extreme["net_median"],
    }
