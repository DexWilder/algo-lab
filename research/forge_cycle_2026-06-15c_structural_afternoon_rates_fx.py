"""Cycle 2026-06-15c — STRUCTURAL / afternoon reversion screen on rates + FX.

Lane B / REPORT-ONLY. First non-momentum, non-MNQ diversification pivot after the
Lane A momentum family was confirmed MNQ-specific. Precedent: ZN-Afternoon-Reversion
(live probation). No tuning, no promotion, no wiring.

Entries (reversion/fade): afternoon_reversion, bb_reversion, prior_day_fade
Filter: session_afternoon
Exit: midline_target  -- thesis-consistent for REVERSION (NOT profit_ladder, a trend
      ratchet that would unfairly test a mean-reversion entry).
Assets: ZN/ZF/ZB (rates) + 6E/6J/6B (FX) + MGC/MCL (gold/energy, cheap add)

params={} (defaults; no tuning). Canonical asset_config costs. Intraday-flat (engine
flattens pre-close) so largest-single-day-loss ~= prop daily-DD exposure.
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

ENTRIES = ["afternoon_reversion", "bb_reversion", "prior_day_fade"]
ASSETS_TO_SCREEN = ["ZN", "ZF", "ZB", "6E", "6J", "6B", "MGC", "MCL"]
FILTER = "session_afternoon"
EXIT = "midline_target"


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
        "net": round(float(m.get("net", 0)), 2),
        "win_rate_pct": round(float(m.get("win_rate_pct", 0)), 1),
        "top3_share_pct": round(float(m.get("top3_share_pct", 0)), 1),
        "max_year_share_pct": round(float(m.get("max_year_share_pct", 0)), 1),
        "largest_single_day_loss": largest_day,
        "archetype": m.get("archetype"), "gate_verdict": m.get("gate_verdict"),
        "blocker_reason": m.get("blocker_reason"),
        "signal_hash": hashlib.sha256(sigs["signal"].values.tobytes()).hexdigest()[:16],
    }


def run():
    print("Cycle 2026-06-15c — STRUCTURAL/afternoon reversion on rates+FX (REPORT-ONLY)\n", flush=True)
    t0 = time.time()
    results = []
    for entry in ENTRIES:
        print(f"\n## {entry} x {FILTER} x {EXIT}", flush=True)
        for a in ASSETS_TO_SCREEN:
            r = screen(entry, a)
            results.append(r)
            if "error" not in r:
                print(f"  {a:4s} {str(r['gate_verdict']):22s} PF={r['pf']} n={r['n']} "
                      f"median=${r['median']} maxyr={r['max_year_share_pct']}% "
                      f"top3={r['top3_share_pct']}% dayLoss=${r['largest_single_day_loss']}", flush=True)
            else:
                print(f"  {a:4s} {r['error']}", flush=True)

    ok = [r for r in results if "error" not in r]
    passes = [r for r in ok if r.get("gate_verdict") == "PASS"]
    watch = [r for r in ok if r.get("gate_verdict") in ("WATCH", "PASS_TO_FORWARD_CLOCK")]
    print("\n=== SUMMARY ===", flush=True)
    print(f"  screened: {len(ok)} | PASS: {len(passes)} | WATCH/FWD: {len(watch)}", flush=True)
    for r in sorted(ok, key=lambda x: (x['pf'] or 0), reverse=True)[:6]:
        print(f"  TOP: {r['entry']}-{r['asset']} PF={r['pf']} median=${r['median']} "
              f"n={r['n']} maxyr={r['max_year_share_pct']}% verdict={r['gate_verdict']}", flush=True)
    print(f"\n  PASS candidates: {[(r['entry'],r['asset']) for r in passes]}", flush=True)
    print(f"  Total: {time.time()-t0:.0f}s", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-15c_structural_afternoon_rates_fx.json"
    out.write_text(json.dumps({
        "cycle": "2026-06-15c_structural_afternoon_rates_fx",
        "mode": "Lane B report-only (Phase 1C frozen)",
        "config": f"entries={ENTRIES}, filter={FILTER}, exit={EXIT} (reversion-consistent), params={{}}",
        "assets": ASSETS_TO_SCREEN,
        "results": results,
        "pass": [(r["entry"], r["asset"]) for r in passes],
        "watch_fwd": [(r["entry"], r["asset"]) for r in watch],
        "boundaries": "report-only; no tuning/promotion/wiring; negative results preserved",
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
