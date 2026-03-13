#!/usr/bin/env python3
"""Asset Expansion Study — Test existing 6-strategy set on candidate assets.

READ-ONLY research tool. Does NOT modify any frozen execution files.

Tests: MYM (Micro Dow), M2K (Micro Russell), MCL (Micro Crude Oil), ES (E-mini S&P)
Strategies: PB, ORB, VWAP, XB-PB-EMA, BB-EQ, Donchian (GRINDING + Profit Ladder)

Usage:
    python3 research/asset_expansion_study.py                    # full run (fetch + test)
    python3 research/asset_expansion_study.py --cost-only        # check Databento cost
    python3 research/asset_expansion_study.py --skip-fetch       # use existing data
    python3 research/asset_expansion_study.py --asset MYM        # test single asset
    python3 research/asset_expansion_study.py --save             # save results JSON
    python3 research/asset_expansion_study.py --skip-fetch --save --asset ES
"""

import argparse
import importlib.util
import inspect
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest
from engine.regime_engine import RegimeEngine
from engine.metrics import compute_extended_metrics

# ── Constants ─────────────────────────────────────────────────────────────────

PROCESSED_DIR = ROOT / "data" / "processed"
STARTING_CAPITAL = 50_000.0

DEFAULT_START = "2024-03-01"
DEFAULT_END = "2026-03-12"

# Databento settings (mirror databento_loader.py without modifying it)
DATASET = "GLBX.MDP3"
SCHEMA = "ohlcv-1m"
STYPE = "continuous"
EASTERN = "US/Eastern"

# ── Expansion Asset Configs ───────────────────────────────────────────────────

EXPANSION_ASSETS = {
    "MYM": {
        "point_value": 0.50,
        "tick_size": 1.0,
        "commission_per_side": 0.62,
        "slippage_ticks": 1,
        "db_symbol": "MYM.c.0",
        "name": "Micro Dow",
    },
    "M2K": {
        "point_value": 5.0,
        "tick_size": 0.10,
        "commission_per_side": 0.62,
        "slippage_ticks": 1,
        "db_symbol": "M2K.c.0",
        "name": "Micro Russell 2000",
    },
    "MCL": {
        "point_value": 100.0,
        "tick_size": 0.01,
        "commission_per_side": 0.62,
        "slippage_ticks": 1,
        "db_symbol": "MCL.c.0",
        "name": "Micro Crude Oil",
    },
    "ES": {
        "point_value": 50.0,
        "tick_size": 0.25,
        "commission_per_side": 1.24,
        "slippage_ticks": 1,
        "db_symbol": "ES.c.0",
        "name": "E-mini S&P 500",
    },
    "ZN": {
        "point_value": 1000.0,
        "tick_size": 0.015625,
        "commission_per_side": 0.85,
        "slippage_ticks": 1,
        "db_symbol": "ZN.c.0",
        "name": "10-Year Treasury Note",
    },
    "ZB": {
        "point_value": 1000.0,
        "tick_size": 0.03125,
        "commission_per_side": 0.85,
        "slippage_ticks": 1,
        "db_symbol": "ZB.c.0",
        "name": "30-Year Treasury Bond",
    },
}

# Existing core assets (for portfolio baseline)
CORE_ASSETS = {
    "MES": {"point_value": 5.0, "tick_size": 0.25, "commission_per_side": 0.62, "slippage_ticks": 1},
    "MNQ": {"point_value": 2.0, "tick_size": 0.25, "commission_per_side": 0.62, "slippage_ticks": 1},
    "MGC": {"point_value": 10.0, "tick_size": 0.10, "commission_per_side": 0.62, "slippage_ticks": 1},
}

# ── Strategy Definitions ──────────────────────────────────────────────────────

STRATEGIES = [
    {
        "name": "pb_trend",
        "label": "PB",
        "mode": "short",
        "grinding_filter": False,
        "exit_variant": None,
    },
    {
        "name": "orb_009",
        "label": "ORB",
        "mode": "long",
        "grinding_filter": False,
        "exit_variant": None,
    },
    {
        "name": "vwap_trend",
        "label": "VWAP",
        "mode": "long",
        "grinding_filter": False,
        "exit_variant": None,
    },
    {
        "name": "xb_pb_ema_timestop",
        "label": "XB-PB-EMA",
        "mode": "short",
        "grinding_filter": False,
        "exit_variant": None,
    },
    {
        "name": "bb_equilibrium",
        "label": "BB-EQ",
        "mode": "long",
        "grinding_filter": False,
        "exit_variant": None,
    },
    {
        "name": "donchian_trend",
        "label": "Donchian",
        "mode": "long",
        "grinding_filter": True,
        "exit_variant": "profit_ladder",
    },
]

