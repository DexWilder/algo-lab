"""Cycle 2026-06-12k — Daily Test 2 Stage 3: failed_daily_breakout on MNQ.

Per operator #204 A. Stages 1 + 1.5 + 2 + 3 sequential build.

Stage 2 primitive: failed_daily_breakout
  - On day T: identify if there was a breakout (close > prior-day high OR
    close < prior-day low)
  - On day T+1: confirm failure (close back inside the prior-day range)
  - Entry on day T+2 OPEN, direction OPPOSITE the original breakout
  - i.e., upside break that fails → SHORT; downside break that fails → LONG

Stage 3 test: failed_daily_breakout × MNQ × 3 exit variants
  Test variants A (3-day hold), B (5-day hold), C (daily_invalidation).
  Variant D (trailing stop) excluded from headline; only test if A/B/C show life.

Full expanded risk report (per harness §4) per pre-declared mandate.

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

from engine.multi_day_exit import (  # noqa: E402
    aggregate_to_daily, find_next_session_open_idx, find_session_open_idx,
    TradeContext, exit_fixed_n_day_hold, exit_daily_invalidation,
)
from engine.multi_day_risk_accounting import compute_full_risk_report  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402


def failed_daily_breakout_signals(daily_df: pd.DataFrame) -> pd.DataFrame:
    """Generate daily-bar failed-breakout signals.

    Returns DataFrame with columns:
      - confirm_date: date of confirmation (the failure)
      - signal: -1 (failed upside break → SHORT) or +1 (failed downside break → LONG)
      - invalidation_level: prior-day high (SHORT) or prior-day low (LONG)
    """
    daily = daily_df.copy().reset_index(drop=True)
    daily["prior_high"] = daily["high"].shift(1)
    daily["prior_low"] = daily["low"].shift(1)
    signals = []
    for i in range(2, len(daily)):
        # Day T-1 (prior to break): provides prior_high/low reference
        # Day T (the break day): close vs daily[i-1]["high"]/["low"]
        # Day i (confirmation): close back inside prior-day range (daily[i-1])
        prev_row = daily.iloc[i - 1]
        cur_row = daily.iloc[i]
        # Check if day T had an upside break (close > daily[i-2]["high"])
        if i < 2: continue
        break_prior_high = daily.iloc[i - 2]["high"]
        break_prior_low = daily.iloc[i - 2]["low"]
        # Day T = i-1; was there a break?
        upside_break_T = prev_row["close"] > break_prior_high
        downside_break_T = prev_row["close"] < break_prior_low
        # Day T+1 = i; does close come back inside the day-T-2 range?
        upside_failure = upside_break_T and cur_row["close"] < break_prior_high
        downside_failure = downside_break_T and cur_row["close"] > break_prior_low
        if upside_failure:
            signals.append({"confirm_date": cur_row["date"], "signal": -1,
                             "invalidation_level": float(break_prior_high),
                             "break_day_close": float(prev_row["close"]),
                             "confirm_day_close": float(cur_row["close"])})
        elif downside_failure:
            signals.append({"confirm_date": cur_row["date"], "signal": 1,
                             "invalidation_level": float(break_prior_low),
                             "break_day_close": float(prev_row["close"]),
                             "confirm_day_close": float(cur_row["close"])})
    return pd.DataFrame(signals)


def execute_trades(signals_df: pd.DataFrame, daily_df: pd.DataFrame,
                    df_5min: pd.DataFrame, exit_variant: str,
                    point_value: float, commission_per_side: float = 0,
                    slippage_ticks: int = 0, tick_size: float = 0.25,
                    contracts: int = 1):
    """Execute trades on signal series with given exit variant. Returns trades_df."""
    trades = []
    for _, sig in signals_df.iterrows():
        confirm_date = pd.to_datetime(sig["confirm_date"]).date()
        # Entry at NEXT-session open (day T+2)
        entry_idx = find_next_session_open_idx(df_5min, confirm_date)
        if entry_idx is None: continue
        entry_dt = pd.to_datetime(df_5min.iloc[entry_idx]["datetime"])
        entry_date = entry_dt.date()
        entry_price = float(df_5min.iloc[entry_idx]["open"])

        ctx = TradeContext(
            entry_idx=entry_idx, entry_date=entry_date,
            entry_price=entry_price, direction=int(sig["signal"]),
            daily_bars=daily_df, df_5min=df_5min,
            invalidation_level=float(sig["invalidation_level"]),
        )
        if exit_variant == "A_fixed_3_day":
            exit_idx, exit_price, exit_reason = exit_fixed_n_day_hold(ctx, n_days=3)
        elif exit_variant == "B_fixed_5_day":
            exit_idx, exit_price, exit_reason = exit_fixed_n_day_hold(ctx, n_days=5)
        elif exit_variant == "C_daily_invalidation":
            exit_idx, exit_price, exit_reason = exit_daily_invalidation(ctx, max_days=5)
        else:
            continue
        if exit_idx is None:
            continue
        exit_dt = pd.to_datetime(df_5min.iloc[exit_idx]["datetime"])
        # Cost: commission per side × 2 (round-trip) + slippage in ticks × 2
        cost = commission_per_side * 2 + slippage_ticks * tick_size * point_value * 2
        gross_pnl = (exit_price - entry_price) * sig["signal"] * contracts * point_value
        net_pnl = gross_pnl - cost
        trades.append({
            "entry_time": entry_dt, "exit_time": exit_dt,
            "entry_date": entry_date, "exit_date": exit_dt.date(),
            "direction": int(sig["signal"]),
            "entry_price": entry_price, "exit_price": exit_price,
            "entry_idx": int(entry_idx), "exit_idx": int(exit_idx),
            "pnl": net_pnl, "gross_pnl": gross_pnl, "cost": cost,
            "exit_reason": exit_reason,
            "invalidation_level": float(sig["invalidation_level"]),
        })
    return pd.DataFrame(trades)


def _metrics(trades_df):
    if trades_df.empty:
        return {"n": 0, "pf": 0, "median": 0, "net": 0, "mean": 0}
    pnl = trades_df["pnl"].values
    w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
    pf = float(w / l) if l > 0 else float("inf")
    return {"n": len(trades_df), "pf": pf,
            "median": float(np.median(pnl)),
            "net": float(pnl.sum()),
            "mean": float(np.mean(pnl))}


def temporal_split(trades_df):
    if trades_df.empty: return None
    df = trades_df.copy()
    df["entry_dt"] = pd.to_datetime(df["entry_time"])
    df["year"] = df["entry_dt"].dt.year
    per_year = []
    for y, g in df.groupby("year"):
        pnl = g["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w / l) if l > 0 else float("inf")
        per_year.append({"year": int(y), "n": int(len(g)), "pf": pf,
                         "median": float(np.median(pnl)), "net": float(pnl.sum())})
    df = df.sort_values("entry_dt").reset_index(drop=True)
    cuts = np.linspace(0, len(df), 4).astype(int)
    eras = []
    for i in range(3):
        sub = df.iloc[cuts[i]:cuts[i+1]]
        if sub.empty: continue
        pnl = sub["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w / l) if l > 0 else float("inf")
        eras.append({"era": i+1, "n": int(len(sub)), "pf": pf,
                     "median": float(np.median(pnl)), "net": float(pnl.sum())})
    nets = [y["net"] for y in per_year]
    total_net = sum(nets)
    max_yr = max(abs(n) for n in nets) / total_net * 100 if total_net > 0 else 0
    nets_arr = np.array(nets)
    instance_cv = float(nets_arr.std() / nets_arr.mean()) if nets_arr.mean() != 0 else float("inf")
    return {"yrs_pos": sum(1 for r in per_year if r["net"] > 0),
            "n_yrs": len(per_year), "era3_pf": eras[-1]["pf"] if eras else 0,
            "era3_median": eras[-1]["median"] if eras else 0,
            "max_yr_share_pct": max_yr, "instance_cv": instance_cv,
            "per_year": per_year, "eras": eras}


def _classify(m):
    n = m["n"]; pf = m["pf"]; median = m["median"]
    if n < 20: return f"KILL (n={n})"
    if median < 0 and pf >= 1.15: return "KILL (asymmetric trap)"
    if median < 0: return "KILL (median neg)"
    if pf < 1.15: return "KILL (PF<1.15)"
    if pf >= 1.20 and median > 0: return "ESCALATE"
    return "WATCH"


def run():
    print("Cycle 2026-06-12k — Daily Test 2 Stage 3: failed_daily_breakout × MNQ\n", flush=True)
    print("Per operator #204 A. Multi-day harness, expanded risk accounting.\n", flush=True)

    asset = "MNQ"
    df_5min = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    pv = cfg["point_value"]
    from engine.backtest import get_cost_params
    costs = get_cost_params(asset)
    print(f"Cost model: ${costs['commission_per_side']}/side, {costs['slippage_ticks']} tick slip, "
          f"tick size ${costs['tick_size']}, point ${pv}", flush=True)

    # Aggregate to daily bars
    print(f"\nAggregating {asset} to RTH daily bars...", flush=True)
    daily = aggregate_to_daily(df_5min)
    print(f"  Daily sessions: {len(daily)}, span {daily['date'].iloc[0]} → {daily['date'].iloc[-1]}", flush=True)

    # Generate failed_daily_breakout signals
    print(f"\nGenerating failed_daily_breakout signals...", flush=True)
    signals = failed_daily_breakout_signals(daily)
    print(f"  Total signals: {len(signals)}", flush=True)
    print(f"    Failed upside breaks (SHORT): {(signals['signal'] == -1).sum()}", flush=True)
    print(f"    Failed downside breaks (LONG): {(signals['signal'] == 1).sum()}", flush=True)

    # Test 3 variants
    results = {}
    for variant in ["A_fixed_3_day", "B_fixed_5_day", "C_daily_invalidation"]:
        print(f"\n--- Variant {variant} ---", flush=True)
        t0 = time.time()
        trades = execute_trades(
            signals, daily, df_5min, variant,
            point_value=pv,
            commission_per_side=costs["commission_per_side"],
            slippage_ticks=costs["slippage_ticks"],
            tick_size=costs["tick_size"],
        )
        m = _metrics(trades)
        verdict = _classify(m)
        elapsed = time.time() - t0
        print(f"  n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f} net=${m['net']:.0f} mean=${m['mean']:.2f} → {verdict} [{elapsed:.0f}s]", flush=True)

        # Risk report
        risk = compute_full_risk_report(trades, daily, df_5min, point_value=pv)
        if not risk.get("no_trades"):
            print(f"\n  Risk per harness §4:", flush=True)
            ptr = risk["per_trade_risk_aggregated"]
            print(f"    worst_overnight_gap_pnl:           ${ptr['worst_overnight_gap_pnl']:>8.0f}", flush=True)
            print(f"    largest_single_day_loss:           ${ptr['largest_single_day_loss']:>8.0f}", flush=True)
            print(f"    worst_close_to_open_loss:          ${ptr['worst_close_to_open_loss']:>8.0f}", flush=True)
            print(f"    worst_open_to_open_loss:           ${ptr['worst_open_to_open_loss']:>8.0f}", flush=True)
            print(f"    max_adverse_excursion:             ${ptr['max_adverse_excursion']:>8.0f}", flush=True)
            print(f"    max_cumulative_unrealized_loss:    ${ptr['max_cumulative_unrealized_loss']:>8.0f}", flush=True)
            ev = risk["event_day_exposure"]
            print(f"    NFP in hold: {ev['n_trades_with_nfp_in_hold']}/{risk['n_trades']} trades", flush=True)
            print(f"    FOMC in hold: {ev['n_trades_with_fomc_in_hold']}/{risk['n_trades']} trades ({ev['pct_trades_with_fomc_exposure']:.1f}%)", flush=True)
            hd = risk["hold_duration"]
            print(f"    Hold avg/max: {hd['avg_trading_days']:.1f}/{hd['max_trading_days']} trading days, "
                  f"{hd['avg_calendar_days']:.1f}/{hd['max_calendar_days']} calendar days", flush=True)
            print(f"    Overnight exposure: {hd['overnight_exposure_pct']:.0f}%", flush=True)
            con = risk["concentration"]
            print(f"    Top-1/3/10 trade % of net: {con['top_1_trade_pct_of_net']:.1f}% / {con['top_3_trades_pct_of_net']:.1f}% / {con['top_10_trades_pct_of_net']:.1f}%", flush=True)
            print(f"    Max-yr share: {con['max_year_share_pct']:.1f}%, instance CV: {con['instance_cv']:.2f}", flush=True)
            print(f"    Max consecutive losing trade-days: {risk['max_consecutive_losing_trade_days']}", flush=True)
            print(f"\n  PROP-FIRM compatibility:", flush=True)
            pf_compat = risk["prop_firm_compatibility"]
            print(f"    {pf_compat['note']}", flush=True)

        ts = temporal_split(trades) if not trades.empty else None
        results[variant] = {
            "metrics": m, "verdict": verdict,
            "temporal_split": ts,
            "risk_report": risk,
        }

    # Summary
    print(f"\n\n=== SUMMARY ===", flush=True)
    for variant, r in results.items():
        m = r["metrics"]; v = r["verdict"]
        print(f"  {variant}: n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f} → {v}", flush=True)

    any_pass = any("ESCALATE" in r["verdict"] for r in results.values())
    any_watch = any("WATCH" in r["verdict"] for r in results.values())
    print(f"\n  Viability: ", end="", flush=True)
    if any_pass:
        print("POSITIVE — at least one variant escalates to V1 audit. Proceed to MES port if MNQ shows life.", flush=True)
    elif any_watch:
        print("BORDERLINE — variants produce WATCH but no full escalation. Per methodology: do NOT add filters; keep as OBSERVATIONAL.", flush=True)
    else:
        print("NEGATIVE — failed_daily_breakout direct port archived. Per operator: pivot to event-conditioning or vol-regime work for existing GREENs. No rescue.", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-12k_daily_test2_failed_breakout_MNQ.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "Daily Test 2 Stage 3: failed_daily_breakout MNQ baseline per #204 A",
        "harness_reference": "docs/fql_forge/daily_test2_harness_methodology_2026-06-12.md",
        "n_total_daily_signals": len(signals),
        "results": results,
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
