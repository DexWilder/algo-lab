"""Prop Account Simulation Engine.

Models the 5-strategy portfolio running across multiple prop accounts
simultaneously, with copy trading, payout cycles, and stress testing.

Simulations:
- Account counts: 3 / 5 / 10 accounts
- Firm configs: Lucid 100K, Apex 50K, generic
- Payout cycle modeling (lock → withdraw → restart)
- Monte Carlo multi-account survival

Metrics:
- P(account failure), P(multi-account failure)
- Expected monthly payout, payout size distribution
- Time to first payout, expected yearly income per account
- Stress tests: strategy failure, correlated drawdowns, vol spikes

Usage:
    python3 research/portfolio/prop_account_simulation.py
"""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest
from engine.regime_engine import RegimeEngine
from backtests.run_baseline import ASSET_CONFIG
from controllers.prop_controller import PropController, load_prop_config

PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = Path(__file__).resolve().parent
STARTING_CAPITAL = 50_000.0

# Vol Target weights from Phase 12.4
VOL_WEIGHTS = {
    "PB": 1.214,
    "ORB": 1.093,
    "VWAP": 0.758,
    "XB-PB": 1.228,
    "DONCH": 0.707,
}

STRATEGIES = [
    {"name": "pb_trend", "asset": "MGC", "mode": "short",
     "label": "PB", "grinding_filter": False, "exit_variant": None},
    {"name": "orb_009", "asset": "MGC", "mode": "long",
     "label": "ORB", "grinding_filter": False, "exit_variant": None},
    {"name": "vwap_trend", "asset": "MNQ", "mode": "long",
     "label": "VWAP", "grinding_filter": False, "exit_variant": None},
    {"name": "xb_pb_ema_timestop", "asset": "MES", "mode": "short",
     "label": "XB-PB", "grinding_filter": False, "exit_variant": None},
    {"name": "donchian_trend", "asset": "MNQ", "mode": "long",
     "label": "DONCH", "grinding_filter": True, "exit_variant": "profit_ladder"},
]

# Prop firm configs to test
PROP_CONFIGS = [
    {
        "name": "Lucid 100K",
        "path": ROOT / "controllers" / "prop_configs" / "lucid_100k.json",
        "payout_threshold": 3100,  # lock threshold = first payout eligible
        "payout_split": 0.80,  # 80% to trader
        "min_payout": 500,
        "payout_frequency_days": 14,  # bi-weekly payouts
        "monthly_fee": 0,  # straight-to-funded, no monthly
        "reset_cost": 99,  # account reset cost if busted
    },
    {
        "name": "Apex 50K",
        "path": ROOT / "controllers" / "prop_configs" / "apex_50k.json",
        "payout_threshold": 3000,  # profit target = pass eval
        "payout_split": 0.90,  # 90% after first payout
        "min_payout": 500,
        "payout_frequency_days": 14,
        "monthly_fee": 0,
        "reset_cost": 147,
    },
    {
        "name": "Generic 50K",
        "path": ROOT / "controllers" / "prop_configs" / "generic.json",
        "payout_threshold": 2500,
        "payout_split": 0.80,
        "min_payout": 500,
        "payout_frequency_days": 14,
        "monthly_fee": 0,
        "reset_cost": 100,
    },
]


# ═══════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════

