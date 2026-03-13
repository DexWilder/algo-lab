#!/usr/bin/env python3
"""Portfolio Opportunity Map — structural gap analysis for research direction.

READ-ONLY tool. Does NOT modify any execution pipeline files.

Analyzes the current portfolio across four dimensions and identifies
specific gaps that should guide strategy discovery research:
  1. Asset gaps — which futures markets lack edge coverage
  2. Session gaps — which time-of-day windows are underrepresented
  3. Regime gaps — which market conditions have weak/no coverage
  4. Strategy family gaps — which strategy archetypes are missing

Uses backtest data from existing portfolio + regime engine to produce
a structured research priority map.

Usage:
    python3 research/portfolio_opportunity_map.py          # full analysis
    python3 research/portfolio_opportunity_map.py --save   # save to reports/
    python3 research/portfolio_opportunity_map.py --json   # save JSON output
"""

import argparse
import importlib.util
import inspect
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest
from engine.regime_engine import RegimeEngine
from engine.strategy_controller import StrategyController, PORTFOLIO_CONFIG

# ── Constants ─────────────────────────────────────────────────────────────────

PROCESSED_DIR = ROOT / "data" / "processed"
TODAY = datetime.now().strftime("%Y-%m-%d")

ASSET_CONFIG = {
    "MES": {"point_value": 5.0, "tick_size": 0.25},
    "MNQ": {"point_value": 2.0, "tick_size": 0.25},
    "MGC": {"point_value": 10.0, "tick_size": 0.10},
    "M2K": {"point_value": 5.0, "tick_size": 0.10},
    "MCL": {"point_value": 100.0, "tick_size": 0.01},
    "MYM": {"point_value": 0.50, "tick_size": 1.0},
    "ZN":  {"point_value": 1000.0, "tick_size": 0.015625},
    "ZB":  {"point_value": 1000.0, "tick_size": 0.03125},
    "ES":  {"point_value": 50.0, "tick_size": 0.25},
}

# All available data files
AVAILABLE_ASSETS = sorted([
    p.stem.replace("_5m", "")
    for p in PROCESSED_DIR.glob("*_5m.csv")
])

# Strategy family classification for existing portfolio
STRATEGY_FAMILIES = {
    "PB-MGC-Short":                {"family": "pullback", "sub": "trend_pullback"},
    "ORB-MGC-Long":                {"family": "breakout", "sub": "opening_range_breakout"},
    "VWAP-MNQ-Long":               {"family": "trend", "sub": "vwap_trend_continuation"},
    "XB-PB-EMA-MES-Short":         {"family": "pullback", "sub": "ema_pullback"},
    "BB-EQ-MGC-Long":              {"family": "mean_reversion", "sub": "bb_equilibrium"},
    "Donchian-MNQ-Long-GRINDING":  {"family": "trend", "sub": "donchian_breakout"},
}

# All known strategy families (what a complete portfolio would cover)
ALL_FAMILIES = {
    "pullback": {
        "description": "Trend pullback entries on retracements",
        "subtypes": ["trend_pullback", "ema_pullback", "fib_pullback"],
    },
    "breakout": {
        "description": "Range/level breakout entries",
        "subtypes": ["opening_range_breakout", "donchian_breakout",
                     "compression_breakout", "range_expansion"],
    },
    "mean_reversion": {
        "description": "Fade overextension back to mean",
        "subtypes": ["bb_equilibrium", "vwap_mean_reversion",
                     "exhaustion_reversal", "range_fade"],
    },
    "trend": {
        "description": "Trend continuation / momentum",
        "subtypes": ["vwap_trend_continuation", "donchian_breakout",
                     "momentum_continuation", "ema_crossover"],
    },
    "volatility_expansion": {
        "description": "Entries on vol expansion after compression",
        "subtypes": ["atr_expansion", "bb_squeeze_breakout",
                     "keltner_breakout", "compression_breakout"],
    },
    "time_based": {
        "description": "Session/time-of-day specific edges",
        "subtypes": ["overnight", "afternoon_breakout", "close_reversion",
                     "power_hour", "london_open"],
    },
    "event_driven": {
        "description": "Reactions to macro events / news",
        "subtypes": ["news_reaction", "macro_release", "gap_fill"],
    },
}

