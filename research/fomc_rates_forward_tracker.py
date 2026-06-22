"""FOMC-week rates sleeve — FORWARD-VALIDATION TRACKER (report-only evidence collection).

NOT promotion/wiring/activation. The FOMC-week rates sleeve is the session's best real find (P-SLEEVE:
~0 corr to incumbents, +net, cuts combined DD). This tracker collects FORWARD evidence toward an
eventual paper packet: lists upcoming FOMC dates, the predeclared trade window (ZN entry -2td, exit
+2td, $1200 stop, long), and a schedule to record actual signal/outcome/slippage when each occurs.
Pure evidence ledger — no orders, no registry, no scheduler. Run anytime to refresh the forward plan.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.forge_fomc_calendar_official import build_official_fomc_calendar  # noqa: E402

TODAY = pd.Timestamp("2026-06-22")  # anchor (no clock dependency in screens)
SPEC = {"sleeve": "FOMC-week-rates (ZN primary, ZF confirmation)", "instrument": "ZN",
        "entry": "-2 trading days vs FOMC", "exit": "+2 trading days vs FOMC", "stop_usd": 1200,
        "direction": "long", "regime_gate": "none for the base sleeve (FOMC-week is all-weather per audit; ZN-FOMC-drift variant was regime-gated separately)",
        "classification": "EVENT/TAIL diversifier (~8/yr), DATA_AUDIT_GREEN, P-SLEEVE-confirmed diversifier",
        "gates_before_paper": ["external DSCL (CME settlement / 2nd vendor)", "forward-window reconciliation vs replay",
                               "executor wiring (out-of-band, gated)", "operator paper approval"]}


def run():
    print("FOMC-week rates sleeve — FORWARD-VALIDATION TRACKER (REPORT-ONLY evidence; NO activation)\n", flush=True)
    cal = build_official_fomc_calendar()
    upcoming = [c for c in cal if pd.Timestamp(c["actual_date"]) >= TODAY]
    past = [c for c in cal if pd.Timestamp(c["actual_date"]) < TODAY]
    print(f"Sleeve spec: {json.dumps(SPEC, indent=0)}\n", flush=True)
    print(f"Calendar: {len(cal)} FOMC events; {len(past)} past, {len(upcoming)} upcoming (>= {TODAY.date()})", flush=True)
    print("\nUPCOMING FOMC windows to record forward (entry ~T-2, exit ~T+2):", flush=True)
    for c in upcoming[:8]:
        f = pd.Timestamp(c["actual_date"])
        print(f"  FOMC {f.date()} ({c.get('actual_time_et','')}) -> record: entry≈{(f - pd.Timedelta(days=4)).date()}..exit≈{(f + pd.Timedelta(days=4)).date()} "
              f"| capture: actual ZN entry/exit fill, realized pnl, slippage vs modeled, data-gap flags", flush=True)
    if not upcoming:
        print("  (none ahead in the loaded calendar — extend calendar with next Fed-published dates when available)", flush=True)
    print("\nFORWARD LEDGER (to append per realized event): date | entered? | entry_px | exit_px | pnl | modeled_pnl | slippage | data_gap | notes", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "fomc_rates_forward_tracker.json"
    out.write_text(json.dumps({"tracker": "fomc_rates_forward", "mode": "report-only evidence collection; NO activation/wiring/registry/scheduler",
        "spec": SPEC, "upcoming_events": [str(pd.Timestamp(c["actual_date"]).date()) for c in upcoming],
        "forward_ledger": [], "note": "best real find of session; collect forward evidence toward eventual paper packet; gated before paper"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; evidence tracker; NO promotion/wiring/mutation)", flush=True)


if __name__ == "__main__":
    run()