def load_strategy(name: str):
    path = ROOT / "strategies" / name / "strategy.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_strategy(strat: dict, engine: RegimeEngine) -> pd.DataFrame:
    """Run strategy and return trades DataFrame."""
    asset = strat["asset"]
    config = ASSET_CONFIG[asset]

    df = pd.read_csv(PROCESSED_DIR / f"{asset}_5m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"])

    mod = load_strategy(strat["name"])
    if hasattr(mod, "TICK_SIZE"):
        mod.TICK_SIZE = config["tick_size"]
    signals = mod.generate_signals(df)

    if strat.get("exit_variant") == "profit_ladder":
        from research.exit_evolution import donchian_entries, apply_profit_ladder
        data = donchian_entries(df)
        pl_signals_df = apply_profit_ladder(data)
        result = run_backtest(
            df, pl_signals_df, mode=strat["mode"],
            point_value=config["point_value"], symbol=asset,
        )
        trades = result["trades_df"]
    else:
        result = run_backtest(
            df, signals, mode=strat["mode"],
            point_value=config["point_value"], symbol=asset,
        )
        trades = result["trades_df"]

    if strat.get("grinding_filter") and not trades.empty:
        regime_daily = engine.get_daily_regimes(df)
        regime_daily["_date"] = pd.to_datetime(regime_daily["_date"])
        regime_daily["_date_date"] = regime_daily["_date"].dt.date
        trades["entry_date"] = pd.to_datetime(trades["entry_time"]).dt.date
        trades = trades.merge(
            regime_daily[["_date_date", "trend_persistence"]],
            left_on="entry_date", right_on="_date_date", how="left",
        )
        trades = trades[trades["trend_persistence"] == "GRINDING"]
        trades = trades.drop(
            columns=["entry_date", "_date_date", "trend_persistence"],
            errors="ignore",
        )

    return trades


def load_all_trades(engine: RegimeEngine) -> dict:
    """Load trades for all strategies. Returns {label: trades_df}."""
    all_trades = {}
    for strat in STRATEGIES:
        trades = run_strategy(strat, engine)
        # Apply vol target weights to PnL
        w = VOL_WEIGHTS.get(strat["label"], 1.0)
        if not trades.empty:
            trades = trades.copy()
            trades["pnl"] = trades["pnl"] * w
        all_trades[strat["label"]] = trades
        print(f"  {strat['label']}: {len(trades)} trades, "
              f"PnL=${trades['pnl'].sum():.0f} (weight={w:.3f}x)")
    return all_trades


def combine_portfolio_trades(all_trades: dict) -> pd.DataFrame:
    """Combine all strategy trades into single chronological DataFrame."""
    frames = []
    for label, trades in all_trades.items():
        if trades.empty:
            continue
        t = trades.copy()
        t["strategy"] = label
        frames.append(t)
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values("exit_time").reset_index(drop=True)
    return combined


def get_daily_pnl(trades_df: pd.DataFrame) -> pd.Series:
    if trades_df.empty:
        return pd.Series(dtype=float)
    tmp = trades_df.copy()
    tmp["date"] = pd.to_datetime(tmp["exit_time"]).dt.date
    daily = tmp.groupby("date")["pnl"].sum()
    daily.index = pd.to_datetime(daily.index)
    return daily


# ═══════════════════════════════════════════════════════════════════════════
# PROP ACCOUNT SIMULATION
# ═══════════════════════════════════════════════════════════════════════════

def simulate_single_account(trades_df: pd.DataFrame, prop_cfg: dict) -> dict:
    """Run portfolio trades through a single prop account."""
    config = load_prop_config(prop_cfg["path"])
    controller = PropController(config)
    result = controller.simulate(trades_df)
    return result


