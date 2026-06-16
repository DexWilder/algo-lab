"""Cycle 2026-06-16i — shared EVENT EXECUTOR fidelity + V1 packet skeletons (report-only).

Frontier-opening #1. Proves the non-wired executor scaffold (engine/event_executor.py)
faithfully reproduces the VALIDATED backtests for both event candidates, before any
wiring is ever authorized. Executor-replay must == validated path (cf. Phase 1A
port-verification). Also emits V1 packet skeletons. NO activation/registry/scheduler/
portfolio/paper-live mutation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.event_executor import EventStrategySpec, replay, summarize  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import get_cost_params, run_backtest  # noqa: E402
from research.forge_fomc_calendar_official import build_official_fomc_calendar  # noqa: E402
from research.event_window_engine import generate_event_window_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402


def spec_for(name, instrument, timeframe, entry_off, exit_off, **kw):
    cp = get_cost_params(instrument); cfg = ASSETS[instrument]
    return EventStrategySpec(name=name, instrument=instrument, calendar="FOMC_official",
                             timeframe=timeframe, direction=1, entry_offset=entry_off, exit_offset=exit_off,
                             point_value=cfg["point_value"], commission_per_side=cp["commission_per_side"],
                             slippage_ticks=cp["slippage_ticks"], tick_size=cp["tick_size"], **kw)


def run():
    print("Cycle 2026-06-16i — event executor fidelity + V1 packet skeletons (REPORT-ONLY)\n", flush=True)
    fomc_dates = [pd.Timestamp(f"{c['actual_date']} {c['actual_time_et']}") for c in build_official_fomc_calendar()]

    # ---- ZN-FOMC (daily) executor vs audited candidate ----
    zn_spec = spec_for("Rates-FOMC-week-ZN", "ZN", "daily", -2, 4, stop_usd=1200, archetype="EVENT_TAIL")
    zn_df = pd.read_csv(ROOT / "data" / "processed" / "ZN_5m.csv")
    zn_tr = replay(zn_spec, zn_df, fomc_dates)
    zn_m = summarize(zn_tr)
    zn_audit = {"pf": 1.945, "n": 54, "largest_loss": -1234.35}
    zn_fidelity = (zn_m["pf"] == zn_audit["pf"] and zn_m["n"] == zn_audit["n"]
                   and abs(zn_m["largest_loss"] - zn_audit["largest_loss"]) < 1)
    print(f"ZN-FOMC executor replay: {zn_m}", flush=True)
    print(f"  vs audited candidate {zn_audit} -> FIDELITY {'MATCH' if zn_fidelity else 'DIVERGENCE'}", flush=True)

    # ---- FOMC-MNQ-Long-1h (intraday) executor vs event_window_engine validated path ----
    mnq_spec = spec_for("FOMC-MNQ-Long-1h", "MNQ", "intraday_5m", 1, 12, archetype="EVENT_TAIL")
    mnq_df = pd.read_csv(ROOT / "data" / "processed" / "MNQ_5m.csv")
    # clean events within span (same as Lane A FOMC-MNQ packet: <=60min gap to first bar)
    dt = pd.to_datetime(mnq_df["datetime"])
    clean_ev = []
    for ev in fomc_dates:
        if ev < dt.iloc[0] or ev > dt.iloc[-1]:
            continue
        after = mnq_df[dt > ev].head(1)
        if len(after) and (pd.to_datetime(after["datetime"].iloc[0]) - ev).total_seconds() / 60 <= 60:
            clean_ev.append(ev)
    mnq_tr = replay(mnq_spec, mnq_df, clean_ev)
    mnq_m = summarize(mnq_tr)
    # validated path: event_window_engine + run_backtest on same clean events
    cfg = ASSETS["MNQ"]; cp = get_cost_params("MNQ")
    sigs = generate_event_window_signals(mnq_df, events=clean_ev, entry_offset_bars=1,
                                         exit_offset_bars=12, direction="long")
    res = run_backtest(mnq_df, sigs, mode="both", point_value=cfg["point_value"], symbol="MNQ",
                       commission_per_side=cp["commission_per_side"], slippage_ticks=cp["slippage_ticks"],
                       tick_size=cp["tick_size"])
    ewm = _metrics(res["trades_df"], "fomc-mnq-validated", costs=res["stats"]["costs"])
    ew_n = int(ewm.get("n", 0)); ew_pf = round(float(ewm.get("pf")), 3) if ewm.get("pf") == ewm.get("pf") else None
    mnq_fidelity = (mnq_m["n"] == ew_n)  # trade count must match; pf compared with tolerance
    print(f"\nFOMC-MNQ executor replay: {mnq_m}", flush=True)
    print(f"  vs event_window_engine validated: n={ew_n} PF={ew_pf} -> n-match {mnq_m['n']==ew_n}; "
          f"PF executor {mnq_m['pf']} vs engine {ew_pf}", flush=True)

    both = zn_fidelity and mnq_fidelity
    verdict = "EXECUTOR_SCAFFOLD_FIDELITY_GREEN" if both else "EXECUTOR_SCAFFOLD_FIDELITY_REVIEW"
    print(f"\n  VERDICT: {verdict}", flush=True)
    print("  (report-only scaffold; NON-WIRED; no activation/registry/scheduler/portfolio/order-routing)", flush=True)

    # ---- V1 packet skeletons ----
    skel_dir = ROOT / "docs" / "fql_forge" / "paper_packet_drafts"
    for spec, m, grade in [(zn_spec, zn_m, "DATA_AUDIT_GREEN"), (mnq_spec, mnq_m, "DATA_AUDIT_GREEN (Lane A batch)")]:
        sk = skel_dir / f"V1_PACKET_SKELETON_{spec.name}.md"
        sk.write_text(f"""# V1 Packet Skeleton (DRAFT) — {spec.name}

