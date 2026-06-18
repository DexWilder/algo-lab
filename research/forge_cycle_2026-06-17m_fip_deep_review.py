"""Cycle 2026-06-17m — Lane 2 DEEP REVIEW: first_impulse_pullback as MNQ addition (report-only).

Tests whether the -36% combined-DD reduction is ROBUST or an in-sample offset artifact.
5 checks (operator):
  1. OOS/split stability of the DD reduction (train<=2022 / test>=2023, and per-year).
  2. Bad-day overlap: on worst incumbent days, does FIP help / stay flat / pile on?
  3. Same-day overlap decomposition (87% same days, corr 0.43): sign-agreement + entry-hour.
  4. Concentration: ADD (orb+srr+fip) vs REWEIGHT/REPLACE (orb+fip) vs incumbents.
  5. Cost/slippage sensitivity + prop daily-loss compat.
Decision: stable+genuine -> ADDITION/REWEIGHT_CANDIDATE; gone OOS/one-period -> NEUTRAL/KILL;
duplicates orb -> REDUNDANT. Report-only; no mutation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import get_cost_params, run_backtest  # noqa: E402
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals as gcs  # noqa: E402


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def _maxdd(daily):
    c = daily.sort_index().cumsum(); return float((c - c.cummax()).min())


def book(entry, slip_mult=1.0):
    df = pd.read_csv(ROOT / "data" / "processed" / "MNQ_5m.csv"); cfg = ASSETS["MNQ"]; c = get_cost_params("MNQ")
    s = gcs(df, entry_name=entry, exit_name="profit_ladder", filter_name="ema_slope", params={})
    res = run_backtest(df, s, mode="both", point_value=cfg["point_value"], symbol="MNQ",
                       commission_per_side=c["commission_per_side"], slippage_ticks=int(np.ceil(c["slippage_ticks"] * slip_mult)), tick_size=c["tick_size"])
    tr = res["trades_df"].copy(); tr["dt"] = pd.to_datetime(tr["entry_time"]); tr["date"] = tr["dt"].dt.normalize().astype("datetime64[ns]"); tr["hour"] = tr["dt"].dt.hour
    return tr


def daily(tr):
    return tr.groupby("date")["pnl"].sum().sort_index()


def run():
    print("Cycle 2026-06-17m — DEEP REVIEW first_impulse_pullback (MNQ addition) (REPORT-ONLY)\n", flush=True)
    orb = book("orb_breakout"); srr = book("stop_run_reversal"); fip = book("first_impulse_pullback")
    do, ds, df_ = daily(orb), daily(srr), daily(fip)
    inc = do.add(ds, fill_value=0).sort_index()
    withfip = inc.add(df_, fill_value=0).sort_index()

    def split(series, yrs):
        return series[series.index.year.isin(yrs)]
    TRY = [2019, 2020, 2021, 2022]; TEY = [2023, 2024, 2025, 2026]

    print("1. OOS/SPLIT DD STABILITY (combined max-DD, incumbents vs +fip):", flush=True)
    for label, yrs in [("FULL", TRY + TEY), ("TRAIN<=2022", TRY), ("TEST>=2023", TEY)]:
        i = split(inc, yrs); w = split(withfip, yrs)
        print(f"   {label:<12} incDD=${_maxdd(i):.0f} -> +fip DD=${_maxdd(w):.0f} "
              f"({'IMPROVES' if _maxdd(w) > _maxdd(i) else 'WORSE/flat'}); incPF={_pf(i.values):.3f}->+fip {_pf(w.values):.3f}", flush=True)
    peryr = []
    for y in TRY + TEY:
        i = split(inc, [y]); w = split(withfip, [y])
        if len(i):
            peryr.append((y, round(_maxdd(i), 0), round(_maxdd(w), 0)))
    print(f"   per-year incDD vs +fipDD: {peryr}", flush=True)
    yr_improve = sum(1 for _, a, b in peryr if b > a)
    print(f"   years DD improves: {yr_improve}/{len(peryr)}", flush=True)

    print("\n2. BAD-DAY OVERLAP (fip on worst incumbent days):", flush=True)
    for N in (10, 20, 40):
        worst = inc.sort_values().head(N).index
        fp = df_.reindex(worst).fillna(0.0)
        print(f"   worst {N} incumbent days: fip mean=${fp.mean():.0f} sum=${fp.sum():.0f} %pos={float((fp>0).mean())*100:.0f}% "
              f"(>0 = offsets, <0 = piles on)", flush=True)

    print("\n3. SAME-DAY OVERLAP DECOMPOSITION (87% same days, corr 0.43 vs orb):", flush=True)
    common = sorted(set(do.index) & set(df_.index))
    co = do.reindex(common); cf = df_.reindex(common)
    sign_agree = float((np.sign(co.values) == np.sign(cf.values)).mean()) * 100
    print(f"   same-day count={len(common)}; sign-agreement={sign_agree:.0f}%; same-day PnL corr={round(float(pd.concat([co,cf],axis=1).corr().iloc[0,1]),3)}", flush=True)
    print(f"   entry-hour dist orb: {orb['hour'].value_counts().head(3).to_dict()} | fip: {fip['hour'].value_counts().head(3).to_dict()}", flush=True)
    # corr by half
    for label, yrs in [("train", TRY), ("test", TEY)]:
        a = split(do, yrs); b = split(df_, yrs); al = pd.concat([a.rename('a'), b.rename('b')], axis=1).fillna(0.0)
        print(f"   orb-fip daily corr ({label}): {round(float(al['a'].corr(al['b'])),3)}", flush=True)

    print("\n4. CONCENTRATION — ADD vs REWEIGHT/REPLACE:", flush=True)
    orb_fip = do.add(df_, fill_value=0).sort_index()  # replace srr with fip
    for label, ser in [("incumbents orb+srr", inc), ("ADD orb+srr+fip", withfip), ("REPLACE-srr orb+fip", orb_fip)]:
        print(f"   {label:<22} PF={_pf(ser.values):.3f} maxDD=${_maxdd(ser):.0f} net=${ser.sum():.0f} worstday=${ser.min():.0f}", flush=True)

    print("\n5. COST/SLIPPAGE + PROP (fip standalone):", flush=True)
    for sm in (1.0, 2.0, 3.0):
        t = book("first_impulse_pullback", sm); d = daily(t)
        print(f"   slip={sm}x: PF={_pf(t['pnl'].values):.3f} net=${t['pnl'].sum():.0f} worstday=${d.min():.0f} maxDD=${_maxdd(d):.0f}", flush=True)

    # verdict
    test_improves = _maxdd(split(withfip, TEY)) > _maxdd(split(inc, TEY))
    train_improves = _maxdd(split(withfip, TRY)) > _maxdd(split(inc, TRY))
    badday_offset = df_.reindex(inc.sort_values().head(20).index).fillna(0).mean() > 0
    replace_better = _maxdd(orb_fip) > _maxdd(inc) and _pf(orb_fip.values) >= _pf(inc.values) - 0.05
    if train_improves and test_improves and badday_offset:
        verdict = "ADDITION_CANDIDATE_CONFIRMED (DD reduction OOS-stable + offsets bad days)"
    elif replace_better and test_improves:
        verdict = "REWEIGHT_CANDIDATE (better as srr-replacement than addition)"
    elif not test_improves:
        verdict = "NEUTRAL_or_KILL (DD benefit not OOS-stable -> likely in-sample artifact)"
    else:
        verdict = "NEUTRAL (mixed; not robust enough)"
    print(f"\n  VERDICT: {verdict}", flush=True)
    print(f"   (train DD improves={train_improves}; test DD improves={test_improves}; bad-day offset={bool(badday_offset)}; replace-better={replace_better})", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-17m_fip_deep_review.json"
    out.write_text(json.dumps({"cycle": "2026-06-17m_fip_deep_review", "mode": "Lane 2 deep review; report-only; NON-WIRED",
        "full_inc_dd": round(_maxdd(inc), 0), "full_withfip_dd": round(_maxdd(withfip), 0),
        "train_inc_dd": round(_maxdd(split(inc, TRY)), 0), "train_withfip_dd": round(_maxdd(split(withfip, TRY)), 0),
        "test_inc_dd": round(_maxdd(split(inc, TEY)), 0), "test_withfip_dd": round(_maxdd(split(withfip, TEY)), 0),
        "per_year_dd": peryr, "replace_srr_orb_fip": {"pf": round(_pf(orb_fip.values), 3), "dd": round(_maxdd(orb_fip), 0)},
        "verdict": verdict, "boundaries": "no mutation/promotion/activation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; deep review; no mutation)", flush=True)


if __name__ == "__main__":
    run()
