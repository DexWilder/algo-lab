"""Cycle 2026-06-15b — bounded cross-asset sanity screen: other 2 Lane A mechanisms.

Lane B / REPORT-ONLY. Follows the stop_run screen discipline (feedback_cross_asset_first):
exact validated config, no tuning, no promotion, no wiring. Tests whether the other
two validated MNQ daily-workhorse mechanisms generalize off MNQ — bounded: if both are
MNQ-specific (like stop_run), stop trying to port the Lane A momentum family.

Mechanisms: range_compression_break, first_impulse_pullback
Config (each): entry=<mech>, exit=profit_ladder, filter=ema_slope, params={}
Assets: MNQ (baseline) + MES/MGC/M2K/MYM/MCL
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402

MECHANISMS = ["range_compression_break", "first_impulse_pullback"]
ASSETS_TO_SCREEN = ["MNQ", "MES", "MGC", "M2K", "MYM", "MCL"]
# Committed MNQ baselines (Lane A batch) for control comparison
MNQ_BASE = {"range_compression_break": {"n": 1244, "pf": 1.370, "median": 9.01},
            "first_impulse_pullback": {"n": 1001, "pf": 1.354, "median": 4.26}}


def screen(mech: str, asset: str) -> dict:
    csv = ROOT / "data" / "processed" / f"{asset}_5m.csv"
    if not csv.exists():
        return {"mech": mech, "asset": asset, "error": "no_data"}
    df = pd.read_csv(csv)
    cfg = ASSETS[asset]
    costs = get_cost_params(asset)
    sigs = generate_crossbred_signals(df, entry_name=mech, exit_name="profit_ladder",
                                      filter_name="ema_slope", params={})
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol=asset,
                       commission_per_side=costs["commission_per_side"],
                       slippage_ticks=costs["slippage_ticks"], tick_size=costs["tick_size"])
    m = _metrics(res["trades_df"], f"{mech}-{asset}", costs=res["stats"]["costs"])
    return {
        "mech": mech, "asset": asset,
        "n": int(m.get("n", 0)),
        "pf": round(float(m.get("pf")), 3) if m.get("pf") == m.get("pf") else None,
        "median": round(float(m.get("median", 0)), 2),
        "win_rate_pct": round(float(m.get("win_rate_pct", 0)), 1),
        "top3_share_pct": round(float(m.get("top3_share_pct", 0)), 1),
        "max_year_share_pct": round(float(m.get("max_year_share_pct", 0)), 1),
        "archetype": m.get("archetype"), "gate_verdict": m.get("gate_verdict"),
        "signal_hash": hashlib.sha256(sigs["signal"].values.tobytes()).hexdigest()[:16],
    }


def run():
    print("Cycle 2026-06-15b — Lane A family cross-asset screen (REPORT-ONLY)\n", flush=True)
    t0 = time.time()
    results = []
    for mech in MECHANISMS:
        print(f"\n## {mech} (MNQ baseline n={MNQ_BASE[mech]['n']} PF={MNQ_BASE[mech]['pf']})", flush=True)
        for a in ASSETS_TO_SCREEN:
            r = screen(mech, a)
            results.append(r)
            if "error" not in r:
                tag = "<-- baseline" if a == "MNQ" else ""
                print(f"  {a:4s} {str(r['gate_verdict']):22s} PF={r['pf']} n={r['n']} "
                      f"median=${r['median']} maxyr={r['max_year_share_pct']}% {tag}", flush=True)
            else:
                print(f"  {a:4s} {r['error']}", flush=True)

    # portability assessment per mechanism (non-MNQ PASS count)
    summary = {}
    for mech in MECHANISMS:
        rows = [r for r in results if r["mech"] == mech and "error" not in r and r["asset"] != "MNQ"]
        passes = [r["asset"] for r in rows if r.get("gate_verdict") == "PASS"]
        summary[mech] = {"non_mnq_pass": sorted(passes), "n_non_mnq_pass": len(passes)}
    print("\n=== PORTABILITY SUMMARY ===", flush=True)
    for mech, s in summary.items():
        print(f"  {mech}: non-MNQ PASS = {s['non_mnq_pass'] or 'NONE'}", flush=True)
    family_mnq_specific = all(s["n_non_mnq_pass"] == 0 for s in summary.values())
    conclusion = ("LANE_A_MOMENTUM_FAMILY_MNQ_SPECIFIC — stop trying to port; asset-diversification "
                  "gap requires NEW mechanisms" if family_mnq_specific
                  else "PARTIAL_PORTABILITY — see per-mechanism PASS list")
    print(f"\n  CONCLUSION: {conclusion}", flush=True)
    print(f"  (stop_run_reversal already shown MNQ-specific 2026-06-15)", flush=True)
    print(f"  Total: {time.time()-t0:.0f}s", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-15b_lane_a_family_cross_asset_screen.json"
    out.write_text(json.dumps({
        "cycle": "2026-06-15b_lane_a_family_cross_asset_screen",
        "mode": "Lane B report-only (Phase 1C activation frozen)",
        "mechanisms": MECHANISMS, "mnq_baselines": MNQ_BASE,
        "results": results, "portability_summary": summary, "conclusion": conclusion,
        "boundaries": "report-only; no tuning/promotion/wiring; negative results preserved",
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