def simulate_payout_cycle(trades_df: pd.DataFrame, prop_cfg: dict) -> dict:
    """Simulate payout cycles: trade → lock/target → withdraw → continue.

    Models withdrawals when cumulative profit crosses thresholds,
    simulating realistic funded account income.
    """
    if trades_df.empty:
        return {"payouts": [], "total_withdrawn": 0, "busted": False}

    config_obj = load_prop_config(prop_cfg["path"])
    payout_threshold = prop_cfg["payout_threshold"]
    payout_split = prop_cfg["payout_split"]
    min_payout = prop_cfg["min_payout"]
    freq_days = prop_cfg["payout_frequency_days"]

    equity = config_obj.account_size
    trailing_dd = config_obj.trailing_drawdown or float("inf")
    eod_hwm = equity
    trailing_floor = equity - trailing_dd
    cumulative_profit = 0.0
    locked = False

    payouts = []
    last_payout_date = None
    busted = False
    bust_date = None

    trades = trades_df.copy()
    trades["_exit_date"] = pd.to_datetime(trades["exit_time"]).dt.date

    for date, day_trades in trades.groupby("_exit_date"):
        if busted:
            break

        day_pnl = day_trades["pnl"].sum()
        cumulative_profit += day_pnl
        equity += day_pnl

        # EOD trailing DD
        if equity > eod_hwm:
            eod_hwm = equity
            if not locked:
                trailing_floor = eod_hwm - trailing_dd

        # Check lock
        if not locked and config_obj.lock_profit and cumulative_profit >= config_obj.lock_profit:
            locked = True
            lock_floor = config_obj.account_size + config_obj.lock_profit - trailing_dd
            trailing_floor = max(trailing_floor, lock_floor)

        # Check bust
        if equity < trailing_floor:
            busted = True
            bust_date = str(date)
            break

        # Check payout eligibility
        if cumulative_profit >= payout_threshold:
            eligible = True
            if last_payout_date is not None:
                days_since = (pd.Timestamp(date) - pd.Timestamp(last_payout_date)).days
                if days_since < freq_days:
                    eligible = False

            if eligible:
                withdrawable = cumulative_profit - (payout_threshold * 0.5)
                payout_amount = max(0, withdrawable * payout_split)
                if payout_amount >= min_payout:
                    payouts.append({
                        "date": str(date),
                        "gross_profit": round(cumulative_profit, 2),
                        "payout_amount": round(payout_amount, 2),
                        "equity_after": round(equity - payout_amount, 2),
                    })
                    equity -= payout_amount
                    cumulative_profit -= payout_amount / payout_split
                    eod_hwm = equity
                    trailing_floor = equity - trailing_dd
                    last_payout_date = date

    total_withdrawn = sum(p["payout_amount"] for p in payouts)

    # Compute time to first payout
    if payouts:
        first_date = pd.Timestamp(payouts[0]["date"])
        start_date = pd.Timestamp(trades["_exit_date"].min())
        days_to_first = (first_date - start_date).days
    else:
        days_to_first = None

    # Data period
    date_range = trades["_exit_date"]
    total_days = (pd.Timestamp(date_range.max()) - pd.Timestamp(date_range.min())).days
    total_months = total_days / 30.44 if total_days > 0 else 1

    return {
        "payouts": payouts,
        "num_payouts": len(payouts),
        "total_withdrawn": round(total_withdrawn, 2),
        "monthly_payout_avg": round(total_withdrawn / total_months, 2),
        "yearly_income_est": round(total_withdrawn / total_months * 12, 2),
        "days_to_first_payout": days_to_first,
        "busted": busted,
        "bust_date": bust_date,
        "final_equity": round(equity, 2),
        "final_profit": round(cumulative_profit, 2),
    }


# ═══════════════════════════════════════════════════════════════════════════
# MONTE CARLO MULTI-ACCOUNT
# ═══════════════════════════════════════════════════════════════════════════

