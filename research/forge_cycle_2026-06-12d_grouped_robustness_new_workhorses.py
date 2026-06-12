"""Cycle 2026-06-12d — Grouped robustness on 2 new workhorse candidates.

Per operator #187: after #6 completes, run robustness on new
PAPER_PACKET_CANDIDATEs as a grouped pass.

Candidates:
  1. WH-MNQ-orb_failure_reversal (mean-reversion)
  2. WH-MNQ-first_impulse_pullback (trend continuation)

Same workhorse robustness suite as cycle 11r:
  - year exclusion (leave-one-year-out)
  - era split
  - Era 3 PF/median
  - remove largest win / loss
  - rolling 60-trade block PF
  - max-year / max-month / max-week share
  - stress cost/slippage ladder
  - day-of-week dependence
  - time-of-day dependence

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


def _pf(pnl):
    arr = np.asarray(pnl)
    w = arr[arr > 0].sum(); l = -arr[arr < 0].sum()
    return float(w / l) if l > 0 else float("inf")


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


def robustness_check(asset, entry, label):
    print(f"\n=== ROBUSTNESS: {label} ===", flush=True)
    m, trades = _run(asset, entry, "profit_ladder", "ema_slope", label)
    trades = trades.copy()
    trades["entry_dt"] = pd.to_datetime(trades["entry_time"])
    trades["year"] = trades["entry_dt"].dt.year
    trades["month"] = trades["entry_dt"].dt.to_period("M")
    trades["week"] = trades["entry_dt"].dt.to_period("W")
    trades["dow"] = trades["entry_dt"].dt.day_name()
    trades["hour"] = trades["entry_dt"].dt.hour
    net = float(trades["pnl"].sum())
    print(f"  Baseline: n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f} net=${net:.0f}", flush=True)

    # Year-excl
    yr_excl = {}
    for y in sorted(trades["year"].unique()):
        sub = trades[trades["year"] != y]
        yr_excl[int(y)] = {"pf": _pf(sub["pnl"]), "median": float(np.median(sub["pnl"]))}
    yr_pfs = [v["pf"] for v in yr_excl.values()]
    print(f"  Year-excl PF range: [{min(yr_pfs):.3f}, {max(yr_pfs):.3f}]", flush=True)

    # Eras
    sorted_t = trades.sort_values("entry_dt").reset_index(drop=True)
    cuts = np.linspace(0, len(sorted_t), 4).astype(int)
    eras = []
    for i in range(3):
        sub = sorted_t.iloc[cuts[i]:cuts[i+1]]
        pnl = sub["pnl"].values
        eras.append({"era": i+1, "n": len(sub), "pf": _pf(pnl),
                     "median": float(np.median(pnl)), "net": float(pnl.sum())})
    for e in eras:
        print(f"  Era {e['era']}: n={e['n']} PF={e['pf']:.3f} median=${e['median']:.2f} net=${e['net']:.0f}", flush=True)

    # Largest event removal
    max_idx = trades["pnl"].idxmax(); min_idx = trades["pnl"].idxmin()
    max_pnl = trades.loc[max_idx, "pnl"]; min_pnl = trades.loc[min_idx, "pnl"]
    pf_no_max = _pf(trades[trades.index != max_idx]["pnl"].values)
    pf_no_min = _pf(trades[trades.index != min_idx]["pnl"].values)
    max_event_abs_share = max(abs(max_pnl), abs(min_pnl)) / net * 100 if net != 0 else 0
    max_is_loss = abs(min_pnl) > abs(max_pnl)
    print(f"  Largest win ${max_pnl:+.2f} → remove PF {pf_no_max:.3f}", flush=True)
    print(f"  Largest loss ${min_pnl:+.2f} → remove PF {pf_no_min:.3f}", flush=True)
    print(f"  Max abs event share: {max_event_abs_share:.1f}% (max is {'LOSS' if max_is_loss else 'WIN'})", flush=True)

    # Rolling blocks
    block_size = 60
    n_blocks = len(sorted_t) // block_size
    block_pfs = [_pf(sorted_t.iloc[i*block_size:(i+1)*block_size]["pnl"].values) for i in range(n_blocks)]
    block_pfs_arr = np.array([p for p in block_pfs if not np.isinf(p)])
    pct_pos = float((block_pfs_arr > 1.0).mean() * 100) if len(block_pfs_arr) else 0
    pct_strong = float((block_pfs_arr > 1.2).mean() * 100) if len(block_pfs_arr) else 0
    print(f"  Rolling 60-block: {n_blocks} blocks, {pct_pos:.0f}% > 1.0, {pct_strong:.0f}% > 1.2", flush=True)

    # Concentration
    per_year_net = trades.groupby("year")["pnl"].sum()
    max_yr = float(per_year_net.abs().max() / net * 100) if net != 0 else 0
    per_month_net = trades.groupby("month")["pnl"].sum()
    max_mo = float(per_month_net.abs().max() / net * 100) if net != 0 else 0
    per_week_net = trades.groupby("week")["pnl"].sum()
    max_wk = float(per_week_net.abs().max() / net * 100) if net != 0 else 0
    print(f"  Max-yr/mo/wk share: {max_yr:.1f}% / {max_mo:.1f}% / {max_wk:.1f}%", flush=True)

    # Day-of-week
    dow_pfs = {d: _pf(g["pnl"].values) for d, g in trades.groupby("dow")}
    print(f"  Day-of-week: {{{', '.join(f'{d[:3]}={pf:.2f}' for d, pf in sorted(dow_pfs.items()))}}}", flush=True)

    # Time-of-day
    tod_pfs = {int(h): _pf(g["pnl"].values) for h, g in trades.groupby("hour")}
    tod_parts = [f"{h}h={pf:.2f}" for h, pf in sorted(tod_pfs.items())[:8]]
    print(f"  Time-of-day: {', '.join(tod_parts)}", flush=True)

    # Stress ladder
    cost_sens = []
    for cm, sm, lab in [(1.0, 1.0, "1x"), (1.5, 2.0, "1.5x+1t"), (2.0, 3.0, "2x+2t"),
                          (3.0, 3.0, "3x+2t"), (4.0, 4.0, "4x+3t"), (5.0, 5.0, "5x+4t")]:
        m_s, _ = _run(asset, entry, "profit_ladder", "ema_slope", f"{label}-stress",
                       cost_mult=cm, slip_mult=sm)
        cost_sens.append({"label": lab, "pf": float(m_s["pf"]), "median": float(m_s["median"])})
    print(f"  Stress: " + " | ".join(f"{c['label']}: PF {c['pf']:.3f} med ${c['median']:.2f}" for c in cost_sens), flush=True)

    # Robustness checks (mirroring stop_run pattern)
    rob_checks = {
        "year_excl_min_PF_>=_1.2": min(yr_pfs) >= 1.2,
        "Era3_PF_>=_1.0": eras[2]["pf"] >= 1.0,
        "Era3_median_>=_0": eras[2]["median"] >= 0,
        "rolling_blocks_>1.0_PF_>_60%": pct_pos > 60,
        "remove_largest_win_PF_>_1.15": pf_no_max >= 1.15,
        "remove_largest_loss_PF_>_1.15": pf_no_min >= 1.15,
        "max_yr_share_<=_50": max_yr <= 50,
        "max_event_share_<=_15_or_LOSS_TAIL_ABSORPTION":
            max_event_abs_share <= 15 or (max_is_loss and pf_no_min > m["pf"]),
        "stress_2x+2t_median_>_0": cost_sens[2]["median"] > 0,
        "stress_5x+4t_PF_>_0.8": cost_sens[5]["pf"] > 0.8,
    }
    all_pass = all(rob_checks.values())
    print(f"  Robustness: {rob_checks}", flush=True)
    if all_pass:
        verdict = "ROBUSTNESS GREEN"
    elif max_is_loss and not (max_event_abs_share <= 15) and pf_no_min > m["pf"] and sum(rob_checks.values()) >= 9:
        verdict = "PASS_WITH_LOSS_TAIL_WARN"
    else:
        failed = [k for k, v in rob_checks.items() if not v]
        verdict = f"ROBUSTNESS PARTIAL — failed: {failed}"
    print(f"  Verdict: {verdict}", flush=True)

    return {
        "label": label, "asset": asset, "entry": entry,
        "baseline": {"n": int(m["n"]), "pf": float(m["pf"]),
                     "median": float(m["median"]), "net": net},
        "year_excl_pf_range": [min(yr_pfs), max(yr_pfs)],
        "eras": eras,
        "largest_event": {"max_pnl": float(max_pnl), "min_pnl": float(min_pnl),
                          "pf_no_max": pf_no_max, "pf_no_min": pf_no_min,
                          "max_event_abs_share_pct": max_event_abs_share,
                          "max_is_loss": bool(max_is_loss)},
        "rolling_blocks": {"n": n_blocks, "pct_>_1.0": pct_pos, "pct_>_1.2": pct_strong},
        "concentration": {"max_yr": max_yr, "max_month": max_mo, "max_week": max_wk},
        "day_of_week": {d: float(p) for d, p in dow_pfs.items()},
        "time_of_day": {str(h): float(p) for h, p in tod_pfs.items()},
        "stress_ladder": cost_sens,
        "robustness_checks": rob_checks,
        "all_pass": all_pass,
        "verdict": verdict,
    }


def run():
    print("Cycle 2026-06-12d — Grouped robustness on 2 new workhorse candidates\n", flush=True)
    t_start = time.time()
    rob_orb_fail = robustness_check("MNQ", "orb_failure_reversal", "WH-MNQ-orb_failure_reversal")
    rob_fip = robustness_check("MNQ", "first_impulse_pullback", "WH-MNQ-first_impulse_pullback")
    print(f"\nTotal: {time.time() - t_start:.0f}s", flush=True)

    print(f"\n=== Summary ===", flush=True)
    print(f"  orb_failure_reversal: {rob_orb_fail['verdict']}", flush=True)
    print(f"  first_impulse_pullback: {rob_fip['verdict']}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-12d_grouped_robustness.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "Grouped robustness on orb_failure_reversal + first_impulse_pullback per #187",
        "orb_failure_reversal": rob_orb_fail,
        "first_impulse_pullback": rob_fip,
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
