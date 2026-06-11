"""Cycle 2026-06-11h — Overnight gap continuation/fade workhorse on MES/MNQ.

Per operator decision #159 OK E: Overnight gap is the second Option B branch
after Last-hour drift failed cleanly (4/4 KILL, no directional edge).

Hypothesis:
  Overnight gaps (prior RTH close → today RTH open) carry information.
  Continuation thesis: gap direction continues during RTH (momentum).
  Fade thesis: gap direction reverses during RTH (mean-reversion).

Mechanism (simplest, no filters first pass):
  For each RTH session:
    - Compute gap = (today RTH open price) - (prior session RTH close price)
    - Continuation: long if gap > 0, short if gap < 0
    - Fade: short if gap > 0, long if gap < 0
    - Entry: 09:35 ET bar (first bar after RTH open at 09:30)
    - Exit: hold for 12 bars (= 60 min, until 10:35 ET)
    - No magnitude threshold first pass

Matrix: 2 assets × 2 strategies (continuation, fade) × 1 hold window = 4 candidates.

Per #159 gates: positive median, PF >= 1.15 cheap-screen / >= 1.30 watch,
PASS_STRESS, max-yr <= 50%, yrs+ >= 50%, Era3 PF >= 1.0, Era3 median >= 0.

Boundaries: report-only Lane B.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def build_gap_signals(df_in, asset, strategy="continuation", hold_bars=12,
                     rth_open_time=(9, 30), rth_close_time=(16, 0)):
    """Build (signal, exit_signal, stop_price, target_price) DataFrame for
    overnight gap continuation or fade — same schema as event_window_engine.

    For each RTH session:
      - prior_close = last bar's close at or before 16:00 ET of prior session
      - today_open = first bar's open at 09:30 ET today
      - gap = today_open - prior_close
      - Continuation: long if gap > 0, short if gap < 0
      - Fade: short if gap > 0, long if gap < 0
      - Entry at 09:35 ET bar (next bar after open)
      - Exit after hold_bars
    """
    df = df_in.copy().reset_index(drop=True)
    df["dt"] = pd.to_datetime(df["datetime"])
    df["date"] = df["dt"].dt.date
    df["hour"] = df["dt"].dt.hour
    df["minute"] = df["dt"].dt.minute

    open_bars = df[(df["hour"] == rth_open_time[0]) & (df["minute"] == rth_open_time[1])].copy()

    n = len(df)
    signal = np.zeros(n, dtype=int)
    exit_signal = np.zeros(n, dtype=int)

    dates_with_open = sorted(open_bars["date"].unique())
    n_trades_planned = 0
    n_no_prior_close = 0
    n_no_signal = 0

    for i, d in enumerate(dates_with_open):
        if i == 0:
            n_no_prior_close += 1
            continue
        prev_date = dates_with_open[i - 1]
        prev_session = df[(df["date"] == prev_date) & ((df["hour"] < rth_close_time[0]) |
                          ((df["hour"] == rth_close_time[0]) & (df["minute"] <= rth_close_time[1])))]
        prev_session = prev_session[prev_session["hour"] >= rth_open_time[0]]
        if len(prev_session) == 0:
            n_no_prior_close += 1
            continue
        prior_close = prev_session["close"].iloc[-1]

        today_open_bar = open_bars[open_bars["date"] == d]
        if len(today_open_bar) == 0:
            continue
        today_open = today_open_bar["open"].iloc[0]
        gap = today_open - prior_close
        if gap == 0:
            n_no_signal += 1
            continue

        if strategy == "continuation":
            entry_direction = 1 if gap > 0 else -1
        elif strategy == "fade":
            entry_direction = -1 if gap > 0 else 1
        else:
            raise ValueError(f"unknown strategy {strategy}")

        open_bar_idx = today_open_bar.index[0]
        entry_idx = open_bar_idx + 1
        if entry_idx >= n:
            continue
        exit_idx = entry_idx + hold_bars
        if exit_idx >= n:
            continue

        signal[entry_idx] = entry_direction
        exit_signal[exit_idx] = 1
        n_trades_planned += 1

    out = pd.DataFrame({
        "signal": signal,
        "exit_signal": exit_signal,
        "stop_price": np.full(n, np.nan),
        "target_price": np.full(n, np.nan),
    })
    out.attrs["stats"] = {
        "n_trades_planned": n_trades_planned,
        "n_no_prior_close": n_no_prior_close,
        "n_no_signal": n_no_signal,
        "n_dates_with_open": len(dates_with_open),
    }
    return out


def _classify(m):
    n = m.get("n", 0); pf = m.get("pf", 0); median = m.get("median", 0)
    if n < 100: return f"KILL (n={n}, workhorse min 100)"
    if median < 0 and pf >= 1.15: return "KILL (asymmetric trap)"
    if median < 0: return "KILL (median neg)"
    if pf < 1.15: return "KILL (PF<1.15)"
    if pf >= 1.30 and median > 0: return "WATCH_FOR_DEEP_SCREEN"
    return "WATCH"


def _run(asset, strategy, hold_bars=12, commission_mult=1.0, slippage_mult=1.0, label=""):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    costs = get_cost_params(asset)
    sigs = build_gap_signals(df, asset, strategy=strategy, hold_bars=hold_bars)
    res = run_backtest(
        df, sigs, mode="both", point_value=cfg["point_value"], symbol=asset,
        commission_per_side=costs["commission_per_side"] * commission_mult,
        slippage_ticks=int(np.ceil(costs["slippage_ticks"] * slippage_mult)),
        tick_size=costs["tick_size"],
    )
    return _metrics(res["trades_df"], label, costs=res["stats"]["costs"]), res["trades_df"], sigs.attrs["stats"]


def stress_screen(asset, strategy, hold_bars, label):
    rows = []
    for stress_label, cm, sm in [
        ("baseline (1x)", 1.0, 1.0),
        ("1.5x cost + 1 tick slip", 1.5, 2.0),
        ("2x cost + 1 tick slip", 2.0, 2.0),
        ("2x cost + 2 ticks slip", 2.0, 3.0),
        ("4x cost + 2 ticks slip", 4.0, 3.0),
    ]:
        m, _, _ = _run(asset, strategy, hold_bars=hold_bars,
                       commission_mult=cm, slippage_mult=sm,
                       label=f"{label}-{stress_label}")
        rows.append({"stress": stress_label, "n": int(m["n"]), "pf": float(m["pf"]),
                     "median": float(m["median"])})
    moderate = next(r for r in rows if r["stress"] == "2x cost + 2 ticks slip")
    extreme = next(r for r in rows if r["stress"] == "4x cost + 2 ticks slip")
    if moderate["median"] <= 0: return {"rows": rows, "verdict": "FAIL_STRESS"}
    if moderate["median"] < 0.5: return {"rows": rows, "verdict": "KNIFE_EDGE"}
    if extreme["median"] <= 0: return {"rows": rows, "verdict": "KNIFE_EDGE (4x)"}
    return {"rows": rows, "verdict": "PASS_STRESS"}


def run():
    print("Cycle 2026-06-11h — Overnight gap workhorse on MES/MNQ (#159 fallback)", flush=True)
    print("Mechanism: gap = today_open - prior_close, enter 09:35 ET, hold 60min.\n", flush=True)
    t_start = time.time()
    results = []
    for asset in ["MES", "MNQ"]:
        for strategy in ["continuation", "fade"]:
            label = f"GAP-{asset}-{strategy[:4].capitalize()}-60m"
            t0 = time.time()
            try:
                m, trades, sig_stats = _run(asset, strategy, hold_bars=12, label=label)
                v = _classify(m)
                stress = None
                if "WATCH" in v:
                    stress = stress_screen(asset, strategy, 12, label)
            except Exception as e:
                print(f"  {label}: ERROR {e}", flush=True)
                import traceback; traceback.print_exc()
                results.append({"label": label, "error": str(e)})
                continue
            elapsed = time.time() - t0
            stress_str = f" stress={stress['verdict']}" if stress else ""
            print(
                f"  {label:30s}: n={m['n']:5d} PF={m['pf']:.3f} "
                f"median=${m['median']:6.2f} → {v}{stress_str} "
                f"[planned={sig_stats['n_trades_planned']}] [{elapsed:.0f}s]",
                flush=True
            )
            results.append({
                "label": label, "asset": asset, "strategy": strategy,
                "hold_bars": 12,
                "metrics": {k: m.get(k) for k in ("n", "pf", "median", "net", "max_dd")},
                "verdict": v, "stress": stress,
                "signal_stats": sig_stats,
            })
    print(f"\nTotal: {time.time() - t_start:.0f}s", flush=True)

    paper, observational, kill = [], [], []
    for r in results:
        if "error" in r: continue
        v = r["verdict"]; s = r.get("stress")
        if "KILL" in v: kill.append(r)
        elif "WATCH_FOR_DEEP_SCREEN" in v:
            if s and s["verdict"] == "PASS_STRESS": paper.append(r)
            else: observational.append(r)
        elif "WATCH" in v: observational.append(r)
    print(f"\nTier: PAPER_PACKET_TIER={len(paper)} OBSERVATIONAL={len(observational)} KILL={len(kill)}", flush=True)
    if paper:
        print("\nPAPER_PACKET tier — deep-screen + family review required:")
        for r in paper:
            m = r["metrics"]
            print(f"  {r['label']}: PF={m['pf']:.3f} median=${m['median']:.2f}", flush=True)
    if observational:
        print("\nOBSERVATIONAL tier:")
        for r in observational:
            m = r["metrics"]
            print(f"  {r['label']}: PF={m['pf']:.3f} median=${m['median']:.2f}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-11h_overnight_gap.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "Overnight gap continuation/fade workhorse on MES/MNQ (#159 Option B fallback)",
        "mechanism": "gap = today_open - prior_close, enter 09:35 ET, hold 60min, no threshold",
        "tier": {"PAPER_PACKET_TIER": len(paper), "OBSERVATIONAL": len(observational), "KILL": len(kill)},
        "results": results,
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
