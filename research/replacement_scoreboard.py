#!/usr/bin/env python3
"""FQL Replacement Scoreboard — Challenger vs Incumbent Board.

Read-only analytics. Shows every active strategy's rubric score,
displacement vulnerability, challenger pipeline, and deadline pressure.

Makes competitive pressure visible in every review cycle. Prevents
weak incumbents from surviving by default and strong challengers from
waiting unnoticed.

Usage:
    python3 research/replacement_scoreboard.py              # Full board
    python3 research/replacement_scoreboard.py --json       # JSON output
    python3 research/replacement_scoreboard.py --save       # Save to reports/
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.utils.atomic_io import atomic_write_json

REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
GENOME_PATH = ROOT / "research" / "data" / "strategy_genome_map.json"
REPORTS_DIR = ROOT / "research" / "reports"
TRADE_LOG = ROOT / "logs" / "trade_log.csv"

TODAY = datetime.now().strftime("%Y-%m-%d")

# Rubric score cache field in registry
RUBRIC_FIELD = "rubric_score"

# Known rubric scores from the 2026-03-18 incumbent review
# These are the authoritative scores until re-scored
KNOWN_RUBRIC = {
    "XB-PB-EMA-MES-Short": 20,
    "ORB-MGC-Long": 19,
    "BB-EQ-MGC-Long": 18,
    "PB-MGC-Short": 16,
    "PreFOMC-Drift-Equity": 22,
    "DailyTrend-MGC-Long": 21,
    "MomPB-6J-Long-US": 19,
    "NoiseBoundary-MNQ-Long": 18,
    "TV-NFP-High-Low-Levels": 18,
    "FXBreak-6J-Short-London": 17,
    "TTMSqueeze-M2K-Short": 17,
    "GapMom": 16,
    "CloseVWAP-M2K-Short": 16,
    "MomIgn-M2K-Short": 14,
    "Commodity-TermStructure-Carry-EnergyMetals": 17,
    "Treasury-Rolldown-Carry-Spread": 18,
}

# Current factor/asset gaps for bonus computation
# CARRY removed 2026-04-14: closed by Treasury-Rolldown-Carry-Spread
# re-probation via out-of-band monthly path. STRUCTURAL remains open
# (FXBreak-6J archived with verified failure mode; no replacement).
FACTOR_GAPS = {"STRUCTURAL"}
ASSET_GAPS = {"MCL", "ZN", "ZF", "ZB", "6B"}  # 0 active strategies

GAP_BONUS = 2


# ── Data Loading ─────────────────────────────────────────────────────────────

def load_registry():
    if not REGISTRY_PATH.exists():
        return []
    return json.load(open(REGISTRY_PATH)).get("strategies", [])


def load_forward_trades():
    """Load forward trade counts and PnL per strategy."""
    if not TRADE_LOG.exists():
        return {}
    try:
        import pandas as pd
        df = pd.read_csv(TRADE_LOG)
        result = {}
        if "strategy" in df.columns and "pnl" in df.columns:
            for sid, grp in df.groupby("strategy"):
                result[sid] = {
                    "trades": len(grp),
                    "pnl": round(float(grp["pnl"].sum()), 2),
                }
        return result
    except Exception:
        return {}


def get_rubric_score(strategy):
    """Get rubric score from cache or known scores."""
    sid = strategy["strategy_id"]
    # Check registry field first
    cached = strategy.get(RUBRIC_FIELD)
    if cached is not None:
        return cached
    # Fall back to known scores
    return KNOWN_RUBRIC.get(sid)


def compute_gap_bonus(strategy):
    """Compute +2 gap bonus if strategy fills a factor or asset gap."""
    tags = strategy.get("tags", [])
    asset = strategy.get("asset", "")
    bonus = 0
    # Factor gap
    for factor in FACTOR_GAPS:
        if factor in tags:
            bonus = GAP_BONUS
            break
    # Asset gap
    if asset in ASSET_GAPS:
        bonus = max(bonus, GAP_BONUS)
    return bonus


def compute_deadline_days(strategy):
    """Compute days until deadline from notes."""
    notes = strategy.get("notes", "")
    for token in notes.split():
        if token.startswith("2026-") and len(token) == 10:
            try:
                deadline = datetime.strptime(token, "%Y-%m-%d")
                delta = (deadline - datetime.now()).days
                if 0 < delta < 365:
                    return delta
            except ValueError:
                continue
    return None


def estimate_survival(strategy, forward_data):
    """Estimate whether a watch strategy will survive its deadline."""
    sid = strategy["strategy_id"]
    fwd = forward_data.get(sid, {"trades": 0, "pnl": 0})
    notes = strategy.get("notes", "")

    if fwd["trades"] == 0:
        return "NO_EVIDENCE"

    # Very rough: positive forward PnL = likely, negative = unlikely
    if fwd["pnl"] > 0 and fwd["trades"] >= 5:
        return "LIKELY"
    elif fwd["pnl"] > 0:
        return "POSSIBLE"
    elif fwd["trades"] >= 10:
        return "UNLIKELY"
    else:
        return "UNCERTAIN"


# ── Scoreboard Building ──────────────────────────────────────────────────────

def build_scoreboard(strategies, forward_data):
    """Build the full replacement scoreboard."""
    board = {
        "generated": TODAY,
        "core": [],
        "conviction": [],
        "watch": [],
        "challengers": [],
        "weakest_core": None,
        "weakest_watch": None,
        "top_challenger": None,
    }

    for s in strategies:
        status = s.get("status")
        sid = s["strategy_id"]
        score = get_rubric_score(s)
        if score is None:
            continue

        gap_bonus = compute_gap_bonus(s)
        effective_score = score + gap_bonus
        fwd = forward_data.get(sid, {"trades": 0, "pnl": 0})
        deadline_days = compute_deadline_days(s)

        entry = {
            "strategy_id": sid,
            "asset": s.get("asset", "?"),
            "factor": [t for t in s.get("tags", []) if t in
                       ("MOMENTUM", "MEAN_REVERSION", "VOLATILITY", "CARRY",
                        "EVENT", "STRUCTURAL", "VALUE")],
            "session": s.get("session", "?"),
            "rubric_score": score,
            "gap_bonus": gap_bonus,
            "effective_score": effective_score,
            "forward_trades": fwd["trades"],
            "forward_pnl": fwd["pnl"],
            "deadline_days": deadline_days,
            "controller_action": s.get("controller_action", "?"),
            "half_life": s.get("half_life_status", "?"),
            "kill_flag": s.get("kill_flag"),
        }

        if status == "core":
            board["core"].append(entry)
        elif status == "probation":
            board["conviction"].append(entry)
        elif status == "watch":
            entry["survival"] = estimate_survival(s, forward_data)
            board["watch"].append(entry)
        elif status == "testing":
            # Challengers
            entry["lifecycle_stage"] = s.get("lifecycle_stage", "?")
            # Identify which incumbent this would challenge
            targets = []
            if effective_score > 16:  # Could challenge PB-MGC-Short
                targets.append("PB-MGC-Short (core, 16)")
            if effective_score > 14:  # Could challenge MomIgn
                targets.append("MomIgn-M2K-Short (watch, 14)")
            entry["displacement_targets"] = targets
            board["challengers"].append(entry)

    # Sort each bucket
    board["core"] = sorted(board["core"], key=lambda x: x["rubric_score"])
    board["conviction"] = sorted(board["conviction"],
                                  key=lambda x: x["rubric_score"], reverse=True)
    board["watch"] = sorted(board["watch"], key=lambda x: x["rubric_score"])
    board["challengers"] = sorted(board["challengers"],
                                   key=lambda x: x["effective_score"], reverse=True)

    # Identify key positions
    if board["core"]:
        board["weakest_core"] = board["core"][0]
    if board["watch"]:
        board["weakest_watch"] = board["watch"][0]
    if board["challengers"]:
        board["top_challenger"] = board["challengers"][0]

    return board


# ── Display ──────────────────────────────────────────────────────────────────

def print_scoreboard(board):
    W = 75
    print()
    print("=" * W)
    print("  FQL REPLACEMENT SCOREBOARD")
    print(f"  {board['generated']}")
    print("=" * W)

    # Core vulnerability
    print(f"\n  CORE VULNERABILITY")
    print(f"  {'-' * (W-4)}")
    if board["weakest_core"]:
        wc = board["weakest_core"]
        print(f"  WEAKEST: {wc['strategy_id']} (score {wc['rubric_score']}, "
              f"{wc['asset']}, fwd: {wc['forward_trades']} trades ${wc['forward_pnl']:+,.0f})")
    for entry in reversed(board["core"]):
        flag = " ◄ VULNERABLE" if entry["rubric_score"] < 18 else ""
        print(f"  {entry['rubric_score']:>3d}  {entry['strategy_id']:<35s} "
              f"{entry['asset']:<6s} fwd:{entry['forward_trades']:>3d} "
              f"${entry['forward_pnl']:>+8,.0f}{flag}")

    # Conviction
    print(f"\n  CONVICTION PROBATION (rubric >= 18 required)")
    print(f"  {'-' * (W-4)}")
    for entry in board["conviction"]:
        event_tag = " [0.5 slot]" if "EVENT" in entry.get("factor", []) else ""
        print(f"  {entry['rubric_score']:>3d}  {entry['strategy_id']:<35s} "
              f"{entry['asset']:<6s} {entry['half_life']:<12s}{event_tag}")

    # Watch
    print(f"\n  WATCH (deadline pressure)")
    print(f"  {'-' * (W-4)}")
    for entry in board["watch"]:
        days = entry.get("deadline_days")
        days_str = f"{days}d" if days else "?"
        surv = entry.get("survival", "?")
        expiry = " ◄ FIRST EXPIRY" if entry["rubric_score"] <= 14 else ""
        print(f"  {entry['rubric_score']:>3d}  {entry['strategy_id']:<35s} "
              f"{entry['asset']:<6s} deadline:{days_str:<5s} "
              f"survive:{surv:<12s}{expiry}")

    # Challengers
    print(f"\n  CHALLENGERS (testing stage)")
    print(f"  {'-' * (W-4)}")
    for entry in board["challengers"]:
        bonus_str = f"(+{entry['gap_bonus']})" if entry['gap_bonus'] > 0 else ""
        targets = ", ".join(entry.get("displacement_targets", []))
        blocked = ""
        if not targets:
            blocked = " [no viable target]"
            # Check if blocked by factor cap
            if "MOMENTUM" in entry.get("factor", []):
                blocked = " [BLOCKED: MOMENTUM > 50%]"
        print(f"  {entry['effective_score']:>3d}{bonus_str:<4s} "
              f"{entry['strategy_id']:<40s} "
              f"→ {targets}{blocked}")

    # Highest-leverage battle
    print(f"\n  HIGHEST-LEVERAGE REPLACEMENT BATTLE")
    print(f"  {'-' * (W-4)}")
    tc = board.get("top_challenger")
    ww = board.get("weakest_watch")
    if tc and ww:
        print(f"  {tc['strategy_id']} ({tc['effective_score']}) "
              f"→ displaces → "
              f"{ww['strategy_id']} ({ww['rubric_score']})")
        if tc.get("gap_bonus", 0) > 0:
            factors = ", ".join(tc.get("factor", []))
            print(f"  Gap value: +{tc['gap_bonus']} ({factors} + {tc['asset']})")
    else:
        print(f"  No active displacement battle.")

    print(f"\n{'=' * W}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FQL Replacement Scoreboard")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    strategies = load_registry()
    forward_data = load_forward_trades()
    board = build_scoreboard(strategies, forward_data)

    if args.json:
        print(json.dumps(board, indent=2, default=str))
    else:
        print_scoreboard(board)

    if args.save:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d")
        out = REPORTS_DIR / f"replacement_scoreboard_{ts}.json"
        atomic_write_json(out, board)
        print(f"\n  Saved: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