# Session windows (ET)
SESSION_WINDOWS = {
    "pre_market":   {"start": 8, "end": 9, "label": "Pre-Market (8:00-9:00)"},
    "open":         {"start": 9, "end": 10, "label": "Open (9:00-10:00)"},
    "morning":      {"start": 10, "end": 12, "label": "Morning (10:00-12:00)"},
    "midday":       {"start": 12, "end": 14, "label": "Midday (12:00-14:00)"},
    "afternoon":    {"start": 14, "end": 15, "label": "Afternoon (14:00-15:00)"},
    "close":        {"start": 15, "end": 16, "label": "Close (15:00-16:00)"},
    "overnight":    {"start": 18, "end": 8, "label": "Overnight (18:00-8:00)"},
}


# ── Data Loading ──────────────────────────────────────────────────────────────

def load_strategy_module(name: str):
    path = ROOT / "strategies" / name / "strategy.py"
    if not path.exists():
        raise FileNotFoundError(f"Strategy not found: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_data(asset: str) -> pd.DataFrame:
    csv_path = PROCESSED_DIR / f"{asset}_5m.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Data file not found: {csv_path}")
    df = pd.read_csv(csv_path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def generate_signals_for_strategy(strat_cfg: dict, df: pd.DataFrame):
    asset = strat_cfg["asset"]
    config = ASSET_CONFIG.get(asset, {})
    tick_size = config.get("tick_size", 0.25)

    if strat_cfg.get("exit_variant") == "profit_ladder":
        from research.exit_evolution import donchian_entries, apply_profit_ladder
        data = donchian_entries(df)
        return apply_profit_ladder(data)

    mod = load_strategy_module(strat_cfg["name"])
    if hasattr(mod, "TICK_SIZE"):
        mod.TICK_SIZE = tick_size

    sig = inspect.signature(mod.generate_signals)
    kwargs = {}
    if "asset" in sig.parameters:
        kwargs["asset"] = asset
    return mod.generate_signals(df, **kwargs)


# ── Analysis Functions ────────────────────────────────────────────────────────

def run_portfolio_backtests() -> tuple[dict, dict]:
    """Run all portfolio backtests, return (trades_dict, regime_daily_cache)."""
    strat_configs = PORTFOLIO_CONFIG["strategies"]
    regime_engine = RegimeEngine()

    data_cache = {}
    regime_daily_cache = {}
    trades_dict = {}

    for strat_key, strat in strat_configs.items():
        asset = strat["asset"]
        config = ASSET_CONFIG.get(asset, {"point_value": 5.0})

        if asset not in data_cache:
            data_cache[asset] = load_data(asset)
            regime_daily_cache[asset] = regime_engine.get_daily_regimes(
                data_cache[asset]
            )

        df = data_cache[asset]

        try:
            signals = generate_signals_for_strategy(strat, df.copy())
            result = run_backtest(
                df, signals,
                mode=strat["mode"],
                point_value=config["point_value"],
                symbol=asset,
            )
            trades = result["trades_df"]

            # GRINDING filter
            if strat.get("grinding_filter") and not trades.empty:
                rd = regime_daily_cache[asset].copy()
                rd["_date"] = pd.to_datetime(rd["_date"])
                rd["_date_date"] = rd["_date"].dt.date
                trades = trades.copy()
                trades["entry_date"] = pd.to_datetime(
                    trades["entry_time"]
                ).dt.date
                trades = trades.merge(
                    rd[["_date_date", "trend_persistence"]],
                    left_on="entry_date", right_on="_date_date", how="left",
                )
                trades = trades[
                    trades["trend_persistence"] == "GRINDING"
                ].drop(
                    columns=["entry_date", "_date_date", "trend_persistence"],
                    errors="ignore",
                ).reset_index(drop=True)

            trades_dict[strat_key] = trades
        except Exception as e:
            print(f"    WARNING: {strat_key} backtest failed: {e}")
            trades_dict[strat_key] = pd.DataFrame()

    return trades_dict, regime_daily_cache


def analyze_asset_gaps(trades_dict: dict) -> dict:
    """Identify which assets have coverage and which don't."""
    # Assets currently in portfolio
    portfolio_assets = set()
    asset_pnl = defaultdict(float)
    asset_trades = defaultdict(int)
    asset_strategies = defaultdict(list)

    strat_configs = PORTFOLIO_CONFIG["strategies"]
    for strat_key, strat in strat_configs.items():
        asset = strat["asset"]
        portfolio_assets.add(asset)
        trades = trades_dict.get(strat_key, pd.DataFrame())
        if not trades.empty:
            asset_pnl[asset] += trades["pnl"].sum()
            asset_trades[asset] += len(trades)
            asset_strategies[asset].append(strat_key)

    # Assets with data but not in portfolio
    missing_assets = []
    for asset in AVAILABLE_ASSETS:
        if asset not in portfolio_assets:
            missing_assets.append({
                "asset": asset,
                "data_available": True,
                "point_value": ASSET_CONFIG.get(asset, {}).get("point_value", "unknown"),
            })

    # Concentration analysis
    total_pnl = sum(asset_pnl.values())
    concentration = {}
    for asset in portfolio_assets:
        share = asset_pnl[asset] / total_pnl if total_pnl != 0 else 0
        concentration[asset] = {
            "pnl": round(asset_pnl[asset], 2),
            "pnl_share": round(share, 3),
            "trades": asset_trades[asset],
            "strategies": asset_strategies[asset],
            "concentrated": share > 0.40,
        }

    return {
        "portfolio_assets": sorted(portfolio_assets),
        "available_assets": AVAILABLE_ASSETS,
        "missing_assets": missing_assets,
        "concentration": concentration,
        "total_pnl": round(total_pnl, 2),
    }


def analyze_session_gaps(trades_dict: dict) -> dict:
    """Identify time-of-day coverage gaps."""
    hour_trades = defaultdict(int)
    hour_pnl = defaultdict(float)
    hour_strategies = defaultdict(set)

    strat_configs = PORTFOLIO_CONFIG["strategies"]
    for strat_key, trades in trades_dict.items():
        if trades.empty:
            continue
        t = trades.copy()
        t["entry_hour"] = pd.to_datetime(t["entry_time"]).dt.hour
        for _, row in t.iterrows():
            h = int(row["entry_hour"])
            hour_trades[h] += 1
            hour_pnl[h] += row["pnl"]
            hour_strategies[h].add(strat_key)

    total_trades = sum(hour_trades.values())

    # Map hours to sessions
    session_stats = {}
    for session_name, window in SESSION_WINDOWS.items():
        start = window["start"]
        end = window["end"]

        if start < end:
            hours = range(start, end)
        else:
            # Overnight wraps around
            hours = list(range(start, 24)) + list(range(0, end))

        session_trades = sum(hour_trades.get(h, 0) for h in hours)
        session_pnl = sum(hour_pnl.get(h, 0) for h in hours)
        session_strats = set()
        for h in hours:
            session_strats.update(hour_strategies.get(h, set()))

        share = session_trades / total_trades if total_trades > 0 else 0

        session_stats[session_name] = {
            "label": window["label"],
            "trades": session_trades,
            "trade_share": round(share, 3),
            "pnl": round(session_pnl, 2),
            "strategies": sorted(session_strats),
            "gap": session_trades < 5,
            "underweight": share < 0.05 and session_name not in ("pre_market", "overnight"),
        }

    # Identify gaps
    gaps = []
    for name, stats in session_stats.items():
        if stats["gap"]:
            gaps.append({
                "session": name,
                "label": stats["label"],
                "reason": "zero or near-zero trades",
                "opportunity": _session_opportunity(name),
            })
        elif stats["underweight"]:
            gaps.append({
                "session": name,
                "label": stats["label"],
                "reason": f"underweight ({stats['trade_share']:.1%} of trades)",
                "opportunity": _session_opportunity(name),
            })

    return {
        "session_stats": session_stats,
        "gaps": gaps,
        "hour_distribution": {h: hour_trades.get(h, 0) for h in range(0, 24)},
        "total_trades": total_trades,
    }


def _session_opportunity(session_name: str) -> str:
    """Suggest research direction for a session gap."""
    suggestions = {
        "pre_market": "Gap fill strategies, overnight position management",
        "open": "ORB variations, opening drive momentum",
        "morning": "Trend continuation, VWAP pullback",
        "midday": "Range-bound mean reversion, compression breakout",
        "afternoon": "Afternoon breakout, trend continuation, power hour momentum",
        "close": "Close reversion, end-of-day mean reversion, MOC strategies",
        "overnight": "Overnight range strategies, globex session edges",
    }
    return suggestions.get(session_name, "General research needed")


def analyze_regime_gaps(trades_dict: dict, regime_daily_cache: dict) -> dict:
    """Identify regime cells with weak or missing coverage."""
    # Load existing regime coverage if available
    coverage_path = ROOT / "research" / "regime" / "regime_coverage.json"
    if coverage_path.exists():
        with open(coverage_path) as f:
            existing_coverage = json.load(f)
    else:
        existing_coverage = None

    # Tag trades with regime cells
    strat_configs = PORTFOLIO_CONFIG["strategies"]
    cell_stats = defaultdict(lambda: {"trades": 0, "pnl": 0.0, "strategies": set()})

    for strat_key, trades in trades_dict.items():
        if trades.empty:
            continue
        asset = strat_configs[strat_key]["asset"]
        if asset not in regime_daily_cache:
            continue

        rd = regime_daily_cache[asset].copy()
        rd["_date"] = pd.to_datetime(rd["_date"])
        rd["_date_date"] = rd["_date"].dt.date

        t = trades.copy()
        t["entry_date"] = pd.to_datetime(t["entry_time"]).dt.date
        t = t.merge(
            rd[["_date_date", "vol_regime", "trend_regime", "rv_regime"]],
            left_on="entry_date", right_on="_date_date", how="left",
        )

        for _, row in t.iterrows():
            if pd.isna(row.get("vol_regime")):
                continue
            cell = f"{row['vol_regime']}_{row['trend_regime']}_{row['rv_regime']}"
            cell_stats[cell]["trades"] += 1
            cell_stats[cell]["pnl"] += row["pnl"]
            cell_stats[cell]["strategies"].add(strat_key)

    # Classify cells
    regime_gaps = []
    regime_covered = []

    # Use existing coverage data for day counts if available
    day_counts = {}
    if existing_coverage and "cells" in existing_coverage:
        for cell_data in existing_coverage["cells"]:
            cell_name = cell_data.get("cell", "")
            day_counts[cell_name] = cell_data.get("days", 0)

    for cell, stats in sorted(cell_stats.items()):
        pf = 0
        pnl_arr = []  # Would need per-trade data for proper PF
        trades_n = stats["trades"]
        total_pnl = stats["pnl"]
        days = day_counts.get(cell, 0)

        entry = {
            "cell": cell,
            "trades": trades_n,
            "pnl": round(total_pnl, 2),
            "strategies": sorted(stats["strategies"]),
            "days": days,
        }

        if total_pnl < 0:
            entry["status"] = "NEGATIVE_EDGE"
            entry["priority"] = "HIGH" if days >= 30 else "MEDIUM"
            entry["suggestion"] = "Avoid or find dedicated strategy for this regime"
            regime_gaps.append(entry)
        elif trades_n < 15:
            entry["status"] = "THIN"
            entry["priority"] = "MEDIUM" if days >= 20 else "LOW"
            entry["suggestion"] = "Needs more coverage — consider regime-specialist strategy"
            regime_gaps.append(entry)
        else:
            entry["status"] = "COVERED"
            regime_covered.append(entry)

    # Check for completely missing cells (regimes with zero trades)
    all_vol = ["LOW_VOL", "NORMAL", "HIGH_VOL"]
    all_trend = ["TRENDING", "RANGING"]
    all_rv = ["LOW_RV", "NORMAL_RV", "HIGH_RV"]
    all_cells = {f"{v}_{t}_{r}" for v in all_vol for t in all_trend for r in all_rv}
    observed_cells = set(cell_stats.keys())
    missing_cells = all_cells - observed_cells

    for cell in sorted(missing_cells):
        days = day_counts.get(cell, 0)
        regime_gaps.append({
            "cell": cell,
            "trades": 0,
            "pnl": 0,
            "strategies": [],
            "days": days,
            "status": "MISSING",
            "priority": "HIGH" if days >= 20 else "LOW",
            "suggestion": "No trades at all — may need dedicated strategy or is very rare",
        })

    return {
        "gaps": sorted(regime_gaps, key=lambda x: (
            {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(x["priority"], 3),
            -x.get("days", 0),
        )),
        "covered": regime_covered,
        "total_cells": len(all_cells),
        "covered_count": len(regime_covered),
        "gap_count": len(regime_gaps),
    }


def analyze_family_gaps() -> dict:
    """Identify which strategy families are represented and which are missing."""
    # Current portfolio families
    represented = defaultdict(list)
    for strat_key, fam_info in STRATEGY_FAMILIES.items():
        represented[fam_info["family"]].append({
            "strategy": strat_key,
            "subtype": fam_info["sub"],
        })

    # Gap analysis
    family_status = {}
    for family, info in ALL_FAMILIES.items():
        strats = represented.get(family, [])
        covered_subs = {s["subtype"] for s in strats}
        missing_subs = [s for s in info["subtypes"] if s not in covered_subs]

        if not strats:
            status = "MISSING"
            priority = "HIGH"
        elif len(missing_subs) > len(covered_subs):
            status = "THIN"
            priority = "MEDIUM"
        else:
            status = "COVERED"
            priority = "LOW"

        family_status[family] = {
            "description": info["description"],
            "status": status,
            "priority": priority,
            "represented_strategies": strats,
            "covered_subtypes": sorted(covered_subs),
            "missing_subtypes": missing_subs,
        }

    return family_status


def generate_research_priorities(
    asset_gaps: dict, session_gaps: dict, regime_gaps: dict, family_gaps: dict
) -> list[dict]:
    """Synthesize all gaps into prioritized research targets."""
    priorities = []

    # From asset gaps
    for asset_info in asset_gaps["missing_assets"]:
        asset = asset_info["asset"]
        if asset in ("ES",):  # Skip full-size duplicates
            continue
        priorities.append({
            "priority": "MEDIUM",
            "category": "asset",
            "target": f"{asset} — no portfolio coverage",
            "suggestion": _asset_research_suggestion(asset),
        })

    # From asset concentration
    for asset, stats in asset_gaps["concentration"].items():
        if stats["concentrated"]:
            priorities.append({
                "priority": "HIGH",
                "category": "asset_concentration",
                "target": f"{asset} concentration ({stats['pnl_share']:.0%} of PnL)",
                "suggestion": f"Diversify away from {asset} — add edges on other assets",
            })

    # From session gaps
    for gap in session_gaps["gaps"]:
        priorities.append({
            "priority": "HIGH" if gap["session"] in ("afternoon", "close") else "MEDIUM",
            "category": "session",
            "target": f"{gap['label']} — {gap['reason']}",
            "suggestion": gap["opportunity"],
        })

    # From regime gaps (high priority only)
    for gap in regime_gaps["gaps"]:
        if gap["priority"] == "HIGH":
            priorities.append({
                "priority": "HIGH",
                "category": "regime",
                "target": f"Regime {gap['cell']} — {gap['status']}",
                "suggestion": gap["suggestion"],
            })

    # From family gaps
    for family, status in family_gaps.items():
        if status["status"] == "MISSING":
            priorities.append({
                "priority": "HIGH" if family in ("volatility_expansion", "time_based") else "MEDIUM",
                "category": "family",
                "target": f"{family} family — not represented",
                "suggestion": f"Build {family} strategies: {', '.join(status['missing_subtypes'][:3])}",
            })
        elif status["status"] == "THIN":
            priorities.append({
                "priority": "LOW",
                "category": "family",
                "target": f"{family} family — thin coverage",
                "suggestion": f"Add subtypes: {', '.join(status['missing_subtypes'][:2])}",
            })

    # Sort by priority
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    priorities.sort(key=lambda x: priority_order.get(x["priority"], 3))

    return priorities


def _asset_research_suggestion(asset: str) -> str:
    suggestions = {
        "M2K": "Russell: breakout, vol expansion, momentum burst strategies (probation: ORB Enhanced)",
        "MCL": "Crude oil: mean reversion, exhaustion reversal, ATR expansion fade (probation: VWAP MR)",
        "MYM": "Dow: similar to S&P but slower — pullback and trend strategies",
        "ZN": "10Y bonds: slow trend following, yield momentum, macro trend continuation",
        "ZB": "30Y bonds: longer timeframe trends, range compression breakout",
        "ES": "Full-size S&P — skip (MES already covered)",
    }
    return suggestions.get(asset, f"Research strategy families on {asset}")


# ── Report Formatting ─────────────────────────────────────────────────────────

def format_report(
    asset_gaps: dict, session_gaps: dict, regime_gaps: dict,
    family_gaps: dict, priorities: list[dict]
) -> str:
    """Format the full opportunity map as a human-readable report."""
    lines = []

    lines.append("=" * 64)
    lines.append("  PORTFOLIO OPPORTUNITY MAP")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 64)

    # ── Research Priorities (top of report) ──
    lines.append("")
    lines.append("RESEARCH PRIORITIES")
    lines.append("\u2500" * 64)

    high = [p for p in priorities if p["priority"] == "HIGH"]
    medium = [p for p in priorities if p["priority"] == "MEDIUM"]
    low = [p for p in priorities if p["priority"] == "LOW"]

    if high:
        lines.append("")
        lines.append("  HIGH PRIORITY:")
        for p in high:
            lines.append(f"    [{p['category'].upper()}] {p['target']}")
            lines.append(f"           → {p['suggestion']}")
    if medium:
        lines.append("")
        lines.append("  MEDIUM PRIORITY:")
        for p in medium:
            lines.append(f"    [{p['category'].upper()}] {p['target']}")
            lines.append(f"           → {p['suggestion']}")
    if low:
        lines.append("")
        lines.append("  LOW PRIORITY:")
        for p in low:
            lines.append(f"    [{p['category'].upper()}] {p['target']}")

    # ── Asset Coverage ──
    lines.append("")
    lines.append("")
    lines.append("ASSET COVERAGE")
    lines.append("\u2500" * 64)

    lines.append(f"  Portfolio assets:  {', '.join(asset_gaps['portfolio_assets'])}")
    lines.append(f"  Available data:    {', '.join(asset_gaps['available_assets'])}")
    lines.append(f"  Missing:           {', '.join(a['asset'] for a in asset_gaps['missing_assets']) or 'None'}")
    lines.append("")

    header = f"  {'Asset':<8} {'Strategies':>3} {'Trades':>7} {'PnL':>10} {'Share':>7} {'Status'}"
    lines.append(header)
    lines.append(f"  {'-'*8} {'-'*3} {'-'*7} {'-'*10} {'-'*7} {'-'*14}")

    for asset, stats in sorted(
        asset_gaps["concentration"].items(),
        key=lambda x: -x[1]["pnl"],
    ):
        status = "CONCENTRATED" if stats["concentrated"] else "OK"
        lines.append(
            f"  {asset:<8} {len(stats['strategies']):>3} "
            f"{stats['trades']:>7} "
            f"${stats['pnl']:>9,.0f} "
            f"{stats['pnl_share']:>6.1%} "
            f"{status}"
        )

    # ── Session Coverage ──
    lines.append("")
    lines.append("")
    lines.append("SESSION COVERAGE")
    lines.append("\u2500" * 64)

    header = f"  {'Session':<30} {'Trades':>7} {'Share':>7} {'PnL':>10} {'Status'}"
    lines.append(header)
    lines.append(f"  {'-'*30} {'-'*7} {'-'*7} {'-'*10} {'-'*10}")

    for name, stats in session_gaps["session_stats"].items():
        if stats["gap"]:
            status = "GAP"
        elif stats["underweight"]:
            status = "UNDERWEIGHT"
        else:
            status = "OK"

        lines.append(
            f"  {stats['label']:<30} {stats['trades']:>7} "
            f"{stats['trade_share']:>6.1%} "
            f"${stats['pnl']:>9,.0f} "
            f"{status}"
        )

    # Hour histogram
    lines.append("")
    lines.append("  Hourly trade distribution (ET):")
    max_trades = max(session_gaps["hour_distribution"].values()) if session_gaps["hour_distribution"] else 1
    for hour in range(7, 17):
        count = session_gaps["hour_distribution"].get(hour, 0)
        bar_len = int(count / max_trades * 30) if max_trades > 0 else 0
        bar = "\u2588" * bar_len
        lines.append(f"    {hour:02d}:00  {bar} {count}")

    # ── Regime Coverage ──
    lines.append("")
    lines.append("")
    lines.append("REGIME COVERAGE")
    lines.append("\u2500" * 64)

    lines.append(f"  Total cells: {regime_gaps['total_cells']}")
    lines.append(f"  Covered:     {regime_gaps['covered_count']}")
    lines.append(f"  Gaps:        {regime_gaps['gap_count']}")
    lines.append("")

    if regime_gaps["gaps"]:
        lines.append("  Gap cells (sorted by priority):")
        lines.append(f"  {'Cell':<35} {'Status':<15} {'Trades':>6} {'PnL':>9} {'Priority'}")
        lines.append(f"  {'-'*35} {'-'*15} {'-'*6} {'-'*9} {'-'*8}")

        for gap in regime_gaps["gaps"]:
            lines.append(
                f"  {gap['cell']:<35} {gap['status']:<15} "
                f"{gap['trades']:>6} "
                f"${gap['pnl']:>8,.0f} "
                f"{gap['priority']}"
            )

    # ── Strategy Families ──
    lines.append("")
    lines.append("")
    lines.append("STRATEGY FAMILY COVERAGE")
    lines.append("\u2500" * 64)

    for family, status in sorted(
        family_gaps.items(),
        key=lambda x: {"MISSING": 0, "THIN": 1, "COVERED": 2}[x[1]["status"]],
    ):
        icon = {"MISSING": "[ ]", "THIN": "[~]", "COVERED": "[x]"}[status["status"]]
        lines.append(f"  {icon} {family}: {status['description']}")

        if status["represented_strategies"]:
            strats = ", ".join(s["strategy"] for s in status["represented_strategies"])
            lines.append(f"      Represented: {strats}")

        if status["missing_subtypes"]:
            lines.append(f"      Missing: {', '.join(status['missing_subtypes'])}")

        lines.append("")

    # ── Footer ──
    lines.append("=" * 64)
    lines.append("  END OF OPPORTUNITY MAP")
    lines.append("=" * 64)

    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Portfolio Opportunity Map — structural gap analysis"
    )
    parser.add_argument(
        "--save", action="store_true",
        help="Save report to reports/ directory",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Save JSON output to research/",
    )
    args = parser.parse_args()

    print("  Running portfolio backtests...")
    trades_dict, regime_daily_cache = run_portfolio_backtests()

    print("  Analyzing asset gaps...")
    asset_gaps = analyze_asset_gaps(trades_dict)

    print("  Analyzing session gaps...")
    session_gaps = analyze_session_gaps(trades_dict)

    print("  Analyzing regime gaps...")
    regime_gaps = analyze_regime_gaps(trades_dict, regime_daily_cache)

    print("  Analyzing strategy family gaps...")
    family_gaps = analyze_family_gaps()

    print("  Generating research priorities...")
    priorities = generate_research_priorities(
        asset_gaps, session_gaps, regime_gaps, family_gaps
    )

    report = format_report(
        asset_gaps, session_gaps, regime_gaps, family_gaps, priorities
    )
    print(report)

    if args.save:
        reports_dir = ROOT / "reports"
        reports_dir.mkdir(exist_ok=True)
        save_path = reports_dir / f"opportunity_map_{TODAY}.md"
        save_path.write_text(report + "\n")
        print(f"\n  Report saved to {save_path.relative_to(ROOT)}")

    if args.json:
        json_output = {
            "scan_date": TODAY,
            "asset_gaps": {
                "portfolio_assets": asset_gaps["portfolio_assets"],
                "missing_assets": asset_gaps["missing_assets"],
                "concentration": {
                    k: {kk: vv for kk, vv in v.items() if kk != "strategies"}
                    for k, v in asset_gaps["concentration"].items()
                },
            },
            "session_gaps": {
                "gaps": session_gaps["gaps"],
                "hour_distribution": session_gaps["hour_distribution"],
            },
            "regime_gaps": {
                "gap_count": regime_gaps["gap_count"],
                "covered_count": regime_gaps["covered_count"],
                "gaps": regime_gaps["gaps"],
            },
            "family_gaps": {
                k: {kk: vv for kk, vv in v.items()}
                for k, v in family_gaps.items()
            },
            "research_priorities": priorities,
        }
        json_path = ROOT / "research" / "opportunity_map_results.json"
        with open(json_path, "w") as f:
            json.dump(json_output, f, indent=2, default=str)
        print(f"  JSON saved to {json_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
