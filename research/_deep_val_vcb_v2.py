"""Deep validation: vol_compression_breakout_v2.

Research-only script. Prints to stdout.
"""
import importlib.util, inspect, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from engine.backtest import run_backtest
from engine.asset_config import get_asset


STRATEGY = "vol_compression_breakout_v2"


def load_and_run(strategy_name: str, symbol: str, mode: str = "both") -> pd.DataFrame:
    cfg = get_asset(symbol)
    spec = importlib.util.spec_from_file_location(
        "strat", ROOT / f"strategies/{strategy_name}/strategy.py"
    )
    mod = importlib.util.module_from_spec(spec)
    mod.TICK_SIZE = cfg["tick_size"]
    spec.loader.exec_module(mod)

    sig = inspect.signature(mod.generate_signals)
    params = set(sig.parameters.keys())
    kwargs = {}
    if "asset" in params:
        kwargs["asset"] = symbol
    if "mode" in params:
        kwargs["mode"] = mode

    df = pd.read_csv(ROOT / f"data/processed/{symbol}_5m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"])
    signals = mod.generate_signals(df.copy(), **kwargs)
    result = run_backtest(
        df,
        signals,
        mode=mode,
        point_value=cfg["point_value"],
        tick_size=cfg["tick_size"],
        commission_per_side=cfg["commission_per_side"],
        slippage_ticks=cfg["slippage_ticks"],
    )
    trades = result["trades_df"].copy()
    return trades, result, sig


def metrics(trades: pd.DataFrame) -> dict:
    if trades is None or len(trades) == 0:
        return {"trades": 0, "pnl": 0.0, "pf": float("nan"), "wr": float("nan"),
                "avg_win": 0, "avg_loss": 0, "payoff": float("nan"),
                "median": 0, "max_dd": 0}
    pnl = trades["pnl"].sum()
    wins = trades.loc[trades["pnl"] > 0, "pnl"]
    losses = trades.loc[trades["pnl"] < 0, "pnl"]
    gp = wins.sum()
    gl = -losses.sum()
    pf = gp / gl if gl > 0 else float("inf")
    wr = len(wins) / len(trades) * 100
    avg_w = wins.mean() if len(wins) else 0
    avg_l = losses.mean() if len(losses) else 0
    payoff = (avg_w / abs(avg_l)) if avg_l != 0 else float("nan")
    eq = trades["pnl"].cumsum()
    peak = eq.cummax()
    dd = (eq - peak)
    max_dd = dd.min()
    return {
        "trades": len(trades),
        "pnl": pnl,
        "pf": pf,
        "wr": wr,
        "avg_win": avg_w,
        "avg_loss": avg_l,
        "payoff": payoff,
        "median": trades["pnl"].median(),
        "max_dd": max_dd,
    }


def fmt(m: dict) -> str:
    return (f"trades={m['trades']:>4} pnl=${m['pnl']:>10,.0f} "
            f"PF={m['pf']:>5.2f} WR={m['wr']:>5.1f}% "
            f"avgW=${m['avg_win']:>7,.0f} avgL=${m['avg_loss']:>7,.0f} "
            f"payoff={m['payoff']:>4.2f} med=${m['median']:>6,.0f} "
            f"maxDD=${m['max_dd']:>9,.0f}")


