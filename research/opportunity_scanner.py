#!/usr/bin/env python3
"""Opportunity Scanner — Automated portfolio improvement identifier.

READ-ONLY research tool. Does NOT modify any execution pipeline files.

Scans the current 6-strategy portfolio for:
  A. Promotion candidates (probation strategies approaching trade thresholds)
  B. Portfolio gaps (time-of-day, asset concentration, strategy type, regime)
  C. Redundancy warnings (high daily PnL correlations)
  D. Regime opportunities (cells with no strategy edge)
  E. Edge improvement ideas (mode additions, regime-specific improvements)

Usage:
    python3 research/opportunity_scanner.py
    python3 research/opportunity_scanner.py --save
"""

import argparse
import importlib.util
import inspect
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest
from engine.regime_engine import RegimeEngine
from engine.strategy_controller import PORTFOLIO_CONFIG

PROCESSED_DIR = ROOT / "data" / "processed"
STARTING_CAPITAL = 50_000.0

ASSET_CONFIG = {
    "MES": {"point_value": 5.0, "tick_size": 0.25},
    "MNQ": {"point_value": 2.0, "tick_size": 0.25},
    "MGC": {"point_value": 10.0, "tick_size": 0.10},
    "M2K": {"point_value": 5.0, "tick_size": 0.10},
    "MCL": {"point_value": 100.0, "tick_size": 0.01},
}

# ── Probation strategies to monitor for promotion ─────────────────────────
# These are NOT in PORTFOLIO_CONFIG yet — they're in probation awaiting trades.
PROBATION_CANDIDATES = {
    "XB-ORB-EMA-MNQ-Short": {
        "name": "xb_orb_ema_ladder",
        "asset": "MNQ",
        "mode": "short",
        "promotion_threshold": 150,
    },
    "Session-VWAP-Fade-MGC-Long": {
        "name": "session_vwap_fade",
        "asset": "MGC",
        "mode": "long",
        "promotion_threshold": 150,
    },
    "MomIgn-M2K-Short": {
        "name": "momentum_ignition",
        "asset": "M2K",
        "mode": "short",
        "promotion_threshold": 50,
    },
}

# Strategy type taxonomy for gap analysis
STRATEGY_TYPES = {
    "PB-MGC-Short":              {"family": "pullback", "session": "morning", "direction": "short"},
    "ORB-MGC-Long":              {"family": "breakout", "session": "morning", "direction": "long"},
    "VWAP-MNQ-Long":             {"family": "trend", "session": "midday", "direction": "long"},
    "XB-PB-EMA-MES-Short":       {"family": "pullback", "session": "morning", "direction": "short"},
    "BB-EQ-MGC-Long":            {"family": "mean_reversion", "session": "full_day", "direction": "long"},
    "Donchian-MNQ-Long-GRINDING": {"family": "trend", "session": "morning", "direction": "long"},
    "MomIgn-M2K-Short":           {"family": "momentum", "session": "midday_afternoon", "direction": "short"},
}

DESIRED_TYPES = {"overnight", "afternoon", "volatility_expansion", "range_fade", "event_driven"}

