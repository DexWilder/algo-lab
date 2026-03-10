"""Phase 13: Range Strategy Discovery.

Evaluates 4 mean-reversion candidates for RANGING regime coverage.
Two-tier gate: discovery (PF>1.15) → promotion candidate (PF>1.4, Sharpe>1.8).
Ranks by portfolio usefulness first, standalone PF second.

Usage:
    python3 research/phase13_range_discovery.py
"""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest
from engine.regime_engine import RegimeEngine
from backtests.run_baseline import compute_extended_metrics, ASSET_CONFIG

PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = Path(__file__).resolve().parent

# ── Candidate strategies ─────────────────────────────────────────────────

RANGE_CANDIDATES = [
    {"name": "vwap_dev_mr",       "label": "VWAP-Dev-MR"},
    {"name": "bb_range_mr",       "label": "BB-Range-MR"},
    {"name": "session_vwap_fade", "label": "Sess-VWAP-Fade"},
    {"name": "orb_fade",          "label": "ORB-Fade"},
]

ASSETS = ["MES", "MNQ", "MGC"]
MODES = ["both", "long", "short"]

# ── Existing portfolio parents (for correlation) ─────────────────────────

PORTFOLIO_PARENTS = [
    {"name": "pb_trend", "asset": "MGC", "mode": "short", "label": "PB",
     "grinding_filter": False, "exit_variant": None},
    {"name": "orb_009", "asset": "MGC", "mode": "long", "label": "ORB",
     "grinding_filter": False, "exit_variant": None},
    {"name": "vwap_trend", "asset": "MNQ", "mode": "long", "label": "VWAP",
     "grinding_filter": False, "exit_variant": None},
    {"name": "xb_pb_ema_timestop", "asset": "MES", "mode": "short", "label": "XB-PB",
     "grinding_filter": False, "exit_variant": None},
    {"name": "donchian_trend", "asset": "MNQ", "mode": "long", "label": "DONCH",
     "grinding_filter": True, "exit_variant": "profit_ladder"},
]

VOL_WEIGHTS = {"PB": 1.214, "ORB": 1.093, "VWAP": 0.758, "XB-PB": 1.228, "DONCH": 0.707}

STARTING_CAPITAL = 50_000.0


# ═══════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════

def load_strategy(name: str):
    path = ROOT / "strategies" / name / "strategy.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def get_daily_pnl(trades_df: pd.DataFrame) -> pd.Series:
    if trades_df.empty:
        return pd.Series(dtype=float)
    tmp = trades_df.copy()
    tmp["date"] = pd.to_datetime(tmp["exit_time"]).dt.date
    daily = tmp.groupby("date")["pnl"].sum()
    daily.index = pd.to_datetime(daily.index)
    return daily


def run_backtest_combo(name, asset, mode):
    """Run a single strategy-asset-mode combo and return trades + metrics."""
    config = ASSET_CONFIG[asset]
    df = pd.read_csv(PROCESSED_DIR / f"{asset}_5m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"])

    mod = load_strategy(name)
    if hasattr(mod, "TICK_SIZE"):
        mod.TICK_SIZE = config["tick_size"]
    signals = mod.generate_signals(df)

    result = run_backtest(
        df, signals, mode=mode,
        point_value=config["point_value"], symbol=asset,
    )
    trades = result["trades_df"]
    equity = result.get("equity_curve", pd.Series(dtype=float))

    if trades.empty:
        return trades, {"profit_factor": 0, "sharpe": 0, "total_pnl": 0,
                        "trade_count": 0, "max_drawdown": 0, "win_rate": 0,
                        "median_trade_duration_bars": 0}

    metrics = compute_extended_metrics(trades, equity, config["point_value"])
    return trades, metrics