def section(title: str):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def main():
    section(f"DEEP VALIDATION: {STRATEGY}")
    print(f"Date: 2026-04-07")

    # ── Interface detection ───────────────────────────────────────────
    section("1. INTERFACE DETECTION")
    spec = importlib.util.spec_from_file_location(
        "strat", ROOT / f"strategies/{STRATEGY}/strategy.py"
    )
    mod = importlib.util.module_from_spec(spec)
    mod.TICK_SIZE = 0.25
    spec.loader.exec_module(mod)
    sig = inspect.signature(mod.generate_signals)
    print(f"  signature: generate_signals{sig}")
    print(f"  params: {list(sig.parameters.keys())}")

    # ── MNQ baseline ──────────────────────────────────────────────────
    section("2. MNQ BASELINE")
    trades_mnq, _, _ = load_and_run(STRATEGY, "MNQ")
    if "exit_time" in trades_mnq.columns:
        trades_mnq["exit_time"] = pd.to_datetime(trades_mnq["exit_time"])
    if "entry_time" in trades_mnq.columns:
        trades_mnq["entry_time"] = pd.to_datetime(trades_mnq["entry_time"])
    print(f"  columns: {list(trades_mnq.columns)}")
    m = metrics(trades_mnq)
    print(f"  {fmt(m)}")

    # Use exit_time as the trade timestamp
    time_col = "exit_time" if "exit_time" in trades_mnq.columns else "entry_time"
    trades_mnq["_ts"] = pd.to_datetime(trades_mnq[time_col])
    trades_mnq["_year"] = trades_mnq["_ts"].dt.year
    trades_mnq["_ym"] = trades_mnq["_ts"].dt.to_period("M")

    # ── Year-by-year ──────────────────────────────────────────────────
    section("3. YEAR-BY-YEAR DECOMPOSITION (MNQ)")
    total_pnl = trades_mnq["pnl"].sum()
    by_year = trades_mnq.groupby("_year")
    rows = []
    for yr, grp in by_year:
        mm = metrics(grp)
        share = grp["pnl"].sum() / total_pnl * 100 if total_pnl != 0 else 0
        rows.append((yr, mm, share))
        print(f"  {yr}: share={share:5.1f}%  {fmt(mm)}")

    max_year = max(rows, key=lambda r: r[2])
    print(f"\n  DOMINANT YEAR: {max_year[0]} with {max_year[2]:.1f}% of total PnL")

    # Year by year w/o dominant
    no_dom = trades_mnq[trades_mnq["_year"] != max_year[0]]
    mm = metrics(no_dom)
    print(f"  EX-DOMINANT-YEAR:  {fmt(mm)}")

    # ── Top-N trade concentration ─────────────────────────────────────
    section("4. TOP-N TRADE CONCENTRATION (MNQ)")
    sorted_pnl = trades_mnq["pnl"].sort_values(ascending=False).reset_index(drop=True)
    gross_pos = sorted_pnl[sorted_pnl > 0].sum()
    for n in (3, 5, 10, 20):
        top_sum = sorted_pnl.head(n).sum()
        share_total = top_sum / total_pnl * 100 if total_pnl != 0 else 0
        share_gp = top_sum / gross_pos * 100 if gross_pos != 0 else 0
        print(f"  top-{n:>2}: ${top_sum:>10,.0f}  "
              f"share-of-net={share_total:5.1f}%  share-of-gross-wins={share_gp:5.1f}%")

    # Strategy w/o top-3
    cut = trades_mnq.sort_values("pnl", ascending=False).iloc[3:]
    mm = metrics(cut)
    print(f"\n  EX-TOP-3:  {fmt(mm)}")
    cut = trades_mnq.sort_values("pnl", ascending=False).iloc[5:]
    mm = metrics(cut)
    print(f"  EX-TOP-5:  {fmt(mm)}")

    # ── Walk-forward H1/H2 ────────────────────────────────────────────
    section("5. WALK-FORWARD H1/H2 SPLIT (MNQ)")
    sorted_t = trades_mnq.sort_values("_ts").reset_index(drop=True)
    midpoint = sorted_t["_ts"].min() + (sorted_t["_ts"].max() - sorted_t["_ts"].min()) / 2
    h1 = sorted_t[sorted_t["_ts"] <= midpoint]
    h2 = sorted_t[sorted_t["_ts"] > midpoint]
    print(f"  midpoint: {midpoint}")
    print(f"  H1 ({h1['_ts'].min().date()} to {h1['_ts'].max().date()}):")
    print(f"     {fmt(metrics(h1))}")
    print(f"  H2 ({h2['_ts'].min().date()} to {h2['_ts'].max().date()}):")
    print(f"     {fmt(metrics(h2))}")

    # ── Rolling walk-forward (2y train, 1y test) ──────────────────────
    section("6. ROLLING WALK-FORWARD (2yr train / 1yr test, MNQ)")
    years = sorted(trades_mnq["_year"].unique())
    print(f"  available years: {years}")
    for i in range(len(years) - 2):
        train_yrs = years[i:i+2]
        test_yr = years[i+2]
        train = trades_mnq[trades_mnq["_year"].isin(train_yrs)]
        test = trades_mnq[trades_mnq["_year"] == test_yr]
        tr_m = metrics(train)
        te_m = metrics(test)
        print(f"  train={train_yrs} -> test={test_yr}")
        print(f"     train: {fmt(tr_m)}")
        print(f"     test : {fmt(te_m)}")

    # ── Direction split ───────────────────────────────────────────────
    section("7. DIRECTION SPLIT (MNQ)")
    if "direction" in trades_mnq.columns:
        dir_col = "direction"
    elif "side" in trades_mnq.columns:
        dir_col = "side"
    else:
        dir_col = None
    print(f"  direction column: {dir_col}")
    if dir_col:
        for d, grp in trades_mnq.groupby(dir_col):
            print(f"  {d}: {fmt(metrics(grp))}")

    # ── Cross-asset ───────────────────────────────────────────────────
    section("8. CROSS-ASSET (MES, M2K)")
    cross = {}
    for sym in ("MNQ", "MES", "M2K"):
        try:
            tr, _, _ = load_and_run(STRATEGY, sym)
            mm = metrics(tr)
            cross[sym] = mm
            print(f"  {sym}: {fmt(mm)}")
        except Exception as e:
            print(f"  {sym}: ERROR {e}")

    # ── Risk: consec losses, DD duration, max $ DD ────────────────────
    section("9. RISK: CONSEC LOSSES / DD DURATION / MAX $ DD (MNQ)")
    pnl_arr = sorted_t["pnl"].values
    max_consec_l = 0
    cur = 0
    for p in pnl_arr:
        if p < 0:
            cur += 1
            max_consec_l = max(max_consec_l, cur)
        else:
            cur = 0
    max_consec_w = 0
    cur = 0
    for p in pnl_arr:
        if p > 0:
            cur += 1
            max_consec_w = max(max_consec_w, cur)
        else:
            cur = 0

    eq = sorted_t["pnl"].cumsum().values
    peaks = np.maximum.accumulate(eq)
    dd = eq - peaks
    max_dd = dd.min()
    # DD duration in days: from peak to recovery
    times = sorted_t["_ts"].values
    in_dd = False
    peak_idx = 0
    durations = []
    cur_peak_val = -np.inf
    for i, v in enumerate(eq):
        if v >= cur_peak_val:
            cur_peak_val = v
            if in_dd:
                # recovered
                durations.append((times[peak_idx], times[i]))
                in_dd = False
            peak_idx = i
        else:
            in_dd = True
    if in_dd:
        durations.append((times[peak_idx], times[-1]))

    if durations:
        days = [(pd.Timestamp(b) - pd.Timestamp(a)).days for a, b in durations]
        max_days = max(days)
        max_idx = int(np.argmax(days))
        print(f"  max consec losses : {max_consec_l}")
        print(f"  max consec wins   : {max_consec_w}")
        print(f"  max $ drawdown    : ${max_dd:,.0f}")
        print(f"  max DD duration   : {max_days} days  "
              f"({pd.Timestamp(durations[max_idx][0]).date()} -> "
              f"{pd.Timestamp(durations[max_idx][1]).date()})")
    else:
        print(f"  max consec losses : {max_consec_l}")
        print(f"  no drawdowns")

    # ── Win/loss distribution ─────────────────────────────────────────
    section("10. WIN/LOSS DISTRIBUTION (MNQ)")
    wins = sorted_t.loc[sorted_t["pnl"] > 0, "pnl"]
    losses = sorted_t.loc[sorted_t["pnl"] < 0, "pnl"]
    scratch = sorted_t.loc[sorted_t["pnl"] == 0, "pnl"]
    print(f"  wins   : {len(wins):>4}  avg=${wins.mean():>8,.0f}  "
          f"median=${wins.median():>7,.0f}  max=${wins.max():>9,.0f}")
    print(f"  losses : {len(losses):>4}  avg=${losses.mean():>8,.0f}  "
          f"median=${losses.median():>7,.0f}  min=${losses.min():>9,.0f}")
    print(f"  scratch: {len(scratch)}")
    if len(losses) and losses.mean() != 0:
        print(f"  payoff ratio (avgW/|avgL|): {wins.mean()/abs(losses.mean()):.2f}")
    print(f"  median trade : ${sorted_t['pnl'].median():,.0f}")
    pcts = [10, 25, 50, 75, 90, 95, 99]
    for p in pcts:
        print(f"  pct {p:>2}      : ${np.percentile(sorted_t['pnl'], p):>9,.0f}")

    # ── Trade frequency ───────────────────────────────────────────────
    section("11. TRADE FREQUENCY / CLUSTERING (MNQ)")
    by_month = sorted_t.groupby("_ym").size()
    print(f"  total months covered : {len(by_month)}")
    print(f"  trades/month  mean   : {by_month.mean():.2f}")
    print(f"  trades/month  median : {by_month.median():.2f}")
    print(f"  trades/month  max    : {by_month.max()}  ({by_month.idxmax()})")
    print(f"  trades/month  min    : {by_month.min()}")
    n_zero_months = 0
    full_idx = pd.period_range(by_month.index.min(), by_month.index.max(), freq="M")
    full = by_month.reindex(full_idx, fill_value=0)
    n_zero_months = (full == 0).sum()
    print(f"  zero-trade months    : {n_zero_months} / {len(full)}")
    # top months by PnL contribution
    pnl_by_month = sorted_t.groupby("_ym")["pnl"].sum().sort_values(ascending=False)
    print(f"  top-5 PnL months:")
    for ym, v in pnl_by_month.head(5).items():
        share = v / total_pnl * 100 if total_pnl != 0 else 0
        print(f"    {ym}: ${v:>9,.0f}  ({share:5.1f}% of total)")

    # ── Verdict signals ───────────────────────────────────────────────
    section("12. VERDICT INPUTS")
    yr_shares = {yr: sh for yr, _, sh in rows}
    sorted_yr = sorted(yr_shares.items(), key=lambda x: -x[1])
    print(f"  year share distribution:")
    for yr, sh in sorted_yr:
        print(f"    {yr}: {sh:5.1f}%")
    print(f"  dominant year       : {max_year[0]} ({max_year[2]:.1f}%)")
    print(f"  ex-dominant PF      : {metrics(no_dom)['pf']:.2f}")
    print(f"  ex-top-3 PF         : {metrics(trades_mnq.sort_values('pnl', ascending=False).iloc[3:])['pf']:.2f}")
    print(f"  ex-top-5 PF         : {metrics(trades_mnq.sort_values('pnl', ascending=False).iloc[5:])['pf']:.2f}")
    print(f"  H2 PF               : {metrics(h2)['pf']:.2f}")
    print(f"  cross-asset PFs     : "
          + " ".join(f"{k}={v['pf']:.2f}" for k, v in cross.items()))


if __name__ == "__main__":
    main()
