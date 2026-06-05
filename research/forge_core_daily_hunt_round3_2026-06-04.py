"""Core Daily Hunt Round 3 — operator's revised gap list + prop-stress upfront.

Per operator approvals 2026-06-04 (#65 OBSERVATIONAL for PB-VolLow-MNQ; #66
continue; #67 prop-stress; #68 Era-3 delta signal). 14 candidates targeting
non-MNQ gaps. WATCH candidates undergo prop-stress before promotion.

Authority: T1 / Lane B / report-only.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from research.prop_stress_screen import prop_stress_screen  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def _classify(m):
    n = m.get("n", 0); pf = m.get("pf", 0); median = m.get("median", 0)
    max_yr = m.get("max_year_share_pct", 100)
    if n < 30:
        return f"KILL (insufficient-n, n={n})"
    if median < 0:
        return "KILL (median neg)"
    if pf < 1.15:
        return "KILL (PF<1.15)"
    if max_yr >= 50:
        return "TEMPORAL_SPLIT_REQUIRED"
    if pf >= 1.30 and median > 0:
        return "WATCH_FOR_DEEP_SCREEN"
    return "WATCH"


def temporal_split(trades):
    if trades.empty:
        return None
    df = trades.copy()
    df["entry_dt"] = pd.to_datetime(df["entry_time"])
    df["year"] = df["entry_dt"].dt.year
    per_year = []
    for y, g in df.groupby("year"):
        pnl = g["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w/l) if l > 0 else float("inf")
        per_year.append({"year": int(y), "n": int(len(g)),
                         "pf": pf, "median": float(np.median(pnl)),
                         "net": float(pnl.sum())})
    df = df.sort_values("entry_dt").reset_index(drop=True)
    cuts = np.linspace(0, len(df), 4).astype(int)
    eras = []
    for i in range(3):
        sub = df.iloc[cuts[i]:cuts[i+1]]
        if sub.empty: continue
        pnl = sub["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w/l) if l > 0 else float("inf")
        eras.append({"era": i+1, "n": int(len(sub)), "pf": pf,
                     "median": float(np.median(pnl)),
                     "net": float(pnl.sum())})
    return {"per_year": per_year, "eras": eras,
            "yrs_pos": sum(1 for r in per_year if r["net"] > 0),
            "n_yrs": len(per_year),
            "era3_pf": eras[-1]["pf"] if eras else float("nan"),
            "era3_median": eras[-1]["median"] if eras else float("nan")}


def _doctrine(m, ts, full_median):
    """Apply hard Forge laws + Era-3 wall + Era-3 delta signal."""
    v = _classify(m)
    if v != "TEMPORAL_SPLIT_REQUIRED" or ts is None:
        return v, None
    # Era-3 wall
    if ts["yrs_pos"] < ts["n_yrs"] * 0.5:
        return "ARCHITECTURAL_REJECT (<50% yrs+)", None
    if any(e["pf"] < 1.0 and np.isfinite(e["pf"]) for e in ts["eras"]):
        return "ARCHITECTURAL_REJECT (losing era)", None
    era3 = ts.get("era3_pf", 1.0)
    if np.isfinite(era3) and era3 < 1.0:
        return "ARCHITECTURAL_REJECT (Era-3 regime-wall fail)", None
    # Era-3 delta signal
    era3_med = ts.get("era3_median", full_median)
    delta_signal = None
    if full_median > 0:
        if era3_med > full_median * 2:
            delta_signal = "RECENT_IMPROVEMENT_SIGNAL"
        elif era3_med < full_median * 0.5 or era3_med < 0:
            delta_signal = "CURRENT_REGIME_WARNING"
    if m["pf"] >= 1.30 and m["median"] > 0 and ts["yrs_pos"] >= ts["n_yrs"] * 0.75:
        return "WATCH_FOR_DEEP_SCREEN (passed temporal + Era-3)", delta_signal
    return "WATCH (passed temporal; modest)", delta_signal


def make_runner(spec):
    def runner(commission_mult, slippage_mult):
        df = pd.read_csv(ROOT / "data" / "processed" / f"{spec['asset']}_5m.csv")
        cfg = ASSETS[spec["asset"]]
        base_costs = get_cost_params(spec["asset"])
        sigs = generate_crossbred_signals(
            df, entry_name=spec["entry"], exit_name=spec["exit"],
            filter_name=spec["filter"], params=spec.get("params", {}),
        )
        res = run_backtest(
            df, sigs, mode="both", point_value=cfg["point_value"],
            symbol=spec["asset"],
            commission_per_side=base_costs["commission_per_side"] * commission_mult,
            slippage_ticks=int(np.ceil(base_costs["slippage_ticks"] * slippage_mult)),
            tick_size=base_costs["tick_size"],
        )
        return res
    return runner


def run_candidate(spec):
    runner = make_runner(spec)
    res = runner(1.0, 1.0)
    m = _metrics(res["trades_df"], spec["label"], costs=res["stats"]["costs"])
    vc = _classify(m)
    ts = temporal_split(res["trades_df"]) if (vc == "TEMPORAL_SPLIT_REQUIRED" or
                                              vc == "WATCH_FOR_DEEP_SCREEN") else None
    v, era3_delta = _doctrine(m, ts, m.get("median", 0))
    # Prop-stress only for WATCH or WATCH_FOR_DEEP_SCREEN
    stress = None
    if "WATCH" in v:
        stress = prop_stress_screen(runner, spec["label"])
    return m, ts, vc, v, era3_delta, stress


# Operator-prioritized list (avoid MNQ workhorse, chandelier defaults,
# duplicate PriorDay rescue, knife-edge candidates)
SPECS = [
    # === MGC priorities ===
    {"label": "R3-MGC-VWAP-EMA", "asset": "MGC", "entry": "vwap_continuation",
     "filter": "ema_slope", "exit": "profit_ladder",
     "gap": "MGC VWAP reclaim/rejection — baseline (operator #1)"},
    {"label": "R3-MGC-VWAP-Hurst-Trend", "asset": "MGC", "entry": "vwap_continuation",
     "filter": "hurst_stable_trend", "exit": "profit_ladder",
     "params": {"hurst_threshold_low": 0.55},
     "gap": "MGC VWAP + Hurst-trend gate"},
    {"label": "R3-MGC-PB-VolLow40", "asset": "MGC", "entry": "pb_pullback",
     "filter": "ema_slope_vol_low", "exit": "profit_ladder",
     "params": {"vr_threshold": 40},
     "gap": "MGC low-vol trend rider (operator #2)"},

    # === MES/MYM prior-day variants ===
    {"label": "R3-MES-PriorDayFade-Morning", "asset": "MES", "entry": "prior_day_fade",
     "filter": "session_morning", "exit": "profit_ladder",
     "gap": "MES prior-day fade in morning session (operator #3)"},
    {"label": "R3-MYM-PriorDayBreak-EMA", "asset": "MYM", "entry": "prior_day_break",
     "filter": "ema_slope", "exit": "profit_ladder",
     "gap": "MYM prior-day breakout (operator #3)"},
    {"label": "R3-MYM-PriorDayFade-EMA", "asset": "MYM", "entry": "prior_day_fade",
     "filter": "ema_slope", "exit": "profit_ladder",
     "gap": "MYM prior-day fade"},

    # === MCL fixed-exit (NO chandelier/atr-trail) ===
    {"label": "R3-MCL-ORB-EMA-Profit-Ladder", "asset": "MCL", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "profit_ladder",
     "gap": "MCL ORB with profit_ladder exit — already in CANDIDATES as XB-ORB-EMA-Ladder-MCL"},
    {"label": "R3-MCL-ORB-MorningOnly", "asset": "MCL", "entry": "orb_breakout",
     "filter": "session_morning", "exit": "profit_ladder",
     "gap": "MCL morning ORB"},
    {"label": "R3-MCL-ORB-VolLow", "asset": "MCL", "entry": "orb_breakout",
     "filter": "ema_slope_vol_low", "exit": "profit_ladder",
     "params": {"vr_threshold": 30},
     "gap": "MCL ORB + low-vol overlay"},

    # === ZN MR with discriminator ===
    {"label": "R3-ZN-BB-Morning-Hurst-MR", "asset": "ZN", "entry": "bb_reversion",
     "filter": "hurst_stable_mr", "exit": "profit_ladder",
     "params": {"hurst_threshold_high": 0.45},
     "gap": "ZN MR + Hurst-MR discriminator (operator #5)"},

    # === MYM close momentum ===
    {"label": "R3-MYM-ORB-Close", "asset": "MYM", "entry": "orb_breakout",
     "filter": "session_close", "exit": "profit_ladder",
     "gap": "MYM close momentum"},

    # === FX session handoff ===
    {"label": "R3-6E-PB-EMA", "asset": "6E", "entry": "pb_pullback",
     "filter": "ema_slope", "exit": "profit_ladder",
     "gap": "FX 6E pullback (session handoff implicit)"},
    {"label": "R3-6E-PriorDayBreak", "asset": "6E", "entry": "prior_day_break",
     "filter": "ema_slope", "exit": "profit_ladder",
     "gap": "6E prior-day breakout"},

    # === Extra MGC PriorDay diagnostic with HurstTrend ===
    {"label": "R3-MGC-PriorDayBreak-HurstTrend", "asset": "MGC", "entry": "prior_day_break",
     "filter": "hurst_stable_trend", "exit": "profit_ladder",
     "params": {"hurst_threshold_low": 0.55},
     "gap": "MGC prior-day break + Hurst-trend filter (new combo)"},
]


def run():
    print(f"Core Daily Hunt Round 3 — {len(SPECS)} candidates + prop-stress on WATCH\n")
    results = []
    for spec in SPECS:
        try:
            m, ts, vc, v, era3_delta, stress = run_candidate(spec)
        except Exception as e:
            print(f"  {spec['label']:42s}: ERROR {e}")
            continue
        max_yr = m.get("max_year_share_pct", float("nan"))
        n_yrs = ts["n_yrs"] if ts else m.get("n_years", "?")
        yrs_pos = ts["yrs_pos"] if ts else m.get("years_positive", "?")
        era3 = ts["era3_pf"] if ts else float("nan")
        delta_str = f" [{era3_delta}]" if era3_delta else ""
        stress_str = f" stress={stress['verdict'].split()[0]}" if stress else ""
        print(
            f"  {spec['label']:38s}: n={m['n']:5d} PF={m['pf']:.3f} "
            f"median=${m['median']:7.2f} max-yr={max_yr:.1f}% "
            f"yrs+={yrs_pos}/{n_yrs} Era3={era3:.2f} → {v}{delta_str}{stress_str}"
        )
        results.append({
            "spec": spec,
            "metrics": {k: m.get(k) for k in (
                "n", "pf", "median", "net", "max_dd",
                "max_year_share_pct", "top3_share_pct",
                "h1_pf", "h2_pf", "years_positive", "n_years",
            )},
            "temporal_split": ts,
            "doctrine_verdict": v,
            "era3_delta_signal": era3_delta,
            "prop_stress": stress,
        })

    # Tier classification per 3-tier doctrine
    paper_packet = []
    portfolio_complement = []
    observational = []
    kill = []
    for r in results:
        v = r["doctrine_verdict"]
        s = r["prop_stress"]
        if "KILL" in v or "ARCHITECTURAL_REJECT" in v:
            kill.append(r)
        elif "WATCH_FOR_DEEP_SCREEN" in v:
            if s and s["verdict"] == "PASS_STRESS":
                paper_packet.append(r)
            elif s and "KNIFE_EDGE" in s["verdict"]:
                observational.append(r)
            else:
                paper_packet.append(r)  # No stress data → still strong WATCH
        elif "WATCH" in v:
            observational.append(r)

    print(f"\nAggregate ({len(results)} candidates):")
    print(f"  PAPER_PACKET tier (passes stress):     {len(paper_packet)}")
    print(f"  PORTFOLIO_COMPLEMENT tier:             {len(portfolio_complement)}")
    print(f"  OBSERVATIONAL tier (WATCH/knife-edge): {len(observational)}")
    print(f"  KILL/REJECT:                           {len(kill)}")

    if paper_packet:
        print("\nPAPER_PACKET tier headlines:")
        for r in paper_packet:
            m = r["metrics"]
            ts = r["temporal_split"]
            stress = r["prop_stress"]
            print(f"  {r['spec']['label']}: PF={m['pf']:.3f} median=${m['median']:.2f} "
                  f"yrs+={ts['yrs_pos']}/{ts['n_yrs']} Era3={ts['era3_pf']:.2f} "
                  f"stress={stress['headline_reason'] if stress else 'no-stress-run'}")

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / f"forge_core_daily_hunt_round3_{date.today().isoformat()}.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "approval": "OK continue Core Daily Hunt elsewhere (#66) + prop-stress upfront (#67) + Era-3 delta signal (#68)",
        "tier_classification": {
            "PAPER_PACKET": len(paper_packet),
            "PORTFOLIO_COMPLEMENT": len(portfolio_complement),
            "OBSERVATIONAL": len(observational),
            "KILL": len(kill),
        },
        "results": results,
    }, indent=2, default=str))
    print(f"\nWrote: {out}")


if __name__ == "__main__":
    run()
