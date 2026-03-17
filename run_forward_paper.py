#!/usr/bin/env python3
"""Forward Paper Trading Runner — Smoke Test.

Processes the latest data through the full 6-strategy pipeline:
    Strategy signals → Strategy Controller → Prop Controller → Kill Switch → Logs

Only processes bars after the last processed timestamp (no reprocessing).
Loads/saves account state between runs.

Usage:
    python3 run_forward_paper.py                # run once
    python3 run_forward_paper.py --reset        # reset state and run fresh
"""

import argparse
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest
from engine.regime_engine import RegimeEngine
from engine.strategy_controller import StrategyController
from engine.strategy_universe import build_portfolio_config

PROCESSED_DIR = ROOT / "data" / "processed"
STATE_DIR = ROOT / "state"
LOGS_DIR = ROOT / "logs"
STATE_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

ACCOUNT_STATE_PATH = STATE_DIR / "account_state.json"

from engine.asset_config import get_execution_params, ASSETS

# Build ASSET_CONFIG from canonical asset_config for all assets with data
ASSET_CONFIG = {}
for sym in ASSETS:
    data_path = ROOT / "data" / "processed" / f"{sym}_5m.csv"
    if data_path.exists():
        ASSET_CONFIG[sym] = get_execution_params(sym)

STARTING_EQUITY = 50_000.0


def load_account_state() -> dict:
    """Load account state from disk, or create fresh state."""
    if ACCOUNT_STATE_PATH.exists():
        with open(ACCOUNT_STATE_PATH) as f:
            state = json.load(f)
        print(f"  Loaded account state (last run: {state.get('last_run', 'unknown')})")
        return state

    state = {
        "equity": STARTING_EQUITY,
        "cumulative_pnl": 0.0,
        "equity_hwm": STARTING_EQUITY,
        "total_trades": 0,
        "total_signals": 0,
        "consecutive_losses": 0,
        "last_processed_bar": {},  # {asset: last_datetime}
        "last_run": None,
        "run_count": 0,
    }
    print(f"  Created fresh account state (equity: ${STARTING_EQUITY:,.0f})")
    return state


