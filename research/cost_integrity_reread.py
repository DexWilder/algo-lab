#!/usr/bin/env python3
"""Cost Integrity Re-Read — Pieces C + D of Item #3 (2026-05-20).

Minimal re-read tool that answers the operator's core question:
"Did the current strategy evidence materially change after costs?"

For each strategy, runs the backtest three times with identical signals:
  1. GROSS  — commission=0, slippage_ticks=0 (the silent-default state that
              affected callers like fql_forge_batch_runner, correlation_matrix,
              run_forward_paper for assets missing from pre-Piece-A SYMBOL_DEFAULTS)
  2. PRIOR  — pre-Piece-I asset_config values (slip=1 across the universe;
              what xb_orb_sweep was actually using before consolidation)
  3. NEW    — post-Piece-I consolidated values (conservative bias; slip=2
              for less-liquid assets including MCL/MYM)

Reports two deltas:
  Delta A = PRIOR → NEW   (the actual probation-baseline shift, since xb_orb_sweep
                           was already using PRIOR cost)
  Delta B = GROSS → NEW   (what the silently-zero-cost callers were missing)

No registry mutation. No status changes. If a candidate drops below a gate,
produce a decision packet — not a state update.

Usage:
    python3 research/cost_integrity_reread.py [--save] [--candidates probation|correlation|all]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest
from engine.asset_config import get_asset
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals


# Pre-Piece-I asset_config cost values (what xb_orb_sweep was actually using).
# Used to compute Delta A. Hardcoded here as historical reference; the live
# values in asset_config.py are now post-Piece-I (more conservative).
PRIOR_COSTS = {
    "MNQ": {"commission_per_side": 0.62, "slippage_ticks": 1},
    "MES": {"commission_per_side": 0.62, "slippage_ticks": 1},
    "MGC": {"commission_per_side": 0.62, "slippage_ticks": 1},
    "M2K": {"commission_per_side": 0.62, "slippage_ticks": 1},
    "MYM": {"commission_per_side": 0.62, "slippage_ticks": 1},
    "MCL": {"commission_per_side": 0.62, "slippage_ticks": 1},
    "SI":  {"commission_per_side": 1.50, "slippage_ticks": 1},
    "HG":  {"commission_per_side": 1.50, "slippage_ticks": 1},
    "ZN":  {"commission_per_side": 1.25, "slippage_ticks": 1},
    "ZF":  {"commission_per_side": 1.25, "slippage_ticks": 1},
    "ZB":  {"commission_per_side": 1.25, "slippage_ticks": 1},
    "6B":  {"commission_per_side": 1.25, "slippage_ticks": 1},
    "6E":  {"commission_per_side": 1.25, "slippage_ticks": 1},
    "6J":  {"commission_per_side": 1.25, "slippage_ticks": 1},
    "ZC":  {"commission_per_side": 1.50, "slippage_ticks": 1},
    "ZS":  {"commission_per_side": 1.50, "slippage_ticks": 1},
    "ZW":  {"commission_per_side": 1.50, "slippage_ticks": 1},
}


# ── Candidate definitions ─────────────────────────────────────────────────────

PROBATION_CANDIDATES = [
    # (strategy_id, asset, entry, filter, exit, params)
    ("XB-ORB-EMA-Ladder-MNQ", "MNQ", "orb_breakout", "ema_slope", "profit_ladder",
     {"stop_mult": 2.0, "target_mult": 4.0, "trail_mult": 2.5}),
    ("XB-ORB-EMA-Ladder-MCL", "MCL", "orb_breakout", "ema_slope", "profit_ladder",
     {"stop_mult": 2.0, "target_mult": 4.0, "trail_mult": 2.5}),
    ("XB-ORB-EMA-Ladder-MYM", "MYM", "orb_breakout", "ema_slope", "profit_ladder",
     {"stop_mult": 2.0, "target_mult": 4.0, "trail_mult": 2.5}),
]


# Exact mirror of the 12 candidates in research/correlation_matrix.py (lines 61-72).
# Params: {"stop_mult": 2.0, "target_mult": 4.0, "trail_mult": 2.5} per
# research/fql_forge_batch_runner.py::PARAMS_DEFAULT (unused params are ignored
# by exits that don't need them).
_PARAMS = {"stop_mult": 2.0, "target_mult": 4.0, "trail_mult": 2.5}
CORRELATION_CANDIDATES = [
    ("XB-PB-EMA-Ladder-MNQ",      "MNQ", "pb_pullback",       "ema_slope", "profit_ladder", _PARAMS),
    ("XB-PB-EMA-Ladder-MCL",      "MCL", "pb_pullback",       "ema_slope", "profit_ladder", _PARAMS),
    ("XB-PB-EMA-Ladder-MYM",      "MYM", "pb_pullback",       "ema_slope", "profit_ladder", _PARAMS),
    ("XB-BB-EMA-Ladder-MNQ",      "MNQ", "bb_reversion",      "ema_slope", "profit_ladder", _PARAMS),
    ("XB-BB-EMA-Ladder-MGC",      "MGC", "bb_reversion",      "ema_slope", "profit_ladder", _PARAMS),
    ("XB-BB-EMA-Ladder-MCL",      "MCL", "bb_reversion",      "ema_slope", "profit_ladder", _PARAMS),
    ("XB-BB-EMA-Ladder-MYM",      "MYM", "bb_reversion",      "ema_slope", "profit_ladder", _PARAMS),
    ("XB-VWAP-EMA-Ladder-MGC",    "MGC", "vwap_continuation", "ema_slope", "profit_ladder", _PARAMS),
    ("XB-VWAP-EMA-Ladder-MCL",    "MCL", "vwap_continuation", "ema_slope", "profit_ladder", _PARAMS),
    ("XB-VWAP-EMA-Ladder-MYM",    "MYM", "vwap_continuation", "ema_slope", "profit_ladder", _PARAMS),
    ("XB-ORB-EMA-Chandelier-MNQ", "MNQ", "orb_breakout",      "ema_slope", "chandelier",    _PARAMS),
    ("XB-ORB-EMA-TimeStop-MNQ",   "MNQ", "orb_breakout",      "ema_slope", "time_stop",     _PARAMS),
]


# ── Metrics ───────────────────────────────────────────────────────────────────

def compute_pf(trades_df: pd.DataFrame) -> float:
    if trades_df is None or len(trades_df) == 0:
        return 0.0
    wins = trades_df.loc[trades_df["pnl"] > 0, "pnl"].sum()
    losses = abs(trades_df.loc[trades_df["pnl"] < 0, "pnl"].sum())
    if losses == 0:
        return float("inf") if wins > 0 else 0.0
    return float(wins / losses)


def cost_per_round_turn(stats: dict) -> float:
    """Approximate per-trade cost in dollars (commission both sides + slippage both sides)."""
    n = max(stats.get("total_trades", 0), 1)
    return float(stats["costs"]["total_friction"] / n)


def concern_level(net_pf: float) -> str:
    """Backtest-PF gate per ELITE_PROMOTION_STANDARDS.md: >=1.2 workhorse primary."""
    if net_pf >= 1.20:
        return "GREEN"
    if net_pf >= 1.05:
        return "YELLOW"
    return "RED"


def verdict_changed(prior_pf: float, new_pf: float, gate: float = 1.20) -> bool:
    return (prior_pf >= gate) != (new_pf >= gate)


# ── Re-read ──────────────────────────────────────────────────────────────────

def reread_one(strategy_id, asset, entry, filt, exit_name, params) -> dict:
    data_path = ROOT / f"data/processed/{asset}_5m.csv"
    if not data_path.exists():
        return {"strategy_id": strategy_id, "asset": asset, "error": f"no data at {data_path}"}

    df = pd.read_csv(data_path)
    df["datetime"] = pd.to_datetime(df["datetime"])

    signals = generate_crossbred_signals(
        df, entry_name=entry, exit_name=exit_name, filter_name=filt, params=params,
    )

    asset_cfg = get_asset(asset)
    point_value = asset_cfg["point_value"]
    tick_size = asset_cfg["tick_size"]
    prior = PRIOR_COSTS.get(asset, {})

    def _run(commission, slip):
        res = run_backtest(
            df, signals, mode="both",
            point_value=point_value, tick_size=tick_size,
            commission_per_side=commission, slippage_ticks=slip,
        )
        return res

    # 1. GROSS (zero-cost)
    gross = _run(0.0, 0)
    # 2. PRIOR (pre-Piece-I asset_config values)
    prior_res = _run(prior.get("commission_per_side", 0.62), prior.get("slippage_ticks", 1))
    # 3. NEW (post-Piece-I consolidated, pulled fresh from asset_config)
    new_res = _run(asset_cfg["commission_per_side"], asset_cfg["slippage_ticks"])

    def _row(label, res):
        t = res["trades_df"]
        return {
            f"{label}_pf": round(compute_pf(t), 3),
            f"{label}_pnl": round(float(t["pnl"].sum()) if len(t) else 0.0, 0),
            f"{label}_trades": int(len(t)),
            f"{label}_avg_trade": round(float(t["pnl"].mean()) if len(t) else 0.0, 2),
            f"{label}_cost_per_rt": round(cost_per_round_turn(res["stats"]), 2),
        }

    metrics = {"strategy_id": strategy_id, "asset": asset}
    metrics.update(_row("gross", gross))
    metrics.update(_row("prior", prior_res))
    metrics.update(_row("new", new_res))

    # Deltas
    metrics["delta_A_pf"] = round(metrics["new_pf"] - metrics["prior_pf"], 3)
    metrics["delta_A_pnl"] = round(metrics["new_pnl"] - metrics["prior_pnl"], 0)
    metrics["delta_B_pf"] = round(metrics["new_pf"] - metrics["gross_pf"], 3)
    metrics["delta_B_pnl"] = round(metrics["new_pnl"] - metrics["gross_pnl"], 0)

    # Cost as % of gross avg trade
    if metrics["gross_avg_trade"] > 0:
        metrics["new_cost_pct_of_gross_avg"] = round(
            100.0 * metrics["new_cost_per_rt"] / metrics["gross_avg_trade"], 1,
        )
    else:
        metrics["new_cost_pct_of_gross_avg"] = None

    # Cost assumption summary
    metrics["new_cost_assumption"] = (
        f"comm=${asset_cfg['commission_per_side']:.2f}, "
        f"slip={asset_cfg['slippage_ticks']}t"
    )

    # Verdict change (gate=1.20 backtest workhorse threshold)
    metrics["verdict_changed_A"] = verdict_changed(metrics["prior_pf"], metrics["new_pf"])
    metrics["verdict_changed_B"] = verdict_changed(metrics["gross_pf"], metrics["new_pf"])

    # Concern level (on the NEW net PF)
    metrics["concern_level"] = concern_level(metrics["new_pf"])

    return metrics


def reread_all(candidates) -> list:
    rows = []
    for c in candidates:
        try:
            rows.append(reread_one(*c))
        except Exception as e:
            rows.append({"strategy_id": c[0], "asset": c[1], "error": str(e)})
    return rows


# ── Reporting ────────────────────────────────────────────────────────────────

def render_table(rows: list) -> str:
    if not rows:
        return "(no rows)"

    cols = [
        ("strategy_id", "Strategy"),
        ("asset", "Asset"),
        ("gross_pf", "Gross PF"),
        ("prior_pf", "Prior net PF"),
        ("new_pf", "New net PF"),
        ("delta_A_pf", "Δ-A"),
        ("delta_B_pf", "Δ-B"),
        ("gross_pnl", "Gross PnL"),
        ("new_pnl", "New net PnL"),
        ("gross_avg_trade", "Gross avg"),
        ("new_avg_trade", "New avg"),
        ("new_cost_per_rt", "Cost/RT $"),
        ("new_cost_pct_of_gross_avg", "Cost %"),
        ("new_cost_assumption", "Cost assumption"),
        ("verdict_changed_A", "Verdict Δ-A"),
        ("verdict_changed_B", "Verdict Δ-B"),
        ("concern_level", "Concern"),
    ]

    out = ["| " + " | ".join(label for _, label in cols) + " |"]
    out.append("|" + "|".join(["---"] * len(cols)) + "|")
    for r in rows:
        if "error" in r:
            out.append(f"| {r['strategy_id']} | {r['asset']} | ERROR: {r['error']} |" + " |" * (len(cols) - 3))
            continue
        row_cells = []
        for key, _ in cols:
            v = r.get(key)
            if isinstance(v, bool):
                v = "yes" if v else "no"
            elif v is None:
                v = "—"
            row_cells.append(str(v))
        out.append("| " + " | ".join(row_cells) + " |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true",
                    help="Write report + JSON to docs/reports/cost_integrity_reset/")
    ap.add_argument("--candidates", choices=["probation", "correlation", "all"], default="probation")
    args = ap.parse_args()

    if args.candidates == "probation":
        candidates = PROBATION_CANDIDATES
        label = "probation"
    elif args.candidates == "correlation":
        candidates = CORRELATION_CANDIDATES
        label = "correlation"
    else:
        candidates = PROBATION_CANDIDATES + CORRELATION_CANDIDATES
        label = "all"

    print(f"Cost integrity re-read — {label} candidates ({len(candidates)} total)\n")
    rows = reread_all(candidates)

    print(render_table(rows))

    # Concern summary
    print("\n=== Concern summary ===")
    for level in ("GREEN", "YELLOW", "RED"):
        names = [r["strategy_id"] for r in rows if r.get("concern_level") == level]
        if names:
            print(f"  {level}: {', '.join(names)}")

    if args.save:
        out_dir = ROOT / "docs" / "reports" / "cost_integrity_reset"
        out_dir.mkdir(parents=True, exist_ok=True)
        date = pd.Timestamp.today().strftime("%Y-%m-%d")
        md_path = out_dir / f"{date}_cost_integrity_reread_{label}.md"
        json_path = out_dir / f"{date}_cost_integrity_reread_{label}.json"
        md_path.write_text(
            f"# Cost Integrity Re-Read — {label} candidates ({date})\n\n"
            f"Per Item #3 Piece {'C' if label == 'probation' else 'D'} "
            f"(`docs/_DRAFT_2026-05-19_item3_cost_slippage_preflight.md`).\n\n"
            f"**Source of truth:** `engine/asset_config.py` (post-Piece-I consolidation).\n\n"
            f"**Cost assumptions are estimated** — broker/firm rate sheets should "
            f"replace these before paper/prop, especially for ZN/ZF/ZB, FX, MCL, MYM.\n\n"
            f"**Deltas:**\n"
            f"- Δ-A = PRIOR net (pre-Piece-I asset_config) → NEW net (post-Piece-I)\n"
            f"- Δ-B = GROSS (silent zero-cost; what fql_forge_batch_runner / correlation_matrix / "
            f"run_forward_paper produced for unconfigured assets) → NEW net\n\n"
            f"**Concern levels** (on NEW net PF, backtest workhorse gate 1.20):\n"
            f"- GREEN: net PF ≥ 1.20\n"
            f"- YELLOW: net PF in [1.05, 1.20)\n"
            f"- RED: net PF < 1.05\n\n"
            f"## Per-candidate table\n\n"
            + render_table(rows)
            + "\n"
        )
        json_path.write_text(json.dumps(rows, indent=2, default=str))
        print(f"\nSaved:\n  {md_path}\n  {json_path}")


if __name__ == "__main__":
    main()