def load_parent_daily_pnls(engine: RegimeEngine) -> dict:
    """Load daily PnL for all 5 portfolio parents."""
    pnls = {}
    for p in PORTFOLIO_PARENTS:
        config = ASSET_CONFIG[p["asset"]]
        df = pd.read_csv(PROCESSED_DIR / f"{p['asset']}_5m.csv")
        df["datetime"] = pd.to_datetime(df["datetime"])

        mod = load_strategy(p["name"])
        if hasattr(mod, "TICK_SIZE"):
            mod.TICK_SIZE = config["tick_size"]

        if p.get("exit_variant") == "profit_ladder":
            from research.exit_evolution import donchian_entries, apply_profit_ladder
            data = donchian_entries(df)
            pl_signals_df = apply_profit_ladder(data)
            result = run_backtest(df, pl_signals_df, mode=p["mode"],
                                 point_value=config["point_value"], symbol=p["asset"])
            trades = result["trades_df"]
        else:
            signals = mod.generate_signals(df)
            result = run_backtest(df, signals, mode=p["mode"],
                                 point_value=config["point_value"], symbol=p["asset"])
            trades = result["trades_df"]

        if p.get("grinding_filter") and not trades.empty:
            regime_daily = engine.get_daily_regimes(df)
            regime_daily["_date"] = pd.to_datetime(regime_daily["_date"])
            regime_daily["_date_date"] = regime_daily["_date"].dt.date
            trades["entry_date"] = pd.to_datetime(trades["entry_time"]).dt.date
            trades = trades.merge(
                regime_daily[["_date_date", "trend_persistence"]],
                left_on="entry_date", right_on="_date_date", how="left",
            )
            trades = trades[trades["trend_persistence"] == "GRINDING"]
            trades = trades.drop(columns=["entry_date", "_date_date", "trend_persistence"],
                                 errors="ignore")

        w = VOL_WEIGHTS.get(p["label"], 1.0)
        if not trades.empty:
            trades = trades.copy()
            trades["pnl"] = trades["pnl"] * w

        pnls[p["label"]] = get_daily_pnl(trades)
    return pnls


def compute_regime_breakdown(trades_df, df_raw, engine):
    """Tag each trade with regime cell and compute regime stats."""
    if trades_df.empty:
        return {}, 0, 0.0

    regime_daily = engine.get_daily_regimes(df_raw)
    regime_daily["_date"] = pd.to_datetime(regime_daily["_date"])
    regime_daily["_date_date"] = regime_daily["_date"].dt.date

    trades = trades_df.copy()
    trades["entry_date"] = pd.to_datetime(trades["entry_time"]).dt.date
    trades = trades.merge(
        regime_daily[["_date_date", "composite_regime", "rv_regime", "trend_regime"]],
        left_on="entry_date", right_on="_date_date", how="left",
    )
    trades["full_regime"] = trades["composite_regime"].fillna("UNK") + "_" + trades["rv_regime"].fillna("UNK")

    breakdown = {}
    for regime, grp in trades.groupby("full_regime"):
        breakdown[regime] = {
            "trades": len(grp),
            "pnl": round(grp["pnl"].sum(), 2),
            "win_rate": round((grp["pnl"] > 0).mean() * 100, 1),
        }

    # RANGING stats
    ranging_mask = trades["trend_regime"] == "RANGING"
    ranging_trades = ranging_mask.sum()
    ranging_pnl = trades.loc[ranging_mask, "pnl"].sum() if ranging_trades > 0 else 0.0
    total_pnl = trades["pnl"].sum()

    # RANGING_EDGE_SCORE
    if total_pnl > 0 and ranging_trades > 0:
        pnl_ratio = ranging_pnl / total_pnl
        trade_adj = min(1.0, ranging_trades / 20.0)
        ranging_edge_score = pnl_ratio * trade_adj
    else:
        ranging_edge_score = 0.0

    # TRENDING bleed check
    trending_mask = trades["trend_regime"] == "TRENDING"
    trending_pnl = trades.loc[trending_mask, "pnl"].sum() if trending_mask.sum() > 0 else 0.0
    trending_bleed_ratio = trending_pnl / total_pnl if total_pnl != 0 else 0.0

    return breakdown, ranging_trades, round(ranging_pnl, 2), round(ranging_edge_score, 3), round(trending_bleed_ratio, 3)