def save_account_state(state: dict):
    from research.utils.atomic_io import atomic_write_json
    state["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state["run_count"] = state.get("run_count", 0) + 1
    atomic_write_json(ACCOUNT_STATE_PATH, state)


def load_strategy(name: str):
    path = ROOT / "strategies" / name / "strategy.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def get_new_bars(asset: str, last_processed: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load full dataset and identify new bars.

    Returns (full_df, new_bars_df).
    full_df is needed for signal generation (indicators need history).
    new_bars_df contains only bars after last_processed.
    """
    csv_path = PROCESSED_DIR / f"{asset}_5m.csv"
    df = pd.read_csv(csv_path)
    df["datetime"] = pd.to_datetime(df["datetime"])

    if last_processed:
        last_dt = pd.Timestamp(last_processed)
        new_bars = df[df["datetime"] > last_dt]
    else:
        # First run: treat last 2 trading days as "new"
        cutoff = df["datetime"].max() - pd.Timedelta(days=3)
        new_bars = df[df["datetime"] > cutoff]

    return df, new_bars


def run_strategy_on_new_bars(
    strat_key: str,
    strat_config: dict,
    full_df: pd.DataFrame,
    new_bars: pd.DataFrame,
    engine: RegimeEngine,
    regime_daily: pd.DataFrame,
) -> tuple[pd.DataFrame, int]:
    """Run a strategy and extract trades that fall within new bars.

    Returns (new_trades, signal_count).
    """
    asset = strat_config["asset"]
    config = ASSET_CONFIG[asset]

    mod = load_strategy(strat_config["name"])
    if hasattr(mod, "TICK_SIZE"):
        mod.TICK_SIZE = config["tick_size"]

    # Generate signals on full dataset (indicators need history)
    if strat_config.get("exit_variant") == "profit_ladder":
        from research.exit_evolution import donchian_entries, apply_profit_ladder
        data = donchian_entries(full_df)
        signals = apply_profit_ladder(data)
    else:
        signals = mod.generate_signals(full_df)

    # Handle daily-bar strategies that resample internally
    # (signals has fewer rows than full_df)
    bt_df = signals if len(signals) < len(full_df) else full_df

    # Run backtest on full dataset
    result = run_backtest(
        bt_df, signals,
        mode=strat_config["mode"],
        point_value=config["point_value"],
        symbol=asset,
    )
    trades = result["trades_df"]

    if trades.empty:
        return pd.DataFrame(), 0

    # Apply GRINDING filter
    if strat_config.get("grinding_filter"):
        rd = regime_daily.copy()
        rd["_date"] = pd.to_datetime(rd["_date"])
        rd["_date_date"] = rd["_date"].dt.date
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

    # Filter to trades whose entry falls within new bars period
    if new_bars.empty:
        return pd.DataFrame(), 0

    new_start = new_bars["datetime"].min()
    trades["entry_dt"] = pd.to_datetime(trades["entry_time"])
    new_trades = trades[trades["entry_dt"] >= new_start].drop(
        columns=["entry_dt"], errors="ignore"
    ).reset_index(drop=True)

    # Count signals in new bars
    if "signal" in signals.columns:
        new_signals = signals[signals["datetime"].isin(new_bars["datetime"]) if "datetime" in signals.columns else False]
        signal_count = 0
        if not new_bars.empty:
            sig_mask = signals.index.isin(new_bars.index) if len(signals) == len(full_df) else False
            if isinstance(sig_mask, pd.Series):
                signal_count = int((signals.loc[sig_mask, "signal"] != 0).sum())
    else:
        signal_count = len(new_trades)

    return new_trades, signal_count


def append_log(log_path: Path, rows: list[dict]):
    """Append rows to a CSV log file, creating headers if new."""
    if not rows:
        return
    df = pd.DataFrame(rows)
    write_header = not log_path.exists() or log_path.stat().st_size == 0
    df.to_csv(log_path, mode="a", header=write_header, index=False)


def main():
    parser = argparse.ArgumentParser(description="Forward Paper Trading Runner")
    parser.add_argument("--reset", action="store_true", help="Reset account state")
    args = parser.parse_args()

    print("=" * 70)
    print("  FORWARD PAPER TRADING — SMOKE TEST")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # ── Load state ───────────────────────────────────────────────────────
    if args.reset and ACCOUNT_STATE_PATH.exists():
        ACCOUNT_STATE_PATH.unlink()
        print("  Account state reset.")

    state = load_account_state()

    # ── Load data & check for new bars ───────────────────────────────────
    print(f"\n  Checking for new data...")
    engine = RegimeEngine()
    # Include probation strategies in forward paper trading
    # (they need forward evidence for promotion review)
    portfolio_config = build_portfolio_config(include_probation=True)
    controller = StrategyController(portfolio_config)
    strat_configs = portfolio_config["strategies"]

    data_cache = {}
    regime_cache = {}
    new_bar_counts = {}

    # Determine which assets are needed by active strategies
    needed_assets = set()
    for strat in strat_configs.values():
        needed_assets.add(strat["asset"])

    for asset in sorted(needed_assets):
        if asset not in ASSET_CONFIG:
            print(f"    {asset}: SKIP (no data or asset config)")
            continue
        csv_path = PROCESSED_DIR / f"{asset}_5m.csv"
        if not csv_path.exists():
            print(f"    {asset}: SKIP (no data file)")
            continue

        last = state["last_processed_bar"].get(asset, "")
        full_df, new_bars = get_new_bars(asset, last)
        data_cache[asset] = (full_df, new_bars)
        regime_cache[asset] = engine.get_daily_regimes(full_df)
        new_bar_counts[asset] = len(new_bars)

        if last:
            print(f"    {asset}: last processed = {last}")
        else:
            print(f"    {asset}: first run (using last 3 days)")
        print(f"    {asset}: {len(new_bars)} new 5m bars")

    total_new = sum(new_bar_counts.values())
    if total_new == 0:
        print(f"\n  No new bars to process. Data is current.")
        print(f"  Run scripts/update_daily_data.py to fetch new data.")
        return

    # ── Get today's regime ───────────────────────────────────────────────
    # Use MES as reference
    mes_full, mes_new = data_cache["MES"]
    if not mes_new.empty:
        last_date = mes_new["datetime"].iloc[-1]
        today_str = last_date.strftime("%Y-%m-%d")
    else:
        today_str = datetime.now().strftime("%Y-%m-%d")

    # Get regime for latest date
    rd = regime_cache["MES"]
    rd["_date"] = pd.to_datetime(rd["_date"])
    latest_regime_row = rd.iloc[-1] if not rd.empty else None
    regime_info = {}
    if latest_regime_row is not None:
        regime_info = {
            "vol_regime": latest_regime_row["vol_regime"],
            "trend_regime": latest_regime_row["trend_regime"],
            "rv_regime": latest_regime_row["rv_regime"],
            "trend_persistence": latest_regime_row["trend_persistence"],
            "composite": latest_regime_row["composite_regime"],
        }

    print(f"\n  Current regime: {regime_info.get('composite', '?')} | "
          f"RV={regime_info.get('rv_regime', '?')} | "
          f"Persist={regime_info.get('trend_persistence', '?')}")

    # ── Run strategies on new bars ───────────────────────────────────────
    print(f"\n  Running strategies on new bars...")

    all_new_trades = {}
    total_signals = 0

    for strat_key, strat in strat_configs.items():
        asset = strat["asset"]
        if asset not in data_cache:
            print(f"    {strat_key}: SKIP (no data for asset '{asset}')")
            all_new_trades[strat_key] = pd.DataFrame()
            continue
        full_df, new_bars = data_cache[asset]
        regime_daily = regime_cache[asset]

        new_trades, sig_count = run_strategy_on_new_bars(
            strat_key, strat, full_df, new_bars, engine, regime_daily,
        )
        all_new_trades[strat_key] = new_trades
        total_signals += sig_count

        tc = len(new_trades)
        pnl = new_trades["pnl"].sum() if not new_trades.empty else 0
        print(f"    {strat_key}: {tc} new trades, PnL=${pnl:,.0f}")

    # ── Apply Strategy Controller ────────────────────────────────────────
    print(f"\n  Applying strategy controller...")
    ctrl_result = controller.simulate(all_new_trades, regime_cache)
    controlled_trades = ctrl_result["filtered_trades"]
    filter_stats = ctrl_result["filter_stats"]

    total_base = sum(len(t) for t in all_new_trades.values())
    total_ctrl = sum(len(t) for t in controlled_trades.values())
    print(f"    Trades: {total_base} raw → {total_ctrl} after controller")

    # ── Compute PnL ──────────────────────────────────────────────────────
    daily_pnl = 0.0
    trade_log_rows = []
    signal_log_rows = []

    # Load allocation matrix for tier info
    alloc_matrix_path = ROOT / "research" / "data" / "allocation_matrix.json"
    alloc_tiers = {}
    if alloc_matrix_path.exists():
        try:
            alloc_data = json.load(open(alloc_matrix_path))
            for sid, a in alloc_data.get("strategies", {}).items():
                alloc_tiers[sid] = a.get("final_tier", "BASE")
        except Exception:
            pass

    # Load registry for probation status
    reg_path = ROOT / "research" / "data" / "strategy_registry.json"
    strategy_status = {}
    if reg_path.exists():
        try:
            reg = json.load(open(reg_path))
            for s in reg.get("strategies", []):
                strategy_status[s["strategy_id"]] = s.get("status", "unknown")
        except Exception:
            pass

    for strat_key, trades in controlled_trades.items():
        if trades.empty:
            continue
        strat_pnl = trades["pnl"].sum()
        daily_pnl += strat_pnl

        strat_cfg = strat_configs.get(strat_key, {})
        status = strategy_status.get(strat_key, "core")
        tier = alloc_tiers.get(strat_key, "BASE")
        horizon = "daily" if strat_cfg.get("name") in ("fx_daily_trend", "rate_daily_momentum") else "intraday"

        for _, row in trades.iterrows():
            trade_log_rows.append({
                "date": today_str,
                "strategy": strat_key,
                "asset": strat_cfg.get("asset", ""),
                "status": status,
                "tier": tier,
                "horizon": horizon,
                "entry_time": str(row.get("entry_time", "")),
                "exit_time": str(row.get("exit_time", "")),
                "side": row.get("side", ""),
                "pnl": float(row["pnl"]),
            })

    # Signal log
    for strat_key in strat_configs:
        fs = filter_stats.get(strat_key, {})
        signal_log_rows.append({
            "date": today_str,
            "strategy": strat_key,
            "signals_total": fs.get("total", 0),
            "signals_kept": fs.get("kept", 0),
            "regime_blocked": fs.get("regime_blocked", 0),
            "timing_blocked": fs.get("timing_blocked", 0),
            "conviction_override": fs.get("conviction_override", 0),
        })

    # ── Update account state ─────────────────────────────────────────────
    state["cumulative_pnl"] += daily_pnl
    state["equity"] = STARTING_EQUITY + state["cumulative_pnl"]
    state["equity_hwm"] = max(state["equity_hwm"], state["equity"])
    state["total_trades"] += total_ctrl
    state["total_signals"] += total_signals

    if daily_pnl < 0 and total_ctrl > 0:
        state["consecutive_losses"] += 1
    elif daily_pnl > 0:
        state["consecutive_losses"] = 0

    # Update last processed bar per asset
    for asset in data_cache:
        full_df, new_bars = data_cache[asset]
        if not new_bars.empty:
            state["last_processed_bar"][asset] = str(new_bars["datetime"].iloc[-1])

    # ── Kill switch check ────────────────────────────────────────────────
    trailing_dd = state["equity_hwm"] - state["equity"]
    kill_switch_status = "OK"
    kill_reasons = []

    if daily_pnl <= -800:
        kill_reasons.append(f"Daily loss: ${daily_pnl:,.0f}")
    if trailing_dd >= 4000:
        kill_reasons.append(f"Trailing DD: ${trailing_dd:,.0f}")
    if state["consecutive_losses"] >= 8:
        kill_reasons.append(f"Consecutive losses: {state['consecutive_losses']}")

    if kill_reasons:
        kill_switch_status = " | ".join(kill_reasons)

    # ── Determine active strategies ──────────────────────────────────────
    active_strats = []
    for strat_key in strat_configs:
        allowed, reason = controller.should_allow_entry(
            strat_key, "10:00", regime_info,
        )
        if allowed:
            active_strats.append(strat_key)

    # ── Write logs ───────────────────────────────────────────────────────
    append_log(LOGS_DIR / "trade_log.csv", trade_log_rows)
    append_log(LOGS_DIR / "signal_log.csv", signal_log_rows)

    daily_report_row = [{
        "date": today_str,
        "equity": state["equity"],
        "daily_pnl": daily_pnl,
        "cumulative_pnl": state["cumulative_pnl"],
        "trailing_dd": trailing_dd,
        "trades_raw": total_base,
        "trades_controlled": total_ctrl,
        "active_strategies": len(active_strats),
        "regime": regime_info.get("composite", ""),
        "rv_regime": regime_info.get("rv_regime", ""),
        "persistence": regime_info.get("trend_persistence", ""),
        "kill_switch": kill_switch_status,
        "run_count": state["run_count"] + 1,
    }]
    append_log(LOGS_DIR / "daily_report.csv", daily_report_row)

    if kill_reasons:
        ks_rows = [{"date": today_str, "reason": r} for r in kill_reasons]
        append_log(LOGS_DIR / "kill_switch_events.csv", ks_rows)

    # Save state
    save_account_state(state)

    # ── Console output ───────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  FORWARD PAPER TRADING REPORT")
    print(f"{'='*70}")
    print(f"""
  Date:                {today_str}
  Equity:              ${state['equity']:,.2f}
  Daily PnL:           ${daily_pnl:+,.2f}
  Cumulative PnL:      ${state['cumulative_pnl']:+,.2f}
  Trailing DD:         ${trailing_dd:,.2f}
  Equity HWM:          ${state['equity_hwm']:,.2f}

  Signals generated:   {total_signals}
  Trades (raw):        {total_base}
  Trades (controlled): {total_ctrl}

  Active strategies:""")
    for s in active_strats:
        print(f"    - {s}")
    if not active_strats:
        print(f"    (none active in current regime)")

    print(f"""
  Controller regime:   {regime_info.get('composite', '?')}
  RV regime:           {regime_info.get('rv_regime', '?')}
  Persistence:         {regime_info.get('trend_persistence', '?')}

  Kill Switch:         {kill_switch_status}

  Last processed bars:""")
    for asset in sorted(data_cache.keys()):
        bar = state["last_processed_bar"].get(asset, "none")
        print(f"    {asset}: {bar}")

    print(f"""
  Run count:           {state['run_count'] + 1}
  Logs written to:     {LOGS_DIR.relative_to(ROOT)}/
    - trade_log.csv
    - signal_log.csv
    - daily_report.csv""")
    if kill_reasons:
        print(f"    - kill_switch_events.csv")

    print(f"\n{'='*70}")
    print(f"  SMOKE TEST {'PASSED' if not kill_reasons else 'COMPLETED (kill switch fired)'}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
