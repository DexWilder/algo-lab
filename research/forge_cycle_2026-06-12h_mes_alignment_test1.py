"""Cycle 2026-06-12h — Test 1: mes_alignment filter on WH-MNQ-stop_run_reversal.

Per operator #196 A: cross-asset methodology Test 1, strict pre-declared
success criteria.

Filter rule (mes_alignment):
  - For MNQ LONG signals: require MES close > MES EMA20 at same bar
  - For MNQ SHORT signals: require MES close < MES EMA20 at same bar
  - Otherwise: filter rejects entry

Compare to baseline stop_run × ema_slope × profit_ladder.

Pre-declared success criteria (must meet ALL):
  - PF improvement >= +0.10 (baseline 1.477 → target >= 1.577)
  - Trade count reduction <= 50% (baseline 1414 → minimum 707)
  - Era 3 PF stable or improving (baseline 1.554)
  - Stress (2x+2t) PF stable or improving (baseline 1.404)
  - Single-parameter filter (EMA20 fixed; no sweep)

Anti-curve-fit: if any criterion fails, archive immediately. No tuning.

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

from research.crossbreeding.crossbreeding_engine import (  # noqa: E402
    compute_features, generate_crossbred_signals,
    entry_stop_run_reversal, exit_profit_ladder, filter_ema_slope,
)
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def compute_mes_alignment(mnq_df, mes_df, ema_window=20):
    """Compute mes_above_ema20 boolean aligned to MNQ timestamps."""
    mes = mes_df.copy()
    mes["dt"] = pd.to_datetime(mes["datetime"])
    mes["ema"] = mes["close"].ewm(span=ema_window, adjust=False).mean()
    mes["above_ema"] = (mes["close"] > mes["ema"]).astype(int)
    mes_idx = mes.set_index("dt")["above_ema"]
    mnq = mnq_df.copy()
    mnq["dt"] = pd.to_datetime(mnq["datetime"])
    # Reindex MES to MNQ timestamps; use forward-fill within reasonable window
    aligned = mes_idx.reindex(mnq["dt"]).ffill(limit=1).fillna(0).astype(int).values
    return aligned


def generate_signals_with_mes_filter(mnq_df, mes_above_ema20_arr):
    """Generate signals using stop_run_reversal entry + mes_alignment filter + PL exit.

    Mirrors the per-bar loop from generate_crossbred_signals.
    """
    f = compute_features(mnq_df)
    n = f["n"]
    signals = np.zeros(n, dtype=int)
    exits = np.zeros(n, dtype=int)
    stops = np.full(n, np.nan)
    targets = np.full(n, np.nan)
    params = {}

    state = {
        "position": 0, "entry_price": 0.0, "initial_risk": 0.0,
        "trailing_stop": 0.0, "target_price": 0.0,
        "highest": 0.0, "lowest": 0.0, "bars_in_trade": 0,
        "long_traded_today": False, "short_traded_today": False,
        "current_date": None,
    }

    for i in range(1, n):
        bar_date = f["dates"][i]
        if bar_date != state["current_date"]:
            if state["position"] != 0:
                exits[i] = 1 if state["position"] == 1 else -1
                state["position"] = 0
            state["current_date"] = bar_date
            state["long_traded_today"] = False
            state["short_traded_today"] = False

        if not f["in_session"][i]:
            continue
        if np.isnan(f["atr"][i]) or f["atr"][i] == 0:
            continue

        if state["position"] != 0 and f["flatten_time"][i]:
            exits[i] = 1 if state["position"] == 1 else -1
            state["position"] = 0
            continue

        if state["position"] != 0:
            state["bars_in_trade"] += 1
            exit_sig = exit_profit_ladder(f, i, state, params)
            if exit_sig != 0:
                exits[i] = exit_sig
                state["position"] = 0
                continue

        if state["position"] == 0 and f["entry_ok"][i]:
            signal, stop, target = entry_stop_run_reversal(f, i, state, params)
            # mes_alignment FILTER (replaces ema_slope):
            if signal != 0:
                mes_up = bool(mes_above_ema20_arr[i])
                if signal == 1 and not mes_up:
                    signal = 0
                elif signal == -1 and mes_up:
                    signal = 0
            if signal != 0:
                signals[i] = signal
                stops[i] = stop
                targets[i] = target
                state["position"] = signal
                state["entry_price"] = f["close"][i]
                state["initial_risk"] = abs(f["close"][i] - stop)
                state["trailing_stop"] = stop
                state["target_price"] = target
                state["highest"] = f["high"][i]
                state["lowest"] = f["low"][i]
                state["bars_in_trade"] = 0
                if signal == 1:
                    state["long_traded_today"] = True
                else:
                    state["short_traded_today"] = True

    df = mnq_df.copy()
    df["signal"] = signals
    df["exit_signal"] = exits
    df["stop_price"] = stops
    df["target_price"] = targets
    return df


def _run_baseline_or_filtered(filtered_signals_df, asset, cost_mult=1.0, slip_mult=1.0, label=""):
    cfg = ASSETS[asset]; costs = get_cost_params(asset)
    res = run_backtest(filtered_signals_df, filtered_signals_df, mode="both",
                       point_value=cfg["point_value"], symbol=asset,
                       commission_per_side=costs["commission_per_side"] * cost_mult,
                       slippage_ticks=int(np.ceil(costs["slippage_ticks"] * slip_mult)),
                       tick_size=costs["tick_size"])
    return _metrics(res["trades_df"], label, costs=res["stats"]["costs"]), res["trades_df"]


def _run_engine(asset, entry, label, cost_mult=1.0, slip_mult=1.0):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]; costs = get_cost_params(asset)
    sigs = generate_crossbred_signals(df, entry_name=entry, exit_name="profit_ladder",
                                       filter_name="ema_slope", params={})
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol=asset,
                       commission_per_side=costs["commission_per_side"] * cost_mult,
                       slippage_ticks=int(np.ceil(costs["slippage_ticks"] * slip_mult)),
                       tick_size=costs["tick_size"])
    return _metrics(res["trades_df"], label, costs=res["stats"]["costs"]), res["trades_df"]


def temporal_split(trades):
    if trades.empty: return None
    df = trades.copy()
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
    return {"yrs_pos": sum(1 for r in per_year if r["net"] > 0),
            "n_yrs": len(per_year),
            "era3_pf": eras[-1]["pf"] if eras else float("nan"),
            "era3_median": eras[-1]["median"] if eras else float("nan"),
            "per_year": per_year, "eras": eras}


def run():
    print("Cycle 2026-06-12h — TEST 1: mes_alignment filter on WH-MNQ-stop_run_reversal\n", flush=True)
    print("Per operator #196 A. Pre-declared success criteria, no curve-fit discretion.\n", flush=True)
    t_start = time.time()

    # === BASELINE: stop_run × ema_slope × profit_ladder ===
    print("--- BASELINE: stop_run × ema_slope × profit_ladder ---", flush=True)
    m_base, t_base = _run_engine("MNQ", "stop_run_reversal", "baseline")
    m_base_stress, _ = _run_engine("MNQ", "stop_run_reversal", "baseline-stress",
                                     cost_mult=2.0, slip_mult=3.0)
    ts_base = temporal_split(t_base)
    print(f"  n={m_base['n']} PF={m_base['pf']:.3f} median=${m_base['median']:.2f}", flush=True)
    print(f"  Era3 PF: {ts_base['era3_pf']:.3f}", flush=True)
    print(f"  Stress PF: {m_base_stress['pf']:.3f}, median ${m_base_stress['median']:.2f}", flush=True)

    # === FILTERED: stop_run × mes_alignment × profit_ladder ===
    print(f"\n--- FILTERED: stop_run × mes_alignment × profit_ladder ---", flush=True)
    mnq_df = pd.read_csv(ROOT / "data" / "processed" / "MNQ_5m.csv")
    mes_df = pd.read_csv(ROOT / "data" / "processed" / "MES_5m.csv")
    mes_arr = compute_mes_alignment(mnq_df, mes_df, ema_window=20)
    print(f"  MES alignment array length: {len(mes_arr)}, sum (bars MES above EMA): {int(mes_arr.sum())}", flush=True)

    filtered_sigs = generate_signals_with_mes_filter(mnq_df, mes_arr)

    # backtest filtered
    cfg = ASSETS["MNQ"]; costs = get_cost_params("MNQ")
    res = run_backtest(mnq_df, filtered_sigs, mode="both", point_value=cfg["point_value"],
                       symbol="MNQ", commission_per_side=costs["commission_per_side"],
                       slippage_ticks=costs["slippage_ticks"], tick_size=costs["tick_size"])
    m_filt = _metrics(res["trades_df"], "filtered", costs=res["stats"]["costs"])
    t_filt = res["trades_df"]
    # stress
    res_s = run_backtest(mnq_df, filtered_sigs, mode="both", point_value=cfg["point_value"],
                         symbol="MNQ",
                         commission_per_side=costs["commission_per_side"] * 2.0,
                         slippage_ticks=int(np.ceil(costs["slippage_ticks"] * 3.0)),
                         tick_size=costs["tick_size"])
    m_filt_stress = _metrics(res_s["trades_df"], "filtered-stress", costs=res_s["stats"]["costs"])
    ts_filt = temporal_split(t_filt)
    print(f"  n={m_filt['n']} PF={m_filt['pf']:.3f} median=${m_filt['median']:.2f}", flush=True)
    print(f"  Era3 PF: {ts_filt['era3_pf']:.3f}", flush=True)
    print(f"  Stress PF: {m_filt_stress['pf']:.3f}, median ${m_filt_stress['median']:.2f}", flush=True)

    # === EVALUATE pre-declared success criteria ===
    pf_delta = float(m_filt["pf"]) - float(m_base["pf"])
    trade_reduction_pct = (1 - float(m_filt["n"]) / float(m_base["n"])) * 100 if m_base["n"] > 0 else 100
    era3_delta = ts_filt["era3_pf"] - ts_base["era3_pf"]
    stress_pf_delta = float(m_filt_stress["pf"]) - float(m_base_stress["pf"])

    print(f"\n=== Pre-declared success criteria ===", flush=True)
    crit_pf = pf_delta >= 0.10
    crit_trade = trade_reduction_pct <= 50.0
    crit_era3 = era3_delta >= 0
    crit_stress = stress_pf_delta >= 0
    print(f"  PF improvement >= +0.10:        baseline {m_base['pf']:.3f} → filtered {m_filt['pf']:.3f} (Δ {pf_delta:+.3f}) — {'PASS' if crit_pf else 'FAIL'}", flush=True)
    print(f"  Trade reduction <= 50%:         baseline {m_base['n']} → filtered {m_filt['n']} (Δ {trade_reduction_pct:.1f}% reduction) — {'PASS' if crit_trade else 'FAIL'}", flush=True)
    print(f"  Era 3 PF stable or improving:   baseline {ts_base['era3_pf']:.3f} → filtered {ts_filt['era3_pf']:.3f} (Δ {era3_delta:+.3f}) — {'PASS' if crit_era3 else 'FAIL'}", flush=True)
    print(f"  Stress PF stable or improving:  baseline {m_base_stress['pf']:.3f} → filtered {m_filt_stress['pf']:.3f} (Δ {stress_pf_delta:+.3f}) — {'PASS' if crit_stress else 'FAIL'}", flush=True)

    all_pass = crit_pf and crit_trade and crit_era3 and crit_stress
    if all_pass:
        verdict = "mes_alignment ACCEPTED — replicate on first_impulse + range_compression next"
    else:
        failed = []
        if not crit_pf: failed.append("PF_improvement")
        if not crit_trade: failed.append("trade_reduction")
        if not crit_era3: failed.append("Era3_stable")
        if not crit_stress: failed.append("stress_stable")
        verdict = f"mes_alignment ARCHIVED — failed criteria: {failed}; per methodology: NO TUNING, move to ZN port"
    print(f"\n  VERDICT: {verdict}", flush=True)

    print(f"\nTotal: {time.time() - t_start:.0f}s", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-12h_mes_alignment_test1.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "Test 1: mes_alignment filter on stop_run_reversal per #196 A methodology",
        "baseline": {
            "metrics": {k: m_base.get(k) for k in ("n", "pf", "median", "net")},
            "era3_pf": ts_base["era3_pf"],
            "stress": {"pf": float(m_base_stress["pf"]), "median": float(m_base_stress["median"])},
        },
        "filtered": {
            "metrics": {k: m_filt.get(k) for k in ("n", "pf", "median", "net")},
            "era3_pf": ts_filt["era3_pf"],
            "stress": {"pf": float(m_filt_stress["pf"]), "median": float(m_filt_stress["median"])},
        },
        "criteria_evaluation": {
            "pf_delta": pf_delta, "pf_pass": crit_pf,
            "trade_reduction_pct": trade_reduction_pct, "trade_pass": crit_trade,
            "era3_delta": era3_delta, "era3_pass": crit_era3,
            "stress_pf_delta": stress_pf_delta, "stress_pass": crit_stress,
        },
        "all_criteria_pass": all_pass,
        "verdict": verdict,
    }, indent=2, default=str))
    print(f"\nWrote: {out}")


if __name__ == "__main__":
    run()
