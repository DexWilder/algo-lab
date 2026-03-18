#!/usr/bin/env python3
"""FQL Edge Vitality Monitor — Unified decay detection.

Combines three data sources into one Edge Vitality Score per strategy:
  - Backtest decay trajectory (from half-life monitor)
  - Forward deviation (from drift monitor)
  - Forward-specific decay (from trade log, when enough trades exist)

Output: a single score per strategy, VITAL / STABLE / FADING / DEAD.
Added to daily pipeline. Writes to registry as edge_vitality field.

Read-only analytics. Does not modify live trading logic.

Usage:
    python3 research/edge_vitality_monitor.py              # Full report
    python3 research/edge_vitality_monitor.py --json       # JSON output
    python3 research/edge_vitality_monitor.py --save       # Save + update registry
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
DRIFT_LOG_PATH = ROOT / "research" / "data" / "live_drift_log.json"
TRADE_LOG_PATH = ROOT / "logs" / "trade_log.csv"
REPORTS_DIR = ROOT / "research" / "reports"

TODAY = datetime.now().strftime("%Y-%m-%d")

# Vitality thresholds
VITAL_THRESHOLD = 0.7
STABLE_THRESHOLD = 0.4
FADING_THRESHOLD = 0.1

# Weights for composite score
W_FORWARD_DEVIATION = 0.40
W_BACKTEST_DECAY = 0.30
W_FORWARD_DECAY = 0.30


# ── Data Sources ─────────────────────────────────────────────────────────────

def load_half_life_data():
    """Load decay scores from registry (set by half-life monitor)."""
    if not REGISTRY_PATH.exists():
        return {}
    reg = json.load(open(REGISTRY_PATH))
    result = {}
    for s in reg.get("strategies", []):
        if s.get("status") not in ("core", "probation", "watch"):
            continue
        sid = s["strategy_id"]
        hl_status = s.get("half_life_status", "UNKNOWN")

        # Map half-life status to a 0-1 score (1 = healthy, 0 = dead)
        hl_score = {
            "HEALTHY": 1.0,
            "MONITOR": 0.65,
            "DECAYING": 0.35,
            "ARCHIVE_CANDIDATE": 0.1,
            "ERROR": 0.5,       # Unknown — neutral assumption
            "UNKNOWN": 0.5,
        }.get(hl_status, 0.5)

        result[sid] = {
            "half_life_status": hl_status,
            "backtest_decay_score": hl_score,
        }
    return result


def load_drift_data():
    """Load latest drift severity from drift log."""
    if not DRIFT_LOG_PATH.exists():
        return {}
    try:
        log = json.load(open(DRIFT_LOG_PATH))
        if not log:
            return {}
        latest = log[-1]
    except Exception:
        return {}

    result = {}
    for sid, sdata in latest.get("strategies", {}).items():
        # Get the worst session severity for this strategy
        worst_severity = "NORMAL"
        for sess, info in sdata.get("sessions", {}).items():
            sev = info.get("severity", "NORMAL")
            if sev == "ALARM":
                worst_severity = "ALARM"
            elif sev == "DRIFT" and worst_severity != "ALARM":
                worst_severity = "DRIFT"

        # Map drift severity to a 0-1 score (1 = no drift, 0 = alarm)
        drift_score = {
            "NORMAL": 1.0,
            "DRIFT": 0.5,
            "ALARM": 0.15,
        }.get(worst_severity, 0.5)

        result[sid] = {
            "drift_severity": worst_severity,
            "forward_deviation_score": drift_score,
        }
    return result


def load_forward_decay():
    """Compute forward-specific decay from trade log.

    For strategies with 10+ forward trades, compute a simple decay signal:
    compare the PnL of the first half of forward trades to the second half.
    If the second half is worse, the forward edge is decaying.
    """
    if not TRADE_LOG_PATH.exists():
        return {}

    try:
        df = pd.read_csv(TRADE_LOG_PATH)
    except Exception:
        return {}

    if df.empty or "strategy" not in df.columns or "pnl" not in df.columns:
        return {}

    result = {}
    for sid, grp in df.groupby("strategy"):
        n = len(grp)
        if n < 6:
            result[sid] = {
                "forward_trades": n,
                "forward_decay_score": None,  # Insufficient data
                "forward_decay_label": "INSUFFICIENT",
            }
            continue

        # Split into first half and second half
        mid = n // 2
        first_half = grp.iloc[:mid]
        second_half = grp.iloc[mid:]

        first_avg = first_half["pnl"].mean()
        second_avg = second_half["pnl"].mean()

        # Decay ratio: how much of the first-half performance survived
        if abs(first_avg) < 0.01:
            # First half was flat — can't compute meaningful decay
            decay_score = 0.5
        elif first_avg > 0:
            # First half positive — second half should also be positive
            decay_score = max(0, min(1, second_avg / first_avg))
        else:
            # First half negative — second half less negative = improvement
            decay_score = max(0, min(1, first_avg / second_avg)) if second_avg < 0 else 0.8

        label = "IMPROVING" if decay_score > 0.8 else \
                "STABLE" if decay_score > 0.5 else \
                "DECLINING" if decay_score > 0.2 else "COLLAPSING"

        result[sid] = {
            "forward_trades": n,
            "first_half_avg_pnl": round(first_avg, 2),
            "second_half_avg_pnl": round(second_avg, 2),
            "forward_decay_score": round(decay_score, 3),
            "forward_decay_label": label,
        }

    return result


# ── Composite Vitality Score ─────────────────────────────────────────────────

def compute_vitality(half_life_data, drift_data, forward_decay_data):
    """Compute unified Edge Vitality Score per strategy.

    Weights:
      40% forward deviation (drift monitor)
      30% backtest decay trajectory (half-life)
      30% forward-specific decay (trade log, if available)

    If forward decay is unavailable, redistribute weight to backtest.
    """
    # Collect all active strategy IDs
    all_sids = set(half_life_data.keys()) | set(drift_data.keys())

    results = {}
    for sid in sorted(all_sids):
        hl = half_life_data.get(sid, {})
        dr = drift_data.get(sid, {})
        fd = forward_decay_data.get(sid, {})

        backtest_score = hl.get("backtest_decay_score", 0.5)
        deviation_score = dr.get("forward_deviation_score", 0.5)
        forward_score = fd.get("forward_decay_score")

        if forward_score is not None:
            # All three sources available
            vitality = (
                W_FORWARD_DEVIATION * deviation_score +
                W_BACKTEST_DECAY * backtest_score +
                W_FORWARD_DECAY * forward_score
            )
        else:
            # No forward decay data — redistribute to backtest
            vitality = (
                W_FORWARD_DEVIATION * deviation_score +
                (W_BACKTEST_DECAY + W_FORWARD_DECAY) * backtest_score
            )

        # Classify
        if vitality >= VITAL_THRESHOLD:
            tier = "VITAL"
        elif vitality >= STABLE_THRESHOLD:
            tier = "STABLE"
        elif vitality >= FADING_THRESHOLD:
            tier = "FADING"
        else:
            tier = "DEAD"

        results[sid] = {
            "vitality_score": round(vitality, 3),
            "tier": tier,
            "backtest_decay": backtest_score,
            "forward_deviation": deviation_score,
            "forward_decay": forward_score,
            "half_life_status": hl.get("half_life_status", "UNKNOWN"),
            "drift_severity": dr.get("drift_severity", "UNKNOWN"),
            "forward_trades": fd.get("forward_trades", 0),
            "forward_decay_label": fd.get("forward_decay_label", "NO_DATA"),
        }

    return results


# ── Display ──────────────────────────────────────────────────────────────────

def print_vitality_report(results):
    W = 80
    print()
    print("=" * W)
    print("  FQL EDGE VITALITY MONITOR")
    print(f"  {TODAY}")
    print("=" * W)

    # Sort by vitality score ascending (worst first = most urgent)
    sorted_results = sorted(results.items(), key=lambda x: x[1]["vitality_score"])

    # Tier summary
    tiers = {"VITAL": 0, "STABLE": 0, "FADING": 0, "DEAD": 0}
    for _, v in sorted_results:
        tiers[v["tier"]] += 1

    print(f"\n  SUMMARY: {tiers['VITAL']} VITAL | {tiers['STABLE']} STABLE | "
          f"{tiers['FADING']} FADING | {tiers['DEAD']} DEAD")

    # Alerts first
    fading_or_dead = [(sid, v) for sid, v in sorted_results
                       if v["tier"] in ("FADING", "DEAD")]
    if fading_or_dead:
        print(f"\n  ALERTS")
        print(f"  {'-' * (W-4)}")
        for sid, v in fading_or_dead:
            print(f"  !! {v['tier']:6s} {sid:<35s} vitality={v['vitality_score']:.3f}  "
                  f"HL={v['half_life_status']:<12s} drift={v['drift_severity']:<8s} "
                  f"fwd_decay={v['forward_decay_label']}")
    else:
        print(f"\n  No FADING or DEAD strategies. Portfolio edge health is good.")

    # Full table
    print(f"\n  FULL VITALITY TABLE (worst-first)")
    print(f"  {'-' * (W-4)}")
    print(f"  {'Strategy':<35s} {'Vital':>6s} {'Tier':>7s} "
          f"{'BT':>5s} {'Drift':>5s} {'Fwd':>5s} {'FwdTr':>5s}")
    print(f"  {'-'*35} {'-'*6} {'-'*7} {'-'*5} {'-'*5} {'-'*5} {'-'*5}")

    for sid, v in sorted_results:
        bt = f"{v['backtest_decay']:.2f}"
        dr = f"{v['forward_deviation']:.2f}"
        fd = f"{v['forward_decay']:.2f}" if v['forward_decay'] is not None else "  —"
        ft = f"{v['forward_trades']:>5d}" if v['forward_trades'] > 0 else "    0"
        tier_marker = " ◄" if v["tier"] in ("FADING", "DEAD") else ""
        print(f"  {sid:<35s} {v['vitality_score']:>6.3f} {v['tier']:>7s} "
              f"{bt:>5s} {dr:>5s} {fd:>5s} {ft}{tier_marker}")

    print(f"\n  Weights: Forward deviation {W_FORWARD_DEVIATION:.0%}, "
          f"Backtest decay {W_BACKTEST_DECAY:.0%}, "
          f"Forward decay {W_FORWARD_DECAY:.0%}")
    print(f"  Thresholds: VITAL>{VITAL_THRESHOLD}, STABLE>{STABLE_THRESHOLD}, "
          f"FADING>{FADING_THRESHOLD}, DEAD<={FADING_THRESHOLD}")

    print(f"\n{'=' * W}")


# ── Registry Update ──────────────────────────────────────────────────────────

def update_registry(results):
    """Write edge_vitality score and tier to registry."""
    if not REGISTRY_PATH.exists():
        return

    from research.utils.atomic_io import atomic_write_json
    reg = json.load(open(REGISTRY_PATH))

    for s in reg.get("strategies", []):
        sid = s["strategy_id"]
        if sid in results:
            s["edge_vitality"] = results[sid]["vitality_score"]
            s["edge_vitality_tier"] = results[sid]["tier"]

    atomic_write_json(REGISTRY_PATH, reg)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FQL Edge Vitality Monitor")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--save", action="store_true",
                        help="Save report + update registry vitality scores")
    args = parser.parse_args()

    hl_data = load_half_life_data()
    drift_data = load_drift_data()
    forward_data = load_forward_decay()

    results = compute_vitality(hl_data, drift_data, forward_data)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print_vitality_report(results)

    if args.save:
        update_registry(results)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d")
        out = REPORTS_DIR / f"edge_vitality_{ts}.json"
        from research.utils.atomic_io import atomic_write_json
        atomic_write_json(out, {"date": TODAY, "results": results})
        print(f"\n  Registry updated with vitality scores.")
        print(f"  Report saved: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
