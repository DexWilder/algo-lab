"""Prop Firm Optimizer — Monte Carlo ranking of prop firms for this portfolio.

READ-ONLY research tool. Uses the daily PnL distribution from Phase 17
equity curve to simulate account trajectories across multiple prop firms.

Usage:
    python3 research/prop_firm_optimizer.py
    python3 research/prop_firm_optimizer.py --trials 10000 --days 252
    python3 research/prop_firm_optimizer.py --save
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Prop firm configurations
# ---------------------------------------------------------------------------

PROP_FIRMS = {
    "Lucid 100K": {
        "account_size": 100_000,
        "trailing_drawdown": 4_000,
        "trailing_type": "eod",
        "daily_loss_limit": None,
        "profit_target": None,
        "lock_profit": 3_100,
        "consistency_rule": None,
        "phases": {
            "P1": {"max_daily_loss": 600, "max_contracts": 2},
            "P2": {"max_daily_loss": 1200, "max_contracts": 5},
        },
        "monthly_fee": 0,
        "startup_fee": 0,
        "payout_split": 0.90,
        "min_payout": 500,
        "payout_frequency_days": 14,
    },
    "Lucid 50K": {
        "account_size": 50_000,
        "trailing_drawdown": 2_500,
        "trailing_type": "eod",
        "daily_loss_limit": None,
        "profit_target": None,
        "lock_profit": 1_800,
        "consistency_rule": None,
        "phases": {
            "P1": {"max_daily_loss": 400, "max_contracts": 2},
            "P2": {"max_daily_loss": 800, "max_contracts": 3},
        },
        "monthly_fee": 0,
        "startup_fee": 0,
        "payout_split": 0.90,
        "min_payout": 500,
        "payout_frequency_days": 14,
    },
    "Apex 50K": {
        "account_size": 50_000,
        "trailing_drawdown": 2_500,
        "trailing_type": "eod",
        "daily_loss_limit": None,
        "profit_target": 3_000,
        "lock_profit": None,
        "consistency_rule": 0.30,
        "phases": None,
        "monthly_fee": 0,
        "startup_fee": 147,
        "payout_split": 1.00,
        "min_payout": 500,
        "payout_frequency_days": 14,
    },
    "Apex 100K": {
        "account_size": 100_000,
        "trailing_drawdown": 3_000,
        "trailing_type": "eod",
        "daily_loss_limit": None,
        "profit_target": 6_000,
        "lock_profit": None,
        "consistency_rule": 0.30,
        "phases": None,
        "monthly_fee": 0,
        "startup_fee": 207,
        "payout_split": 1.00,
        "min_payout": 500,
        "payout_frequency_days": 14,
    },
    "Tradeify 50K": {
        "account_size": 50_000,
        "trailing_drawdown": 2_000,
        "trailing_type": "eod",
        "daily_loss_limit": 1_000,
        "profit_target": 2_500,
        "lock_profit": None,
        "consistency_rule": 0.40,
        "phases": None,
        "monthly_fee": 0,
        "startup_fee": 99,
        "payout_split": 0.80,
        "min_payout": 250,
        "payout_frequency_days": 7,
    },
}

BASELINE_CONTRACTS = 2  # baseline contract count in equity curve data


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_daily_pnl() -> np.ndarray:
    """Load non-zero daily PnL values from Phase 17 equity curve."""
    csv_path = ROOT / "research" / "phase17_paper_trading" / "equity_curve.csv"
    if not csv_path.exists():
        print(f"ERROR: Equity curve not found at {csv_path}")
        sys.exit(1)
    df = pd.read_csv(csv_path)
    pnl = df["daily_pnl"].values
    # Filter out zero days (no activity)
    pnl = pnl[pnl != 0.0]
    return pnl


# ---------------------------------------------------------------------------
# Simulation engine
# ---------------------------------------------------------------------------

def simulate_firm(firm_name: str, config: dict, pnl_pool: np.ndarray,
                  n_trials: int, n_days: int, rng: np.random.Generator) -> dict:
    """Run Monte Carlo simulation for a single prop firm."""

    has_phases = config["phases"] is not None
    has_eval = config["profit_target"] is not None
    trailing_dd = config["trailing_drawdown"]
    daily_limit = config["daily_loss_limit"]
    consistency = config["consistency_rule"]
    payout_split = config["payout_split"]
    min_payout = config["min_payout"]
    payout_freq = config["payout_frequency_days"]
    lock_profit = config["lock_profit"]
    startup_fee = config["startup_fee"]
    monthly_fee = config["monthly_fee"]

    # Phase contract scaling factors
    if has_phases:
        phases = config["phases"]
        p1_scale = phases["P1"]["max_contracts"] / BASELINE_CONTRACTS
        p2_scale = phases["P2"]["max_contracts"] / BASELINE_CONTRACTS
        p1_daily_limit = phases["P1"]["max_daily_loss"]
        p2_daily_limit = phases["P2"]["max_daily_loss"]

    # Pre-sample all daily PnL draws: (n_trials, n_days)
    samples = rng.choice(pnl_pool, size=(n_trials, n_days), replace=True)

    bust_count = 0
    pass_count = 0
    days_to_pass_list = []
    total_payouts_list = []
    consistency_blocks = 0
    consistency_attempts = 0

    for t in range(n_trials):
        equity = 0.0  # profit relative to starting balance
        hwm = 0.0
        busted = False
        funded = False  # for eval firms
        day_funded = 0
        in_p2 = False  # for phase firms
        day_p2 = 0

        # Payout tracking
        total_payouts = 0.0
        last_payout_day = -payout_freq  # allow payout from day 0
        profit_since_last_payout = 0.0
        daily_pnl_log = []  # for consistency rule

        for d in range(n_days):
            raw_pnl = samples[t, d]

            # --- Scale PnL by phase/contract limits ---
            if has_phases:
                if in_p2:
                    scaled_pnl = raw_pnl * p2_scale
                    current_daily_limit = p2_daily_limit
                else:
                    scaled_pnl = raw_pnl * p1_scale
                    current_daily_limit = p1_daily_limit
                # Apply daily loss limit
                if scaled_pnl < -current_daily_limit:
                    scaled_pnl = -current_daily_limit
            else:
                scaled_pnl = raw_pnl
                # Apply daily loss limit if set
                if daily_limit is not None and scaled_pnl < -daily_limit:
                    scaled_pnl = -daily_limit

            # Apply PnL
            equity += scaled_pnl

            # Update HWM (EOD trailing)
            if equity > hwm:
                hwm = equity

            # Check trailing drawdown bust
            if equity < hwm - trailing_dd:
                busted = True
                break

            # --- Phase transition (Lucid) ---
            if has_phases and not in_p2:
                if lock_profit is not None and equity >= lock_profit:
                    in_p2 = True
                    day_p2 = d + 1

            # --- Eval pass (Apex, Tradeify) ---
            if has_eval and not funded:
                if equity >= config["profit_target"]:
                    funded = True
                    day_funded = d + 1

            # --- Payout logic (only when funded/P2) ---
            can_payout = (has_phases and in_p2) or (has_eval and funded) or \
                         (not has_phases and not has_eval)

            if can_payout:
                profit_since_last_payout += scaled_pnl
                daily_pnl_log.append(scaled_pnl)

                if (d - last_payout_day) >= payout_freq and profit_since_last_payout > 0:
                    payout_amount = profit_since_last_payout * payout_split

                    # Consistency rule check
                    if consistency is not None:
                        consistency_attempts += 1
                        total_profit_at_payout = sum(daily_pnl_log)
                        if total_profit_at_payout > 0:
                            max_single_day = max(daily_pnl_log)
                            if max_single_day / total_profit_at_payout > consistency:
                                consistency_blocks += 1
                                # Can't take payout yet, skip
                                continue

                    if payout_amount >= min_payout:
                        total_payouts += payout_amount
                        last_payout_day = d
                        profit_since_last_payout = 0.0

        if busted:
            bust_count += 1
        else:
            total_payouts_list.append(total_payouts)

        # Track pass/days-to-pass
        if has_phases:
            if in_p2:
                pass_count += 1
                days_to_pass_list.append(day_p2)
        elif has_eval:
            if funded:
                pass_count += 1
                days_to_pass_list.append(day_funded)
        else:
            # No eval/phase — always "passed"
            if not busted:
                pass_count += 1

    # --- Compute metrics ---
    pass_prob = pass_count / n_trials
    bust_prob = bust_count / n_trials
    median_days = float(np.median(days_to_pass_list)) if days_to_pass_list else np.nan

    total_fees = startup_fee + monthly_fee * (n_days / 21)  # ~21 trading days/month
    months = n_days / 21

    if total_payouts_list:
        mean_total_payout = np.mean(total_payouts_list)
        median_total_payout = np.median(total_payouts_list)
    else:
        mean_total_payout = 0.0
        median_total_payout = 0.0

    # Expected 6-month net includes bust scenarios (0 payout) and fee
    all_payouts = []
    for t in range(n_trials):
        # Reconstruct: busted trials get 0
        pass
    # Simpler: use pass rate * mean payout for those who passed
    expected_6mo_gross = pass_prob * mean_total_payout
    expected_6mo_net = expected_6mo_gross - total_fees
    expected_monthly_net = expected_6mo_net / months if months > 0 else 0

    consistency_block_rate = (consistency_blocks / consistency_attempts
                              if consistency_attempts > 0 else 0.0)

    roi_on_fees = expected_6mo_net / startup_fee if startup_fee > 0 else np.inf

    return {
        "firm": firm_name,
        "pass_probability": pass_prob,
        "bust_probability": bust_prob,
        "median_days_to_pass": median_days,
        "expected_monthly_net": expected_monthly_net,
        "six_month_net_profit": expected_6mo_net,
        "consistency_blockage_rate": consistency_block_rate,
        "roi_on_fees": roi_on_fees,
        "startup_fee": startup_fee,
        "mean_total_payout": mean_total_payout,
    }


def compute_score(r: dict, all_results: list) -> float:
    """Compute weighted overall score (0-10 scale)."""
    # Normalize monthly net across firms
    monthly_nets = [x["expected_monthly_net"] for x in all_results]
    max_monthly = max(monthly_nets) if max(monthly_nets) > 0 else 1.0
    monthly_norm = r["expected_monthly_net"] / max_monthly if max_monthly > 0 else 0

    # Normalize speed (inverse days to pass — lower is better)
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
        speed_norm = 1.0  # no eval needed = instant

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


def print_report(results: list, pnl_pool: np.ndarray, n_trials: int, n_days: int):
    """Print the formatted ranking report."""
    w = 70

    print()
    print("=" * w)
    print("  PROP FIRM OPTIMIZER")
    print(f"  Monte Carlo: {n_trials:,} trials x {n_days} trading days")
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
        print(f"  #{rank}  {name:<45s} Score: {score}/10")
        print("  " + "-" * (w - 4))
        print(f"  Pass probability:      {fmt_pct(r['pass_probability'])}")
        print(f"  Bust probability:      {fmt_pct(r['bust_probability'])}")
        print(f"  Days to funded:        {fmt_days(r['median_days_to_pass'])}")
        print(f"  Monthly net:           {fmt_dollars(r['expected_monthly_net'])}")
        print(f"  6-month net:           {fmt_dollars(r['six_month_net_profit'])}")
        print(f"  Consistency block:     {fmt_pct(r['consistency_blockage_rate'])}")
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
    header = (f"  {'Firm':<16s} {'Pass%':>6s}  {'Bust%':>6s}  {'Days':>5s}  "
              f"{'Monthly':>8s}  {'6mo Net':>8s}  {'Consist':>7s}  {'Score':>5s}")
    print(header)
    print("  " + "-" * (w - 4))
    for r in results:
        days_str = fmt_days(r["median_days_to_pass"])
        print(f"  {r['firm']:<16s} {fmt_pct(r['pass_probability']):>6s}  "
              f"{fmt_pct(r['bust_probability']):>6s}  {days_str:>5s}  "
              f"{fmt_dollars(r['expected_monthly_net']):>8s}  "
              f"{fmt_dollars(r['six_month_net_profit']):>8s}  "
              f"{fmt_pct(r['consistency_blockage_rate']):>7s}  "
              f"{r['score']:>5.1f}")

    # Recommendations
    print()
    print("  RECOMMENDATION")
    print("  " + "-" * 36)

    best_overall = results[0]["firm"]
    print(f"  Best overall:          {best_overall}")

    # Fastest to pass (among those with eval/phases)
    passable = [r for r in results if not np.isnan(r["median_days_to_pass"])]
    if passable:
        fastest = min(passable, key=lambda x: x["median_days_to_pass"])
        print(f"  Best for fast payout:  {fastest['firm']} ({fmt_days(fastest['median_days_to_pass'])} days)")
    else:
        no_eval = [r for r in results if np.isnan(r["median_days_to_pass"])]
        if no_eval:
            print(f"  Best for fast payout:  {no_eval[0]['firm']} (no eval required)")

    # Best ROI on fees
    fee_firms = [r for r in results if r["startup_fee"] > 0 and np.isfinite(r["roi_on_fees"])]
    if fee_firms:
        best_roi = max(fee_firms, key=lambda x: x["roi_on_fees"])
        print(f"  Best ROI on fees:      {best_roi['firm']} ({best_roi['roi_on_fees']:.1f}x)")
    else:
        print(f"  Best ROI on fees:      N/A (no fee-based firms)")

    # Most consistent
    best_consist = min(results, key=lambda x: x["consistency_blockage_rate"])
    print(f"  Most consistent:       {best_consist['firm']} ({fmt_pct(best_consist['consistency_blockage_rate'])} blocked)")

    print()
    print("=" * w)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Prop Firm Optimizer — Monte Carlo ranking")
    parser.add_argument("--trials", type=int, default=5000, help="Number of MC trials (default: 5000)")
    parser.add_argument("--days", type=int, default=180, help="Trading days per trial (default: 180)")
    parser.add_argument("--save", action="store_true", help="Save results to research/prop_firm_ranking.json")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    pnl_pool = load_daily_pnl()
    print(f"Loaded {len(pnl_pool)} non-zero daily PnL samples")

    rng = np.random.default_rng(args.seed)

    # Run simulations
    results = []
    for name, config in PROP_FIRMS.items():
        print(f"  Simulating {name}...")
        r = simulate_firm(name, config, pnl_pool, args.trials, args.days, rng)
        results.append(r)

    # Compute scores
    for r in results:
        r["score"] = compute_score(r, results)

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)

    # Print report
    print_report(results, pnl_pool, args.trials, args.days)

    # Save if requested
    if args.save:
        out_path = ROOT / "research" / "prop_firm_ranking.json"
        # Convert numpy types for JSON serialization
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
