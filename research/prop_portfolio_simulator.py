"""Prop Portfolio Simulator — Monte Carlo analysis of multi-account prop trading.

READ-ONLY research tool. Simulates running the validated 6-strategy portfolio
across multiple prop accounts to answer: "How fast can I get prop payouts?"

Bootstraps daily PnL from the Phase 17 equity curve and simulates prop account
lifecycle including trailing drawdown, daily loss limits, phase transitions,
consistency rules, account busts, replacements, and payout timing.

Usage:
    python3 research/prop_portfolio_simulator.py
    python3 research/prop_portfolio_simulator.py --accounts 1,5,10 --trials 5000
    python3 research/prop_portfolio_simulator.py --days 360 --save
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

EQUITY_CURVE_PATH = ROOT / "research" / "phase17_paper_trading" / "equity_curve.csv"
PROP_CONFIG_PATH = ROOT / "controllers" / "prop_configs" / "lucid_100k.json"


def load_daily_pnl() -> np.ndarray:
    """Load daily PnL distribution from the Phase 17 equity curve."""
    if not EQUITY_CURVE_PATH.exists():
        print(f"ERROR: Equity curve not found at {EQUITY_CURVE_PATH}")
        sys.exit(1)

    df = pd.read_csv(EQUITY_CURVE_PATH)
    daily_pnl = df["daily_pnl"].values

    # Filter out zero-PnL days (no trades) to get the true trading distribution
    nonzero = daily_pnl[daily_pnl != 0.0]
    if len(nonzero) < 20:
        print(f"WARNING: Only {len(nonzero)} non-zero PnL days. Using all days.")
        return daily_pnl

    return nonzero


def load_prop_config() -> dict:
    """Load prop account configuration."""
    if PROP_CONFIG_PATH.exists():
        with open(PROP_CONFIG_PATH) as f:
            return json.load(f)
    # Fallback defaults matching Lucid 100K
    return {
        "account_size": 100000,
        "trailing_drawdown": 4000,
        "lock_profit": 3100,
        "phases": {
            "P1": {"max_daily_loss": 600},
            "P2": {"max_daily_loss": 1200},
        },
    }


# ---------------------------------------------------------------------------
# Prop account state machine
# ---------------------------------------------------------------------------

@dataclass
class PropAccount:
    """Single prop account state."""
    equity: float
    hwm: float  # high water mark (EOD)
    trailing_dd_limit: float
    lock_profit: float
    starting_equity: float
    phase: str = "P1"
    busted: bool = False
    locked: bool = False
    cumulative_pnl: float = 0.0
    total_payouts: float = 0.0
    payout_count: int = 0
    days_active: int = 0
    day_reached_p2: int = -1
    cooldown_remaining: int = 0

    # Consistency tracking: daily PnLs for the current payout cycle
    cycle_daily_pnls: list = field(default_factory=list)

    def apply_day(self, raw_pnl: float, day_idx: int, p1_daily_cap: float,
                  p2_daily_cap: float, consistency_pct: float) -> dict:
        """Process one trading day. Returns event dict."""
        if self.busted or self.cooldown_remaining > 0:
            if self.cooldown_remaining > 0:
                self.cooldown_remaining -= 1
            return {"event": "inactive"}

        self.days_active += 1

        # Apply daily loss cap based on phase
        daily_cap = p1_daily_cap if self.phase == "P1" else p2_daily_cap
        capped_pnl = max(raw_pnl, -daily_cap)

        # Update equity
        self.equity += capped_pnl
        self.cumulative_pnl += capped_pnl
        self.cycle_daily_pnls.append(capped_pnl)

        # EOD trailing drawdown: update HWM at end of day
        if self.equity > self.hwm:
            self.hwm = self.equity

        # Check trailing DD bust
        trailing_floor = self.hwm - self.trailing_dd_limit

        # Once locked, trailing floor stops at lock level
        if self.locked:
            lock_floor = self.starting_equity + self.lock_profit - self.trailing_dd_limit
            trailing_floor = max(trailing_floor, lock_floor)

        if self.equity < trailing_floor:
            self.busted = True
            return {"event": "bust", "day": day_idx}

        # Phase transition: P1 -> P2 at lock_profit
        if self.phase == "P1" and self.cumulative_pnl >= self.lock_profit:
            self.phase = "P2"
            self.locked = True
            self.day_reached_p2 = day_idx
            return {"event": "p2_reached", "day": day_idx}

        return {"event": "ok"}

    def attempt_payout(self, consistency_pct: float, payout_min: float = 1000.0) -> float:
        """Attempt a payout if in P2 with sufficient profit above lock level."""
        if self.phase != "P2" or self.busted:
            return 0.0

        # Available profit above the lock level
        profit_above_lock = self.cumulative_pnl - self.lock_profit
        if profit_above_lock < payout_min:
            return 0.0

        # Consistency check: no single day > consistency_pct of total profit
        if len(self.cycle_daily_pnls) > 0 and self.cumulative_pnl > 0:
            max_single_day = max(self.cycle_daily_pnls)
            if max_single_day / self.cumulative_pnl > consistency_pct:
                return 0.0  # Would violate consistency

        # Withdraw available profit (keep lock_profit cushion)
        payout = profit_above_lock
        self.total_payouts += payout
        self.payout_count += 1
        self.equity -= payout
        self.cumulative_pnl -= payout
        self.hwm = self.equity  # Reset HWM after payout
        self.cycle_daily_pnls = []  # Reset cycle tracking
        return payout


# ---------------------------------------------------------------------------
# Simulation engine
# ---------------------------------------------------------------------------

def run_single_account_trial(
    daily_pnl_pool: np.ndarray,
    rng: np.random.Generator,
    n_days: int,
    config: dict,
) -> dict:
    """Simulate one prop account for n_days."""
    starting_eq = config["account_size"]
    trailing_dd = config["trailing_drawdown"]
    lock_profit = config["lock_profit"]
    p1_cap = config["phases"]["P1"].get("max_daily_loss", 600)
    p2_cap = config["phases"]["P2"].get("max_daily_loss", 1200)
    consistency_pct = 0.30  # 30% consistency rule
    payout_interval = 20  # Attempt payout every ~20 trading days

    acct = PropAccount(
        equity=starting_eq,
        hwm=starting_eq,
        trailing_dd_limit=trailing_dd,
        lock_profit=lock_profit,
        starting_equity=starting_eq,
    )

    # Sample daily PnLs for the trial
    sampled_pnl = rng.choice(daily_pnl_pool, size=n_days, replace=True)

    payouts = []
    bust_day = -1
    p2_day = -1
    worst_dd = 0.0
    payout_attempts = 0
    payout_blocked_by_consistency = 0

    for day in range(n_days):
        result = acct.apply_day(
            sampled_pnl[day], day, p1_cap, p2_cap, consistency_pct
        )

        if result["event"] == "bust":
            bust_day = day
            break
        elif result["event"] == "p2_reached":
            p2_day = day

        # Track drawdown
        dd = acct.hwm - acct.equity
        if dd > worst_dd:
            worst_dd = dd

        # Attempt payout periodically
        if acct.phase == "P2" and day > 0 and day % payout_interval == 0:
            # Check if consistency would block before attempting
            profit_above_lock = acct.cumulative_pnl - acct.lock_profit
            if profit_above_lock >= 1000.0:
                payout_attempts += 1
                payout = acct.attempt_payout(consistency_pct)
                if payout > 0:
                    payouts.append({"day": day, "amount": payout})
                else:
                    payout_blocked_by_consistency += 1

    # Final payout attempt
    if not acct.busted and acct.phase == "P2":
        profit_above_lock = acct.cumulative_pnl - acct.lock_profit
        if profit_above_lock >= 500.0:
            payout_attempts += 1
            payout = acct.attempt_payout(consistency_pct, payout_min=500.0)
            if payout > 0:
                payouts.append({"day": n_days, "amount": payout})
            else:
                payout_blocked_by_consistency += 1

    total_payout = sum(p["amount"] for p in payouts)

    return {
        "busted": acct.busted,
        "bust_day": bust_day,
        "reached_p2": p2_day >= 0,
        "p2_day": p2_day,
        "total_payout": total_payout,
        "payout_count": len(payouts),
        "worst_dd": worst_dd,
        "final_equity": acct.equity,
        "final_pnl": acct.cumulative_pnl,
        "payout_attempts": payout_attempts,
        "payout_blocked_by_consistency": payout_blocked_by_consistency,
        "payouts": payouts,
    }


def run_multi_account_trial(
    daily_pnl_pool: np.ndarray,
    rng: np.random.Generator,
    n_days: int,
    n_accounts: int,
    config: dict,
    account_fee: float = 100.0,
    cooldown_days: int = 5,
) -> dict:
    """Simulate n_accounts running independently for n_days."""
    starting_eq = config["account_size"]
    trailing_dd = config["trailing_drawdown"]
    lock_profit = config["lock_profit"]
    p1_cap = config["phases"]["P1"].get("max_daily_loss", 600)
    p2_cap = config["phases"]["P2"].get("max_daily_loss", 1200)
    consistency_pct = 0.30
    payout_interval = 20

    # Initialize accounts
    accounts = []
    for _ in range(n_accounts):
        accounts.append(PropAccount(
            equity=starting_eq,
            hwm=starting_eq,
            trailing_dd_limit=trailing_dd,
            lock_profit=lock_profit,
            starting_equity=starting_eq,
        ))

    total_payouts = 0.0
    total_payout_count = 0
    total_busts = 0
    total_fees = n_accounts * account_fee  # Initial fees
    monthly_payouts = [0.0] * ((n_days // 21) + 1)  # ~21 trading days/month

    for day in range(n_days):
        month_idx = day // 21

        for i, acct in enumerate(accounts):
            # Handle cooldown
            if acct.cooldown_remaining > 0:
                acct.cooldown_remaining -= 1
                if acct.cooldown_remaining == 0:
                    # Replace with fresh account
                    accounts[i] = PropAccount(
                        equity=starting_eq,
                        hwm=starting_eq,
                        trailing_dd_limit=trailing_dd,
                        lock_profit=lock_profit,
                        starting_equity=starting_eq,
                    )
                    total_fees += account_fee
                    acct = accounts[i]
                else:
                    continue

            if acct.busted:
                # Start cooldown
                total_busts += 1
                acct.cooldown_remaining = cooldown_days
                acct.busted = False  # Will be replaced after cooldown
                continue

            # Sample independent PnL for this account
            day_pnl = rng.choice(daily_pnl_pool)
            result = acct.apply_day(day_pnl, day, p1_cap, p2_cap, consistency_pct)

            # Attempt payout periodically
            if acct.phase == "P2" and day > 0 and day % payout_interval == 0:
                payout = acct.attempt_payout(consistency_pct)
                if payout > 0:
                    total_payouts += payout
                    total_payout_count += 1
                    if month_idx < len(monthly_payouts):
                        monthly_payouts[month_idx] += payout

    # Final payout sweep
    month_idx = n_days // 21
    for acct in accounts:
        if not acct.busted and acct.phase == "P2":
            payout = acct.attempt_payout(consistency_pct, payout_min=500.0)
            if payout > 0:
                total_payouts += payout
                total_payout_count += 1
                if month_idx < len(monthly_payouts):
                    monthly_payouts[month_idx] += payout

    net_profit = total_payouts - total_fees
    n_months = max(n_days / 21.0, 1.0)

    return {
        "total_payouts": total_payouts,
        "total_payout_count": total_payout_count,
        "total_busts": total_busts,
        "total_fees": total_fees,
        "net_profit": net_profit,
        "monthly_income": net_profit / n_months,
        "monthly_payouts": monthly_payouts[:int(n_months) + 1],
    }


# ---------------------------------------------------------------------------
# Monte Carlo runner
# ---------------------------------------------------------------------------

def run_simulation(
    daily_pnl_pool: np.ndarray,
    config: dict,
    account_counts: list[int],
    n_trials: int,
    n_days: int,
) -> dict:
    """Run full Monte Carlo simulation."""
    rng = np.random.default_rng(42)

    # --- Single account trials ---
    single_results = []
    for _ in range(n_trials):
        r = run_single_account_trial(daily_pnl_pool, rng, n_days, config)
        single_results.append(r)

    busted = [r for r in single_results if r["busted"]]
    reached_p2 = [r for r in single_results if r["reached_p2"]]
    p2_days = [r["p2_day"] for r in reached_p2]
    payouts_if_p2 = [r["total_payout"] for r in reached_p2 if r["total_payout"] > 0]
    all_payouts = [r["total_payout"] for r in single_results]
    all_dd = [r["worst_dd"] for r in single_results]
    total_attempts = sum(r["payout_attempts"] for r in single_results)
    total_blocked = sum(r["payout_blocked_by_consistency"] for r in single_results)
    consistency_block_rate = total_blocked / total_attempts if total_attempts > 0 else 0.0

    single_stats = {
        "p_bust": len(busted) / n_trials,
        "p_reach_p2": len(reached_p2) / n_trials,
        "median_days_to_p2": int(np.median(p2_days)) if p2_days else None,
        "median_payout_if_p2": float(np.median(payouts_if_p2)) if payouts_if_p2 else 0,
        "expected_6mo_profit": float(np.mean(all_payouts)),
        "dd_p95": float(np.percentile(all_dd, 95)),
        "dd_p99": float(np.percentile(all_dd, 99)),
        "consistency_block_rate": consistency_block_rate,
    }

    # --- Multi-account trials ---
    multi_stats = {}
    for n_accts in account_counts:
        trials = []
        for _ in range(n_trials):
            r = run_multi_account_trial(
                daily_pnl_pool, rng, n_days, n_accts, config
            )
            trials.append(r)

        all_busts = [t["total_busts"] for t in trials]
        all_net = [t["net_profit"] for t in trials]
        all_monthly = [t["monthly_income"] for t in trials]
        any_bust = [1 if t["total_busts"] > 0 else 0 for t in trials]

        # Monthly payout timeline (average across trials)
        max_months = max(len(t["monthly_payouts"]) for t in trials)
        monthly_timeline = []
        for m in range(max_months):
            month_vals = [
                t["monthly_payouts"][m]
                for t in trials
                if m < len(t["monthly_payouts"])
            ]
            monthly_timeline.append(float(np.mean(month_vals)) if month_vals else 0.0)

        multi_stats[n_accts] = {
            "monthly_income": float(np.mean(all_monthly)),
            "six_month_profit": float(np.mean(all_net)),
            "p_any_bust": float(np.mean(any_bust)),
            "avg_busts": float(np.mean(all_busts)),
            "net_profit": float(np.mean(all_net)),
            "monthly_timeline": monthly_timeline,
        }

    return {
        "single": single_stats,
        "multi": multi_stats,
    }


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def display_input_stats(daily_pnl: np.ndarray):
    """Print input distribution statistics."""
    mean = np.mean(daily_pnl)
    std = np.std(daily_pnl)
    n = len(daily_pnl)
    # Manual skewness calculation
    skew = float((n / ((n - 1) * (n - 2))) * np.sum(((daily_pnl - mean) / std) ** 3)) if n > 2 and std > 0 else 0.0
    win_rate = np.mean(daily_pnl > 0)

    print(f"  INPUT DISTRIBUTION")
    print(f"  {'─' * 36}")
    print(f"  Daily PnL samples:     {len(daily_pnl)}")
    print(f"  Mean daily PnL:        ${mean:,.2f}")
    print(f"  Std daily PnL:         ${std:,.2f}")
    print(f"  Skew:                  {skew:.2f}")
    print(f"  Win day rate:          {win_rate:.0%}")
    print()


def display_results(results: dict, account_counts: list[int], n_trials: int,
                    n_days: int):
    """Print formatted results."""
    s = results["single"]
    m = results["multi"]

    print(f"\n{'=' * 70}")
    print(f"  PROP PORTFOLIO SIMULATOR")
    print(f"  Monte Carlo: {n_trials:,} trials x {n_days} trading days")
    print(f"{'=' * 70}\n")

    print(f"  SINGLE ACCOUNT RESULTS")
    print(f"  {'─' * 36}")
    print(f"  P(bust within {n_days} days):     {s['p_bust']:.1%}")
    print(f"  P(reach P2):                 {s['p_reach_p2']:.1%}")
    if s["median_days_to_p2"] is not None:
        print(f"  Median days to P2:           {s['median_days_to_p2']}")
    else:
        print(f"  Median days to P2:           N/A")
    print(f"  Median payout (if P2):       ${s['median_payout_if_p2']:,.0f}")
    n_months = max(n_days // 21, 1)
    print(f"  Expected {n_months}-month profit:     ${s['expected_6mo_profit']:,.0f}")
    print()

    print(f"  MULTI-ACCOUNT RESULTS")
    print(f"  {'─' * 36}")
    header = f"  {'Accounts':<12}{'Monthly':>10}{'6-Month':>12}{'P(any bust)':>14}{'Busts/6mo':>12}{'Net Profit':>13}"
    divider = f"  {'─' * 12}{'─' * 10}{'─' * 12}{'─' * 14}{'─' * 12}{'─' * 13}"
    print(header)
    print(divider)

    for n_accts in account_counts:
        if n_accts not in m:
            continue
        ms = m[n_accts]
        print(
            f"  {n_accts:<12}"
            f"${ms['monthly_income']:>8,.0f}"
            f"${ms['six_month_profit']:>10,.0f}"
            f"{ms['p_any_bust']:>13.1%}"
            f"{ms['avg_busts']:>11.2f}"
            f"${ms['net_profit']:>11,.0f}"
        )
    print()

    print(f"  RISK ANALYSIS")
    print(f"  {'─' * 36}")
    print(f"  Worst drawdown (p95):        ${s['dd_p95']:,.0f}")
    print(f"  Worst drawdown (p99):        ${s['dd_p99']:,.0f}")
    print(f"  Payouts blocked (consistency): {s['consistency_block_rate']:.1%}")
    print()

    # Payout timeline for the middle account count
    timeline_accts = account_counts[len(account_counts) // 2] if len(account_counts) > 1 else account_counts[0]
    if timeline_accts in m:
        timeline = m[timeline_accts]["monthly_timeline"]
        print(f"  PAYOUT TIMELINE ({timeline_accts} accounts)")
        print(f"  {'─' * 36}")
        for i, val in enumerate(timeline[:7]):
            label = f"Month {i + 1}:"
            print(f"  {label:<12}${val:>8,.0f}")
        print()

    print(f"{'=' * 70}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Prop Portfolio Simulator — Monte Carlo multi-account analysis"
    )
    parser.add_argument(
        "--accounts", type=str, default="1,3,5,10",
        help="Comma-separated account counts (default: 1,3,5,10)",
    )
    parser.add_argument(
        "--trials", type=int, default=10000,
        help="Number of Monte Carlo trials (default: 10000)",
    )
    parser.add_argument(
        "--days", type=int, default=180,
        help="Trading days to simulate (default: 180)",
    )
    parser.add_argument(
        "--save", action="store_true",
        help="Save results to research/prop_simulation_results.json",
    )
    args = parser.parse_args()

    account_counts = [int(x.strip()) for x in args.accounts.split(",")]

    # Load data
    print("\nLoading data...")
    daily_pnl = load_daily_pnl()
    config = load_prop_config()
    print(f"  Loaded {len(daily_pnl)} daily PnL samples from Phase 17 equity curve")
    print(f"  Prop config: {config.get('name', 'Lucid 100K')}")
    print(f"  Account size: ${config['account_size']:,}")
    print(f"  Trailing DD: ${config['trailing_drawdown']:,}")
    print(f"  Lock profit: ${config['lock_profit']:,}")
    print()

    display_input_stats(daily_pnl)

    # Run simulation
    print(f"Running {args.trials:,} trials x {args.days} days "
          f"for {account_counts} accounts...")

    results = run_simulation(
        daily_pnl, config, account_counts, args.trials, args.days
    )

    display_results(results, account_counts, args.trials, args.days)

    # Save if requested
    if args.save:
        out_path = ROOT / "research" / "prop_simulation_results.json"
        save_data = {
            "config": {
                "trials": args.trials,
                "days": args.days,
                "account_counts": account_counts,
                "account_fee": 100,
                "cooldown_days": 5,
            },
            "input_distribution": {
                "n_samples": len(daily_pnl),
                "mean": float(np.mean(daily_pnl)),
                "std": float(np.std(daily_pnl)),
                "win_rate": float(np.mean(daily_pnl > 0)),
            },
            "single_account": {k: v for k, v in results["single"].items()},
            "multi_account": {
                str(k): v for k, v in results["multi"].items()
            },
        }
        with open(out_path, "w") as f:
            json.dump(save_data, f, indent=2)
        print(f"\n  Results saved to {out_path}")


if __name__ == "__main__":
    main()