# Regime grid dimensions
VOL_REGIMES = ["LOW_VOL", "NORMAL", "HIGH_VOL"]
TREND_REGIMES = ["TRENDING", "RANGING"]
RV_REGIMES = ["LOW_RV", "NORMAL_RV", "HIGH_RV"]


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_strategy(name: str):
    """Dynamically load a strategy module."""
    path = ROOT / "strategies" / name / "strategy.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_data(asset: str) -> pd.DataFrame:
    """Load processed 5m CSV for an asset."""
    csv_path = PROCESSED_DIR / f"{asset}_5m.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Data file not found: {csv_path}")
    df = pd.read_csv(csv_path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def run_strategy_backtest(strat_key: str, strat_cfg: dict) -> pd.DataFrame:
    """Run backtest for a strategy from PORTFOLIO_CONFIG, return trades_df."""
    name = strat_cfg["name"]
    asset = strat_cfg["asset"]
    mode = strat_cfg["mode"]
    acfg = ASSET_CONFIG[asset]

    df = load_data(asset)
    mod = load_strategy(name)

    if hasattr(mod, "TICK_SIZE"):
        mod.TICK_SIZE = acfg["tick_size"]

    sig = inspect.signature(mod.generate_signals)
    kwargs = {}
    if "asset" in sig.parameters:
        kwargs["asset"] = asset
    if "mode" in sig.parameters:
        kwargs["mode"] = mode

    signals = mod.generate_signals(df, **kwargs)

    result = run_backtest(
        df, signals,
        mode=mode,
        point_value=acfg["point_value"],
        symbol=asset,
    )
    return result["trades_df"]


def get_daily_pnl(trades_df: pd.DataFrame) -> pd.Series:
    """Convert trades_df to daily PnL series keyed by date."""
    if trades_df.empty:
        return pd.Series(dtype=float)
    tmp = trades_df.copy()
    tmp["date"] = pd.to_datetime(tmp["exit_time"]).dt.date
    daily = tmp.groupby("date")["pnl"].sum()
    daily.index = pd.to_datetime(daily.index)
    return daily


def compute_pf(trades_df: pd.DataFrame) -> float:
    """Compute profit factor from trades."""
    if trades_df.empty:
        return 0.0
    winners = trades_df[trades_df["pnl"] > 0]["pnl"].sum()
    losers = abs(trades_df[trades_df["pnl"] <= 0]["pnl"].sum())
    if losers < 0.01:
        return 99.0 if winners > 0 else 0.0
    return round(winners / losers, 2)


def compute_sharpe(daily_pnl: pd.Series) -> float:
    """Annualized Sharpe from daily PnL series."""
    if len(daily_pnl) < 10 or daily_pnl.std() == 0:
        return 0.0
    return round((daily_pnl.mean() / daily_pnl.std()) * np.sqrt(252), 2)


# ── Scan Functions ───────────────────────────────────────────────────────────

def scan_promotion_candidates(all_trades: dict) -> list:
    """Check probation strategies for trade count progress."""
    results = []

    for label, cfg in PROBATION_CANDIDATES.items():
        try:
            trades = run_strategy_backtest(label, cfg)
            n_trades = len(trades)
            threshold = cfg["promotion_threshold"]
            pct = round(n_trades / threshold * 100)

            # Estimate days to threshold from data date range
            if n_trades > 1:
                first_trade = pd.to_datetime(trades["entry_time"].iloc[0])
                last_trade = pd.to_datetime(trades["entry_time"].iloc[-1])
                span_days = max((last_trade - first_trade).days, 1)
                trades_per_day = n_trades / span_days
                remaining = max(threshold - n_trades, 0)
                est_days = int(remaining / trades_per_day) if trades_per_day > 0 else 999
            else:
                est_days = 999

            pf = compute_pf(trades)

            results.append({
                "label": label,
                "trades": n_trades,
                "threshold": threshold,
                "pct": pct,
                "est_days": est_days,
                "pf": pf,
            })
        except Exception as e:
            results.append({
                "label": label,
                "trades": 0,
                "threshold": cfg["promotion_threshold"],
                "pct": 0,
                "est_days": 999,
                "pf": 0.0,
                "error": str(e),
            })

    return results


def scan_portfolio_gaps(all_trades: dict) -> dict:
    """Analyze time-of-day, asset concentration, and strategy type gaps."""
    gaps = {
        "time_concentration": [],
        "asset_concentration": [],
        "missing_types": [],
    }

    # ── Time-of-day analysis ──
    all_entry_hours = []
    for strat_key, trades in all_trades.items():
        if trades.empty:
            continue
        hours = pd.to_datetime(trades["entry_time"]).dt.hour
        all_entry_hours.extend(hours.tolist())

    if all_entry_hours:
        hour_series = pd.Series(all_entry_hours)
        hour_counts = hour_series.value_counts().sort_index()
        total_trades = len(all_entry_hours)

        # Check 2-hour windows for >60% concentration
        for start_hour in range(7, 16):
            window_trades = hour_counts.reindex(
                [start_hour, start_hour + 1], fill_value=0
            ).sum()
            window_pct = round(window_trades / total_trades * 100, 1)
            if window_pct > 60:
                gaps["time_concentration"].append({
                    "window": f"{start_hour:02d}:00-{start_hour + 2:02d}:00 ET",
                    "pct": window_pct,
                    "trades": int(window_trades),
                })

        gaps["hour_distribution"] = {
            int(h): int(c) for h, c in hour_counts.items()
        }

    # ── Asset concentration ──
    asset_pnl = {}
    for strat_key, trades in all_trades.items():
        if trades.empty:
            continue
        asset = PORTFOLIO_CONFIG["strategies"][strat_key]["asset"]
        asset_pnl[asset] = asset_pnl.get(asset, 0.0) + trades["pnl"].sum()

    total_pnl = sum(abs(v) for v in asset_pnl.values())
    if total_pnl > 0:
        for asset, pnl in asset_pnl.items():
            pct = round(abs(pnl) / total_pnl * 100, 1)
            if pct > 50:
                gaps["asset_concentration"].append({
                    "asset": asset,
                    "pnl": round(pnl, 2),
                    "pct_of_total": pct,
                })
    gaps["asset_pnl"] = {k: round(v, 2) for k, v in asset_pnl.items()}

    # ── Strategy type gaps ──
    present_families = set()
    present_sessions = set()
    for strat_key in all_trades:
        if strat_key in STRATEGY_TYPES:
            info = STRATEGY_TYPES[strat_key]
            present_families.add(info["family"])
            present_sessions.add(info["session"])

    missing = DESIRED_TYPES - present_families - present_sessions
    gaps["missing_types"] = sorted(missing)
    gaps["present_families"] = sorted(present_families)
    gaps["present_sessions"] = sorted(present_sessions)

    return gaps


def scan_redundancy(all_trades: dict) -> list:
    """Compute daily PnL correlations between all strategy pairs."""
    daily_series = {}
    sharpes = {}
    for strat_key, trades in all_trades.items():
        daily = get_daily_pnl(trades)
        if len(daily) > 10:
            daily_series[strat_key] = daily
            sharpes[strat_key] = compute_sharpe(daily)

    warnings = []
    keys = sorted(daily_series.keys())
    max_corr = 0.0
    max_pair = ("", "")

    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            combined = pd.DataFrame({
                "a": daily_series[keys[i]],
                "b": daily_series[keys[j]],
            }).fillna(0)
            if len(combined) < 10:
                continue
            corr = round(combined["a"].corr(combined["b"]), 3)

            if abs(corr) > abs(max_corr):
                max_corr = corr
                max_pair = (keys[i], keys[j])

            if abs(corr) > 0.3:
                # Suggest keeping the one with higher Sharpe
                keep = keys[i] if sharpes.get(keys[i], 0) >= sharpes.get(keys[j], 0) else keys[j]
                investigate = keys[j] if keep == keys[i] else keys[i]
                warnings.append({
                    "pair": (keys[i], keys[j]),
                    "correlation": corr,
                    "keep": keep,
                    "investigate": investigate,
                    "keep_sharpe": sharpes.get(keep, 0),
                    "investigate_sharpe": sharpes.get(investigate, 0),
                })

    return {
        "warnings": warnings,
        "max_corr": max_corr,
        "max_pair": max_pair,
    }


def scan_regime_gaps(all_trades: dict, regime_daily_cache: dict) -> list:
    """Identify regime cells where portfolio has no edge or negative PnL."""
    # Tag every trade with its regime cell
    cell_stats = {}  # cell_key -> {trades, pnl, gross_win, gross_loss, strategies}

    for strat_key, trades in all_trades.items():
        if trades.empty:
            continue
        asset = PORTFOLIO_CONFIG["strategies"][strat_key]["asset"]
        regime_daily = regime_daily_cache.get(asset)
        if regime_daily is None:
            continue

        rd = regime_daily.copy()
        rd["_date"] = pd.to_datetime(rd["_date"])
        rd["_date_date"] = rd["_date"].dt.date

        t = trades.copy()
        t["trade_date"] = pd.to_datetime(t["exit_time"]).dt.date
        t = t.merge(
            rd[["_date_date", "vol_regime", "trend_regime", "rv_regime"]],
            left_on="trade_date", right_on="_date_date", how="left",
        )

        for _, row in t.iterrows():
            vol = row.get("vol_regime", "NORMAL")
            trend = row.get("trend_regime", "RANGING")
            rv = row.get("rv_regime", "NORMAL_RV")
            cell_key = f"{vol}_{trend}_{rv}"

            if cell_key not in cell_stats:
                cell_stats[cell_key] = {
                    "trades": 0, "pnl": 0.0,
                    "gross_win": 0.0, "gross_loss": 0.0,
                    "strategies": set(),
                }

            cell_stats[cell_key]["trades"] += 1
            cell_stats[cell_key]["pnl"] += row["pnl"]
            cell_stats[cell_key]["strategies"].add(strat_key)
            if row["pnl"] > 0:
                cell_stats[cell_key]["gross_win"] += row["pnl"]
            else:
                cell_stats[cell_key]["gross_loss"] += abs(row["pnl"])

    # Build full 18-cell grid and identify gaps
    gaps = []
    for vol in VOL_REGIMES:
        for trend in TREND_REGIMES:
            for rv in RV_REGIMES:
                cell_key = f"{vol}_{trend}_{rv}"
                stats = cell_stats.get(cell_key, {
                    "trades": 0, "pnl": 0.0,
                    "gross_win": 0.0, "gross_loss": 0.0,
                    "strategies": set(),
                })

                gl = stats["gross_loss"]
                pf = round(stats["gross_win"] / gl, 2) if gl > 0.01 else (
                    99.0 if stats["gross_win"] > 0 else 0.0
                )

                is_gap = (
                    stats["trades"] == 0
                    or stats["pnl"] < 0
                    or pf < 1.0
                    or stats["trades"] < 10
                )

                gaps.append({
                    "cell_key": cell_key,
                    "vol": vol,
                    "trend": trend,
                    "rv": rv,
                    "trades": stats["trades"],
                    "pnl": round(stats["pnl"], 2),
                    "pf": pf,
                    "n_strategies": len(stats["strategies"]),
                    "strategies": sorted(stats["strategies"]) if isinstance(stats["strategies"], set) else [],
                    "is_gap": is_gap,
                })

    return gaps


def scan_edge_improvements(all_trades: dict, regime_daily_cache: dict) -> list:
    """Check if strategies have regime-specific strengths worth exploiting."""
    suggestions = []

    for strat_key, trades in all_trades.items():
        if trades.empty or len(trades) < 20:
            continue

        asset = PORTFOLIO_CONFIG["strategies"][strat_key]["asset"]
        mode = PORTFOLIO_CONFIG["strategies"][strat_key]["mode"]
        regime_daily = regime_daily_cache.get(asset)
        if regime_daily is None:
            continue

        rd = regime_daily.copy()
        rd["_date"] = pd.to_datetime(rd["_date"])
        rd["_date_date"] = rd["_date"].dt.date

        t = trades.copy()
        t["trade_date"] = pd.to_datetime(t["exit_time"]).dt.date
        t = t.merge(
            rd[["_date_date", "vol_regime", "trend_regime", "rv_regime",
                "trend_persistence"]],
            left_on="trade_date", right_on="_date_date", how="left",
        )

        overall_pf = compute_pf(trades)

        # Check per-composite-regime performance
        t["composite"] = t["vol_regime"].fillna("NORMAL") + "_" + t["trend_regime"].fillna("RANGING")
        for regime, group in t.groupby("composite"):
            if len(group) < 5:
                continue
            regime_pf = compute_pf(group)
            if regime_pf > overall_pf * 1.5 and regime_pf > 1.5 and len(group) >= 10:
                suggestions.append({
                    "type": "regime_specialist",
                    "strategy": strat_key,
                    "regime": regime,
                    "regime_pf": regime_pf,
                    "overall_pf": overall_pf,
                    "regime_trades": len(group),
                    "regime_pnl": round(group["pnl"].sum(), 2),
                    "suggestion": f"{strat_key} outperforms in {regime} "
                                  f"(PF={regime_pf} vs overall {overall_pf}). "
                                  f"Consider regime-specific parameter tuning.",
                })

        # Check GRINDING filter benefit
        grinding_trades = t[t["trend_persistence"] == "GRINDING"]
        if len(grinding_trades) >= 10:
            grinding_pf = compute_pf(grinding_trades)
            if grinding_pf > overall_pf * 1.3 and grinding_pf > 1.5:
                strat_cfg = PORTFOLIO_CONFIG["strategies"][strat_key]
                if not strat_cfg.get("grinding_filter", False):
                    suggestions.append({
                        "type": "grinding_filter",
                        "strategy": strat_key,
                        "grinding_pf": grinding_pf,
                        "overall_pf": overall_pf,
                        "grinding_trades": len(grinding_trades),
                        "suggestion": f"{strat_key}: GRINDING filter boosts PF from "
                                      f"{overall_pf} to {grinding_pf} "
                                      f"({len(grinding_trades)} trades). Worth investigating.",
                    })

        # Check opposite mode potential
        opposite_mode = "short" if mode == "long" else "long"
        try:
            opp_trades = run_strategy_backtest(
                strat_key,
                {**PORTFOLIO_CONFIG["strategies"][strat_key], "mode": opposite_mode},
            )
            if len(opp_trades) >= 20:
                opp_pf = compute_pf(opp_trades)
                if opp_pf > 1.2:
                    suggestions.append({
                        "type": "mode_addition",
                        "strategy": strat_key,
                        "current_mode": mode,
                        "opposite_mode": opposite_mode,
                        "opposite_pf": opp_pf,
                        "opposite_trades": len(opp_trades),
                        "opposite_pnl": round(opp_trades["pnl"].sum(), 2),
                        "suggestion": f"{strat_key}: {opposite_mode} side shows PF={opp_pf} "
                                      f"({len(opp_trades)} trades, "
                                      f"${opp_trades['pnl'].sum():,.0f}). Worth validating.",
                    })
        except Exception:
            pass  # Not all strategies support mode switching

    return suggestions


# ── Main Scanner ─────────────────────────────────────────────────────────────

def run_scan() -> dict:
    """Run all opportunity scans and return structured results."""
    print()
    print("=" * 65)
    print("  OPPORTUNITY SCANNER")
    print("  Portfolio improvement identifier")
    print("=" * 65)

    # ── Step 1: Run baseline backtests for all portfolio strategies ──
    print("\n  Running portfolio backtests...")
    all_trades = {}
    strategies = PORTFOLIO_CONFIG["strategies"]

    for strat_key, strat_cfg in strategies.items():
        print(f"    {strat_key}...", end=" ", flush=True)
        try:
            trades = run_strategy_backtest(strat_key, strat_cfg)
            all_trades[strat_key] = trades
            pnl = trades["pnl"].sum() if not trades.empty else 0
            print(f"{len(trades)} trades, ${pnl:,.0f}")
        except Exception as e:
            all_trades[strat_key] = pd.DataFrame()
            print(f"ERROR: {e}")

    # ── Step 2: Classify regimes for each asset ──
    print("\n  Classifying regimes...")
    engine = RegimeEngine()
    regime_daily_cache = {}
    assets_used = set(cfg["asset"] for cfg in strategies.values())

    for asset in assets_used:
        df = load_data(asset)
        daily = engine.get_daily_regimes(df)
        regime_daily_cache[asset] = daily
        print(f"    {asset}: {len(daily)} trading days")

    # ── Step 3: Apply GRINDING filter for Donchian ──
    for strat_key, strat_cfg in strategies.items():
        if strat_cfg.get("grinding_filter") and not all_trades[strat_key].empty:
            asset = strat_cfg["asset"]
            rd = regime_daily_cache[asset].copy()
            rd["_date"] = pd.to_datetime(rd["_date"])
            rd["_date_date"] = rd["_date"].dt.date

            t = all_trades[strat_key].copy()
            t["entry_date"] = pd.to_datetime(t["entry_time"]).dt.date
            t = t.merge(
                rd[["_date_date", "trend_persistence"]],
                left_on="entry_date", right_on="_date_date", how="left",
            )
            all_trades[strat_key] = t[t["trend_persistence"] == "GRINDING"].drop(
                columns=["entry_date", "_date_date", "trend_persistence"],
                errors="ignore",
            ).reset_index(drop=True)
            print(f"    {strat_key}: GRINDING filter -> {len(all_trades[strat_key])} trades")

    # ── Run all scans ──
    print("\n  Scanning promotion candidates...")
    promotions = scan_promotion_candidates(all_trades)

    print("  Scanning portfolio gaps...")
    gaps = scan_portfolio_gaps(all_trades)

    print("  Scanning redundancy...")
    redundancy = scan_redundancy(all_trades)

    print("  Scanning regime gaps...")
    regime_gaps = scan_regime_gaps(all_trades, regime_daily_cache)

    print("  Scanning edge improvements...")
    improvements = scan_edge_improvements(all_trades, regime_daily_cache)

    results = {
        "scan_date": datetime.now().strftime("%Y-%m-%d"),
        "portfolio_strategies": list(strategies.keys()),
        "promotions": promotions,
        "gaps": gaps,
        "redundancy": redundancy,
        "regime_gaps": regime_gaps,
        "improvements": improvements,
    }

    return results


# ── Display ──────────────────────────────────────────────────────────────────

def display_results(results: dict):
    """Print formatted opportunity scan report."""
    date = results["scan_date"]

    print()
    print(f"OPPORTUNITY SCAN -- {date}")
    print("=" * 65)

    # ── Promotion Candidates ──
    print()
    print("PROMOTION CANDIDATES")
    print("-" * 45)
    promotions = results["promotions"]
    if not promotions:
        print("  No probation strategies configured.")
    else:
        for p in promotions:
            if "error" in p:
                print(f"  x {p['label']}: ERROR - {p['error']}")
            else:
                est = f"~{p['est_days']} days" if p["est_days"] < 999 else "insufficient data"
                print(f"  -> {p['label']}: {p['trades']}/{p['threshold']} trades "
                      f"({p['pct']}%), PF={p['pf']}, est. {est} to promotion")

    # ── Portfolio Gaps ──
    print()
    print("PORTFOLIO GAPS")
    print("-" * 45)

    gaps = results["gaps"]

    if gaps["time_concentration"]:
        for tc in gaps["time_concentration"]:
            print(f"  ! Time concentration: {tc['pct']}% of trades "
                  f"between {tc['window']} ({tc['trades']} trades)")
    else:
        print("  OK No severe time concentration detected")

    if gaps.get("hour_distribution"):
        dist = gaps["hour_distribution"]
        hours_str = ", ".join(f"{h}h:{c}" for h, c in sorted(dist.items()))
        print(f"     Hour distribution: {hours_str}")

    if gaps["asset_concentration"]:
        for ac in gaps["asset_concentration"]:
            print(f"  ! Asset concentration: {ac['asset']} = "
                  f"{ac['pct_of_total']}% of total PnL (${ac['pnl']:,.0f})")
    else:
        print("  OK No single asset dominates (>50%)")

    if gaps.get("asset_pnl"):
        pnl_str = ", ".join(f"{a}: ${v:,.0f}" for a, v in gaps["asset_pnl"].items())
        print(f"     Asset PnL: {pnl_str}")

    if gaps["missing_types"]:
        for mt in gaps["missing_types"]:
            print(f"  ! No {mt} strategies in portfolio")
    else:
        print("  OK All desired strategy types present")

    print(f"     Present families: {', '.join(gaps.get('present_families', []))}")
    print(f"     Present sessions: {', '.join(gaps.get('present_sessions', []))}")

    # ── Redundancy ──
    print()
    print("REDUNDANCY WARNINGS")
    print("-" * 45)

    redundancy = results["redundancy"]
    if redundancy["warnings"]:
        for w in redundancy["warnings"]:
            print(f"  ! {w['pair'][0]} vs {w['pair'][1]}: r={w['correlation']:+.3f}")
            print(f"       Keep: {w['keep']} (Sharpe={w['keep_sharpe']})")
            print(f"       Investigate: {w['investigate']} (Sharpe={w['investigate_sharpe']})")
    else:
        print(f"  OK No high-correlation pairs detected "
              f"(max |r|={abs(redundancy['max_corr']):.3f} "
              f"between {redundancy['max_pair'][0]} and {redundancy['max_pair'][1]})")

    # ── Regime Gaps ──
    print()
    print("REGIME GAPS")
    print("-" * 45)

    regime_gaps = results["regime_gaps"]
    gap_cells = [g for g in regime_gaps if g["is_gap"]]
    non_gap_cells = [g for g in regime_gaps if not g["is_gap"]]

    if gap_cells:
        # Sort by severity: negative PnL first, then zero trades, then low trades
        negative_pnl = sorted(
            [g for g in gap_cells if g["pnl"] < 0],
            key=lambda x: x["pnl"],
        )
        zero_trade = [g for g in gap_cells if g["trades"] == 0]
        low_trade = sorted(
            [g for g in gap_cells if g["trades"] > 0 and g["pnl"] >= 0],
            key=lambda x: x["trades"],
        )

        if negative_pnl:
            print("  Negative PnL cells:")
            for g in negative_pnl:
                print(f"    ! {g['cell_key']}: ${g['pnl']:,.0f} PnL, "
                      f"PF={g['pf']}, {g['trades']} trades, "
                      f"{g['n_strategies']} strats")

        if zero_trade:
            print("  Zero-trade cells:")
            for g in zero_trade:
                print(f"    ! {g['cell_key']}: no trades")

        if low_trade:
            print("  Low-sample cells (<10 trades):")
            for g in low_trade:
                print(f"    ~ {g['cell_key']}: {g['trades']} trades, "
                      f"PF={g['pf']}, ${g['pnl']:,.0f}")
    else:
        print("  OK All regime cells have positive edge")

    print(f"\n  Coverage: {len(non_gap_cells)}/18 cells with edge, "
          f"{len(gap_cells)} gaps")

    # ── Edge Improvements ──
    print()
    print("EDGE IMPROVEMENTS")
    print("-" * 45)

    improvements = results["improvements"]
    if improvements:
        for imp in improvements:
            print(f"  -> {imp['suggestion']}")
    else:
        print("  No obvious edge improvements detected.")

    # ── Research Suggestions ──
    print()
    print("SUGGESTED RESEARCH")
    print("-" * 45)

    suggestions = []

    # Time gap suggestions
    if gaps["missing_types"]:
        for mt in gaps["missing_types"]:
            if mt == "overnight":
                suggestions.append("Overnight session strategy (fill time gap, new regime exposure)")
            elif mt == "afternoon":
                suggestions.append("Afternoon breakout/fade variant (fill 13:00-15:00 ET gap)")
            elif mt == "volatility_expansion":
                suggestions.append("Volatility expansion system for HIGH_VOL regime cells")
            elif mt == "event_driven":
                suggestions.append("Event-driven regime override layer (not strategy family)")

    # Regime gap suggestions
    neg_cells = [g for g in gap_cells if g["pnl"] < 0]
    if neg_cells:
        cell_names = ", ".join(g["cell_key"] for g in neg_cells[:3])
        suggestions.append(f"Strategy research for negative-edge cells: {cell_names}")

    # Promotion monitoring
    close_promotions = [p for p in promotions if p.get("pct", 0) >= 60 and "error" not in p]
    if close_promotions:
        for p in close_promotions:
            suggestions.append(
                f"Monitor {p['label']} — approaching promotion "
                f"({p['trades']}/{p['threshold']})"
            )

    if suggestions:
        for i, s in enumerate(suggestions, 1):
            print(f"  {i}. {s}")
    else:
        print("  Portfolio is well-positioned. Monitor probation candidates.")

    print()
    print("=" * 65)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Portfolio Opportunity Scanner")
    parser.add_argument("--save", action="store_true",
                        help="Save results to research/opportunity_scan_results.json")
    args = parser.parse_args()

    results = run_scan()
    display_results(results)

    if args.save:
        save_path = ROOT / "research" / "opportunity_scan_results.json"

        # Make sets/tuples JSON-serializable
        def _default(obj):
            if isinstance(obj, set):
                return sorted(obj)
            if isinstance(obj, tuple):
                return list(obj)
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, (np.bool_,)):
                return bool(obj)
            raise TypeError(f"Object of type {type(obj)} not serializable")

        with open(save_path, "w") as f:
            json.dump(results, f, indent=2, default=_default)
        print(f"  Results saved to {save_path}")
        print()


if __name__ == "__main__":
    main()
