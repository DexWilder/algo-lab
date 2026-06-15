"""Cycle 2026-06-15 — Cross-asset screen of the Wave 1 winner (stop_run_reversal).

Lane B / REPORT-ONLY (Phase 1C activation frozen; Forge engine continues).
Doctrine: feedback_cross_asset_first — cross-asset test the winner BEFORE building
new families. The validated MNQ config (entry=stop_run_reversal, exit=profit_ladder,
filter=ema_slope, params={}) produced n=1414 PF=1.477. All 4 Lane A candidates were
MNQ-only; asset diversification is the flagged portfolio gap. This screens whether
the EXACT validated config ports to the other equity-index micros + gold + energy
where XB-ORB validated (MES/MGC/M2K/MYM/MCL).

Uses the same generate_crossbred_signals + run_backtest + canonical asset_config
costs as the DATA_AUDIT_GREEN harness. NO wiring, NO registry mutation, NO promotion.

Boundaries: report-only. Surfaces a PASS/WATCH/KILL packet for future consideration.
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

BASELINE_MNQ = {"n": 1414, "pf": 1.477, "median": 15.51}  # validated reference
ASSETS_TO_SCREEN = ["MNQ", "MES", "MGC", "M2K", "MYM", "MCL"]  # MNQ = baseline control


def screen_asset(asset: str) -> dict:
    csv = ROOT / "data" / "processed" / f"{asset}_5m.csv"
    if not csv.exists():
        return {"asset": asset, "error": "no_data"}
    df = pd.read_csv(csv)
    cfg = ASSETS[asset]
    costs = get_cost_params(asset)
    sigs = generate_crossbred_signals(df, entry_name="stop_run_reversal",
                                      exit_name="profit_ladder", filter_name="ema_slope", params={})
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol=asset,
                       commission_per_side=costs["commission_per_side"],
                       slippage_ticks=costs["slippage_ticks"], tick_size=costs["tick_size"])
    m = _metrics(res["trades_df"], f"SRR-{asset}", costs=res["stats"]["costs"])
    return {
        "asset": asset,
        "n": int(m.get("n", 0)),
        "pf": round(float(m.get("pf")), 3) if m.get("pf") == m.get("pf") else None,
        "median": round(float(m.get("median", 0)), 2),
        "net": round(float(m.get("net", 0)), 2),
        "win_rate_pct": round(float(m.get("win_rate_pct", 0)), 1),
        "top3_share_pct": round(float(m.get("top3_share_pct", 0)), 1),
        "max_year_share_pct": round(float(m.get("max_year_share_pct", 0)), 1),
        "archetype": m.get("archetype"),
        "gate_verdict": m.get("gate_verdict"),
        "blocker_reason": m.get("blocker_reason"),
        "cost_tier": res["stats"]["costs"].get("cost_tier"),
        "signal_hash": hashlib.sha256(sigs["signal"].values.tobytes()).hexdigest()[:16],
    }


def run():
    print("Cycle 2026-06-15 — stop_run_reversal cross-asset screen (REPORT-ONLY)\n", flush=True)
    t0 = time.time()
    results = []
    for a in ASSETS_TO_SCREEN:
        print(f"  screening {a} ...", flush=True)
        r = screen_asset(a)
        results.append(r)
        if "error" not in r:
            print(f"    n={r['n']} PF={r['pf']} median=${r['median']} WR={r['win_rate_pct']}% "
                  f"top3={r['top3_share_pct']}% maxyr={r['max_year_share_pct']}% "
                  f"verdict={r['gate_verdict']} ({r['archetype']})", flush=True)
        else:
            print(f"    {r['error']}", flush=True)

    ok = [r for r in results if "error" not in r]
    passes = [r for r in ok if r.get("gate_verdict") == "PASS"]
    print(f"\n=== SUMMARY (baseline MNQ: n={BASELINE_MNQ['n']} PF={BASELINE_MNQ['pf']}) ===", flush=True)
    for r in ok:
        flag = "<-- baseline" if r["asset"] == "MNQ" else ""
        print(f"  {r['asset']:4s} {str(r['gate_verdict']):6s} PF={r['pf']} n={r['n']} "
              f"median=${r['median']} {flag}", flush=True)
    print(f"\n  PASS (non-MNQ portability): {sorted(r['asset'] for r in passes if r['asset']!='MNQ')}", flush=True)
    print(f"  Total: {time.time()-t0:.0f}s", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-15_stop_run_cross_asset_screen.json"
    out.write_text(json.dumps({
        "cycle": "2026-06-15_stop_run_cross_asset_screen",
        "mode": "Lane B report-only (Phase 1C activation frozen)",
        "config": "entry=stop_run_reversal, exit=profit_ladder, filter=ema_slope, params={} (validated MNQ config)",
        "baseline_mnq": BASELINE_MNQ,
        "results": results,
        "pass_non_mnq": sorted(r["asset"] for r in passes if r["asset"] != "MNQ"),
        "boundaries": "report-only; no wiring/registry/promotion; surfaces candidates for future consideration",
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
