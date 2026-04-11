"""Deep validation: ema_trend_rider (Tier-A thinnest edge, PF 1.08).

Research only. Prints to stdout.
"""
import importlib.util
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from engine.backtest import run_backtest
from engine.asset_config import get_asset


STRATEGY_NAME = "ema_trend_rider"
PRIMARY = "MNQ"
ASSETS = ["MNQ", "MES", "MGC", "M2K", "MCL", "ZN"]


def load_strategy(symbol):
    cfg = get_asset(symbol)
    spec = importlib.util.spec_from_file_location(
        f"strat_{symbol}", ROOT / f"strategies/{STRATEGY_NAME}/strategy.py"
    )
    mod = importlib.util.module_from_spec(spec)
    mod.TICK_SIZE = cfg["tick_size"]
    spec.loader.exec_module(mod)
    return mod, cfg


def run(symbol, mode="both", slip_mult=1.0, df=None, signals=None):
    mod, cfg = load_strategy(symbol)
    sig = inspect.signature(mod.generate_signals)
    params = set(sig.parameters.keys())
    kwargs = {}
    if "asset" in params:
        kwargs["asset"] = symbol
    if "mode" in params:
        kwargs["mode"] = mode

    if df is None:
        df = pd.read_csv(ROOT / f"data/processed/{symbol}_5m.csv")
        df["datetime"] = pd.to_datetime(df["datetime"])
    if signals is None:
        signals = mod.generate_signals(df.copy(), **kwargs)
    slippage = cfg["slippage_ticks"] * slip_mult
    result = run_backtest(
        df, signals, mode=mode,
        point_value=cfg["point_value"],
        tick_size=cfg["tick_size"],
        commission_per_side=cfg["commission_per_side"],
        slippage_ticks=slippage,
    )
    return result, df, signals, cfg


def metrics(trades):
    if len(trades) == 0:
        return dict(n=0, pf=np.nan, win_rate=np.nan, total_pnl=0,
                    avg_win=np.nan, avg_loss=np.nan, payoff=np.nan,
                    median=np.nan, expectancy=np.nan)
    pnl = trades["pnl"].values
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gp = wins.sum()
    gl = -losses.sum()
    pf = gp / gl if gl > 0 else np.inf
    return dict(
        n=len(trades),
        pf=pf,
        win_rate=len(wins) / len(trades),
        total_pnl=pnl.sum(),
        avg_win=wins.mean() if len(wins) else np.nan,
        avg_loss=losses.mean() if len(losses) else np.nan,
        payoff=(wins.mean() / -losses.mean()) if len(wins) and len(losses) else np.nan,
        median=np.median(pnl),
        expectancy=pnl.mean(),
    )


def fmt(m):
    return (f"n={m['n']:5d}  PF={m['pf']:.3f}  WR={m['win_rate']*100:5.1f}%  "
            f"PnL=${m['total_pnl']:>10,.0f}  expct=${m['expectancy']:>7.2f}")


def header(s):
    print("\n" + "=" * 78)
    print(s)
    print("=" * 78)


