"""Cycle 2026-06-11j — Packet #1 NFP-MGC-Long-2h strict-filter re-audit.

Per operator decision #162 OK A. Defensive hygiene re-verification of the
sprint's only accepted packet after the 06-11i strict 8-asset audit revealed
that MGC NFP clean coverage drops from 70.8% (permissive) to 65.6% (strict).

Three-version comparison:
  1. Permissive filter (cycle 10g basis): exact match OR next-bar gap <= 60min
  2. Strict filter (cycle 11f/11i basis): next-bar gap <= 60min only
  3. Strict + hold-window continuity: also require no gaps within the 24-bar
     (2h) hold window after entry

Per #162 required reports:
  - scheduled events / included strict-clean events / excluded + reason
  - PF, median, mean, win rate, years positive
  - max-yr concentration, Era 3 PF/median
  - PASS_STRESS verdict at 2x cost + 2 ticks slippage
  - artifact reproducibility (signal hash)
  - gate-by-gate pass/fail

Classification:
  - All gates pass on strict: Packet #1 acceptance HOLDS (with amendment)
  - Any gate fails on strict: Packet #1 → REOPEN / REVIEW status

Boundaries: report-only Lane B. No registry mutation.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.event_window_engine import generate_event_window_signals  # noqa: E402
from research.forge_nfp_calendar_verify import build_verified_nfp_calendar  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def permissive_filter(events, df, max_gap_minutes=60):
    """Cycle 10g/11e style: exact match OR next-bar gap <= max_gap_minutes."""
    df_dt = pd.to_datetime(df["datetime"])
    clean, excluded = [], []
    for ev in events:
        if ev < df_dt.iloc[0]:
            excluded.append((ev, "pre-data-start"))
            continue
        exact = df[df_dt == ev]
        if len(exact) > 0:
            clean.append(ev)
            continue
        after = df[df_dt > ev].head(1)
        if len(after) == 0:
            excluded.append((ev, "no future bar"))
            continue
        gap_min = (pd.to_datetime(after["datetime"].iloc[0]) - ev).total_seconds() / 60
        if gap_min <= max_gap_minutes:
            clean.append(ev)
        else:
            excluded.append((ev, f"{gap_min/60:.1f}h gap"))
    return clean, excluded


def strict_filter(events, df, max_gap_minutes=60):
    """Cycle 11f/11i style: next-bar gap <= max_gap_minutes only.

    No exact-match override. Even if a bar exists at the event time, if the
    next bar after is > max_gap_minutes away, the event is contaminated.
    """
    df_dt = pd.to_datetime(df["datetime"])
    clean, excluded = [], []
    for ev in events:
        if ev < df_dt.iloc[0]:
            excluded.append((ev, "pre-data-start"))
            continue
        after = df[df_dt > ev].head(1)
        if len(after) == 0:
            excluded.append((ev, "no future bar"))
            continue
        gap_min = (pd.to_datetime(after["datetime"].iloc[0]) - ev).total_seconds() / 60
        if gap_min <= max_gap_minutes:
            clean.append(ev)
        else:
            excluded.append((ev, f"{gap_min/60:.1f}h next-bar gap (strict reject)"))
    return clean, excluded


def strict_filter_with_hold_continuity(events, df, max_gap_minutes=60,
                                         hold_bars=24, max_intra_hold_gap_minutes=60):
    """Strict + check that the next hold_bars bars after entry have no >gap.

    For event-window strategies with N-bar hold, ALSO require that the bars
    from entry through entry+hold_bars are continuous (each consecutive bar
    within max_intra_hold_gap_minutes).
    """
    df_dt = pd.to_datetime(df["datetime"]).reset_index(drop=True)
    n = len(df_dt)
    clean, excluded = [], []
    for ev in events:
        if ev < df_dt.iloc[0]:
            excluded.append((ev, "pre-data-start"))
            continue
        # Find next-bar after event
        future_mask = df_dt > ev
        if not future_mask.any():
            excluded.append((ev, "no future bar"))
            continue
        next_idx = int(np.argmax(future_mask.values))
        gap_min = (df_dt.iloc[next_idx] - ev).total_seconds() / 60
        if gap_min > max_gap_minutes:
            excluded.append((ev, f"{gap_min/60:.1f}h next-bar gap"))
            continue
        # Entry bar is at next_idx + 1 (entry_offset_bars=1 convention).
        entry_idx = next_idx + 1
        exit_idx = entry_idx + hold_bars
        if exit_idx >= n:
            excluded.append((ev, "hold window exceeds data"))
            continue
        # Check intra-hold continuity
        hold_window = df_dt.iloc[entry_idx:exit_idx + 1].reset_index(drop=True)
        intra_gaps = hold_window.diff().dropna()
        max_intra_gap_min = intra_gaps.dt.total_seconds().max() / 60
        if max_intra_gap_min > max_intra_hold_gap_minutes:
            excluded.append((ev, f"intra-hold gap {max_intra_gap_min/60:.1f}h"))
            continue
        clean.append(ev)
    return clean, excluded


def run_packet(events, label):
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    cfg = ASSETS["MGC"]
    costs = get_cost_params("MGC")
    sigs = generate_event_window_signals(
        df, events=events, entry_offset_bars=1, exit_offset_bars=24, direction="long",
    )
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"],
                       symbol="MGC", commission_per_side=costs["commission_per_side"],
                       slippage_ticks=costs["slippage_ticks"], tick_size=costs["tick_size"])
    m = _metrics(res["trades_df"], label, costs=res["stats"]["costs"])
    trades = res["trades_df"]
    # Artifact hash of signal column for reproducibility
    sig_hash = hashlib.sha256(sigs["signal"].values.tobytes()).hexdigest()[:16]
    return m, trades, sig_hash


def run_stress(events, label, cost_mult=2.0, slip_mult=3.0):
    """2x cost + 2 ticks slippage stress per #162."""
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    cfg = ASSETS["MGC"]
    costs = get_cost_params("MGC")
    sigs = generate_event_window_signals(
        df, events=events, entry_offset_bars=1, exit_offset_bars=24, direction="long",
    )
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"],
                       symbol="MGC",
                       commission_per_side=costs["commission_per_side"] * cost_mult,
                       slippage_ticks=int(np.ceil(costs["slippage_ticks"] * slip_mult)),
                       tick_size=costs["tick_size"])
    return _metrics(res["trades_df"], label, costs=res["stats"]["costs"])


