"""Deep validation: pre_fomc_drift_v2 — research only, prints to stdout."""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import numpy as np
from engine.backtest import run_backtest
from engine.asset_config import get_asset

# ── Load strategy module ────────────────────────────────────────────────────
spec = importlib.util.spec_from_file_location(
    "strat", ROOT / "strategies/pre_fomc_drift_v2/strategy.py"
)
mod = importlib.util.module_from_spec(spec)


def backtest_asset(symbol):
    """Run strategy on a single asset, return trades_df and stats."""
    cfg = get_asset(symbol)
    mod.TICK_SIZE = cfg["tick_size"]
    spec.loader.exec_module(mod)

    df = pd.read_csv(ROOT / f"data/processed/{symbol}_5m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"])
    df_signals = mod.generate_signals(df.copy(), asset=symbol, mode="both")

    result = run_backtest(
        df, df_signals, mode="long",
        point_value=cfg["point_value"],
        symbol=symbol,
        tick_size=cfg["tick_size"],
    )
    return result["trades_df"], result["stats"], result["equity_curve"]


def pf(wins, losses):
    """Profit factor from gross win / gross loss."""
    gw = wins.sum() if len(wins) > 0 else 0
    gl = abs(losses.sum()) if len(losses) > 0 else 0
    return round(gw / gl, 2) if gl > 0 else float("inf")


def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


# ── Run backtests ───────────────────────────────────────────────────────────
results = {}
for sym in ["MNQ", "MES"]:
    trades, stats, eq = backtest_asset(sym)
    trades["entry_time"] = pd.to_datetime(trades["entry_time"])
    trades["exit_time"] = pd.to_datetime(trades["exit_time"])
    trades["year"] = trades["entry_time"].dt.year
    trades["month"] = trades["entry_time"].dt.month
    results[sym] = {"trades": trades, "stats": stats, "equity": eq}

# ════════════════════════════════════════════════════════════════════════════
# 1. YEAR-BY-YEAR DECOMPOSITION
# ════════════════════════════════════════════════════════════════════════════
print_section("1. YEAR-BY-YEAR DECOMPOSITION")

for sym in ["MNQ", "MES"]:
    trades = results[sym]["trades"]
    total_pnl = trades["pnl"].sum()
    print(f"\n--- {sym} ---")
    print(f"{'Year':>6}  {'Trades':>6}  {'PnL':>10}  {'PF':>6}  {'% of Total':>10}  {'Win%':>6}")
    print("-" * 56)
    for year, grp in trades.groupby("year"):
        wins = grp.loc[grp["pnl"] > 0, "pnl"]
        losses = grp.loc[grp["pnl"] <= 0, "pnl"]
        yr_pnl = grp["pnl"].sum()
        yr_pf = pf(wins, losses)
        pct = yr_pnl / total_pnl * 100 if total_pnl != 0 else 0
        wr = len(wins) / len(grp) * 100 if len(grp) > 0 else 0
        flag = " *** DOMINANT" if abs(pct) > 40 else ""
        print(f"{year:>6}  {len(grp):>6}  {yr_pnl:>10.2f}  {yr_pf:>6.2f}  {pct:>9.1f}%  {wr:>5.1f}%{flag}")
    print(f"{'TOTAL':>6}  {len(trades):>6}  {total_pnl:>10.2f}")

# ════════════════════════════════════════════════════════════════════════════
# 2. DIRECTION SPLIT
# ════════════════════════════════════════════════════════════════════════════
print_section("2. DIRECTION SPLIT")

for sym in ["MNQ", "MES"]:
    trades = results[sym]["trades"]
    print(f"\n--- {sym} ---")
    for side in ["long", "short"]:
        sub = trades[trades["side"] == side]
        if len(sub) == 0:
            print(f"  {side.upper():>5}: 0 trades")
            continue
        wins = sub.loc[sub["pnl"] > 0, "pnl"]
        losses = sub.loc[sub["pnl"] <= 0, "pnl"]
        print(f"  {side.upper():>5}: {len(sub)} trades, PnL ${sub['pnl'].sum():.2f}, "
              f"PF {pf(wins, losses):.2f}, Win% {len(wins)/len(sub)*100:.1f}%")

# ════════════════════════════════════════════════════════════════════════════
# 3. TRADE DISTRIBUTION — MONTHLY CLUSTERING & BIG WINNERS
# ════════════════════════════════════════════════════════════════════════════
print_section("3. TRADE DISTRIBUTION (monthly clustering & big winners)")