def main():
    header(f"DEEP VALIDATION: {STRATEGY_NAME}  (primary={PRIMARY})")
    sig = inspect.signature(load_strategy(PRIMARY)[0].generate_signals)
    print(f"Strategy generate_signals signature: {sig}")

    # ── Baseline on MNQ ────────────────────────────────────────────────
    header("1. BASELINE on MNQ")
    res, df, signals, cfg = run(PRIMARY)
    trades = res["trades_df"].copy()
    trades["entry_time"] = pd.to_datetime(trades["entry_time"])
    trades["exit_time"] = pd.to_datetime(trades["exit_time"])
    base = metrics(trades)
    print(fmt(base))
    print(f"Costs: {res['stats']['costs']}")

    # ── 1. Year-by-year ─────────────────────────────────────────────────
    header("1. YEAR-BY-YEAR DECOMPOSITION (MNQ)")
    trades["year"] = trades["entry_time"].dt.year
    year_rows = []
    for y, g in trades.groupby("year"):
        m = metrics(g)
        year_rows.append((y, m))
        print(f"  {y}:  {fmt(m)}")
    year_pnls = [m["total_pnl"] for _, m in year_rows]
    pos_years = sum(1 for p in year_pnls if p > 0)
    neg_years = sum(1 for p in year_pnls if p < 0)
    print(f"\n  Positive years: {pos_years}/{len(year_pnls)}   Negative: {neg_years}")
    if year_pnls:
        max_y = max(year_rows, key=lambda r: r[1]["total_pnl"])
        min_y = min(year_rows, key=lambda r: r[1]["total_pnl"])
        total = sum(year_pnls)
        if total > 0:
            print(f"  Max year: {max_y[0]} (${max_y[1]['total_pnl']:,.0f}) = {max_y[1]['total_pnl']/total*100:.1f}% of total")
        print(f"  Worst year: {min_y[0]} (${min_y[1]['total_pnl']:,.0f})")

    # ── 2. Trade concentration ──────────────────────────────────────────
    header("2. TRADE CONCENTRATION (MNQ)")
    pnl_sorted = trades["pnl"].sort_values(ascending=False).values
    total_pnl = pnl_sorted.sum()
    gross_profit = pnl_sorted[pnl_sorted > 0].sum()
    for k in (3, 5, 10, 25, 50):
        if len(pnl_sorted) >= k:
            top = pnl_sorted[:k].sum()
            print(f"  Top-{k:>2} trades: ${top:,.0f}  "
                  f"= {top/total_pnl*100:6.1f}% of net  "
                  f"= {top/gross_profit*100:6.1f}% of gross profit")
    # Worst trades
    bot = pnl_sorted[-5:][::-1]
    print(f"  Worst 5 trades: {[f'${x:,.0f}' for x in bot]}")
    print(f"  Best  5 trades: {[f'${x:,.0f}' for x in pnl_sorted[:5]]}")

    # PF without top-K
    for k in (3, 5, 10):
        rest = pnl_sorted[k:]
        gp = rest[rest > 0].sum()
        gl = -rest[rest < 0].sum()
        pf_x = gp / gl if gl > 0 else np.inf
        print(f"  PF without top-{k:>2}: {pf_x:.3f}  (net=${rest.sum():,.0f})")

    # ── 3. Walk-forward H1/H2 ───────────────────────────────────────────
    header("3. WALK-FORWARD H1/H2 SPLIT (MNQ)")
    trades_sorted = trades.sort_values("entry_time").reset_index(drop=True)
    mid = len(trades_sorted) // 2
    h1 = trades_sorted.iloc[:mid]
    h2 = trades_sorted.iloc[mid:]
    print(f"  H1 ({h1['entry_time'].min().date()} -> {h1['entry_time'].max().date()}):")
    print(f"     {fmt(metrics(h1))}")
    print(f"  H2 ({h2['entry_time'].min().date()} -> {h2['entry_time'].max().date()}):")
    print(f"     {fmt(metrics(h2))}")

    # ── 4. Rolling walk-forward 2yr train / 1yr test ───────────────────
    header("4. ROLLING WALK-FORWARD (2yr train / 1yr test) (MNQ)")
    years = sorted(trades["year"].unique())
    print(f"  Years available: {years}")
    print(f"  Note: backtest uses static params, so 'train' is informational only.")
    rows = []
    for i in range(len(years) - 2):
        train_yrs = years[i:i+2]
        test_yr = years[i+2]
        train = trades[trades["year"].isin(train_yrs)]
        test = trades[trades["year"] == test_yr]
        tm = metrics(train)
        sm = metrics(test)
        rows.append((train_yrs, test_yr, tm, sm))
        print(f"  Train {train_yrs} -> Test {test_yr}:")
        print(f"     train: {fmt(tm)}")
        print(f"     test : {fmt(sm)}")
    pos_oos = sum(1 for *_, sm in rows if sm["total_pnl"] > 0)
    print(f"\n  OOS positive windows: {pos_oos}/{len(rows)}")

    # ── 5. Direction split ─────────────────────────────────────────────
    header("5. DIRECTION SPLIT (long vs short, MNQ)")
    longs = trades[trades["side"] == "long"]
    shorts = trades[trades["side"] == "short"]
    print(f"  LONGS : {fmt(metrics(longs))}")
    print(f"  SHORTS: {fmt(metrics(shorts))}")

    # Re-run via mode= to confirm
    res_l, *_ = run(PRIMARY, mode="long")
    res_s, *_ = run(PRIMARY, mode="short")
    print(f"  --- via mode= ---")
    print(f"  long mode : {fmt(metrics(res_l['trades_df']))}")
    print(f"  short mode: {fmt(metrics(res_s['trades_df']))}")

    # ── 6. Cross-asset ─────────────────────────────────────────────────
    header("6. CROSS-ASSET (all 6 assets)")
    cross_results = {}
    for sym in ASSETS:
        try:
            r, _, _, _ = run(sym)
            t = r["trades_df"]
            m = metrics(t)
            cross_results[sym] = m
            print(f"  {sym:5s}: {fmt(m)}")
        except Exception as e:
            print(f"  {sym:5s}: ERROR {e}")
    pos_assets = sum(1 for m in cross_results.values() if m["pf"] > 1.0)
    pf11 = sum(1 for m in cross_results.values() if m["pf"] >= 1.1)
    print(f"\n  Profitable (PF>1.0): {pos_assets}/{len(cross_results)}")
    print(f"  PF >= 1.10:           {pf11}/{len(cross_results)}")

    # ── 7. Drawdown / consecutive losses ───────────────────────────────
    header("7. DRAWDOWN / CONSECUTIVE LOSSES (MNQ)")
    eq = res["equity_curve"]
    dt_idx = pd.to_datetime(df["datetime"].values)
    eq_s = pd.Series(eq.values, index=dt_idx)
    running_max = eq_s.cummax()
    dd = eq_s - running_max
    max_dd = dd.min()
    max_dd_idx = dd.idxmin()
    peak_idx = eq_s.loc[:max_dd_idx].idxmax()
    # Recovery
    after = eq_s.loc[max_dd_idx:]
    recovered = after[after >= running_max.loc[max_dd_idx]]
    if len(recovered) > 0:
        recovery_idx = recovered.index[0]
        dd_days = (recovery_idx - peak_idx).days
        recovered_msg = f"recovered {recovery_idx.date()} ({dd_days} days peak->recover)"
    else:
        dd_days = (eq_s.index[-1] - peak_idx).days
        recovered_msg = f"NOT recovered as of {eq_s.index[-1].date()} ({dd_days} days)"
    print(f"  Max $ drawdown: ${max_dd:,.0f}")
    print(f"  Peak: {peak_idx.date()}  Trough: {max_dd_idx.date()}")
    print(f"  {recovered_msg}")

    # Longest underwater duration (any drawdown)
    underwater = (dd < 0).astype(int)
    # Simple longest run
    max_run = 0
    cur = None
    longest_start = None
    longest_end = None
    cur_start = None
    for ts, val in zip(eq_s.index, underwater.values):
        if val == 1:
            if cur_start is None:
                cur_start = ts
            run_days = (ts - cur_start).days
            if run_days > max_run:
                max_run = run_days
                longest_start = cur_start
                longest_end = ts
        else:
            cur_start = None
    print(f"  Longest underwater stretch: {max_run} days ({longest_start} -> {longest_end})")

    # Consecutive losses
    pnl_seq = trades_sorted["pnl"].values
    max_consec_loss = 0
    max_consec_win = 0
    cur_l = cur_w = 0
    for p in pnl_seq:
        if p < 0:
            cur_l += 1
            cur_w = 0
            max_consec_loss = max(max_consec_loss, cur_l)
        elif p > 0:
            cur_w += 1
            cur_l = 0
            max_consec_win = max(max_consec_win, cur_w)
    print(f"  Max consecutive losses: {max_consec_loss}")
    print(f"  Max consecutive wins:   {max_consec_win}")

    # ── 8. Win/loss distribution ───────────────────────────────────────
    header("8. WIN/LOSS DISTRIBUTION (MNQ)")
    pnl = trades["pnl"].values
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    print(f"  N trades:    {len(pnl)}")
    print(f"  Wins / Losses / Scratch: {len(wins)} / {len(losses)} / {(pnl==0).sum()}")
    print(f"  Win rate:    {len(wins)/len(pnl)*100:.2f}%")
    print(f"  Avg winner:  ${wins.mean():.2f}   median ${np.median(wins):.2f}")
    print(f"  Avg loser:   ${losses.mean():.2f}   median ${np.median(losses):.2f}")
    print(f"  Payoff ratio (avg W / avg L): {wins.mean() / -losses.mean():.3f}")
    print(f"  Median trade PnL: ${np.median(pnl):.2f}")
    print(f"  Mean expectancy : ${pnl.mean():.2f}")
    print(f"  Std deviation   : ${pnl.std():.2f}")
    print(f"  Sharpe-of-trades: {pnl.mean() / pnl.std():.4f}")
    print(f"  Largest winner  : ${wins.max():.2f}")
    print(f"  Largest loser   : ${losses.min():.2f}")

    # ── 9. Trade frequency ─────────────────────────────────────────────
    header("9. TRADE FREQUENCY (MNQ)")
    span_days = (trades["entry_time"].max() - trades["entry_time"].min()).days
    span_months = span_days / 30.44
    span_years = span_days / 365.25
    print(f"  Span: {trades['entry_time'].min().date()} -> {trades['entry_time'].max().date()}")
    print(f"        {span_days} days = {span_years:.2f} years = {span_months:.1f} months")
    print(f"  Trades/month: {len(trades)/span_months:.2f}")
    print(f"  Trades/year:  {len(trades)/span_years:.1f}")
    # Per-year trade counts
    print("  Trades per calendar year:")
    for y, g in trades.groupby("year"):
        print(f"     {y}: {len(g)}")

    # ── 10. Friction sensitivity ───────────────────────────────────────
    header("10. FRICTION SENSITIVITY (MNQ)")
    base_costs = res["stats"]["costs"]
    print(f"  Baseline friction:  commission=${base_costs['total_commission']:,.0f}  "
          f"slippage=${base_costs['total_slippage']:,.0f}  "
          f"total=${base_costs['total_friction']:,.0f}")
    print(f"  Baseline net PnL :  ${res['stats']['total_pnl']:,.0f}")
    print(f"  Edge after friction = net PnL")
    print(f"  Gross PnL (PnL+friction) ~ ${res['stats']['total_pnl'] + base_costs['total_friction']:,.0f}")
    friction_pct = base_costs['total_friction'] / (res['stats']['total_pnl'] + base_costs['total_friction']) * 100 if (res['stats']['total_pnl'] + base_costs['total_friction']) > 0 else float('nan')
    print(f"  Friction eats {friction_pct:.1f}% of gross profit")

    print("\n  --- Slippage stress tests ---")
    for mult, label in [(0.5, "0.5x"), (1.0, "1.0x"), (1.25, "1.25x"),
                        (1.5, "1.5x"), (2.0, "2.0x"), (3.0, "3.0x")]:
        r, *_ = run(PRIMARY, slip_mult=mult)
        m = metrics(r["trades_df"])
        c = r["stats"]["costs"]
        print(f"  slip={label:5s} (ticks={c['slippage_ticks']:.2f}): "
              f"PF={m['pf']:.3f}  net=${m['total_pnl']:>9,.0f}  "
              f"friction=${c['total_friction']:,.0f}")

    # ── Summary ─────────────────────────────────────────────────────────
    header("VERDICT SUMMARY")
    print(f"  Baseline MNQ: PF={base['pf']:.3f}  n={base['n']}  net=${base['total_pnl']:,.0f}")
    print(f"  Avg trade:    ${base['expectancy']:.2f}")
    print(f"  Friction/trade ~ ${base_costs['total_friction']/base['n']:.2f}")
    print(f"  Per-trade edge as multiple of friction: "
          f"{base['expectancy'] / (base_costs['total_friction']/base['n']):.3f}x")


if __name__ == "__main__":
    main()