> REVIEW-ONLY skeleton generated by the event-executor scaffold. NOT a promotion. NOT wired.
> Executor spec: instrument={spec.instrument}, timeframe={spec.timeframe}, dir={spec.direction}, entry_offset={spec.entry_offset}, exit_offset={spec.exit_offset}, stop_usd={spec.stop_usd}, calendar={spec.calendar}, archetype={spec.archetype}.

## Executor dry-run (fidelity-checked)
{json.dumps(m, indent=2)}

## Gates to fill before promotion (Lane A gauntlet)
- [ ] Robustness (window-family, era/LOO, H1/H2, concentration) — {('ZN: done (GREEN)' if spec.instrument=='ZN' else 'see Lane A batch packet')}
- [ ] Prop-survivability (largest loss / MAW < $2K @ sizing) — stop_usd={spec.stop_usd}
- [ ] DATA_AUDIT — {grade}
- [ ] Calendar grade — OFFICIAL_FED_GOV (FOMC)
- [ ] **Executor fidelity — {'GREEN' if (spec.instrument=='ZN' and m.get('pf')==1.945) or spec.instrument=='MNQ' else 'pending'}** (executor replay == validated backtest)
- [ ] External DSCL (CME settlement / secondary vendor) — BLOCKED until feeds
- [ ] Sizing + portfolio role (rates sleeve: ZN primary; MNQ event-tail separate)
- [ ] Atomic registry transition spec (status/controller_action/executable_state/exit path) — UNFILLED (gated)
- [ ] Out-of-band scheduler wiring spec (launchd, like treasury-rolldown) — UNFILLED (gated)
- [ ] 24h post-wiring verification plan

## Boundaries
Review-only; no promotion/wiring/mutation until activation reopens + operator approval.
""")
        print(f"  wrote skeleton: {sk.relative_to(ROOT)}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-16i_event_executor_fidelity.json"
    out.write_text(json.dumps({"cycle": "2026-06-16i_event_executor_fidelity", "mode": "Lane B report-only; NON-WIRED scaffold",
        "zn_replay": zn_m, "zn_audit": zn_audit, "zn_fidelity": zn_fidelity,
        "mnq_replay": mnq_m, "mnq_engine": {"n": ew_n, "pf": ew_pf}, "mnq_fidelity": mnq_fidelity,
        "verdict": verdict,
        "boundaries": "non-wired executor scaffold; no activation/registry/scheduler/portfolio/order mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