def monte_carlo_multi_account(
    daily_pnl: pd.Series,
    prop_cfg: dict,
    n_accounts_list: list = [3, 5, 10],
    n_sims: int = 5000,
) -> dict:
    """Monte Carlo simulation of multiple accounts.

    Reshuffles daily PnL, runs through prop rules, measures:
    - P(single account bust)
    - P(at least 1 bust in N accounts)
    - P(all N accounts bust)
    - Distribution of survivors
    """
    rng = np.random.default_rng(42)
    config_obj = load_prop_config(prop_cfg["path"])
    trailing_dd = config_obj.trailing_drawdown or float("inf")
    account_size = config_obj.account_size

    daily_arr = daily_pnl.values
    n_days = len(daily_arr)

    # Run sims
    bust_count = 0
    final_profits = []
    max_dds = []

    for _ in range(n_sims):
        shuffled = rng.choice(daily_arr, size=n_days, replace=False)
        equity = account_size
        eod_hwm = equity
        floor = equity - trailing_dd
        busted = False

        peak = equity
        max_dd = 0.0

        for pnl in shuffled:
            equity += pnl
            if equity > eod_hwm:
                eod_hwm = equity
                floor = eod_hwm - trailing_dd
            if equity < floor:
                busted = True
                break
            dd = peak - equity if equity < peak else 0.0
            if dd > max_dd:
                max_dd = dd
            if equity > peak:
                peak = equity

        if busted:
            bust_count += 1
        else:
            final_profits.append(equity - account_size)
            max_dds.append(max_dd)

    p_single_bust = bust_count / n_sims

    # Multi-account joint probabilities
    multi_results = {}
    for n_accts in n_accounts_list:
        # P(at least 1 bust in N accounts) = 1 - (1-p)^N
        p_at_least_one = 1.0 - (1.0 - p_single_bust) ** n_accts
        # P(all bust) = p^N
        p_all_bust = p_single_bust ** n_accts
        # Expected survivors
        expected_survivors = n_accts * (1.0 - p_single_bust)

        multi_results[f"{n_accts}_accounts"] = {
            "n_accounts": n_accts,
            "p_at_least_one_bust": round(p_at_least_one * 100, 1),
            "p_all_bust": round(p_all_bust * 100, 4),
            "expected_survivors": round(expected_survivors, 1),
            "expected_busted": round(n_accts - expected_survivors, 1),
        }

    return {
        "p_single_bust": round(p_single_bust * 100, 1),
        "n_sims": n_sims,
        "median_profit": round(float(np.median(final_profits)), 2) if final_profits else 0,
        "p5_profit": round(float(np.percentile(final_profits, 5)), 2) if final_profits else 0,
        "median_maxdd": round(float(np.median(max_dds)), 2) if max_dds else 0,
        "p95_maxdd": round(float(np.percentile(max_dds, 95)), 2) if max_dds else 0,
        "multi_account": multi_results,
    }


# ═══════════════════════════════════════════════════════════════════════════
# INCOME PROJECTIONS
# ═══════════════════════════════════════════════════════════════════════════

def project_income(payout_result: dict, prop_cfg: dict,
                   n_accounts_list: list = [3, 5, 10]) -> dict:
    """Project income across N identical accounts."""
    monthly = payout_result["monthly_payout_avg"]
    yearly = payout_result["yearly_income_est"]
    reset_cost = prop_cfg["reset_cost"]

    projections = {}
    for n in n_accounts_list:
        projections[f"{n}_accounts"] = {
            "monthly_gross": round(monthly * n, 2),
            "yearly_gross": round(yearly * n, 2),
            "monthly_fees": round(prop_cfg["monthly_fee"] * n, 2),
            "yearly_fees": round(prop_cfg["monthly_fee"] * n * 12, 2),
            "monthly_net": round(monthly * n - prop_cfg["monthly_fee"] * n, 2),
            "yearly_net": round((yearly - prop_cfg["monthly_fee"] * 12) * n, 2),
            "reset_cost_per_bust": reset_cost,
        }
    return projections


# ═══════════════════════════════════════════════════════════════════════════
# STRESS TESTS
# ═══════════════════════════════════════════════════════════════════════════

def stress_strategy_failure(
    all_trades: dict, prop_cfg: dict, daily_pnl_full: pd.Series,
) -> list:
    """Remove each strategy and re-run prop simulation."""
    results = []
    for removed in all_trades:
        remaining = {k: v for k, v in all_trades.items() if k != removed}
        combined = combine_portfolio_trades(remaining)
        if combined.empty:
            continue
        daily = get_daily_pnl(combined)
        mc = monte_carlo_multi_account(daily, prop_cfg, [5], n_sims=2000)

        results.append({
            "removed": removed,
            "p_bust": mc["p_single_bust"],
            "p_5acct_bust": mc["multi_account"]["5_accounts"]["p_at_least_one_bust"],
            "median_profit": mc["median_profit"],
        })
    return results