for sym in ["MNQ", "MES"]:
    trades = results[sym]["trades"]
    total_pnl = trades["pnl"].sum()
    print(f"\n--- {sym} ---")

    # Monthly distribution
    print("\nTrades by month:")
    month_counts = trades.groupby("month").size()
    for m in range(1, 13):
        cnt = month_counts.get(m, 0)
        bar = "#" * cnt
        print(f"  {m:>2}: {cnt:>3}  {bar}")

    # Top 5 individual trades as % of total PnL
    print(f"\nTop 5 trades (as % of total PnL = ${total_pnl:.2f}):")
    top5 = trades.nlargest(5, "pnl")
    for _, row in top5.iterrows():
        pct = row["pnl"] / total_pnl * 100 if total_pnl != 0 else 0
        print(f"  {str(row['entry_time'])[:10]}  PnL ${row['pnl']:>8.2f}  ({pct:>5.1f}%)")

    # Concentration: top-3 trades as % of total
    top3_pnl = trades.nlargest(3, "pnl")["pnl"].sum()
    print(f"\n  Top 3 trades = ${top3_pnl:.2f} = {top3_pnl/total_pnl*100:.1f}% of total")
    if top3_pnl / total_pnl > 0.50:
        print("  *** WARNING: >50% of PnL from top 3 trades — high concentration risk")

# ════════════════════════════════════════════════════════════════════════════
# 4. ROLLING WALK-FORWARD (3yr train / 1yr test)
# ════════════════════════════════════════════════════════════════════════════
print_section("4. ROLLING WALK-FORWARD (3yr train / 1yr test)")

# Note: This strategy has NO optimizable parameters (calendar-based entries,
# fixed FOMC dates). The walk-forward here measures out-of-sample stability,
# not parameter re-optimization. We simply compute PF in each test window.

for sym in ["MNQ", "MES"]:
    trades = results[sym]["trades"]
    print(f"\n--- {sym} ---")
    years = sorted(trades["year"].unique())
    print(f"Available years: {years}")
    print(f"\n{'Test Year':>10}  {'Train Yrs':>20}  {'Test Trades':>12}  {'Test PnL':>10}  {'Test PF':>8}  {'Train PF':>9}")
    print("-" * 78)

    for i in range(len(years)):
        test_year = years[i]
        # Train on prior 3 years (whatever is available)
        train_years = [y for y in years if y < test_year][-3:]
        if len(train_years) == 0:
            continue

        train = trades[trades["year"].isin(train_years)]
        test = trades[trades["year"] == test_year]

        if len(test) == 0:
            continue

        train_wins = train.loc[train["pnl"] > 0, "pnl"]
        train_losses = train.loc[train["pnl"] <= 0, "pnl"]
        test_wins = test.loc[test["pnl"] > 0, "pnl"]
        test_losses = test.loc[test["pnl"] <= 0, "pnl"]

        tpf = pf(test_wins, test_losses)
        trpf = pf(train_wins, train_losses)
        flag = " FAIL" if tpf < 1.0 else ""
        print(f"{test_year:>10}  {str(train_years):>20}  {len(test):>12}  "
              f"{test['pnl'].sum():>10.2f}  {tpf:>8.2f}  {trpf:>9.2f}{flag}")

# ════════════════════════════════════════════════════════════════════════════
# 5. CROSS-ASSET COMPARISON
# ════════════════════════════════════════════════════════════════════════════
print_section("5. CROSS-ASSET COMPARISON (MNQ vs MES)")

print(f"\n{'Metric':>25}  {'MNQ':>12}  {'MES':>12}")
print("-" * 55)

for metric_name, metric_fn in [
    ("Total Trades", lambda t: len(t)),
    ("Total PnL", lambda t: f"${t['pnl'].sum():.2f}"),
    ("Profit Factor", lambda t: f"{pf(t.loc[t['pnl']>0,'pnl'], t.loc[t['pnl']<=0,'pnl']):.2f}"),
    ("Win Rate %", lambda t: f"{len(t[t['pnl']>0])/len(t)*100:.1f}%" if len(t) > 0 else "N/A"),
    ("Avg Trade PnL", lambda t: f"${t['pnl'].mean():.2f}"),
    ("Median Trade PnL", lambda t: f"${t['pnl'].median():.2f}"),
    ("Max Single Win", lambda t: f"${t['pnl'].max():.2f}"),
    ("Max Single Loss", lambda t: f"${t['pnl'].min():.2f}"),
    ("Std Dev PnL", lambda t: f"${t['pnl'].std():.2f}"),
]:
    mnq_val = metric_fn(results["MNQ"]["trades"])
    mes_val = metric_fn(results["MES"]["trades"])
    print(f"{metric_name:>25}  {str(mnq_val):>12}  {str(mes_val):>12}")

