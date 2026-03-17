#!/usr/bin/env python3
"""FQL Portfolio Contribution Report -- Strategy-level value analysis.

Answers the key questions for the current portfolio:
  - Which strategies contribute positively vs dilute?
  - Are the two 6J strategies complementary or redundant?
  - Is DailyTrend-MGC-Long diversifying or amplifying existing MGC exposure?
  - What's the overlap structure across the full portfolio?

Uses both backtest-derived scores (from controller) and forward trade
data (from trade log) when available.

Usage:
    python3 research/portfolio_contribution_report.py
    python3 research/portfolio_contribution_report.py --save
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.utils.atomic_io import atomic_write_json

DATA_DIR = ROOT / "research" / "data"
LOGS_DIR = ROOT / "logs"
REPORTS_DIR = ROOT / "research" / "reports"


def load_activation_matrix():
    """Load latest activation matrix for backtest-derived scores."""
    path = DATA_DIR / "portfolio_activation_matrix.json"
    if not path.exists():
        return []
    data = json.load(open(path))
    return data.get("activation_matrix", [])


def load_allocation_matrix():
    """Load allocation tiers."""
    path = DATA_DIR / "allocation_matrix.json"
    if not path.exists():
        return {}
    data = json.load(open(path))
    return data.get("strategies", {})


def load_registry():
    """Load strategy registry."""
    path = DATA_DIR / "strategy_registry.json"
    if not path.exists():
        return []
    return json.load(open(path)).get("strategies", [])


def load_forward_trades():
    """Load forward trade log."""
    path = LOGS_DIR / "trade_log.csv"
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def analyze_backtest_contribution(matrix, allocations):
    """Analyze contribution from backtest-derived controller scores."""
    results = []

    for entry in matrix:
        sid = entry["strategy_id"]
        scores = entry.get("sub_scores", {})
        alloc = allocations.get(sid, {})

        results.append({
            "strategy_id": sid,
            "asset": entry.get("asset", "?"),
            "family": entry.get("family", "?"),
            "exposure": entry.get("primary_exposure", "?"),
            "activation_score": entry.get("activation_score", 0),
            "recommended_action": entry.get("recommended_action", "?"),
            "contribution_score": scores.get("contribution", 0),
            "redundancy_score": scores.get("redundancy", 0),
            "regime_fit_score": scores.get("regime_fit", 0),
            "allocation_tier": alloc.get("final_tier", "?"),
            "situation": entry.get("situation", "HEALTHY"),
        })

    return sorted(results, key=lambda x: x["activation_score"], reverse=True)


def analyze_forward_contribution(trades):
    """Analyze contribution from forward trade data."""
    if trades.empty or "strategy" not in trades.columns:
        return {"status": "no_forward_data", "strategies": {}}

    results = {}
    for sid, grp in trades.groupby("strategy"):
        n = len(grp)
        pnl = grp["pnl"].sum()
        wins = grp[grp["pnl"] > 0]
        losses = grp[grp["pnl"] < 0]
        gw = wins["pnl"].sum() if len(wins) else 0
        gl = abs(losses["pnl"].sum()) if len(losses) else 0
        pf = gw / gl if gl > 0 else (99 if gw > 0 else 0)
        wr = len(wins) / n * 100 if n > 0 else 0

        results[sid] = {
            "forward_trades": n,
            "forward_pnl": round(float(pnl), 2),
            "forward_pf": round(float(pf), 2),
            "forward_wr": round(float(wr), 1),
            "contributing": pnl > 0,
        }

    return {"status": "data_available", "strategies": results}


def analyze_overlap(matrix, registry):
    """Analyze overlap and complementarity between strategies."""
    analysis = {
        "asset_concentration": {},
        "exposure_clusters": {},
        "session_overlap": {},
        "complementarity_notes": [],
    }

    # Asset concentration
    active = [e for e in matrix if e.get("recommended_action") in ("FULL_ON", "REDUCED_ON", "PROBATION")]
    asset_counts = defaultdict(list)
    for e in active:
        asset_counts[e.get("asset", "?")].append(e["strategy_id"])

    for asset, sids in asset_counts.items():
        analysis["asset_concentration"][asset] = {
            "count": len(sids),
            "strategies": sids,
            "risk": "HIGH" if len(sids) >= 4 else "MODERATE" if len(sids) >= 2 else "LOW",
        }

    # Exposure clusters
    exposure_counts = defaultdict(list)
    for e in active:
        exposure_counts[e.get("primary_exposure", "?")].append(e["strategy_id"])

    for exp, sids in exposure_counts.items():
        analysis["exposure_clusters"][exp] = {
            "count": len(sids),
            "strategies": sids,
            "crowded": len(sids) >= 3,
        }

    # Session overlap — check registry for session info
    reg_map = {s["strategy_id"]: s for s in registry}
    session_map = defaultdict(list)
    for e in active:
        reg = reg_map.get(e["strategy_id"], {})
        sess = reg.get("session", "all_day")
        session_map[sess].append(e["strategy_id"])

    analysis["session_overlap"] = {
        sess: {"count": len(sids), "strategies": sids}
        for sess, sids in session_map.items()
    }

    # Specific complementarity checks
    active_ids = {e["strategy_id"] for e in active}

    # 6J complementarity
    j_strats = [sid for sid in active_ids if "6J" in sid or "6j" in sid.lower()]
    if len(j_strats) >= 2:
        j_sessions = {sid: reg_map.get(sid, {}).get("session", "?") for sid in j_strats}
        j_directions = {sid: reg_map.get(sid, {}).get("direction", "?") for sid in j_strats}
        same_session = len(set(j_sessions.values())) < len(j_sessions)
        same_direction = len(set(j_directions.values())) < len(j_directions)

        if not same_session and not same_direction:
            analysis["complementarity_notes"].append(
                f"6J strategies are COMPLEMENTARY: different sessions ({dict(j_sessions)}), "
                f"different directions ({dict(j_directions)})"
            )
        elif same_session:
            analysis["complementarity_notes"].append(
                f"6J strategies have SESSION OVERLAP: {dict(j_sessions)} — potential redundancy"
            )

    # MGC daily vs intraday
    mgc_strats = [sid for sid in active_ids if "MGC" in sid or "mgc" in sid.lower()]
    if len(mgc_strats) >= 2:
        mgc_horizons = {}
        for sid in mgc_strats:
            reg = reg_map.get(sid, {})
            sess = reg.get("session", "")
            mgc_horizons[sid] = "daily" if "daily" in sess else "intraday"

        has_daily = "daily" in mgc_horizons.values()
        has_intraday = "intraday" in mgc_horizons.values()

        if has_daily and has_intraday:
            analysis["complementarity_notes"].append(
                f"MGC strategies span MULTIPLE HORIZONS ({dict(mgc_horizons)}) — "
                f"daily + intraday provides genuine diversification on same asset"
            )
        elif not has_daily:
            analysis["complementarity_notes"].append(
                f"MGC strategies are ALL INTRADAY ({dict(mgc_horizons)}) — "
                f"concentrated in one horizon, overlap risk"
            )

    return analysis


def print_report(backtest, forward, overlap):
    """Print formatted contribution report."""
    W = 70
    print()
    print("=" * W)
    print("  FQL PORTFOLIO CONTRIBUTION REPORT")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * W)

    # Backtest contribution
    print(f"\n  1. BACKTEST-DERIVED CONTRIBUTION (controller scores)")
    print(f"  {'-' * (W-4)}")
    print(f"  {'Strategy':<30s} {'Asset':<5s} {'Score':>5s} {'Contrib':>7s} {'Redund':>6s} {'Action':<12s} {'Tier'}")
    print(f"  {'-' * 68}")
    for s in backtest:
        print(f"  {s['strategy_id']:<30s} {s['asset']:<5s} {s['activation_score']:>5.2f} "
              f"{s['contribution_score']:>7.1f} {s['redundancy_score']:>6.1f} "
              f"{s['recommended_action']:<12s} {s['allocation_tier']}")

    # Forward contribution
    print(f"\n  2. FORWARD TRADE CONTRIBUTION")
    print(f"  {'-' * (W-4)}")
    if forward["status"] == "no_forward_data":
        print(f"  No forward trade data available yet.")
    else:
        for sid, data in sorted(forward["strategies"].items(), key=lambda x: x[1]["forward_pnl"], reverse=True):
            icon = "+" if data["contributing"] else "-"
            print(f"  [{icon}] {sid:<30s} {data['forward_trades']:>3d} trades  "
                  f"PnL ${data['forward_pnl']:>+8,.2f}  PF {data['forward_pf']:.2f}  WR {data['forward_wr']:.0f}%")

    # Overlap analysis
    print(f"\n  3. OVERLAP & COMPLEMENTARITY")
    print(f"  {'-' * (W-4)}")

    print(f"\n  Asset concentration:")
    for asset, data in sorted(overlap["asset_concentration"].items(), key=lambda x: -x[1]["count"]):
        risk_icon = "!!" if data["risk"] == "HIGH" else "! " if data["risk"] == "MODERATE" else "  "
        print(f"  {risk_icon} {asset}: {data['count']} strategies ({', '.join(data['strategies'][:3])})")

    crowded = [exp for exp, d in overlap["exposure_clusters"].items() if d["crowded"]]
    if crowded:
        print(f"\n  Crowded exposure clusters:")
        for exp in crowded:
            d = overlap["exposure_clusters"][exp]
            print(f"  !! {exp}: {d['count']} strategies ({', '.join(d['strategies'][:3])})")

    if overlap["complementarity_notes"]:
        print(f"\n  Complementarity assessment:")
        for note in overlap["complementarity_notes"]:
            print(f"  >> {note}")

    print(f"\n{'=' * W}")


def main():
    parser = argparse.ArgumentParser(description="FQL Portfolio Contribution Report")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    matrix = load_activation_matrix()
    allocations = load_allocation_matrix()
    registry = load_registry()
    trades = load_forward_trades()

    backtest = analyze_backtest_contribution(matrix, allocations)
    forward = analyze_forward_contribution(trades)
    overlap = analyze_overlap(matrix, registry)

    report = {
        "generated": datetime.now().isoformat(),
        "backtest_contribution": backtest,
        "forward_contribution": forward,
        "overlap_analysis": overlap,
    }

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print_report(backtest, forward, overlap)

    if args.save:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        out = REPORTS_DIR / f"contribution_report_{ts}.json"
        atomic_write_json(out, report)
        print(f"\n  Saved: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