def stress_correlated_drawdown(
    daily_pnl: pd.Series, prop_cfg: dict,
    shock_sizes: list = [500, 1000, 1500, 2000],
) -> list:
    """Inject a single-day drawdown shock and measure survival."""
    results = []
    config_obj = load_prop_config(prop_cfg["path"])
    trailing_dd = config_obj.trailing_drawdown or float("inf")
    account_size = config_obj.account_size

    rng = np.random.default_rng(42)
    daily_arr = daily_pnl.values
    n_days = len(daily_arr)

    for shock in shock_sizes:
        bust_count = 0
        n_sims = 2000

        for _ in range(n_sims):
            shuffled = rng.choice(daily_arr, size=n_days, replace=False)
            # Inject shock at random point in first half
            shock_idx = rng.integers(0, n_days // 2)
            shocked = shuffled.copy()
            shocked[shock_idx] -= shock

            equity = account_size
            eod_hwm = equity
            floor = equity - trailing_dd
            busted = False

            for pnl in shocked:
                equity += pnl
                if equity > eod_hwm:
                    eod_hwm = equity
                    floor = eod_hwm - trailing_dd
                if equity < floor:
                    busted = True
                    break

            if busted:
                bust_count += 1

        results.append({
            "shock_size": f"${shock}",
            "p_bust": round(bust_count / n_sims * 100, 1),
        })
    return results


def stress_volatility_spike(
    daily_pnl: pd.Series, prop_cfg: dict,
    multipliers: list = [1.5, 2.0, 2.5],
) -> list:
    """Multiply PnL variance for a period and measure survival."""
    results = []
    config_obj = load_prop_config(prop_cfg["path"])
    trailing_dd = config_obj.trailing_drawdown or float("inf")
    account_size = config_obj.account_size

    rng = np.random.default_rng(42)
    daily_arr = daily_pnl.values
    n_days = len(daily_arr)

    for mult in multipliers:
        bust_count = 0
        n_sims = 2000

        for _ in range(n_sims):
            shuffled = rng.choice(daily_arr, size=n_days, replace=False)
            # Apply vol spike to 20% of days (random block)
            spike_len = max(1, n_days // 5)
            spike_start = rng.integers(0, n_days - spike_len)
            spiked = shuffled.copy()
            spiked[spike_start:spike_start + spike_len] *= mult

            equity = account_size
            eod_hwm = equity
            floor = equity - trailing_dd
            busted = False

            for pnl in spiked:
                equity += pnl
                if equity > eod_hwm:
                    eod_hwm = equity
                    floor = eod_hwm - trailing_dd
                if equity < floor:
                    busted = True
                    break

            if busted:
                bust_count += 1

        results.append({
            "vol_multiplier": f"{mult}x",
            "p_bust": round(bust_count / n_sims * 100, 1),
        })
    return results


# ═══════════════════════════════════════════════════════════════════════════
# OUTPUT
# ═══════════════════════════════════════════════════════════════════════════

def print_header(title):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def main():
    print_header("PROP ACCOUNT SIMULATION ENGINE")

    engine = RegimeEngine()

    # ─── Load all strategy trades ──────────────────────────────────────
    print("\n  Loading strategies (Vol Target weights)...")
    all_trades = load_all_trades(engine)

    combined = combine_portfolio_trades(all_trades)
    daily_pnl = get_daily_pnl(combined)
    total_trades = len(combined)
    total_pnl = combined["pnl"].sum()
    print(f"\n  Portfolio: {total_trades} trades, PnL=${total_pnl:,.0f}")

    # Store all results
    all_results = {"strategies": {s["label"]: s["name"] for s in STRATEGIES}}

    # ═══════════════════════════════════════════════════════════════════
    # PART 1: BASELINE PROP SIMULATION (per config)
    # ═══════════════════════════════════════════════════════════════════
    print_header("PART 1: BASELINE PROP ACCOUNT SIMULATION")

    for prop_cfg in PROP_CONFIGS:
        name = prop_cfg["name"]
        print(f"\n  ── {name} ──")

        # Run baseline
        result = simulate_single_account(combined, prop_cfg)
        print(f"  Passed: {'YES' if result['passed'] else 'NO — BUSTED on ' + str(result['bust_date'])}")
        print(f"  Final profit: ${result['final_profit']:,.2f}")
        print(f"  Trades executed: {result['total_trades_executed']}/{result['total_trades_input']}")
        print(f"  Skipped: {result['skipped_trades']} "
              f"(daily loss: {result['skipped_by_daily_loss']}, "
              f"contract cap: {result['skipped_by_contract_cap']})")
        if result["locked"]:
            print(f"  Locked: {result['lock_date']}")
        if result["phase_transitions"]:
            for pt in result["phase_transitions"]:
                print(f"  Phase: {pt['from']}→{pt['to']} on {pt['date']} at ${pt['profit_at_transition']}")
        if result["halted_days"]:
            print(f"  Halted days: {len(result['halted_days'])}")

        all_results[name] = {
            "baseline": {
                "passed": result["passed"],
                "busted": result["busted"],
                "final_profit": result["final_profit"],
                "trades_executed": result["total_trades_executed"],
                "skipped": result["skipped_trades"],
                "locked": result["locked"],
            }
        }

    # ═══════════════════════════════════════════════════════════════════
    # PART 2: PAYOUT CYCLE SIMULATION
    # ═══════════════════════════════════════════════════════════════════
    print_header("PART 2: PAYOUT CYCLE SIMULATION")

    print(f"\n  {'Config':<20s} {'Payouts':>8s} {'Total':>10s} {'Monthly':>10s} "
          f"{'Yearly':>10s} {'1st Pay':>8s} {'Busted':>7s}")
    print(f"  {'-'*18:<20s} {'-'*8:>8s} {'-'*10:>10s} {'-'*10:>10s} "
          f"{'-'*10:>10s} {'-'*8:>8s} {'-'*7:>7s}")

    for prop_cfg in PROP_CONFIGS:
        name = prop_cfg["name"]
        payout = simulate_payout_cycle(combined, prop_cfg)

        days_str = f"{payout['days_to_first_payout']}d" if payout["days_to_first_payout"] else "—"
        bust_str = "YES" if payout["busted"] else "NO"

        print(f"  {name:<20s} {payout['num_payouts']:>8d} "
              f"${payout['total_withdrawn']:>9,.0f} "
              f"${payout['monthly_payout_avg']:>9,.0f} "
              f"${payout['yearly_income_est']:>9,.0f} "
              f"{days_str:>8s} {bust_str:>7s}")

        all_results[name]["payout_cycle"] = {
            "num_payouts": payout["num_payouts"],
            "total_withdrawn": payout["total_withdrawn"],
            "monthly_avg": payout["monthly_payout_avg"],
            "yearly_est": payout["yearly_income_est"],
            "days_to_first": payout["days_to_first_payout"],
            "busted": payout["busted"],
            "payouts": payout["payouts"],
        }

    # ═══════════════════════════════════════════════════════════════════
    # PART 3: MONTE CARLO MULTI-ACCOUNT SURVIVAL
    # ═══════════════════════════════════════════════════════════════════
    print_header("PART 3: MONTE CARLO MULTI-ACCOUNT SURVIVAL (5K sims)")

    for prop_cfg in PROP_CONFIGS:
        name = prop_cfg["name"]
        print(f"\n  ── {name} ──")

        mc = monte_carlo_multi_account(daily_pnl, prop_cfg)

        print(f"  P(single account bust): {mc['p_single_bust']}%")
        print(f"  Median profit: ${mc['median_profit']:,.0f}")
        print(f"  Median MaxDD: ${mc['median_maxdd']:,.0f}")
        print(f"  95th pct MaxDD: ${mc['p95_maxdd']:,.0f}")

        print(f"\n  {'Accounts':>10s} {'P(≥1 bust)':>12s} {'P(all bust)':>12s} "
              f"{'Exp survivors':>14s}")
        print(f"  {'-'*10:>10s} {'-'*12:>12s} {'-'*12:>12s} {'-'*14:>14s}")

        for key, data in mc["multi_account"].items():
            n = data["n_accounts"]
            print(f"  {n:>10d} {data['p_at_least_one_bust']:>11.1f}% "
                  f"{data['p_all_bust']:>11.4f}% "
                  f"{data['expected_survivors']:>10.1f}/{n}")

        all_results[name]["monte_carlo"] = mc

    # ═══════════════════════════════════════════════════════════════════
    # PART 4: INCOME PROJECTIONS (Multi-Account Scaling)
    # ═══════════════════════════════════════════════════════════════════
    print_header("PART 4: INCOME PROJECTIONS (Multi-Account Scaling)")

    for prop_cfg in PROP_CONFIGS:
        name = prop_cfg["name"]
        payout = all_results[name]["payout_cycle"]
        mc = all_results[name]["monte_carlo"]

        payout_data = {
            "monthly_payout_avg": payout["monthly_avg"],
            "yearly_income_est": payout["yearly_est"],
        }
        projections = project_income(payout_data, prop_cfg)

        print(f"\n  ── {name} (per-account monthly: ${payout['monthly_avg']:,.0f}) ──")
        print(f"  {'Accounts':>10s} {'Monthly Net':>12s} {'Yearly Net':>12s} "
              f"{'Bust Risk':>10s}")
        print(f"  {'-'*10:>10s} {'-'*12:>12s} {'-'*12:>12s} {'-'*10:>10s}")

        for key, data in projections.items():
            n = int(key.split("_")[0])
            bust_risk = mc["multi_account"].get(f"{n}_accounts", {})
            p_bust = bust_risk.get("p_at_least_one_bust", 0)
            print(f"  {n:>10d} ${data['monthly_net']:>11,.0f} "
                  f"${data['yearly_net']:>11,.0f} {p_bust:>9.1f}%")

        all_results[name]["income_projections"] = projections

    # ═══════════════════════════════════════════════════════════════════
    # PART 5: STRESS TESTS
    # ═══════════════════════════════════════════════════════════════════
    print_header("PART 5: STRESS TESTS (Lucid 100K)")

    primary_cfg = PROP_CONFIGS[0]  # Lucid 100K
    primary_name = primary_cfg["name"]

    # 5a. Strategy failure
    print("\n  ── Strategy Failure (remove each, 5-account bust risk) ──")
    strat_fail = stress_strategy_failure(all_trades, primary_cfg, daily_pnl)

    print(f"  {'Removed':>12s} {'P(bust)':>10s} {'P(5-acct ≥1)':>14s} {'Profit':>10s}")
    print(f"  {'-'*12:>12s} {'-'*10:>10s} {'-'*14:>14s} {'-'*10:>10s}")
    for r in strat_fail:
        print(f"  {r['removed']:>12s} {r['p_bust']:>9.1f}% "
              f"{r['p_5acct_bust']:>13.1f}% ${r['median_profit']:>9,.0f}")

    all_results[primary_name]["stress_strategy_failure"] = strat_fail

    # 5b. Correlated drawdown shocks
    print("\n  ── Correlated Drawdown Shocks ──")
    dd_stress = stress_correlated_drawdown(daily_pnl, primary_cfg)

    print(f"  {'Shock':>10s} {'P(bust)':>10s}")
    print(f"  {'-'*10:>10s} {'-'*10:>10s}")
    for r in dd_stress:
        print(f"  {r['shock_size']:>10s} {r['p_bust']:>9.1f}%")

    all_results[primary_name]["stress_correlated_dd"] = dd_stress

    # 5c. Volatility spikes
    print("\n  ── Volatility Spikes (20% of days at Nx vol) ──")
    vol_stress = stress_volatility_spike(daily_pnl, primary_cfg)

    print(f"  {'Multiplier':>12s} {'P(bust)':>10s}")
    print(f"  {'-'*12:>12s} {'-'*10:>10s}")
    for r in vol_stress:
        print(f"  {r['vol_multiplier']:>12s} {r['p_bust']:>9.1f}%")

    all_results[primary_name]["stress_vol_spike"] = vol_stress

    # ═══════════════════════════════════════════════════════════════════
    # PART 6: DEPLOYMENT RECOMMENDATIONS
    # ═══════════════════════════════════════════════════════════════════
    print_header("PART 6: DEPLOYMENT RECOMMENDATIONS")

    # Find best config
    best_cfg = None
    best_yearly = 0
    for prop_cfg in PROP_CONFIGS:
        name = prop_cfg["name"]
        yearly = all_results[name]["payout_cycle"]["yearly_est"]
        mc_bust = all_results[name]["monte_carlo"]["p_single_bust"]
        if yearly > best_yearly and mc_bust < 10:
            best_yearly = yearly
            best_cfg = name

    if best_cfg:
        cfg_data = all_results[best_cfg]
        mc = cfg_data["monte_carlo"]

        print(f"\n  Recommended config: {best_cfg}")
        print(f"  Per-account yearly income: ${cfg_data['payout_cycle']['yearly_est']:,.0f}")
        print(f"  P(single bust): {mc['p_single_bust']}%")
        print(f"  Days to first payout: {cfg_data['payout_cycle']['days_to_first']}")

        print(f"\n  SCALING TABLE:")
        print(f"  {'Accounts':>10s} {'Yearly Income':>14s} {'Risk':>10s}")
        print(f"  {'-'*10:>10s} {'-'*14:>14s} {'-'*10:>10s}")
        for n in [1, 3, 5, 10]:
            yearly = cfg_data["payout_cycle"]["yearly_est"] * n
            if n == 1:
                risk = mc["p_single_bust"]
            else:
                risk = mc["multi_account"].get(f"{n}_accounts", {}).get(
                    "p_at_least_one_bust", 0)
            print(f"  {n:>10d} ${yearly:>13,.0f} {risk:>9.1f}%")

    # ─── Verdict ───────────────────────────────────────────────────────
    lucid_mc = all_results["Lucid 100K"]["monte_carlo"]
    lucid_bust = lucid_mc["p_single_bust"]
    lucid_payout = all_results["Lucid 100K"]["payout_cycle"]

    verdict_lines = []
    if lucid_bust < 5:
        verdict_lines.append("PASS: MC bust risk < 5%")
    elif lucid_bust < 15:
        verdict_lines.append("CAUTION: MC bust risk 5-15%")
    else:
        verdict_lines.append("FAIL: MC bust risk > 15%")

    if lucid_payout["num_payouts"] > 0:
        verdict_lines.append(f"PASS: {lucid_payout['num_payouts']} payouts achieved")
    else:
        verdict_lines.append("FAIL: No payouts achieved")

    if lucid_payout["days_to_first"] and lucid_payout["days_to_first"] < 90:
        verdict_lines.append(f"PASS: First payout in {lucid_payout['days_to_first']} days")
    elif lucid_payout["days_to_first"]:
        verdict_lines.append(f"CAUTION: First payout took {lucid_payout['days_to_first']} days")
    else:
        verdict_lines.append("FAIL: No payout achieved")

    print(f"\n  VERDICT:")
    for v in verdict_lines:
        print(f"    {v}")

    all_pass = all(v.startswith("PASS") for v in verdict_lines)
    if all_pass:
        print(f"\n  ✓ PORTFOLIO READY FOR FUNDED ACCOUNT DEPLOYMENT")
    else:
        print(f"\n  ⚠ REVIEW NEEDED BEFORE DEPLOYMENT")

    all_results["verdict"] = verdict_lines

    # ─── Save JSON ─────────────────────────────────────────────────────
    output_path = OUTPUT_DIR / "prop_account_simulation_results.json"

    # Clean non-serializable data
    def clean_for_json(obj):
        if isinstance(obj, dict):
            return {k: clean_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_for_json(i) for i in obj]
        elif isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.DataFrame):
            return None  # skip DataFrames
        return obj

    with open(output_path, "w") as f:
        json.dump(clean_for_json(all_results), f, indent=2)

    print(f"\n  Saved to: {output_path}")


if __name__ == "__main__":
    main()
