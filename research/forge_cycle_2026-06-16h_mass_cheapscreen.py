"""Cycle 2026-06-16h — Cheap-screen MASS-TEST (discovery lane, report-only).

Lane B / REPORT-ONLY. Corrected posture: Forge discovery does NOT idle. This is the
cheap-screen mass-testing lane — breadth over perfection, kill most quickly, surface
only survivors for later deep audit. Pivots AWAY from the exhausted diagonal
(entry x ema_slope x profit_ladder, already covered) into un-screened exit x filter
combinatorial space, on the diversification-relevant NON-equity assets.

No promotion/wiring/mutation. Survivors are leads for deep audit, NOT candidates.
"""
from __future__ import annotations

import json
import sys
import time
from itertools import product
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import research.crossbreeding.crossbreeding_engine as ce  # noqa: E402
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402

ASSETS_T = ["ZN", "MGC", "MNQ"]   # rates + gold (diversification) + MNQ control
EXITS = ["profit_ladder", "midline_target", "fixed_ratio"]
FILTERS = ["none", "ema_slope", "vwap_slope", "hurst_stable_mr", "session_afternoon"]
# already-known families to flag (so survivors highlight NEW combos, not the live workhorse)
KNOWN = {("orb_breakout", "ema_slope", "profit_ladder"), ("stop_run_reversal", "ema_slope", "profit_ladder"),
         ("range_compression_break", "ema_slope", "profit_ladder"), ("first_impulse_pullback", "ema_slope", "profit_ladder")}


def screen(df, asset, entry, exit_, filt):
    cfg = ASSETS[asset]; costs = get_cost_params(asset)
    try:
        sigs = generate_crossbred_signals(df, entry_name=entry, exit_name=exit_, filter_name=filt, params={})
        res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol=asset,
                           commission_per_side=costs["commission_per_side"],
                           slippage_ticks=costs["slippage_ticks"], tick_size=costs["tick_size"])
        m = _metrics(res["trades_df"], f"{entry}-{exit_}-{filt}", costs=res["stats"]["costs"])
    except Exception as e:
        return {"error": f"{type(e).__name__}"}
    pf = m.get("pf"); h1 = m.get("h1_pf"); h2 = m.get("h2_pf")
    return {"n": int(m.get("n", 0)), "pf": round(float(pf), 3) if pf == pf else None,
            "median": round(float(m.get("median", 0)), 2),
            "h1_pf": round(float(h1), 3) if h1 == h1 else None,
            "h2_pf": round(float(h2), 3) if h2 == h2 else None,
            "max_year_share_pct": round(float(m.get("max_year_share_pct", 0)), 1),
            "gate_verdict": m.get("gate_verdict")}


def run():
    print("Cycle 2026-06-16h — cheap-screen MASS-TEST (REPORT-ONLY discovery lane)\n", flush=True)
    entries = sorted(ce.ENTRY_MAP)
    grid = list(product(entries, EXITS, FILTERS))
    print(f"grid: {len(entries)} entries x {len(EXITS)} exits x {len(FILTERS)} filters = {len(grid)}/asset; assets={ASSETS_T}\n", flush=True)
    t0 = time.time(); results = {}; survivors = []
    for a in ASSETS_T:
        df = pd.read_csv(ROOT / "data" / "processed" / f"{a}_5m.csv")
        ce.feature_cache_clear()
        vc = {"KILL": 0, "DEFER": 0, "WATCH": 0, "PASS_TO_FORWARD_CLOCK": 0, "PASS": 0, "other": 0, "err": 0, "lown": 0}
        for (entry, exit_, filt) in grid:
            r = screen(df, a, entry, exit_, filt)
            if "error" in r:
                vc["err"] += 1; continue
            if r["n"] < 100:
                vc["lown"] += 1; continue
            v = r.get("gate_verdict", "other"); vc[v if v in vc else "other"] += 1
            # survivor = PF>=1.3, both halves>1, conc<=50%, NOT a known family
            if (r["pf"] and r["pf"] >= 1.3 and r["h1_pf"] and r["h2_pf"] and r["h1_pf"] > 1.0 and r["h2_pf"] > 1.0
                    and r["max_year_share_pct"] <= 50 and r["median"] > 0):
                tag = "KNOWN" if (entry, filt, exit_) in KNOWN else "NEW"
                survivors.append({"asset": a, "entry": entry, "exit": exit_, "filter": filt, "tag": tag, **r})
        results[a] = vc
        print(f"  {a}: {vc}  ({time.time()-t0:.0f}s elapsed)", flush=True)

    print("\n=== SURVIVORS (PF>=1.3, both halves>1, conc<=50%, median>0) ===", flush=True)
    new = [s for s in survivors if s["tag"] == "NEW"]
    for s in sorted(survivors, key=lambda x: x["pf"], reverse=True):
        print(f"  [{s['tag']}] {s['asset']} {s['entry']} x {s['exit']} x {s['filter']}: "
              f"PF={s['pf']} n={s['n']} med=${s['median']} maxyr={s['max_year_share_pct']}% H1/H2={s['h1_pf']}/{s['h2_pf']}", flush=True)
    if not survivors:
        print("  (none cleared the cheap-screen survivor bar)", flush=True)
    print(f"\n  total survivors: {len(survivors)} | NEW (non-known-family): {len(new)}", flush=True)
    print(f"  Total: {time.time()-t0:.0f}s", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-16h_mass_cheapscreen.json"
    out.write_text(json.dumps({"cycle": "2026-06-16h_mass_cheapscreen", "mode": "Lane B report-only (discovery lane)",
        "grid": {"entries": len(entries), "exits": EXITS, "filters": FILTERS, "assets": ASSETS_T, "combos_per_asset": len(grid)},
        "verdict_distribution": results, "survivors": survivors, "new_survivors": new,
        "boundaries": "report-only; breadth over perfection; survivors are leads for deep audit, NOT candidates; no promotion/wiring/mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