# Current portfolio mapping (for correlation baseline)
CURRENT_PORTFOLIO = [
    {"name": "pb_trend", "asset": "MGC", "mode": "short",
     "label": "PB-MGC-Short", "grinding_filter": False, "exit_variant": None},
    {"name": "orb_009", "asset": "MGC", "mode": "long",
     "label": "ORB-MGC-Long", "grinding_filter": False, "exit_variant": None},
    {"name": "vwap_trend", "asset": "MNQ", "mode": "long",
     "label": "VWAP-MNQ-Long", "grinding_filter": False, "exit_variant": None},
    {"name": "xb_pb_ema_timestop", "asset": "MES", "mode": "short",
     "label": "XB-PB-EMA-MES-Short", "grinding_filter": False, "exit_variant": None},
    {"name": "bb_equilibrium", "asset": "MGC", "mode": "long",
     "label": "BB-EQ-MGC-Long", "grinding_filter": False, "exit_variant": None},
    {"name": "donchian_trend", "asset": "MNQ", "mode": "long",
     "label": "Donchian-MNQ-Long", "grinding_filter": True, "exit_variant": "profit_ladder"},
]


# ── Data Acquisition (Phase 1) ───────────────────────────────────────────────

def get_databento_client():
    """Get Databento client from .env key."""
    from dotenv import load_dotenv
    import databento as db

    load_dotenv(ROOT / ".env")
    key = os.getenv("DATABENTO_API_KEY")
    if not key:
        print("  ERROR: DATABENTO_API_KEY not set in .env")
        sys.exit(1)
    return db.Historical(key)


def check_cost(client, asset_key: str, start: str, end: str) -> float:
    """Check Databento cost for a single symbol."""
    cfg = EXPANSION_ASSETS[asset_key]
    cost = client.metadata.get_cost(
        dataset=DATASET,
        start=start,
        end=end,
        symbols=[cfg["db_symbol"]],
        schema=SCHEMA,
        stype_in=STYPE,
    )
    return cost


