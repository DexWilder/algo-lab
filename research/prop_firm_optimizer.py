"""Prop Firm Optimizer — Monte Carlo ranking of prop firms for this portfolio.

READ-ONLY research tool. Uses the daily PnL distribution from Phase 17
equity curve to simulate account trajectories across multiple prop firms.

Loads verified firm data from research/data/prop_firm_dataset.json.

Usage:
    python3 research/prop_firm_optimizer.py
    python3 research/prop_firm_optimizer.py --trials 10000 --days 252
    python3 research/prop_firm_optimizer.py --save
    python3 research/prop_firm_optimizer.py --preview   # show dataset table only
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

DATASET_PATH = ROOT / "research" / "data" / "prop_firm_dataset.json"
EQUITY_CURVE_PATH = ROOT / "research" / "phase17_paper_trading" / "equity_curve.csv"

BASELINE_CONTRACTS = 2  # baseline contract count in equity curve data


# ---------------------------------------------------------------------------
# Firm configs — built from dataset, with simulation-ready parameters
# ---------------------------------------------------------------------------

def load_dataset() -> list[dict]:
    """Load verified prop firm dataset."""
    if not DATASET_PATH.exists():
        print(f"ERROR: Dataset not found at {DATASET_PATH}")
        sys.exit(1)
    with open(DATASET_PATH) as f:
        data = json.load(f)
    return data["offerings"]


def build_sim_configs(offerings: list[dict]) -> dict:
    """Convert dataset offerings into simulation-ready configs.

    Groups eval + funded offerings from the same firm/size into unified
    configs. Only includes offerings with enough info to simulate.
    """
    configs = {}

    # ── Lucid: phase-based (eval target → lock → payout) ──────────────
    configs["Lucid Pro 50K"] = {
        "account_size": 50_000,
        "trailing_drawdown": 2_000,
        "trailing_type": "eod",
        "daily_loss_limit": 1_200,
        "profit_target": 3_000,
        "lock_profit": None,
        "consistency_rule": None,
        "funded_consistency_rule": None,
        "phases": None,
        "startup_fee": 0,
        "activation_fee": 0,
        "payout_split": 0.90,
        "min_payout": 500,
        "payout_frequency_days": 1,
        "max_contracts": 4,
        "winning_day_requirement": None,
        "payout_cap": None,
        "dd_locks_at_zero_after_payout": False,
        "min_days_to_pass": 0,
    }

    configs["Lucid Pro 100K"] = {
        "account_size": 100_000,
        "trailing_drawdown": 3_000,
        "trailing_type": "eod",
        "daily_loss_limit": 1_800,
        "profit_target": 6_000,
        "lock_profit": None,
        "consistency_rule": None,
        "funded_consistency_rule": None,
        "phases": None,
        "startup_fee": 0,
        "activation_fee": 0,
        "payout_split": 0.90,
        "min_payout": 500,
        "payout_frequency_days": 1,
        "max_contracts": 6,
        "winning_day_requirement": None,
        "payout_cap": None,
        "dd_locks_at_zero_after_payout": False,
        "min_days_to_pass": 0,
    }

    configs["Lucid Flex 100K"] = {
        "account_size": 100_000,
        "trailing_drawdown": 3_000,
        "trailing_type": "eod",
        "daily_loss_limit": 1_800,
        "profit_target": 6_000,
        "lock_profit": None,
        "consistency_rule": None,
        "funded_consistency_rule": None,
        "phases": None,
        "startup_fee": 0,
        "activation_fee": 0,
        "payout_split": 0.90,
        "min_payout": 500,
        "payout_frequency_days": 1,
        "max_contracts": 6,
        "winning_day_requirement": None,
        "payout_cap": None,
        "dd_locks_at_zero_after_payout": False,
        "min_days_to_pass": 0,
    }

    configs["Lucid Direct 50K"] = {
        "account_size": 50_000,
        "trailing_drawdown": 2_000,
        "trailing_type": "eod",
        "daily_loss_limit": 1_200,
        "profit_target": 3_000,
        "lock_profit": None,
        "consistency_rule": 0.20,
        "funded_consistency_rule": None,
        "phases": None,
        "startup_fee": 0,
        "activation_fee": 0,
        "payout_split": 0.90,
        "min_payout": 500,
        "payout_frequency_days": 1,
        "max_contracts": 4,
        "winning_day_requirement": None,
        "payout_cap": None,
        "dd_locks_at_zero_after_payout": False,
        "min_days_to_pass": 10,
    }

    # ── Tradeify Select Flex: 3-day eval → funded ──────────────────────
    configs["Tradeify Flex 50K"] = {
        "account_size": 50_000,
        "trailing_drawdown": 2_000,
        "trailing_type": "eod",
        "daily_loss_limit": None,
        "profit_target": None,  # no profit target for funded stage
        "lock_profit": None,
        "consistency_rule": None,
        "funded_consistency_rule": None,
        "phases": None,
        "startup_fee": 0,
        "activation_fee": 0,
        "payout_split": 0.90,
        "min_payout": 500,
        "payout_frequency_days": 5,  # every 5 winning days
        "max_contracts": 4,
        "winning_day_requirement": 5,
        "payout_cap": 3_000,
        "dd_locks_at_zero_after_payout": True,
        "min_days_to_pass": 3,
    }

    configs["Tradeify Flex 100K"] = {
        "account_size": 100_000,
        "trailing_drawdown": 3_000,
        "trailing_type": "eod",
        "daily_loss_limit": None,
        "profit_target": None,
        "lock_profit": None,
        "consistency_rule": None,
        "funded_consistency_rule": None,
        "phases": None,
        "startup_fee": 0,
        "activation_fee": 0,
        "payout_split": 0.90,
        "min_payout": 500,
        "payout_frequency_days": 5,
        "max_contracts": 8,
        "winning_day_requirement": 5,
        "payout_cap": 4_000,
        "dd_locks_at_zero_after_payout": True,
        "min_days_to_pass": 3,
    }

    configs["Tradeify Flex 150K"] = {
        "account_size": 150_000,
        "trailing_drawdown": 4_500,
        "trailing_type": "eod",
        "daily_loss_limit": None,
        "profit_target": None,
        "lock_profit": None,
        "consistency_rule": None,
        "funded_consistency_rule": None,
        "phases": None,
        "startup_fee": 0,
        "activation_fee": 0,
        "payout_split": 0.90,
        "min_payout": 500,
        "payout_frequency_days": 5,
        "max_contracts": 12,
        "winning_day_requirement": 5,
        "payout_cap": 5_000,
        "dd_locks_at_zero_after_payout": True,
        "min_days_to_pass": 3,
    }

    configs["Tradeify Daily 50K"] = {
        "account_size": 50_000,
        "trailing_drawdown": 2_000,
        "trailing_type": "eod",
        "daily_loss_limit": 1_000,
        "profit_target": None,
        "lock_profit": None,
        "consistency_rule": None,
        "funded_consistency_rule": None,
        "phases": None,
        "startup_fee": 0,
        "activation_fee": 0,
        "payout_split": 0.90,
        "min_payout": 250,
        "payout_frequency_days": 1,
        "max_contracts": 4,
        "winning_day_requirement": None,
        "payout_cap": None,
        "dd_locks_at_zero_after_payout": False,
        "min_days_to_pass": 3,
    }

    # ── MFFU Rapid ─────────────────────────────────────────────────────
    configs["MFFU Rapid 50K"] = {
        "account_size": 50_000,
        "trailing_drawdown": 2_000,
        "trailing_type": "eod",  # eval is EOD
        "daily_loss_limit": None,
        "profit_target": 3_000,
        "lock_profit": None,
        "consistency_rule": 0.50,  # eval only
        "funded_consistency_rule": None,
        "phases": None,
        "startup_fee": 0,
        "activation_fee": 0,
        "payout_split": 0.80,
        "min_payout": 250,
        "payout_frequency_days": 5,
        "max_contracts": 5,
        "winning_day_requirement": 5,
        "payout_cap": 5_000,
        "dd_locks_at_zero_after_payout": False,
        "min_days_to_pass": 2,
        # NOTE: sim-funded uses INTRADAY trailing — modeled as harder
        "funded_trailing_type": "intraday",
    }

    # ── Apex ───────────────────────────────────────────────────────────
    configs["Apex 50K EOD"] = {
        "account_size": 50_000,
        "trailing_drawdown": 2_500,
        "trailing_type": "eod",
        "daily_loss_limit": None,
        "profit_target": 3_000,
        "lock_profit": None,
        "consistency_rule": None,
        "funded_consistency_rule": 0.30,
        "phases": None,
        "startup_fee": 147,
        "activation_fee": 0,
        "payout_split": 1.00,
        "min_payout": 500,
        "payout_frequency_days": 14,
        "max_contracts": 5,
        "winning_day_requirement": None,
        "payout_cap": None,
        "dd_locks_at_zero_after_payout": False,
        "min_days_to_pass": 7,
    }

    configs["Apex 100K EOD"] = {
        "account_size": 100_000,
        "trailing_drawdown": 3_000,
        "trailing_type": "eod",
        "daily_loss_limit": None,
        "profit_target": 6_000,
        "lock_profit": None,
        "consistency_rule": None,
        "funded_consistency_rule": 0.30,
        "phases": None,
        "startup_fee": 207,
        "activation_fee": 0,
        "payout_split": 1.00,
        "min_payout": 500,
        "payout_frequency_days": 14,
        "max_contracts": 10,
        "winning_day_requirement": None,
        "payout_cap": None,
        "dd_locks_at_zero_after_payout": False,
        "min_days_to_pass": 7,
    }

    configs["Apex 50K Intraday"] = {
        "account_size": 50_000,
        "trailing_drawdown": 2_500,
        "trailing_type": "intraday",
        "daily_loss_limit": None,
        "profit_target": 3_000,
        "lock_profit": None,
        "consistency_rule": None,
        "funded_consistency_rule": 0.30,
        "phases": None,
        "startup_fee": 147,
        "activation_fee": 0,
        "payout_split": 1.00,
        "min_payout": 500,
        "payout_frequency_days": 14,
        "max_contracts": 5,
        "winning_day_requirement": None,
        "payout_cap": None,
        "dd_locks_at_zero_after_payout": False,
        "min_days_to_pass": 7,
    }

    # ── Topstep Express ────────────────────────────────────────────────
    configs["Topstep Express 50K"] = {
        "account_size": 50_000,
        "trailing_drawdown": 2_000,
        "trailing_type": "eod",
        "daily_loss_limit": None,
        "profit_target": None,
        "lock_profit": None,
        "consistency_rule": None,
        "funded_consistency_rule": None,
        "phases": None,
        "startup_fee": 0,
        "activation_fee": 0,
        "payout_split": 0.90,
        "min_payout": 500,
        "payout_frequency_days": 5,
        "max_contracts": 5,
        "winning_day_requirement": 5,
        "payout_cap": 5_000,
        "dd_locks_at_zero_after_payout": True,
        "min_days_to_pass": 0,
    }

    configs["Topstep Express 100K"] = {
        "account_size": 100_000,
        "trailing_drawdown": 3_000,
        "trailing_type": "eod",
        "daily_loss_limit": None,
        "profit_target": None,
        "lock_profit": None,
        "consistency_rule": None,
        "funded_consistency_rule": None,
        "phases": None,
        "startup_fee": 0,
        "activation_fee": 0,
        "payout_split": 0.90,
        "min_payout": 500,
        "payout_frequency_days": 5,
        "max_contracts": 10,
        "winning_day_requirement": 5,
        "payout_cap": 5_000,
        "dd_locks_at_zero_after_payout": True,
        "min_days_to_pass": 0,
    }

    # ── The Trading Pit ────────────────────────────────────────────────
    configs["Trading Pit Futures"] = {
        "account_size": 50_000,
        "trailing_drawdown": 2_000,
        "trailing_type": "eod",
        "daily_loss_limit": None,
        "profit_target": None,
        "lock_profit": None,
        "consistency_rule": 0.40,
        "funded_consistency_rule": 0.40,
        "phases": None,
        "startup_fee": 0,
        "activation_fee": 0,
        "payout_split": 0.80,
        "min_payout": 500,
        "payout_frequency_days": 14,
        "max_contracts": 5,
        "winning_day_requirement": None,
        "payout_cap": None,
        "dd_locks_at_zero_after_payout": False,
        "min_days_to_pass": 3,
        "overnight_restricted": True,
    }

    return configs


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_daily_pnl() -> np.ndarray:
    """Load non-zero daily PnL values from Phase 17 equity curve."""
    if not EQUITY_CURVE_PATH.exists():
        print(f"ERROR: Equity curve not found at {EQUITY_CURVE_PATH}")
        sys.exit(1)
    df = pd.read_csv(EQUITY_CURVE_PATH)
    pnl = df["daily_pnl"].values
    pnl = pnl[pnl != 0.0]
    return pnl


# ---------------------------------------------------------------------------
# Simulation engine
# ---------------------------------------------------------------------------

def simulate_firm(firm_name: str, config: dict, pnl_pool: np.ndarray,
                  n_trials: int, n_days: int, rng: np.random.Generator) -> dict:
    """Run Monte Carlo simulation for a single prop firm."""

    trailing_dd = config["trailing_drawdown"]
    daily_limit = config["daily_loss_limit"]
    consistency_eval = config.get("consistency_rule")
    consistency_funded = config.get("funded_consistency_rule")
    payout_split = config["payout_split"]
    min_payout = config["min_payout"]
    payout_freq = config["payout_frequency_days"]
    profit_target = config["profit_target"]
    startup_fee = config["startup_fee"]
    payout_cap = config.get("payout_cap")
    dd_locks = config.get("dd_locks_at_zero_after_payout", False)
    winning_day_req = config.get("winning_day_requirement")
    min_days = config.get("min_days_to_pass", 0)
    is_intraday = config["trailing_type"] == "intraday"
    funded_intraday = config.get("funded_trailing_type") == "intraday"

    # Contract scaling: scale PnL by max_contracts / baseline
    contract_scale = min(config["max_contracts"], 5) / BASELINE_CONTRACTS

    # Intraday trailing penalty: model as ~20% worse drawdown behavior
    intraday_dd_penalty = 0.80 if is_intraday else 1.0

    # Pre-sample
    samples = rng.choice(pnl_pool, size=(n_trials, n_days), replace=True)

    bust_count = 0
    pass_count = 0
    days_to_pass_list = []
    total_payouts_list = []
    consistency_blocks = 0
    consistency_attempts = 0

    for t in range(n_trials):
        equity = 0.0
        hwm = 0.0
        busted = False
        funded = profit_target is None  # no eval = already funded
        day_funded = 0
        has_paid_out = False

        total_payouts = 0.0
        winning_days = 0
        last_payout_day = -payout_freq
        profit_since_last_payout = 0.0
        daily_pnl_log = []

        # Effective DD limit (reduced for intraday)
        eff_dd = trailing_dd * intraday_dd_penalty
        dd_floor = None  # for dd_locks_at_zero

        for d in range(n_days):
            raw_pnl = float(samples[t, d])

            # Scale by contracts
            scaled_pnl = raw_pnl * contract_scale

            # Apply daily loss limit
            if daily_limit is not None and scaled_pnl < -daily_limit:
                scaled_pnl = -daily_limit

            equity += scaled_pnl

            # Track winning days
            if scaled_pnl > 0:
                winning_days += 1

            # Update HWM
            if equity > hwm:
                hwm = equity

            # Check trailing drawdown bust
            floor = dd_floor if dd_floor is not None else (hwm - eff_dd)
            if equity < floor:
                busted = True
                break

            # Switch to intraday trailing after funded (MFFU Rapid)
            if funded and funded_intraday and not is_intraday:
                # After passing eval, use intraday DD
                eff_dd = trailing_dd * 0.80

            # Eval pass check
            if not funded and profit_target is not None:
                # Check consistency during eval
                if consistency_eval is not None and d > 0:
                    total_profit = equity
                    if total_profit > 0:
                        max_day = max(float(samples[t, i]) * contract_scale
                                      for i in range(d + 1))
                        if max_day / total_profit > consistency_eval:
                            continue  # can't pass yet

                if equity >= profit_target and d + 1 >= min_days:
                    funded = True
                    day_funded = d + 1

            # Payout logic (only when funded)
            if funded:
                profit_since_last_payout += scaled_pnl
                daily_pnl_log.append(scaled_pnl)

                # Check payout eligibility
                can_pay = False
                if winning_day_req is not None:
                    if winning_days >= winning_day_req and (d - last_payout_day) >= payout_freq:
                        can_pay = True
                elif (d - last_payout_day) >= payout_freq:
                    can_pay = True

                if can_pay and profit_since_last_payout > 0:
                    payout_amount = profit_since_last_payout * payout_split

                    # Apply payout cap
                    if payout_cap is not None:
                        payout_amount = min(payout_amount, payout_cap)

                    # Funded consistency rule check
                    if consistency_funded is not None:
                        consistency_attempts += 1
                        total_profit_at_payout = sum(daily_pnl_log)
                        if total_profit_at_payout > 0:
                            max_day_pnl = max(daily_pnl_log)
                            if max_day_pnl / total_profit_at_payout > consistency_funded:
                                consistency_blocks += 1
                                continue

                    if payout_amount >= min_payout:
                        total_payouts += payout_amount
                        last_payout_day = d
                        profit_since_last_payout = 0.0
                        winning_days = 0  # reset for next cycle

                        # DD locks at zero after first payout
                        if dd_locks and not has_paid_out:
                            dd_floor = 0.0  # can't go negative
                            has_paid_out = True

        if busted:
            bust_count += 1
        else:
            total_payouts_list.append(total_payouts)

        if funded and not busted:
            pass_count += 1
            if day_funded > 0:
                days_to_pass_list.append(day_funded)

    # Compute metrics
    pass_prob = pass_count / n_trials
    bust_prob = bust_count / n_trials
    median_days = float(np.median(days_to_pass_list)) if days_to_pass_list else np.nan

    total_fees = startup_fee
    months = n_days / 21

    if total_payouts_list:
        mean_total_payout = float(np.mean(total_payouts_list))
    else:
        mean_total_payout = 0.0

    expected_gross = pass_prob * mean_total_payout
    expected_net = expected_gross - total_fees
    expected_monthly_net = expected_net / months if months > 0 else 0

    consistency_block_rate = (consistency_blocks / consistency_attempts
                              if consistency_attempts > 0 else 0.0)

    roi_on_fees = expected_net / startup_fee if startup_fee > 0 else np.inf

    return {
        "firm": firm_name,
        "pass_probability": pass_prob,
        "bust_probability": bust_prob,
        "median_days_to_pass": median_days,
        "expected_monthly_net": expected_monthly_net,
        "six_month_net_profit": expected_net,
        "consistency_blockage_rate": consistency_block_rate,
        "roi_on_fees": roi_on_fees,
        "startup_fee": startup_fee,
        "mean_total_payout": mean_total_payout,
        "trailing_type": config["trailing_type"],
        "account_size": config["account_size"],
    }


def compute_score(r: dict, all_results: list) -> float:
    """Compute weighted overall score (0-10 scale)."""
    monthly_nets = [x["expected_monthly_net"] for x in all_results]
    max_monthly = max(monthly_nets) if max(monthly_nets) > 0 else 1.0
    monthly_norm = r["expected_monthly_net"] / max_monthly if max_monthly > 0 else 0

    days_list = [x["median_days_to_pass"] for x in all_results
                 if not np.isnan(x["median_days_to_pass"])]
    if days_list:
        min_days = min(days_list)
        max_days = max(days_list)
        if max_days > min_days and not np.isnan(r["median_days_to_pass"]):
            speed_norm = 1.0 - (r["median_days_to_pass"] - min_days) / (max_days - min_days)
        else:
            speed_norm = 1.0
    else:
        speed_norm = 1.0
    if np.isnan(r["median_days_to_pass"]):
        speed_norm = 1.0

    score = (
        r["pass_probability"] * 0.25
        + monthly_norm * 0.30
        + (1 - r["bust_probability"]) * 0.20
        + speed_norm * 0.15
        + (1 - r["consistency_blockage_rate"]) * 0.10
    ) * 10.0

    return round(score, 1)


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def fmt_pct(v: float) -> str:
    return f"{v * 100:.1f}%"

def fmt_dollars(v: float) -> str:
    if v < 0:
        return f"-${abs(v):,.0f}"
    return f"${v:,.0f}"

def fmt_days(v: float) -> str:
    if np.isnan(v):
        return "N/A"
    return f"{v:.0f}"


def print_preview(offerings: list[dict]):
    """Print dataset preview table."""
    w = 70
    print()
    print("=" * w)
    print("  PROP FIRM DATASET PREVIEW")
    print(f"  {len(offerings)} verified offerings")
    print("=" * w)

    print(f"\n  {'Firm':<18s} {'Offering':<28s} {'Size':>8s} {'DD':>7s} {'DD Type':<10s} {'Consist':>8s}")
    print(f"  {'-'*18} {'-'*28} {'-'*8} {'-'*7} {'-'*10} {'-'*8}")

    for o in offerings:
        size = f"${o['account_size']:,}" if o['account_size'] else "?"
        dd = f"${o['max_drawdown_amount']:,}" if o['max_drawdown_amount'] else "?"
        dd_type = (o.get("drawdown_type") or "?")[:10]
        consist = ""
        if o.get("eval_consistency_rule"):
            consist = f"{o['eval_consistency_rule']*100:.0f}%E"
        if o.get("funded_consistency_rule"):
            consist += f" {o['funded_consistency_rule']*100:.0f}%F"
        if not consist:
            consist = "None"

        print(f"  {o['firm']:<18s} {o['offering']:<28s} {size:>8s} {dd:>7s} {dd_type:<10s} {consist:>8s}")

    print()
    print("=" * w)


def print_report(results: list, pnl_pool: np.ndarray, n_trials: int, n_days: int):
    """Print the formatted ranking report."""
    w = 78

    print()
    print("=" * w)
    print("  PROP FIRM OPTIMIZER")
    print(f"  Monte Carlo: {n_trials:,} trials x {n_days} trading days")
    print(f"  {len(results)} offerings simulated")
    print("=" * w)

    print()
    print("  INPUT DISTRIBUTION")
    print("  " + "-" * 36)
    print(f"  Daily PnL samples:     {len(pnl_pool)}")
    print(f"  Mean daily PnL:        ${np.mean(pnl_pool):.2f}")
    print(f"  Std daily PnL:         ${np.std(pnl_pool):.2f}")
    print(f"  Median daily PnL:      ${np.median(pnl_pool):.2f}")
    print(f"  Win rate:              {(pnl_pool > 0).mean() * 100:.1f}%")

    print()
    print("  FIRM RANKINGS (best to worst)")
    print("  " + "=" * (w - 4))

    for i, r in enumerate(results):
        rank = i + 1
        name = r["firm"]
        score = r["score"]

        print()
        print(f"  #{rank}  {name:<50s} Score: {score}/10")
        print("  " + "-" * (w - 4))
        print(f"  Pass probability:      {fmt_pct(r['pass_probability'])}")
        print(f"  Bust probability:      {fmt_pct(r['bust_probability'])}")
        print(f"  Days to funded:        {fmt_days(r['median_days_to_pass'])}")
        print(f"  Monthly net:           {fmt_dollars(r['expected_monthly_net'])}")
        print(f"  6-month net:           {fmt_dollars(r['six_month_net_profit'])}")
        print(f"  Consistency block:     {fmt_pct(r['consistency_blockage_rate'])}")
        print(f"  DD type:               {r['trailing_type']}")
        if r["startup_fee"] > 0:
            roi = r["roi_on_fees"]
            print(f"  ROI on fees:           {roi:.1f}x" if np.isfinite(roi) else
                  f"  ROI on fees:           N/A")
        else:
            print(f"  ROI on fees:           N/A (no startup fee)")

    # Comparison table
    print()
    print("  COMPARISON TABLE")
    print("  " + "=" * (w - 4))
    header = (f"  {'Firm':<24s} {'Pass%':>6s} {'Bust%':>6s} {'Days':>5s} "
              f"{'Monthly':>8s} {'6mo Net':>8s} {'Consist':>7s} {'Score':>5s}")
    print(header)
    print("  " + "-" * (w - 4))
    for r in results:
        days_str = fmt_days(r["median_days_to_pass"])
        name = r["firm"][:24]
        print(f"  {name:<24s} {fmt_pct(r['pass_probability']):>6s} "
              f"{fmt_pct(r['bust_probability']):>6s} {days_str:>5s} "
              f"{fmt_dollars(r['expected_monthly_net']):>8s} "
              f"{fmt_dollars(r['six_month_net_profit']):>8s} "
              f"{fmt_pct(r['consistency_blockage_rate']):>7s} "
              f"{r['score']:>5.1f}")

    # Recommendations
    print()
    print("  RECOMMENDATIONS")
    print("  " + "-" * 36)

    best_overall = results[0]["firm"]
    print(f"  Best overall:          {best_overall}")

    # Fastest
    passable = [r for r in results if not np.isnan(r["median_days_to_pass"])]
    if passable:
        fastest = min(passable, key=lambda x: x["median_days_to_pass"])
        print(f"  Fastest to payout:     {fastest['firm']} ({fmt_days(fastest['median_days_to_pass'])} days)")

    no_eval = [r for r in results if np.isnan(r["median_days_to_pass"])]
    if no_eval:
        best_no_eval = max(no_eval, key=lambda x: x["expected_monthly_net"])
        print(f"  Best no-eval:          {best_no_eval['firm']}")

    # Best ROI
    fee_firms = [r for r in results if r["startup_fee"] > 0 and np.isfinite(r["roi_on_fees"])]
    if fee_firms:
        best_roi = max(fee_firms, key=lambda x: x["roi_on_fees"])
        print(f"  Best ROI on fees:      {best_roi['firm']} ({best_roi['roi_on_fees']:.1f}x)")

    # Highest monthly net
    best_monthly = max(results, key=lambda x: x["expected_monthly_net"])
    print(f"  Highest monthly:       {best_monthly['firm']} ({fmt_dollars(best_monthly['expected_monthly_net'])})")

    # Most consistent (lowest blockage)
    best_consist = min(results, key=lambda x: x["consistency_blockage_rate"])
    print(f"  Most consistent:       {best_consist['firm']} ({fmt_pct(best_consist['consistency_blockage_rate'])} blocked)")

    # Top 3 for deployment
    print()
    print("  DEPLOYMENT PRIORITY")
    print("  " + "-" * 36)
    for i, r in enumerate(results[:3]):
        print(f"  {i+1}. {r['firm']} — Score {r['score']}/10, "
              f"{fmt_dollars(r['expected_monthly_net'])}/mo")

    print()
    print("=" * w)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Prop Firm Optimizer — Monte Carlo ranking")
    parser.add_argument("--trials", type=int, default=5000)
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--preview", action="store_true", help="Show dataset preview only")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    # Load dataset
    offerings = load_dataset()

    if args.preview:
        print_preview(offerings)
        return

    # Build sim configs
    configs = build_sim_configs(offerings)

    # Load PnL distribution
    pnl_pool = load_daily_pnl()
    print(f"Loaded {len(pnl_pool)} non-zero daily PnL samples")

    rng = np.random.default_rng(args.seed)

    # Run simulations
    results = []
    for name, config in configs.items():
        print(f"  Simulating {name}...")
        r = simulate_firm(name, config, pnl_pool, args.trials, args.days, rng)
        results.append(r)

    # Compute scores
    for r in results:
        r["score"] = compute_score(r, results)

    results.sort(key=lambda x: x["score"], reverse=True)

    print_report(results, pnl_pool, args.trials, args.days)

    if args.save:
        out_path = ROOT / "research" / "prop_firm_ranking.json"
        serializable = []
        for r in results:
            sr = {}
            for k, v in r.items():
                if isinstance(v, (np.floating, np.float64)):
                    sr[k] = float(v) if not np.isnan(v) else None
                elif isinstance(v, (np.integer, np.int64)):
                    sr[k] = int(v)
                else:
                    sr[k] = v
            serializable.append(sr)

        out_path.write_text(json.dumps({
            "trials": args.trials,
            "days": args.days,
            "seed": args.seed,
            "pnl_samples": len(pnl_pool),
            "pnl_mean": float(np.mean(pnl_pool)),
            "pnl_std": float(np.std(pnl_pool)),
            "rankings": serializable,
        }, indent=2))
        print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