def compute_duration_fingerprint(metrics):
    """Get median hold in bars from metrics dict."""
    return int(metrics.get("median_trade_duration_bars", 0))


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def _clean_for_json(obj):
    """Convert numpy types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _clean_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_for_json(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def print_header(title):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def main():
    print_header("PHASE 13: RANGE STRATEGY DISCOVERY")

    engine = RegimeEngine()

    # ═══════════════════════════════════════════════════════════════════
    # STEP 1: BACKTEST GRID (4 strategies × 3 assets × 3 modes = 36)
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 1: BACKTEST GRID")

    all_results = {}
    best_combos = {}

    print(f"\n  {'Strategy':<18s} {'Asset':<5s} {'Mode':<6s} {'PF':>6s} {'Sharpe':>7s} "
          f"{'Trades':>7s} {'PnL':>10s} {'MaxDD':>8s}")
    print(f"  {'-'*17:<18s} {'-'*4:<5s} {'-'*5:<6s} {'-'*6:>6s} {'-'*7:>7s} "
          f"{'-'*7:>7s} {'-'*10:>10s} {'-'*8:>8s}")

    for cand in RANGE_CANDIDATES:
        for asset in ASSETS:
            for mode in MODES:
                trades, metrics = run_backtest_combo(cand["name"], asset, mode)
                key = f"{cand['label']}_{asset}_{mode}"
                pf = metrics.get("profit_factor", 0) or 0
                sharpe = metrics.get("sharpe", 0) or 0
                n_trades = metrics.get("trade_count", 0) or 0
                pnl = metrics.get("total_pnl", 0) or 0
                maxdd = metrics.get("max_drawdown", 0) or 0

                all_results[key] = {
                    "strategy": cand["label"],
                    "name": cand["name"],
                    "asset": asset,
                    "mode": mode,
                    "pf": round(pf, 2),
                    "sharpe": round(sharpe, 2),
                    "trades": n_trades,
                    "pnl": round(pnl, 2),
                    "maxdd": round(maxdd, 2),
                    "trades_df": trades,
                    "metrics": metrics,
                }

                # Track best combo per strategy
                if n_trades >= 30 and pf > 1.0:
                    curr_best = best_combos.get(cand["label"])
                    if curr_best is None or pf > curr_best["pf"]:
                        best_combos[cand["label"]] = all_results[key]

                flag = ""
                if n_trades >= 30 and pf >= 1.15:
                    flag = " ◄ T1"
                if n_trades >= 30 and pf >= 1.4 and sharpe >= 1.8:
                    flag = " ◄ T2"

                print(f"  {cand['label']:<18s} {asset:<5s} {mode:<6s} {pf:>6.2f} {sharpe:>7.2f} "
                      f"{n_trades:>7d} ${pnl:>9,.0f} ${maxdd:>7,.0f}{flag}")

    # ═══════════════════════════════════════════════════════════════════
    # STEP 2: TWO-TIER QUALITY GATE
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 2: QUALITY GATE")

    tier1_candidates = []
    tier2_candidates = []

    for key, r in all_results.items():
        if r["trades"] < 30 or r["pf"] < 1.15:
            continue
        tier1_candidates.append(r)
        if r["pf"] >= 1.4 and r["sharpe"] >= 1.8 and r["trades"] >= 80:
            tier2_candidates.append(r)

    print(f"\n  Tier 1 (discovery gate: PF>1.15, trades≥30): {len(tier1_candidates)} combos")
    print(f"  Tier 2 (promotion gate: PF>1.4, Sharpe>1.8, trades≥80): {len(tier2_candidates)} combos")

    # Select best combo per strategy for deep analysis
    deep_candidates = {}
    for cand in RANGE_CANDIDATES:
        label = cand["label"]
        if label in best_combos:
            deep_candidates[label] = best_combos[label]

    if not deep_candidates:
        print("\n  NO CANDIDATES PASSED DISCOVERY GATE")
        print("  Phase 13 complete — no range engines found.")
        return

    print(f"\n  Best combo per strategy for deep analysis:")
    for label, r in deep_candidates.items():
        t1 = "T1" if r["pf"] >= 1.15 else "—"
        t2 = "T2" if r["pf"] >= 1.4 and r["sharpe"] >= 1.8 else "—"
        print(f"    {label:<18s} {r['asset']}-{r['mode']:<6s} PF={r['pf']:.2f} "
              f"Sharpe={r['sharpe']:.2f} Trades={r['trades']} [{t1}/{t2}]")

    # ═══════════════════════════════════════════════════════════════════
    # STEP 3: REGIME BREAKDOWN (RANGING focus)
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 3: REGIME BREAKDOWN")

    for label, r in deep_candidates.items():
        trades = r["trades_df"]
        if trades.empty:
            continue

        df_raw = pd.read_csv(PROCESSED_DIR / f"{r['asset']}_5m.csv")
        df_raw["datetime"] = pd.to_datetime(df_raw["datetime"])

        breakdown, ranging_trades, ranging_pnl, ranging_edge, trending_bleed = \
            compute_regime_breakdown(trades, df_raw, engine)

        r["ranging_trades"] = ranging_trades
        r["ranging_pnl"] = ranging_pnl
        r["ranging_edge_score"] = ranging_edge
        r["trending_bleed_ratio"] = trending_bleed
        r["regime_breakdown"] = breakdown

        median_hold = compute_duration_fingerprint(r["metrics"])
        r["median_hold"] = median_hold
        dna_ok = 5 <= median_hold <= 20
        r["dna_check"] = "PASS" if dna_ok else ("SHORT" if median_hold < 5 else "LONG")

        # TRENDING bleed check
        bleed_ok = trending_bleed > -0.5  # Not more than 50% of PnL lost in TRENDING
        r["trending_bleed_ok"] = bleed_ok

        print(f"\n  ── {label} ({r['asset']}-{r['mode']}) ──")
        print(f"  RANGING: {ranging_trades} trades, ${ranging_pnl:,.0f} PnL")
        print(f"  RANGING_EDGE_SCORE: {ranging_edge:.3f} {'(range specialist)' if ranging_edge > 0.3 else ''}")
        print(f"  TRENDING bleed ratio: {trending_bleed:.3f} {'PASS' if bleed_ok else 'FAIL — catastrophic bleed'}")
        print(f"  Duration: {median_hold} bars {'(MR DNA OK)' if dna_ok else '(WRONG DNA)'}")

        # Top regime cells
        sorted_cells = sorted(breakdown.items(), key=lambda x: x[1]["pnl"], reverse=True)
        print(f"  Top 5 regime cells:")
        for cell, data in sorted_cells[:5]:
            is_ranging = "RANGING" in cell
            marker = " ★" if is_ranging else ""
            print(f"    {cell:<35s} {data['trades']:>4d} trades  ${data['pnl']:>8,.0f}{marker}")

    # ═══════════════════════════════════════════════════════════════════
    # STEP 4: CORRELATION VS 5 PARENTS
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 4: CORRELATION VS PORTFOLIO")

    print("  Loading parent daily PnLs...")
    parent_pnls = load_parent_daily_pnls(engine)

    # Build portfolio daily PnL
    port_df = pd.DataFrame(parent_pnls).fillna(0)
    portfolio_daily = port_df.sum(axis=1).sort_index()

    for label, r in deep_candidates.items():
        trades = r["trades_df"]
        if trades.empty:
            continue

        cand_daily = get_daily_pnl(trades)
        if cand_daily.empty:
            continue

        # Pairwise correlation vs each parent
        correlations = {}
        for p_label, p_daily in parent_pnls.items():
            combined = pd.DataFrame({"cand": cand_daily, "parent": p_daily}).fillna(0)
            if combined["cand"].std() > 0 and combined["parent"].std() > 0:
                corr = combined["cand"].corr(combined["parent"])
            else:
                corr = 0.0
            correlations[p_label] = round(corr, 3)

        # Correlation vs full portfolio
        combined_port = pd.DataFrame({"cand": cand_daily, "port": portfolio_daily}).fillna(0)
        if combined_port["cand"].std() > 0:
            port_corr = combined_port["cand"].corr(combined_port["port"])
        else:
            port_corr = 0.0

        r["correlations"] = correlations
        r["portfolio_corr"] = round(port_corr, 3)
        r["max_parent_corr"] = max(abs(v) for v in correlations.values())
        r["corr_ok"] = r["max_parent_corr"] < 0.35

        print(f"\n  ── {label} ({r['asset']}-{r['mode']}) ──")
        for p_label, corr in correlations.items():
            marker = " !" if abs(corr) > 0.3 else ""
            print(f"    vs {p_label:<8s}: r={corr:+.3f}{marker}")
        print(f"    vs PORTFOLIO: r={port_corr:+.3f}")
        print(f"    Max |r|: {r['max_parent_corr']:.3f} — {'PASS' if r['corr_ok'] else 'FAIL (>0.35)'}")

    # ═══════════════════════════════════════════════════════════════════
    # STEP 5: PORTFOLIO IMPACT SIMULATION
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 5: PORTFOLIO IMPACT")

    # Baseline portfolio metrics
    baseline_daily = portfolio_daily
    baseline_sharpe = baseline_daily.mean() / baseline_daily.std() * np.sqrt(252) if baseline_daily.std() > 0 else 0
    baseline_eq = STARTING_CAPITAL + baseline_daily.cumsum()
    baseline_peak = baseline_eq.cummax()
    baseline_maxdd = (baseline_peak - baseline_eq).max()
    baseline_calmar = baseline_daily.sum() / baseline_maxdd if baseline_maxdd > 0 else 0
    baseline_monthly = baseline_daily.resample("ME").sum()
    baseline_monthly_pct = (baseline_monthly > 0).sum() / len(baseline_monthly) * 100

    print(f"\n  5-strat baseline: Sharpe={baseline_sharpe:.2f}, Calmar={baseline_calmar:.2f}, "
          f"MaxDD=${baseline_maxdd:,.0f}, Monthly={baseline_monthly_pct:.0f}%")

    for label, r in deep_candidates.items():
        trades = r["trades_df"]
        if trades.empty:
            continue

        cand_daily = get_daily_pnl(trades)
        if cand_daily.empty:
            continue

        # 6-strat portfolio
        combined = pd.DataFrame({"port": portfolio_daily, "cand": cand_daily}).fillna(0)
        port6_daily = combined.sum(axis=1).sort_index()

        sharpe6 = port6_daily.mean() / port6_daily.std() * np.sqrt(252) if port6_daily.std() > 0 else 0
        eq6 = STARTING_CAPITAL + port6_daily.cumsum()
        peak6 = eq6.cummax()
        maxdd6 = (peak6 - eq6).max()
        calmar6 = port6_daily.sum() / maxdd6 if maxdd6 > 0 else 0
        monthly6 = port6_daily.resample("ME").sum()
        monthly6_pct = (monthly6 > 0).sum() / len(monthly6) * 100

        sharpe_delta = sharpe6 - baseline_sharpe
        calmar_delta = calmar6 - baseline_calmar
        maxdd_delta = maxdd6 - baseline_maxdd

        r["portfolio_impact"] = {
            "sharpe_6strat": round(sharpe6, 2),
            "sharpe_delta": round(sharpe_delta, 2),
            "calmar_6strat": round(calmar6, 2),
            "calmar_delta": round(calmar_delta, 2),
            "maxdd_6strat": round(maxdd6, 2),
            "maxdd_delta": round(maxdd_delta, 2),
            "monthly_pct": round(monthly6_pct, 1),
            "pnl_6strat": round(port6_daily.sum(), 2),
        }
        r["positive_portfolio_impact"] = sharpe_delta > 0

        print(f"\n  ── {label} ({r['asset']}-{r['mode']}) ──")
        print(f"  6-strat: Sharpe={sharpe6:.2f} ({sharpe_delta:+.2f}), "
              f"Calmar={calmar6:.2f} ({calmar_delta:+.2f})")
        print(f"  MaxDD=${maxdd6:,.0f} ({maxdd_delta:+,.0f}), Monthly={monthly6_pct:.0f}%")
        print(f"  Portfolio impact: {'POSITIVE' if sharpe_delta > 0 else 'NEGATIVE'}")

    # ═══════════════════════════════════════════════════════════════════
    # STEP 6: FINAL RANKING (portfolio usefulness first)
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 6: FINAL RANKING")

    rankings = []
    for label, r in deep_candidates.items():
        # Compute composite score (portfolio usefulness first)
        portfolio_score = 0.0

        # Portfolio impact weight (40%)
        if "portfolio_impact" in r:
            sd = r["portfolio_impact"]["sharpe_delta"]
            portfolio_score += max(0, sd) * 10  # Scale up

        # RANGING edge weight (30%)
        ranging_edge = r.get("ranging_edge_score", 0)
        portfolio_score += ranging_edge * 10

        # Correlation bonus (20%) — lower correlation = better
        max_corr = r.get("max_parent_corr", 1.0)
        portfolio_score += (0.35 - max_corr) * 10 if max_corr < 0.35 else 0

        # Standalone PF weight (10%)
        pf = r.get("pf", 0)
        portfolio_score += min(pf - 1.0, 1.0) * 3

        r["portfolio_usefulness_score"] = round(portfolio_score, 2)

        # Classification
        corr_ok = r.get("corr_ok", False)
        dna_ok = r.get("dna_check", "") == "PASS"
        bleed_ok = r.get("trending_bleed_ok", False)
        positive_impact = r.get("positive_portfolio_impact", False)

        # Tier assessment
        passes_t1 = r["pf"] >= 1.15 and r["trades"] >= 30 and dna_ok and bleed_ok and corr_ok
        passes_t2 = (passes_t1 and r["pf"] >= 1.4 and r["sharpe"] >= 1.8
                     and r["trades"] >= 80 and positive_impact
                     and ranging_edge > 0.3)

        # Portfolio usefulness override
        override = (not passes_t2 and corr_ok and r.get("portfolio_corr", 1) < 0.1
                    and (positive_impact or ranging_edge > 0.2))

        # Same-family classification
        if r.get("max_parent_corr", 1) > 0.25:
            family_class = "refinement"
        else:
            family_class = "new_engine"

        if not passes_t1:
            classification = "reject"
        elif passes_t2:
            classification = "new_engine"
        elif override:
            classification = "new_engine (override)"
        elif family_class == "refinement":
            classification = "refinement"
        else:
            classification = "new_engine"

        r["tier"] = "T2" if passes_t2 else ("T1" if passes_t1 else "—")
        r["classification"] = classification
        r["override"] = override

        rankings.append(r)

    # Sort by portfolio usefulness score
    rankings.sort(key=lambda x: x["portfolio_usefulness_score"], reverse=True)

    print(f"\n  {'Rank':>4s} {'Strategy':<18s} {'Combo':<12s} {'PF':>6s} {'Sharpe':>7s} "
          f"{'Trades':>7s} {'RES':>5s} {'|r|max':>7s} {'Δ Sharpe':>9s} {'Score':>6s} {'Class':<20s}")
    print(f"  {'-'*4:>4s} {'-'*17:<18s} {'-'*11:<12s} {'-'*6:>6s} {'-'*7:>7s} "
          f"{'-'*7:>7s} {'-'*5:>5s} {'-'*7:>7s} {'-'*9:>9s} {'-'*6:>6s} {'-'*19:<20s}")

    for rank, r in enumerate(rankings, 1):
        combo = f"{r['asset']}-{r['mode']}"
        res = f"{r.get('ranging_edge_score', 0):.2f}"
        max_r = f"{r.get('max_parent_corr', 0):.3f}"
        sd = r.get("portfolio_impact", {}).get("sharpe_delta", 0)
        score = r["portfolio_usefulness_score"]
        cls = r["classification"]
        tier = r["tier"]

        print(f"  {rank:>4d} {r['strategy']:<18s} {combo:<12s} {r['pf']:>6.2f} {r['sharpe']:>7.2f} "
              f"{r['trades']:>7d} {res:>5s} {max_r:>7s} {sd:>+9.2f} {score:>6.2f} {cls:<20s}")

    # ═══════════════════════════════════════════════════════════════════
    # SAVE RESULTS
    # ═══════════════════════════════════════════════════════════════════
    output = {
        "phase": "Phase 13 — Range Strategy Discovery",
        "candidates": {},
        "ranking": [],
    }

    for r in rankings:
        label = r["strategy"]
        output["candidates"][label] = {
            "best_combo": f"{r['asset']}-{r['mode']}",
            "pf": r["pf"],
            "sharpe": r["sharpe"],
            "trades": r["trades"],
            "pnl": r["pnl"],
            "maxdd": r["maxdd"],
            "median_hold": r.get("median_hold", 0),
            "dna_check": r.get("dna_check", ""),
            "ranging_trades": r.get("ranging_trades", 0),
            "ranging_pnl": r.get("ranging_pnl", 0),
            "ranging_edge_score": r.get("ranging_edge_score", 0),
            "trending_bleed_ratio": r.get("trending_bleed_ratio", 0),
            "correlations": r.get("correlations", {}),
            "portfolio_corr": r.get("portfolio_corr", 0),
            "max_parent_corr": r.get("max_parent_corr", 0),
            "portfolio_impact": r.get("portfolio_impact", {}),
            "portfolio_usefulness_score": r.get("portfolio_usefulness_score", 0),
            "tier": r.get("tier", "—"),
            "classification": r.get("classification", "reject"),
        }
        output["ranking"].append({
            "strategy": label,
            "score": r.get("portfolio_usefulness_score", 0),
            "classification": r.get("classification", "reject"),
        })

    output_path = OUTPUT_DIR / "phase13_range_discovery_results.json"
    with open(output_path, "w") as f:
        json.dump(_clean_for_json(output), f, indent=2)

    print(f"\n  Saved to: {output_path}")


if __name__ == "__main__":
    main()