def fetch_and_save(client, asset_key: str, start: str, end: str) -> pd.DataFrame:
    """Download 1m bars from Databento, resample to 5m, and save."""
    import databento as db

    cfg = EXPANSION_ASSETS[asset_key]
    db_symbol = cfg["db_symbol"]
    print(f"    Downloading {db_symbol} 1m bars [{start} -> {end}] ...")

    store = client.timeseries.get_range(
        dataset=DATASET,
        start=start,
        end=end,
        symbols=[db_symbol],
        schema=SCHEMA,
        stype_in=STYPE,
    )
    df = store.to_df()

    # Convert UTC -> Eastern, strip tz
    df.index = df.index.tz_convert(EASTERN).tz_localize(None)
    df.index.name = "datetime"

    # Keep OHLCV only
    df = df[["open", "high", "low", "close", "volume"]].copy()

    # Fixed-point price check
    if df["close"].mean() > 100_000:
        print("    WARNING: Prices appear fixed-point, dividing by 1e9")
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col] / 1e9

    print(f"    Got {len(df):,} 1m bars")

    # Resample to 5m
    df_5m = df.resample("5min", label="left", closed="left").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna(subset=["open"])

    print(f"    Resampled to {len(df_5m):,} 5m bars")

    # Save processed
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = PROCESSED_DIR / f"{asset_key}_5m.csv"
    df_5m.to_csv(csv_path)
    print(f"    Saved -> {csv_path.relative_to(ROOT)}")

    # Save metadata
    meta = {
        "dataset_id": f"{asset_key}_5m",
        "symbol": asset_key,
        "timeframe": "5m",
        "start_date": str(df_5m.index[0]),
        "end_date": str(df_5m.index[-1]),
        "bar_count": len(df_5m),
        "trading_days": df_5m.index.normalize().nunique(),
        "source": "databento",
        "source_dataset": DATASET,
        "source_schema": SCHEMA,
        "has_volume": True,
        "volume_mean": round(float(df_5m["volume"].mean()), 1),
        "processed_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    json_path = PROCESSED_DIR / f"{asset_key}_5m.json"
    json_path.write_text(json.dumps(meta, indent=2) + "\n")

    return df_5m


def load_data(asset_key: str) -> pd.DataFrame:
    """Load 5m data from processed CSV."""
    csv_path = PROCESSED_DIR / f"{asset_key}_5m.csv"
    if not csv_path.exists():
        return None
    df = pd.read_csv(csv_path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def data_status(assets: list[str]) -> dict:
    """Check which assets have data and their coverage."""
    status = {}
    for asset in assets:
        csv_path = PROCESSED_DIR / f"{asset}_5m.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path, usecols=["datetime"], parse_dates=["datetime"])
            status[asset] = {
                "exists": True,
                "bars": len(df),
                "start": str(df["datetime"].iloc[0].date()),
                "end": str(df["datetime"].iloc[-1].date()),
            }
        else:
            status[asset] = {"exists": False, "bars": 0, "start": "N/A", "end": "N/A"}
    return status


# ── Strategy Loading ──────────────────────────────────────────────────────────

def load_strategy_module(name: str):
    """Load a strategy module from strategies/<name>/strategy.py."""
    path = ROOT / "strategies" / name / "strategy.py"
    if not path.exists():
        raise FileNotFoundError(f"Strategy not found: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _donchian_entries_for_asset(df: pd.DataFrame, tick_size: float) -> dict:
    """Replicate donchian_entries() from exit_evolution.py with configurable tick size.

    This avoids importing donchian_entries directly (which hard-codes MNQ tick size).
    """
    ATR_STOP_MULT = 2.5
    SESSION_START = "09:30"
    SESSION_END = "15:45"

    mod = load_strategy_module("donchian_trend")
    mod.TICK_SIZE = tick_size

    original_signals = mod.generate_signals(df.copy())

    sig_arr = original_signals["signal"].values
    stop_arr_orig = original_signals["stop_price"].values

    # Compute ATR matching the original strategy's formula exactly
    df_c = df.copy()
    low_channel = df_c["low"].rolling(window=30, min_periods=30).min().shift(1)
    prev_close = df_c["close"].shift(1)
    tr = pd.concat([
        df_c["high"] - df_c["low"],
        (df_c["high"] - prev_close).abs(),
        (low_channel - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=14, adjust=False).mean()
    atr_arr = atr.values

    dt = pd.to_datetime(df_c["datetime"])
    time_str = dt.dt.strftime("%H:%M")
    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)

    entries = []
    for i in range(len(sig_arr)):
        if sig_arr[i] != 0:
            direction = int(sig_arr[i])
            entry_price = df_c["close"].iloc[i]
            bar_atr = atr_arr[i]
            initial_stop = stop_arr_orig[i]
            if np.isnan(initial_stop):
                if direction == 1:
                    initial_stop = entry_price - bar_atr * ATR_STOP_MULT
                else:
                    initial_stop = entry_price + bar_atr * ATR_STOP_MULT
            entries.append({
                "bar_idx": i,
                "direction": direction,
                "entry_price": entry_price,
                "atr_at_entry": bar_atr,
                "initial_stop": initial_stop,
            })

    return {
        "entries": entries,
        "original_signals": original_signals,
        "atr": atr_arr,
        "close": df_c["close"].values,
        "high": df_c["high"].values,
        "low": df_c["low"].values,
        "time": time_str.values,
        "dates": dt.dt.date.values,
        "in_session": in_session.values,
        "n": len(df_c),
        "df": df_c,
    }


def generate_signals_for_strategy(strat: dict, df: pd.DataFrame, asset: str, tick_size: float):
    """Generate signals, handling exit_variant and asset kwarg."""
    if strat["exit_variant"] == "profit_ladder":
        from research.exit_evolution import apply_profit_ladder
        data = _donchian_entries_for_asset(df, tick_size)
        signals = apply_profit_ladder(data)
        return signals
    else:
        mod = load_strategy_module(strat["name"])
        if hasattr(mod, "TICK_SIZE"):
            mod.TICK_SIZE = tick_size

        sig = inspect.signature(mod.generate_signals)
        if "asset" in sig.parameters:
            return mod.generate_signals(df, asset=asset)
        else:
            return mod.generate_signals(df)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_daily_pnl(trades_df: pd.DataFrame) -> pd.Series:
    """Convert trades to daily PnL series."""
    if trades_df.empty:
        return pd.Series(dtype=float)
    tmp = trades_df.copy()
    tmp["date"] = pd.to_datetime(tmp["exit_time"]).dt.date
    daily = tmp.groupby("date")["pnl"].sum()
    daily.index = pd.to_datetime(daily.index)
    return daily


def apply_grinding_filter(trades_df: pd.DataFrame, regime_daily: pd.DataFrame) -> pd.DataFrame:
    """Filter trades to GRINDING days only."""
    if trades_df.empty:
        return trades_df
    rd = regime_daily.copy()
    rd["_date"] = pd.to_datetime(rd["_date"])
    rd["_date_date"] = rd["_date"].dt.date

    trades = trades_df.copy()
    trades["entry_date"] = pd.to_datetime(trades["entry_time"]).dt.date
    trades = trades.merge(
        rd[["_date_date", "trend_persistence"]],
        left_on="entry_date", right_on="_date_date", how="left",
    )
    trades = trades[trades["trend_persistence"] == "GRINDING"]
    trades = trades.drop(
        columns=["entry_date", "_date_date", "trend_persistence"],
        errors="ignore",
    ).reset_index(drop=True)
    return trades


def portfolio_metrics(port_daily: pd.Series, trade_count: int) -> dict:
    """Compute portfolio-level metrics from daily PnL series."""
    if port_daily.empty or port_daily.sum() == 0:
        return {"sharpe": 0, "maxdd": 0, "calmar": 0, "monthly_pct": 0,
                "total_pnl": 0, "trades": trade_count}

    total_pnl = port_daily.sum()
    sharpe = (port_daily.mean() / port_daily.std() * np.sqrt(252)
              if port_daily.std() > 0 else 0)

    equity = STARTING_CAPITAL + port_daily.cumsum()
    peak = equity.cummax()
    dd = peak - equity
    maxdd = dd.max()
    calmar = total_pnl / maxdd if maxdd > 0 else 0

    monthly = port_daily.resample("ME").sum()
    profitable_months = (monthly > 0).sum()
    total_months = len(monthly)
    monthly_pct = profitable_months / total_months * 100 if total_months > 0 else 0

    return {
        "sharpe": round(sharpe, 2),
        "maxdd": round(maxdd, 2),
        "calmar": round(calmar, 2),
        "monthly_pct": round(monthly_pct, 1),
        "total_pnl": round(total_pnl, 2),
        "trades": trade_count,
    }


# ── Phase 2: Strategy Testing ────────────────────────────────────────────────

def run_strategy_on_asset(
    strat: dict,
    asset: str,
    df: pd.DataFrame,
    engine: RegimeEngine,
) -> dict:
    """Run a single strategy on a single asset. Returns result dict or None on error."""
    cfg = EXPANSION_ASSETS[asset]

    try:
        signals = generate_signals_for_strategy(
            strat, df.copy(), asset, cfg["tick_size"],
        )
    except Exception as e:
        return {"error": str(e), "label": f"{strat['label']}-{asset}-{strat['mode'].title()}"}

    try:
        result = run_backtest(
            df, signals,
            mode=strat["mode"],
            point_value=cfg["point_value"],
            symbol=asset,
            commission_per_side=cfg["commission_per_side"],
            slippage_ticks=cfg["slippage_ticks"],
            tick_size=cfg["tick_size"],
        )
    except Exception as e:
        return {"error": str(e), "label": f"{strat['label']}-{asset}-{strat['mode'].title()}"}

    trades = result["trades_df"]

    # Apply GRINDING filter for Donchian
    if strat.get("grinding_filter") and not trades.empty:
        regime_daily = engine.get_daily_regimes(df)
        trades = apply_grinding_filter(trades, regime_daily)

    equity = result["equity_curve"]

    # Compute metrics
    if trades.empty or len(trades) == 0:
        return {
            "label": f"{strat['label']}-{asset}-{strat['mode'].title()}",
            "strategy": strat["label"],
            "asset": asset,
            "mode": strat["mode"],
            "trades": 0,
            "pf": 0,
            "sharpe": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "maxdd": 0,
            "avg_trade": 0,
            "daily_pnl": pd.Series(dtype=float),
            "trades_df": pd.DataFrame(),
        }

    metrics = compute_extended_metrics(trades, equity, cfg["point_value"])

    daily = get_daily_pnl(trades)

    return {
        "label": f"{strat['label']}-{asset}-{strat['mode'].title()}",
        "strategy": strat["label"],
        "asset": asset,
        "mode": strat["mode"],
        "trades": metrics["trade_count"],
        "pf": metrics["profit_factor"],
        "sharpe": metrics["sharpe"],
        "win_rate": metrics["win_rate"],
        "total_pnl": metrics["total_pnl"],
        "maxdd": metrics["max_drawdown"],
        "avg_trade": metrics["expectancy"],
        "daily_pnl": daily,
        "trades_df": trades,
    }


# ── Phase 3: Correlation Analysis ────────────────────────────────────────────

def run_current_portfolio(engine: RegimeEngine) -> dict:
    """Run the current 6-strategy portfolio and return daily PnLs."""
    daily_pnls = {}
    trade_counts = {}

    for strat in CURRENT_PORTFOLIO:
        asset = strat["asset"]
        asset_cfg = CORE_ASSETS[asset]
        label = strat["label"]

        df = load_data(asset)
        if df is None:
            print(f"    WARNING: Missing data for {asset}, skipping {label}")
            continue

        try:
            signals = generate_signals_for_strategy(
                strat, df.copy(), asset, asset_cfg["tick_size"],
            )
            result = run_backtest(
                df, signals,
                mode=strat["mode"],
                point_value=asset_cfg["point_value"],
                symbol=asset,
            )
            trades = result["trades_df"]

            if strat.get("grinding_filter") and not trades.empty:
                regime_daily = engine.get_daily_regimes(df)
                trades = apply_grinding_filter(trades, regime_daily)

            daily_pnls[label] = get_daily_pnl(trades)
            trade_counts[label] = len(trades)
        except Exception as e:
            print(f"    WARNING: Error running {label}: {e}")
            daily_pnls[label] = pd.Series(dtype=float)
            trade_counts[label] = 0

    return daily_pnls, trade_counts


def compute_correlation_vs_portfolio(
    combo_daily: pd.Series,
    portfolio_daily_pnls: dict,
) -> dict:
    """Compute daily PnL correlation between a new combo and each existing strategy."""
    correlations = {}
    if combo_daily.empty:
        return correlations

    for label, existing_daily in portfolio_daily_pnls.items():
        if existing_daily.empty:
            correlations[label] = 0.0
            continue
        # Align on common dates
        combined = pd.DataFrame({
            "new": combo_daily,
            "existing": existing_daily,
        }).fillna(0)
        if combined["new"].std() == 0 or combined["existing"].std() == 0:
            correlations[label] = 0.0
        else:
            correlations[label] = round(combined.corr().loc["new", "existing"], 3)

    return correlations


# ── Phase 5: Report Printing ─────────────────────────────────────────────────

def print_report(
    data_stat: dict,
    results_matrix: dict,
    viable_combos: list,
    portfolio_impact: list,
    portfolio_daily_pnls: dict,
    current_port_metrics: dict,
    assets_tested: list[str],
):
    """Print the full formatted report."""
    W = 70

    print()
    print("=" * W)
    print("  ASSET EXPANSION STUDY")
    print("=" * W)

    # ── Data Status ───────────────────────────────────────────────
    print()
    print("  DATA STATUS")
    print(f"  {'─' * 40}")
    for asset in assets_tested:
        s = data_stat.get(asset, {})
        if s.get("exists"):
            print(f"  {asset:<5} {s['bars']:>7,} bars  ({s['start']} to {s['end']})")
        else:
            print(f"  {asset:<5} NO DATA")

    # ── Strategy x Asset Matrix ───────────────────────────────────
    print()
    print("  STRATEGY x ASSET MATRIX")
    print(f"  {'═' * (W - 4)}")

    col_w = 14
    header = f"  {'Strategy':<{col_w}}"
    for asset in assets_tested:
        header += f"  {asset:<{col_w}}"
    print(header)
    print(f"  {'─' * col_w}" + f"  {'─' * col_w}" * len(assets_tested))

    for strat in STRATEGIES:
        row1 = f"  {strat['label'] + '-' + strat['mode'].title():<{col_w}}"
        row2 = f"  {'':<{col_w}}"
        for asset in assets_tested:
            key = (strat["label"], asset)
            r = results_matrix.get(key)
            if r is None:
                row1 += f"  {'N/A':<{col_w}}"
                row2 += f"  {'':<{col_w}}"
            elif "error" in r:
                row1 += f"  {'ERROR':<{col_w}}"
                row2 += f"  {'':<{col_w}}"
            elif r["trades"] == 0:
                row1 += f"  {'0 trades':<{col_w}}"
                row2 += f"  {'':<{col_w}}"
            else:
                pf_str = f"PF={r['pf']:.2f}"
                tr_str = f"{r['trades']} trades"
                pnl_str = f"${r['total_pnl']:,.0f}"
                row1 += f"  {pf_str:<{col_w}}"
                row2 += f"  {tr_str:<{col_w}}"
        print(row1)
        print(row2)

    # ── Viable Combos ─────────────────────────────────────────────
    print()
    print("  VIABLE COMBOS (PF > 1.3, trades > 30)")
    print(f"  {'─' * (W - 4)}")

    if not viable_combos:
        print("  None found.")
    else:
        print(f"  {'Rank':<6} {'Combo':<28} {'PF':>6} {'Sharpe':>8} {'Trades':>8} {'PnL':>10} {'Corr vs Port':>16}")
        print(f"  {'─' * 4}  {'─' * 26}  {'─' * 4}  {'─' * 6}  {'─' * 6}  {'─' * 8}  {'─' * 14}")
        for i, c in enumerate(viable_combos, 1):
            max_corr = max(abs(v) for v in c["correlations"].values()) if c["correlations"] else 0
            corr_label = "excellent" if max_corr < 0.1 else "good" if max_corr < 0.2 else "moderate" if max_corr < 0.3 else "HIGH"
            corr_str = f"r={max_corr:.2f} ({corr_label})"
            print(f"  {i:<6} {c['label']:<28} {c['pf']:>6.2f} {c['sharpe']:>8.2f} {c['trades']:>8} "
                  f"{'${:,.0f}'.format(c['total_pnl']):>10} {corr_str:>16}")

    # ── Portfolio Impact ──────────────────────────────────────────
    print()
    print("  PORTFOLIO IMPACT (adding top combos)")
    print(f"  {'─' * (W - 4)}")
    print(f"  {'Portfolio':<30} {'Sharpe':>8} {'MaxDD':>10} {'Monthly%':>10} {'Trades':>8} {'PnL':>12}")
    print(f"  {'─' * 28}  {'─' * 6}  {'─' * 8}  {'─' * 8}  {'─' * 6}  {'─' * 10}")

    # Current portfolio baseline
    print(f"  {'Current 6-strat':<30} {current_port_metrics['sharpe']:>8.2f} "
          f"{'${:,.0f}'.format(current_port_metrics['maxdd']):>10} "
          f"{current_port_metrics['monthly_pct']:>9.0f}% "
          f"{current_port_metrics['trades']:>8} "
          f"{'${:,.0f}'.format(current_port_metrics['total_pnl']):>12}")

    for pi in portfolio_impact:
        label = f"+ {pi['added_label']}"
        print(f"  {label:<30} {pi['sharpe']:>8.2f} "
              f"{'${:,.0f}'.format(pi['maxdd']):>10} "
              f"{pi['monthly_pct']:>9.0f}% "
              f"{pi['trades']:>8} "
              f"{'${:,.0f}'.format(pi['total_pnl']):>12}")

    # ── Correlation Detail ────────────────────────────────────────
    if viable_combos:
        print()
        print("  CORRELATION DETAIL (viable combos vs existing strategies)")
        print(f"  {'─' * (W - 4)}")
        for c in viable_combos[:5]:  # top 5
            print(f"\n  {c['label']}:")
            for strat_label, corr_val in sorted(c["correlations"].items(), key=lambda x: abs(x[1]), reverse=True):
                flag = " *** HIGH ***" if abs(corr_val) > 0.3 else ""
                print(f"    vs {strat_label:<30} r={corr_val:>7.3f}{flag}")

    # ── Recommendation ────────────────────────────────────────────
    print()
    print("  RECOMMENDATION")
    print(f"  {'─' * 40}")

    add_list = []
    skip_list = []
    needs_data = []

    for asset in assets_tested:
        ds = data_stat.get(asset, {})
        if not ds.get("exists"):
            needs_data.append(asset)
            continue

        # Find best combo for this asset
        asset_combos = [c for c in viable_combos if c["asset"] == asset]
        if not asset_combos:
            # Check if any strategies ran
            asset_results = [r for (sl, a), r in results_matrix.items()
                             if a == asset and "error" not in r and r.get("trades", 0) > 0]
            if asset_results:
                best = max(asset_results, key=lambda x: x.get("pf", 0))
                skip_list.append(f"{asset} (best PF={best['pf']:.2f}, {best['trades']} trades — below threshold)")
            else:
                skip_list.append(f"{asset} (no viable strategy-asset combos)")
        else:
            best = asset_combos[0]
            max_corr = max(abs(v) for v in best["correlations"].values()) if best["correlations"] else 0
            if max_corr > 0.3:
                skip_list.append(f"{asset} ({best['label']} has high correlation r={max_corr:.2f})")
            else:
                add_list.append(f"{best['label']} (PF={best['pf']:.2f}, Sharpe={best['sharpe']:.2f}, r_max={max_corr:.2f})")

    if add_list:
        print("  Add:")
        for item in add_list:
            print(f"    + {item}")
    else:
        print("  Add: None recommended at this time.")

    if skip_list:
        print("  Skip:")
        for item in skip_list:
            print(f"    - {item}")

    if needs_data:
        print("  Needs more data:")
        for item in needs_data:
            print(f"    ? {item} (run without --skip-fetch to acquire)")

    print()
    print("=" * W)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Asset Expansion Study")
    parser.add_argument("--cost-only", action="store_true", help="Check Databento cost only")
    parser.add_argument("--skip-fetch", action="store_true", help="Skip data fetch, use existing data")
    parser.add_argument("--asset", type=str, choices=list(EXPANSION_ASSETS.keys()),
                        help="Test single expansion asset")
    parser.add_argument("--save", action="store_true", help="Save results to JSON")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip cost confirmation prompt")
    parser.add_argument("--start", type=str, default=DEFAULT_START, help=f"Start date (default: {DEFAULT_START})")
    parser.add_argument("--end", type=str, default=DEFAULT_END, help=f"End date (default: {DEFAULT_END})")
    args = parser.parse_args()

    assets_to_test = [args.asset] if args.asset else list(EXPANSION_ASSETS.keys())

    print()
    print("=" * 70)
    print("  ASSET EXPANSION STUDY")
    print(f"  Assets: {', '.join(assets_to_test)}")
    print(f"  Strategies: {len(STRATEGIES)}")
    print("=" * 70)

    # ── Phase 1: Data Acquisition ─────────────────────────────────
    print("\n  PHASE 1: DATA ACQUISITION")
    print(f"  {'─' * 40}")

    if args.cost_only:
        client = get_databento_client()
        total_cost = 0.0
        for asset in assets_to_test:
            cost = check_cost(client, asset, args.start, args.end)
            total_cost += cost
            print(f"    {asset}: ${cost:.4f}")
        print(f"\n    Total estimated cost: ${total_cost:.4f}")
        return

    if not args.skip_fetch:
        # Check which assets need fetching
        missing = []
        for asset in assets_to_test:
            csv_path = PROCESSED_DIR / f"{asset}_5m.csv"
            if csv_path.exists():
                print(f"    {asset}: data exists, skipping fetch")
            else:
                missing.append(asset)

        if missing:
            client = get_databento_client()

            # Cost check first
            total_cost = 0.0
            for asset in missing:
                cost = check_cost(client, asset, args.start, args.end)
                total_cost += cost
                print(f"    {asset}: estimated cost ${cost:.4f}")

            print(f"    Total fetch cost: ${total_cost:.4f}")

            if total_cost > 5.0 and not args.yes:
                resp = input(f"\n    Cost exceeds $5. Continue? [y/N] ")
                if resp.lower() != "y":
                    print("    Aborted.")
                    return

            for asset in missing:
                print(f"\n    Fetching {asset}...")
                fetch_and_save(client, asset, args.start, args.end)
    else:
        print("    --skip-fetch: using existing data only")

    # Verify data status
    ds = data_status(assets_to_test)
    available_assets = [a for a in assets_to_test if ds[a]["exists"]]
    if not available_assets:
        print("\n    ERROR: No data available for any requested asset.")
        print("    Run without --skip-fetch to download data.")
        return

    # ── Phase 2: Strategy Testing ─────────────────────────────────
    print(f"\n  PHASE 2: STRATEGY TESTING")
    print(f"  {'─' * 40}")

    engine = RegimeEngine()
    results_matrix = {}  # (strategy_label, asset) -> result dict

    for asset in available_assets:
        df = load_data(asset)
        if df is None:
            continue
        print(f"\n    {asset}: {len(df):,} bars ({df['datetime'].iloc[0].date()} to {df['datetime'].iloc[-1].date()})")

        for strat in STRATEGIES:
            combo_label = f"{strat['label']}-{asset}-{strat['mode'].title()}"
            print(f"      {combo_label}...", end=" ", flush=True)

            result = run_strategy_on_asset(strat, asset, df, engine)
            results_matrix[(strat["label"], asset)] = result

            if "error" in result:
                print(f"ERROR: {result['error'][:60]}")
            elif result["trades"] == 0:
                print("0 trades")
            else:
                print(f"{result['trades']} trades, PF={result['pf']:.2f}, "
                      f"Sharpe={result['sharpe']:.2f}, PnL=${result['total_pnl']:,.0f}")

    # ── Phase 3: Correlation Analysis ─────────────────────────────
    print(f"\n  PHASE 3: CORRELATION ANALYSIS")
    print(f"  {'─' * 40}")

    print("    Running current portfolio baseline...")
    portfolio_daily_pnls, portfolio_trade_counts = run_current_portfolio(engine)
    current_total_trades = sum(portfolio_trade_counts.values())

    # Build current portfolio aggregate daily PnL
    port_df = pd.DataFrame(portfolio_daily_pnls).fillna(0)
    current_port_daily = port_df.sum(axis=1).sort_index() if not port_df.empty else pd.Series(dtype=float)
    current_port_metrics = portfolio_metrics(current_port_daily, current_total_trades)

    print(f"    Current portfolio: {current_total_trades} trades, "
          f"Sharpe={current_port_metrics['sharpe']:.2f}, "
          f"PnL=${current_port_metrics['total_pnl']:,.0f}")

    # Compute correlations for each viable result
    viable_combos = []
    for (strat_label, asset), result in results_matrix.items():
        if "error" in result:
            continue
        if result.get("trades", 0) < 30:
            continue
        if result.get("pf", 0) < 1.3:
            continue

        corr = compute_correlation_vs_portfolio(result["daily_pnl"], portfolio_daily_pnls)
        result["correlations"] = corr
        viable_combos.append(result)

    # Sort by Sharpe descending
    viable_combos.sort(key=lambda x: x.get("sharpe", 0), reverse=True)

    print(f"    Found {len(viable_combos)} viable combos (PF > 1.3, trades > 30)")

    # ── Phase 4: Portfolio Impact ─────────────────────────────────
    print(f"\n  PHASE 4: PORTFOLIO IMPACT")
    print(f"  {'─' * 40}")

    portfolio_impact = []
    for combo in viable_combos[:10]:  # top 10
        # Add this combo's daily PnL to existing portfolio
        augmented_pnls = dict(portfolio_daily_pnls)
        augmented_pnls[combo["label"]] = combo["daily_pnl"]

        aug_df = pd.DataFrame(augmented_pnls).fillna(0)
        aug_daily = aug_df.sum(axis=1).sort_index()
        aug_trades = current_total_trades + combo["trades"]

        aug_metrics = portfolio_metrics(aug_daily, aug_trades)

        impact = {
            "added_label": combo["label"],
            "sharpe": aug_metrics["sharpe"],
            "maxdd": aug_metrics["maxdd"],
            "monthly_pct": aug_metrics["monthly_pct"],
            "trades": aug_metrics["trades"],
            "total_pnl": aug_metrics["total_pnl"],
            "sharpe_delta": aug_metrics["sharpe"] - current_port_metrics["sharpe"],
            "maxdd_delta": aug_metrics["maxdd"] - current_port_metrics["maxdd"],
        }
        portfolio_impact.append(impact)

        print(f"    + {combo['label']}: Sharpe {current_port_metrics['sharpe']:.2f} -> {aug_metrics['sharpe']:.2f} "
              f"({impact['sharpe_delta']:+.2f}), "
              f"MaxDD ${current_port_metrics['maxdd']:,.0f} -> ${aug_metrics['maxdd']:,.0f}")

    # Sort by Sharpe improvement
    portfolio_impact.sort(key=lambda x: x["sharpe_delta"], reverse=True)

    # ── Phase 5: Report ───────────────────────────────────────────
    print_report(
        data_stat=ds,
        results_matrix=results_matrix,
        viable_combos=viable_combos,
        portfolio_impact=portfolio_impact,
        portfolio_daily_pnls=portfolio_daily_pnls,
        current_port_metrics=current_port_metrics,
        assets_tested=available_assets,
    )

    # ── Save results ──────────────────────────────────────────────
    if args.save:
        output_path = ROOT / "research" / "asset_expansion_results.json"
        save_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "assets_tested": available_assets,
            "data_status": ds,
            "results_matrix": {
                f"{sl}|{a}": {
                    k: v for k, v in r.items()
                    if k not in ("daily_pnl", "trades_df", "correlations")
                }
                for (sl, a), r in results_matrix.items()
            },
            "viable_combos": [
                {k: v for k, v in c.items() if k not in ("daily_pnl", "trades_df")}
                for c in viable_combos
            ],
            "portfolio_impact": portfolio_impact,
            "current_portfolio_metrics": current_port_metrics,
        }
        output_path.write_text(json.dumps(save_data, indent=2, default=str) + "\n")
        print(f"\n  Results saved to {output_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