def temporal_split(trades):
    df = trades.copy()
    df["entry_dt"] = pd.to_datetime(df["entry_time"])
    df["year"] = df["entry_dt"].dt.year
    per_year = []
    for y, g in df.groupby("year"):
        pnl = g["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w / l) if l > 0 else float("inf")
        per_year.append({"year": int(y), "n": int(len(g)), "pf": pf,
                         "median": float(np.median(pnl)),
                         "net": float(pnl.sum()),
                         "win_rate": float((pnl > 0).mean())})
    df = df.sort_values("entry_dt").reset_index(drop=True)
    cuts = np.linspace(0, len(df), 4).astype(int)
    eras = []
    for i in range(3):
        sub = df.iloc[cuts[i]:cuts[i + 1]]
        if sub.empty: continue
        pnl = sub["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w / l) if l > 0 else float("inf")
        eras.append({"era": i + 1, "n": int(len(sub)), "pf": pf,
                     "median": float(np.median(pnl)), "net": float(pnl.sum())})
    nets = [y["net"] for y in per_year]
    total_net = sum(nets)
    max_yr_share = max(abs(n) for n in nets) / total_net * 100 if total_net > 0 else 0
    return {
        "per_year": per_year, "eras": eras,
        "yrs_pos": sum(1 for r in per_year if r["net"] > 0),
        "n_yrs": len(per_year),
        "total_net": total_net,
        "era3_pf": eras[-1]["pf"] if eras else float("nan"),
        "era3_median": eras[-1]["median"] if eras else float("nan"),
        "max_yr_share_pct": max_yr_share,
    }


def evaluate_gates(m, ts, stress_median):
    """Per #162: apply all packet gates."""
    return {
        "positive_median": m["median"] > 0,
        "PF_>=_1.30": m["pf"] >= 1.30,
        "PASS_STRESS_2x_2ticks": stress_median > 0,
        "max_yr_<=_50pct": ts["max_yr_share_pct"] <= 50.0,
        "yrs_pos_>=_50pct": ts["yrs_pos"] / ts["n_yrs"] >= 0.5,
        "Era3_PF_>=_1.0": ts["era3_pf"] >= 1.0,
        "Era3_median_>=_0": ts["era3_median"] >= 0,
    }


def run():
    print("Cycle 2026-06-11j — Packet #1 NFP-MGC-Long-2h strict-filter re-audit", flush=True)
    print("Per #162 OK A: defensive hygiene before any further search work.\n", flush=True)

    nfp_events = [pd.to_datetime(f"{c['actual_date']} 08:30:00")
                  for c in build_verified_nfp_calendar(2019, 2026)]
    df_mgc = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    print(f"Total scheduled NFP events 2019-2026: {len(nfp_events)}\n", flush=True)

    # Three filter versions
    print("--- Filter version comparison ---", flush=True)
    perm_clean, perm_excl = permissive_filter(nfp_events, df_mgc)
    strict_clean, strict_excl = strict_filter(nfp_events, df_mgc)
    strict_hold_clean, strict_hold_excl = strict_filter_with_hold_continuity(
        nfp_events, df_mgc, hold_bars=24, max_intra_hold_gap_minutes=60)
    print(f"  Permissive filter (cycle 10g): {len(perm_clean)} clean / {len(perm_excl)} excluded", flush=True)
    print(f"  Strict filter (11f/11i):       {len(strict_clean)} clean / {len(strict_excl)} excluded", flush=True)
    print(f"  Strict + hold continuity:      {len(strict_hold_clean)} clean / {len(strict_hold_excl)} excluded", flush=True)

    # Diff: which events does strict exclude that permissive includes?
    perm_set = set(str(e) for e in perm_clean)
    strict_set = set(str(e) for e in strict_clean)
    strict_hold_set = set(str(e) for e in strict_hold_clean)
    perm_minus_strict = perm_set - strict_set
    strict_minus_strict_hold = strict_set - strict_hold_set
    print(f"\n  Permissive but NOT strict ({len(perm_minus_strict)} events): {sorted(perm_minus_strict)[:5]}{'...' if len(perm_minus_strict) > 5 else ''}", flush=True)
    print(f"  Strict but NOT strict+hold ({len(strict_minus_strict_hold)} events): {sorted(strict_minus_strict_hold)[:5]}{'...' if len(strict_minus_strict_hold) > 5 else ''}", flush=True)

    # Run all 3 versions
    print(f"\n--- Three-version backtest ---", flush=True)
    versions = {
        "permissive (cycle 10g basis)": perm_clean,
        "strict (#161-C doctrine)": strict_clean,
        "strict + hold-continuity (most conservative)": strict_hold_clean,
    }
    version_results = {}
    for name, events in versions.items():
        m, trades, sig_hash = run_packet(events, name)
        stress_m = run_stress(events, name)
        ts = temporal_split(trades)
        gates = evaluate_gates(m, ts, stress_m["median"])
        print(f"\n  Version: {name}", flush=True)
        print(f"    n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f} mean=${m['mean']:.2f}", flush=True)
        print(f"    yrs+: {ts['yrs_pos']}/{ts['n_yrs']}, max-yr: {ts['max_yr_share_pct']:.1f}%", flush=True)
        print(f"    Era1 PF: {ts['eras'][0]['pf']:.2f}, Era2 PF: {ts['eras'][1]['pf']:.2f}, Era3 PF: {ts['eras'][2]['pf']:.2f}", flush=True)
        print(f"    Era3 median: ${ts['era3_median']:.2f}", flush=True)
        print(f"    Stress (2x cost + 2 ticks slip): median=${stress_m['median']:.2f} PF={stress_m['pf']:.3f}", flush=True)
        print(f"    Signal hash: {sig_hash}", flush=True)
        print(f"    Gates: {gates}", flush=True)
        print(f"    ALL PASS: {all(gates.values())}", flush=True)
        version_results[name] = {
            "n_events": len(events),
            "metrics": {k: m.get(k) for k in ("n", "pf", "median", "mean", "net", "max_dd")},
            "win_rate": float((trades["pnl"] > 0).mean()) if len(trades) > 0 else 0,
            "temporal_split": ts,
            "stress_metrics": {"median": float(stress_m["median"]), "pf": float(stress_m["pf"]), "n": int(stress_m["n"])},
            "signal_hash": sig_hash,
            "gates": gates,
            "all_gates_pass": all(gates.values()),
        }

    # Summary classification
    print(f"\n=== VERDICT ===", flush=True)
    strict_result = version_results["strict (#161-C doctrine)"]
    strict_hold_result = version_results["strict + hold-continuity (most conservative)"]

    if strict_result["all_gates_pass"] and strict_hold_result["all_gates_pass"]:
        verdict = "PACKET #1 ACCEPTANCE HOLDS — both strict variants pass all gates"
        sprint_status = "YELLOW remains (acceptance survives strict re-audit)"
    elif strict_result["all_gates_pass"]:
        verdict = "PACKET #1 ACCEPTANCE HOLDS — strict passes; strict+hold-continuity does NOT (review for amendment)"
        sprint_status = "YELLOW with amendment"
    else:
        failed = [g for g, v in strict_result["gates"].items() if not v]
        verdict = f"PACKET #1 → REOPEN / REVIEW — strict filter fails: {failed}"
        sprint_status = "RED — accepted packet count becomes 0"

    print(f"  {verdict}", flush=True)
    print(f"  Sprint status: {sprint_status}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-11j_packet1_strict_reaudit.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "Packet #1 NFP-MGC-Long-2h strict-filter re-audit per #162",
        "boundaries": "report-only Lane B; no registry mutation",
        "calendar_source": "verified NFP (used by Packet #1 since 2026-06-04)",
        "filter_versions": {
            "permissive": {"n_clean": len(perm_clean), "n_excluded": len(perm_excl)},
            "strict_next_bar_only": {"n_clean": len(strict_clean), "n_excluded": len(strict_excl)},
            "strict_with_hold_continuity": {"n_clean": len(strict_hold_clean), "n_excluded": len(strict_hold_excl)},
        },
        "events_lost_strict_vs_permissive": sorted(perm_minus_strict),
        "events_lost_hold_vs_strict": sorted(strict_minus_strict_hold),
        "version_results": version_results,
        "verdict": verdict,
        "sprint_status": sprint_status,
        "prior_metrics_for_comparison": {
            "original_accepted_PF": 2.264,
            "permissive_clean_re_audit_PF (10g)": 2.393,
        },
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
