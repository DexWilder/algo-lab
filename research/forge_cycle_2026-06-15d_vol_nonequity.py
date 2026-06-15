"""Cycle 2026-06-15d — VOL mechanisms on non-equity assets.

Lane B / REPORT-ONLY. Second non-momentum diversification pivot (structural/afternoon
reversion failed cleanly). Tests whether vol-expansion/regime/squeeze mechanisms have
edge on non-equity assets. No tuning, no promotion, no wiring.

Entries (vol, directional expansion -> trend-consistent exit): vol_expansion,
volatility_regime_compound, bb_keltner_squeeze
Filter: none (vol-conditioning is inside the entries; params={} = no tuning)
Exit: profit_ladder (thesis-consistent for breakout/expansion, NOT reversion)
Assets: MNQ (equity CONTROL) + MGC/MCL (gold/energy) + ZN/ZF/ZB (rates) + 6E/6J/6B (FX)
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

ENTRIES = ["vol_expansion", "volatility_regime_compound", "bb_keltner_squeeze"]
ASSETS_TO_SCREEN = ["MNQ", "MGC", "MCL", "ZN", "ZF", "ZB", "6E", "6J", "6B"]  # MNQ=control
FILTER = "none"
EXIT = "profit_ladder"


def screen(entry: str, asset: str) -> dict:
    csv = ROOT / "data" / "processed" / f"{asset}_5m.csv"
    if not csv.exists():
        return {"entry": entry, "asset": asset, "error": "no_data"}
    df = pd.read_csv(csv)
    cfg = ASSETS[asset]
    costs = get_cost_params(asset)
    sigs = generate_crossbred_signals(df, entry_name=entry, exit_name=EXIT,
                                      filter_name=FILTER, params={})
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol=asset,
                       commission_per_side=costs["commission_per_side"],
                       slippage_ticks=costs["slippage_ticks"], tick_size=costs["tick_size"])
    trades = res["trades_df"]
    m = _metrics(trades, f"{entry}-{asset}", costs=res["stats"]["costs"])
    largest_day = None
    if trades is not None and not trades.empty and "pnl" in trades.columns:
        day = pd.to_datetime(trades["entry_time"]).dt.date
        largest_day = round(float(trades["pnl"].astype(float).groupby(day).sum().min()), 2)
    return {
        "entry": entry, "asset": asset,
        "n": int(m.get("n", 0)),
        "pf": round(float(m.get("pf")), 3) if m.get("pf") == m.get("pf") else None,
        "median": round(float(m.get("median", 0)), 2),
        "win_rate_pct": round(float(m.get("win_rate_pct", 0)), 1),
        "top3_share_pct": round(float(m.get("top3_share_pct", 0)), 1),
        "max_year_share_pct": round(float(m.get("max_year_share_pct", 0)), 1),
        "largest_single_day_loss": largest_day,
        "archetype": m.get("archetype"), "gate_verdict": m.get("gate_verdict"),
        "signal_hash": hashlib.sha256(sigs["signal"].values.tobytes()).hexdigest()[:16],
    }


def run():
    print("Cycle 2026-06-15d — VOL mechanisms on non-equity (REPORT-ONLY)\n", flush=True)
    t0 = time.time()
    results = []
    for entry in ENTRIES:
        print(f"\n## {entry} x filter=none x {EXIT}", flush=True)
        for a in ASSETS_TO_SCREEN:
            r = screen(entry, a)
            results.append(r)
            if "error" not in r:
                tag = "<-- control" if a == "MNQ" else ""
                print(f"  {a:4s} {str(r['gate_verdict']):22s} PF={r['pf']} n={r['n']} "
                      f"median=${r['median']} maxyr={r['max_year_share_pct']}% dayLoss=${r['largest_single_day_loss']} {tag}", flush=True)
            else:
                print(f"  {a:4s} {r['error']}", flush=True)

    ok = [r for r in results if "error" not in r]
    passes = [r for r in ok if r.get("gate_verdict") == "PASS"]
    interesting = [r for r in ok if r.get("pf") and r["pf"] >= 1.2 and r["asset"] != "MNQ"]
    print("\n=== SUMMARY ===", flush=True)
    print(f"  screened: {len(ok)} | PASS: {len(passes)} | non-MNQ PF>=1.2: {len(interesting)}", flush=True)
    for r in sorted(ok, key=lambda x: (x['pf'] or 0), reverse=True)[:8]:
        print(f"  TOP: {r['entry']}-{r['asset']} PF={r['pf']} median=${r['median']} "
              f"n={r['n']} maxyr={r['max_year_share_pct']}% {r['gate_verdict']}", flush=True)
    print(f"\n  PASS: {[(r['entry'],r['asset']) for r in passes]}", flush=True)
    print(f"  non-MNQ PF>=1.2 (watch): {[(r['entry'],r['asset'],r['pf']) for r in interesting]}", flush=True)
    print(f"  Total: {time.time()-t0:.0f}s", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-15d_vol_nonequity.json"
    out.write_text(json.dumps({
        "cycle": "2026-06-15d_vol_nonequity",
        "mode": "Lane B report-only (Phase 1C frozen)",
        "config": f"entries={ENTRIES}, filter={FILTER}, exit={EXIT}, params={{}}; MNQ=control",
        "assets": ASSETS_TO_SCREEN, "results": results,
        "pass": [(r["entry"], r["asset"]) for r in passes],
        "non_mnq_pf_ge_1_2": [(r["entry"], r["asset"], r["pf"]) for r in interesting],
        "boundaries": "report-only; no tuning/promotion/wiring; negative results preserved",
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