# ════════════════════════════════════════════════════════════════════════════
# 6. WIN/LOSS DISTRIBUTION
# ════════════════════════════════════════════════════════════════════════════
print_section("6. WIN/LOSS DISTRIBUTION")

for sym in ["MNQ", "MES"]:
    trades = results[sym]["trades"]
    total_pnl = trades["pnl"].sum()
    wins = trades[trades["pnl"] > 0]
    losses = trades[trades["pnl"] <= 0]

    print(f"\n--- {sym} ---")
    print(f"  Winners: {len(wins)}   Losers: {len(losses)}")
    if len(wins) > 0:
        print(f"  Avg Winner:      ${wins['pnl'].mean():>8.2f}")
        print(f"  Median Winner:   ${wins['pnl'].median():>8.2f}")
        print(f"  Largest Winner:  ${wins['pnl'].max():>8.2f}")
    if len(losses) > 0:
        print(f"  Avg Loser:       ${losses['pnl'].mean():>8.2f}")
        print(f"  Median Loser:    ${losses['pnl'].median():>8.2f}")
        print(f"  Largest Loser:   ${losses['pnl'].min():>8.2f}")
    if len(wins) > 0 and len(losses) > 0:
        ratio = abs(wins['pnl'].mean() / losses['pnl'].mean())
        print(f"  Avg Win / Avg Loss Ratio: {ratio:.2f}")

    # Largest single trade as % of total PnL
    largest = trades.loc[trades["pnl"].idxmax()]
    print(f"\n  Largest single trade: ${largest['pnl']:.2f} "
          f"= {largest['pnl']/total_pnl*100:.1f}% of total PnL")
    if abs(largest["pnl"] / total_pnl) > 0.20:
        print("  *** WARNING: Single trade > 20% of total PnL")

    # PnL histogram buckets
    print("\n  PnL Distribution:")
    bins = [-np.inf, -500, -200, -100, 0, 100, 200, 500, np.inf]
    labels = ["< -500", "-500 to -200", "-200 to -100", "-100 to 0",
              "0 to 100", "100 to 200", "200 to 500", "> 500"]
    trades_copy = trades.copy()
    trades_copy["bucket"] = pd.cut(trades_copy["pnl"], bins=bins, labels=labels)
    for label in labels:
        cnt = (trades_copy["bucket"] == label).sum()
        bar = "#" * cnt
        print(f"    {label:>15}: {cnt:>3}  {bar}")

# ════════════════════════════════════════════════════════════════════════════
# 7. MAX CONSECUTIVE LOSSES AND DRAWDOWN DURATION
# ════════════════════════════════════════════════════════════════════════════
print_section("7. MAX CONSECUTIVE LOSSES & DRAWDOWN DURATION")

