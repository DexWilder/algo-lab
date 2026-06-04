"""Temporal-split mutation for XB-BB-EMA-Ladder-MGC.

Per operator approval 2026-06-03: both filter axes (session, vol-regime) have
empirically failed to repair the candidate's 95%+ max-year concentration.
Pivoting to year-axis robustness diagnostics.

Three tests:
1. Year-exclusion: re-run with each calendar year removed; report PF/median/n.
   Identify the "dominant year" — the one whose removal collapses the edge.
2. Rolling-window robustness: trailing 252-day (≈ 12mo) and 504-day (≈ 24mo)
   rolling PF. Worst window, percent windows PF > 1.0, percent > 1.2.
3. Era-split: first-third / middle-third / final-third PF + median + n.

Classification:
- Edge disappears after removing one dominant year → KILL or ARCHITECTURAL_REJECT
- PF > 1.2 & median > 0 & rolling-window acceptable → WATCH_FOR_DEEP_SCREEN
- Partial robustness but concentration remains high → RETEST_WITH_YEAR_GATE
  (only if year-gate is defensible, not curve-fit)

Authority: T1 / Lane B / report-only. No registry mutation, no Lane A touch.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.crossbreeding.crossbreeding_engine import (  # noqa: E402
    generate_crossbred_signals,
)
from engine.backtest import run_backtest  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402


def _baseline_trades(asset="MGC"):
    """Run XB-BB-EMA-Ladder baseline; return trades_df + stats."""
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"])
    cfg = ASSETS[asset]
    sigs = generate_crossbred_signals(
        df, entry_name="bb_reversion", exit_name="profit_ladder",
        filter_name="ema_slope", params={},
    )
    res = run_backtest(df, sigs, mode="both",
                       point_value=cfg["point_value"], symbol=asset)
    trades = res["trades_df"].copy()
    # Trade date for grouping — use entry_time
    if "entry_time" in trades.columns:
        trades["entry_dt"] = pd.to_datetime(trades["entry_time"])
        trades["year"] = trades["entry_dt"].dt.year
        trades["date"] = trades["entry_dt"].dt.date
    return df, trades, res["stats"]["costs"]


def _trade_summary(trades: pd.DataFrame) -> dict:
    if trades is None or len(trades) == 0:
        return {"n": 0, "pf": float("nan"), "median": float("nan"),
                "net": 0.0, "max_dd": 0.0}
    pnl = trades["pnl"].values
    wins = pnl[pnl > 0].sum()
    losses = -pnl[pnl < 0].sum()
    pf = wins / losses if losses > 0 else float("inf")
    eq = np.cumsum(pnl)
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak).min() if len(eq) else 0.0
    return {
        "n": int(len(trades)),
        "pf": float(pf),
        "median": float(np.median(pnl)),
        "net": float(pnl.sum()),
        "max_dd": float(dd),
        "win_rate_pct": float((pnl > 0).mean() * 100),
    }


def year_exclusion(trades: pd.DataFrame):
    """Run baseline with each year excluded; report changes."""
    base = _trade_summary(trades)
    yrs = sorted(trades["year"].unique())
    rows = []
    for y in yrs:
        sub = trades[trades["year"] != y]
        s = _trade_summary(sub)
        s["excluded_year"] = int(y)
        s["pf_delta"] = float(s["pf"] - base["pf"]) if np.isfinite(base["pf"]) else float("nan")
        s["net_delta"] = float(s["net"] - base["net"])
        rows.append(s)
    return {"baseline": base, "exclusions": rows, "years": yrs}


def per_year(trades: pd.DataFrame):
    """Per-year PnL breakdown."""
    rows = []
    for y, g in trades.groupby("year"):
        s = _trade_summary(g)
        s["year"] = int(y)
        rows.append(s)
    return rows


def rolling_window(trades: pd.DataFrame, window_days_list=(252, 504)):
    """Trailing-N-day rolling PF; report worst window + % windows PF > 1 / > 1.2."""
    if len(trades) == 0:
        return []
    trades = trades.sort_values("entry_dt").copy()
    out = []
    for w in window_days_list:
        rolling_pfs = []
        for i in range(len(trades)):
            end = trades.iloc[i]["entry_dt"]
            start = end - pd.Timedelta(days=w)
            window = trades[(trades["entry_dt"] > start) & (trades["entry_dt"] <= end)]
            s = _trade_summary(window)
            if s["n"] >= 20:  # only count windows with ≥ 20 trades
                rolling_pfs.append(s["pf"])
        if not rolling_pfs:
            out.append({"window_days": w, "samples": 0})
            continue
        rp = np.array(rolling_pfs, dtype=float)
        rp = rp[np.isfinite(rp)]
        out.append({
            "window_days": w,
            "samples": int(len(rp)),
            "worst_pf": float(rp.min()),
            "median_pf": float(np.median(rp)),
            "best_pf": float(rp.max()),
            "pct_pf_gt_1": float((rp > 1.0).mean() * 100),
            "pct_pf_gt_1p2": float((rp > 1.2).mean() * 100),
        })
    return out


def era_split(trades: pd.DataFrame, n_eras=3):
    """Split trades into N equal-trade-count eras and report each."""
    if len(trades) == 0:
        return []
    trades = trades.sort_values("entry_dt").reset_index(drop=True)
    cuts = np.linspace(0, len(trades), n_eras + 1).astype(int)
    rows = []
    for i in range(n_eras):
        sub = trades.iloc[cuts[i]:cuts[i+1]]
        if len(sub) == 0:
            continue
        s = _trade_summary(sub)
        s["era"] = i + 1
        s["start"] = str(sub.iloc[0]["entry_dt"])
        s["end"] = str(sub.iloc[-1]["entry_dt"])
        rows.append(s)
    return rows


def classify(base: dict, year_excl: dict, rolling: list, eras: list) -> tuple[str, list[str]]:
    """Apply the operator-approved classification rules."""
    tags = []
    notes = []

    # Identify dominant year via single-year exclusion: which exclusion drops PF most?
    if year_excl["exclusions"]:
        worst_exclusion = min(year_excl["exclusions"], key=lambda r: r["pf"] if np.isfinite(r["pf"]) else 1e9)
        notes.append(
            f"Worst single-year exclusion = {worst_exclusion['excluded_year']} → PF drops to {worst_exclusion['pf']:.3f}"
        )
        if not np.isfinite(worst_exclusion["pf"]):
            notes.append("PF inf — likely all-losers when dominant year removed")
        if worst_exclusion["pf"] < 1.0:
            tags.append("dominant-year-carries-edge")

    # Rolling-window robustness
    rw_12mo = next((r for r in rolling if r.get("window_days") == 252), None)
    if rw_12mo and rw_12mo.get("samples", 0) > 0:
        if rw_12mo["pct_pf_gt_1p2"] < 30:
            tags.append("rolling-window-fail")
            notes.append(f"12mo rolling PF > 1.2 only {rw_12mo['pct_pf_gt_1p2']:.0f}% of windows")
        else:
            notes.append(f"12mo rolling PF > 1.2 in {rw_12mo['pct_pf_gt_1p2']:.0f}% of windows")

    # Era split — any era's PF below 1.0?
    if eras and any(e["pf"] < 1.0 for e in eras if np.isfinite(e["pf"])):
        tags.append("era-split-fail")
        notes.append("at least one third of the sample is unprofitable")

    # Classify
    if "dominant-year-carries-edge" in tags:
        verdict = "KILL / ARCHITECTURAL_REJECT"
    elif base["pf"] > 1.2 and base["median"] > 0 and "rolling-window-fail" not in tags and "era-split-fail" not in tags:
        verdict = "WATCH_FOR_DEEP_SCREEN"
    elif any(t == "rolling-window-fail" for t in tags) or any(t == "era-split-fail" for t in tags):
        # Partial robustness — RETEST_WITH_YEAR_GATE only if defensible
        verdict = "RETEST_WITH_YEAR_GATE"
        notes.append("year gate would need defensibility check before any registry surface")
    else:
        verdict = "WATCH (mixed signal)"
    return verdict, notes


def run():
    print("Loading baseline XB-BB-EMA-Ladder-MGC trades...")
    df, trades, costs = _baseline_trades("MGC")
    print(f"  n_trades = {len(trades)}")

    base_summary = _trade_summary(trades)
    print(f"  baseline: n={base_summary['n']} PF={base_summary['pf']:.3f} median=${base_summary['median']:.2f} netPnL=${base_summary['net']:.0f}")

    print("\nPer-year breakdown:")
    pyr = per_year(trades)
    for r in pyr:
        print(f"  {r['year']}: n={r['n']:3d} PF={r['pf']:.3f} median=${r['median']:.2f} net=${r['net']:7.0f}")

    print("\nYear-exclusion:")
    ye = year_exclusion(trades)
    for r in ye["exclusions"]:
        pf_str = f"{r['pf']:.3f}" if np.isfinite(r['pf']) else "inf"
        print(f"  exclude {r['excluded_year']}: n={r['n']:3d} PF={pf_str} median=${r['median']:.2f} netΔ=${r['net_delta']:+8.0f}")

    print("\nRolling-window robustness:")
    rw = rolling_window(trades, (252, 504))
    for r in rw:
        if r.get("samples", 0) == 0:
            print(f"  window {r['window_days']}d: insufficient samples")
            continue
        print(f"  window {r['window_days']}d: samples={r['samples']:4d} worst PF={r['worst_pf']:.3f} median PF={r['median_pf']:.3f} pct PF>1.0={r['pct_pf_gt_1']:.0f}% pct PF>1.2={r['pct_pf_gt_1p2']:.0f}%")

    print("\nEra split (3 equal-trade-count thirds):")
    es = era_split(trades, 3)
    for r in es:
        print(f"  era {r['era']} ({r['start'][:10]} → {r['end'][:10]}): n={r['n']:3d} PF={r['pf']:.3f} median=${r['median']:.2f}")

    verdict, notes = classify(base_summary, ye, rw, es)
    print(f"\nFinal classification: **{verdict}**")
    for n in notes:
        print(f"  - {n}")

    out_dir = ROOT / "research" / "data" / "fql_forge" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_iso = date.today().isoformat()
    json_path = out_dir / f"forge_xb_bb_mgc_temporal_split_{date_iso}.json"
    md_path = out_dir / f"forge_xb_bb_mgc_temporal_split_{date_iso}.md"

    payload = {
        "date": date_iso,
        "candidate": "XB-BB-EMA-Ladder-MGC",
        "harness": "research/forge_xb_bb_mgc_temporal_split.py",
        "baseline": base_summary,
        "per_year": pyr,
        "year_exclusion": ye,
        "rolling_window": rw,
        "era_split": es,
        "verdict": verdict,
        "notes": notes,
        "cost_block": costs,
    }
    json_path.write_text(json.dumps(payload, indent=2, default=str))

    md_lines = [
        f"# Temporal-Split Mutation — XB-BB-EMA-Ladder-MGC",
        f"\n**Date:** {date_iso} • Authority: T1 / report-only / Lane B\n",
        f"## Baseline\n",
        f"- n = {base_summary['n']}",
        f"- PF = {base_summary['pf']:.3f}",
        f"- median = ${base_summary['median']:.2f}",
        f"- net = ${base_summary['net']:.0f}",
        f"- max DD = ${base_summary['max_dd']:.0f}",
        f"\n## Per-year breakdown\n",
        "| Year | n | PF | Median | Net |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in pyr:
        md_lines.append(f"| {r['year']} | {r['n']} | {r['pf']:.3f} | ${r['median']:.2f} | ${r['net']:.0f} |")
    md_lines += [f"\n## Year exclusion\n",
                 "| Excluded | n | PF | Median | Δ net |",
                 "|---|---:|---:|---:|---:|"]
    for r in ye["exclusions"]:
        pf_str = f"{r['pf']:.3f}" if np.isfinite(r['pf']) else "inf"
        md_lines.append(f"| {r['excluded_year']} | {r['n']} | {pf_str} | ${r['median']:.2f} | ${r['net_delta']:+.0f} |")
    md_lines += [f"\n## Rolling-window robustness\n",
                 "| Window | Samples | Worst PF | Median PF | % > 1.0 | % > 1.2 |",
                 "|---|---:|---:|---:|---:|---:|"]
    for r in rw:
        if r.get("samples", 0) == 0:
            md_lines.append(f"| {r['window_days']}d | 0 | — | — | — | — |")
        else:
            md_lines.append(f"| {r['window_days']}d | {r['samples']} | {r['worst_pf']:.3f} | {r['median_pf']:.3f} | {r['pct_pf_gt_1']:.0f}% | {r['pct_pf_gt_1p2']:.0f}% |")
    md_lines += [f"\n## Era split (3 equal-trade-count thirds)\n",
                 "| Era | Range | n | PF | Median |",
                 "|---|---|---:|---:|---:|"]
    for r in es:
        md_lines.append(f"| {r['era']} | {r['start'][:10]} → {r['end'][:10]} | {r['n']} | {r['pf']:.3f} | ${r['median']:.2f} |")
    md_lines += [f"\n## Verdict: **{verdict}**\n"]
    for n in notes:
        md_lines.append(f"- {n}")
    md_path.write_text("\n".join(md_lines))
    print(f"\nWrote: {md_path}")
    print(f"Wrote: {json_path}")
    return payload


if __name__ == "__main__":
    run()