for sym in ["MNQ", "MES"]:
    trades = results[sym]["trades"]
    equity = results[sym]["equity"]
    print(f"\n--- {sym} ---")

    # Max consecutive losses
    is_loss = (trades["pnl"] <= 0).astype(int).values
    max_consec = 0
    current = 0
    for val in is_loss:
        if val == 1:
            current += 1
            max_consec = max(max_consec, current)
        else:
            current = 0
    print(f"  Max consecutive losses: {max_consec}")

    # Max consecutive wins
    is_win = (trades["pnl"] > 0).astype(int).values
    max_consec_w = 0
    current_w = 0
    for val in is_win:
        if val == 1:
            current_w += 1
            max_consec_w = max(max_consec_w, current_w)
        else:
            current_w = 0
    print(f"  Max consecutive wins:   {max_consec_w}")

    # Max drawdown from equity curve
    eq_vals = equity.values
    peak = eq_vals[0]
    max_dd = 0
    dd_start_idx = 0
    max_dd_start = 0
    max_dd_end = 0

    for i in range(len(eq_vals)):
        if eq_vals[i] > peak:
            peak = eq_vals[i]
            dd_start_idx = i
        dd = peak - eq_vals[i]
        if dd > max_dd:
            max_dd = dd
            max_dd_start = dd_start_idx
            max_dd_end = i

    print(f"  Max drawdown: ${max_dd:.2f}")

    # Drawdown duration in terms of trades
    # Compute trade-level equity and find longest underwater period
    cum_pnl = trades["pnl"].cumsum().values
    starting = results[sym]["stats"]["starting_capital"]
    trade_equity = starting + cum_pnl
    trade_peak = np.maximum.accumulate(trade_equity)
    underwater = trade_equity < trade_peak

    max_dur = 0
    current_dur = 0
    for uw in underwater:
        if uw:
            current_dur += 1
            max_dur = max(max_dur, current_dur)
        else:
            current_dur = 0
    print(f"  Max drawdown duration: {max_dur} trades")

    # Also in calendar days
    if len(trades) > 1:
        # Find the longest underwater stretch in calendar time
        trade_dd = trade_peak - trade_equity
        in_dd = trade_dd > 0
        max_cal_days = 0
        dd_start_time = None
        for idx in range(len(trades)):
            if in_dd.iloc[idx] if hasattr(in_dd, 'iloc') else in_dd[idx]:
                if dd_start_time is None:
                    dd_start_time = trades.iloc[idx]["entry_time"]
                dd_end_time = trades.iloc[idx]["exit_time"]
                cal_days = (dd_end_time - dd_start_time).days
                max_cal_days = max(max_cal_days, cal_days)
            else:
                dd_start_time = None
        print(f"  Max drawdown duration: ~{max_cal_days} calendar days")


# ════════════════════════════════════════════════════════════════════════════
# SUMMARY VERDICT
# ════════════════════════════════════════════════════════════════════════════
print_section("VALIDATION SUMMARY")

mnq_trades = results["MNQ"]["trades"]
mes_trades = results["MES"]["trades"]
mnq_total = mnq_trades["pnl"].sum()
mes_total = mes_trades["pnl"].sum()

mnq_pf = pf(mnq_trades.loc[mnq_trades["pnl"] > 0, "pnl"],
             mnq_trades.loc[mnq_trades["pnl"] <= 0, "pnl"])
mes_pf = pf(mes_trades.loc[mes_trades["pnl"] > 0, "pnl"],
             mes_trades.loc[mes_trades["pnl"] <= 0, "pnl"])

# Check year dominance
flags = []
for sym in ["MNQ", "MES"]:
    trades = results[sym]["trades"]
    total = trades["pnl"].sum()
    for year, grp in trades.groupby("year"):
        yr_pnl = grp["pnl"].sum()
        if total != 0 and abs(yr_pnl / total) > 0.40:
            flags.append(f"  - {sym} {year}: {yr_pnl/total*100:.1f}% of total PnL (year dominance)")

# Check top-3 concentration
for sym in ["MNQ", "MES"]:
    trades = results[sym]["trades"]
    total = trades["pnl"].sum()
    top3 = trades.nlargest(3, "pnl")["pnl"].sum()
    if total != 0 and top3 / total > 0.50:
        flags.append(f"  - {sym}: Top 3 trades = {top3/total*100:.1f}% of total PnL (concentration risk)")

# Check walk-forward failures
for sym in ["MNQ", "MES"]:
    trades = results[sym]["trades"]
    years = sorted(trades["year"].unique())
    for i in range(len(years)):
        test_year = years[i]
        train_years = [y for y in years if y < test_year][-3:]
        if len(train_years) == 0:
            continue
        test = trades[trades["year"] == test_year]
        if len(test) == 0:
            continue
        tw = test.loc[test["pnl"] > 0, "pnl"]
        tl = test.loc[test["pnl"] <= 0, "pnl"]
        if pf(tw, tl) < 1.0:
            flags.append(f"  - {sym} walk-forward FAIL in {test_year} (PF < 1.0)")

print(f"\n  MNQ: {len(mnq_trades)} trades, PF {mnq_pf:.2f}, Total PnL ${mnq_total:.2f}")
print(f"  MES: {len(mes_trades)} trades, PF {mes_pf:.2f}, Total PnL ${mes_total:.2f}")

if flags:
    print(f"\n  FLAGS ({len(flags)}):")
    for f in flags:
        print(f)
else:
    print("\n  No flags raised.")

print(f"\n{'='*70}")
print("  END OF DEEP VALIDATION")
print(f"{'='*70}\n")
