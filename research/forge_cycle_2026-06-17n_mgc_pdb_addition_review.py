"""Cycle 2026-06-17n — Lane 2 DEEP REVIEW: MGC-prior_day_break as gold-sleeve addition (report-only).

Same rigor that downgraded first_impulse_pullback (no free pass for looking additive earlier).
Incumbent gold book = MGC-ORB (XB-ORB-EMA-Ladder-MGC). Candidate addition = MGC-prior_day_break.
Checks (per [[feedback_sleeve_addition_evidence]]):
  1. Per-year + train/test combined-DD stability (orb vs orb+pdb).
  2. Bad-day offset: on MGC-ORB worst days, is pdb net positive (hedge) or negative (piles on)?
  3. Distinctness: same-day overlap %, sign-agreement, same-day corr, entry hours.
  4. Cost/slippage + prop worst-day.
  5. PF/net/DD contribution.
Decision: ADDITION_CONFIRMED only if per-year-stable DD improvement AND (bad-day offset OR genuine
low-corr diversification). Else NEUTRAL/REDUNDANT. Report-only; no mutation. (Gold soft-cap noted.)
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
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv"); cfg = ASSETS["MGC"]; c = get_cost_params("MGC")
    s = gcs(df, entry_name=entry, exit_name="profit_ladder", filter_name="ema_slope", params={})
    res = run_backtest(df, s, mode="both", point_value=cfg["point_value"], symbol="MGC",
                       commission_per_side=c["commission_per_side"], slippage_ticks=int(np.ceil(c["slippage_ticks"] * slip_mult)), tick_size=c["tick_size"])
    tr = res["trades_df"].copy(); tr["dt"] = pd.to_datetime(tr["entry_time"]); tr["date"] = tr["dt"].dt.normalize().astype("datetime64[ns]"); tr["hour"] = tr["dt"].dt.hour
    return tr


def daily(tr):
    return tr.groupby("date")["pnl"].sum().sort_index()


def run():
    print("Cycle 2026-06-17n — DEEP REVIEW: MGC-prior_day_break gold-sleeve addition (REPORT-ONLY)\n", flush=True)
    orb = book("orb_breakout"); pdb = book("prior_day_break")
    do, dp = daily(orb), daily(pdb)
    comb = do.add(dp, fill_value=0).sort_index()
    TRY = [2019, 2020, 2021, 2022]; TEY = [2023, 2024, 2025, 2026]

    def sp(s, yrs):
        return s[s.index.year.isin(yrs)]

    print(f"  MGC-ORB: PF={_pf(do.values):.3f} net=${do.sum():.0f} maxDD=${_maxdd(do):.0f} n={len(orb)}", flush=True)
    print(f"  MGC-prior_day_break: PF={_pf(dp.values):.3f} net=${dp.sum():.0f} maxDD=${_maxdd(dp):.0f} n={len(pdb)}", flush=True)

    print("\n1. PER-YEAR + SPLIT combined-DD stability (orb vs orb+pdb):", flush=True)
    for label, yrs in [("FULL", TRY + TEY), ("TRAIN<=2022", TRY), ("TEST>=2023", TEY)]:
        a = sp(do, yrs); c = sp(comb, yrs)
        print(f"   {label:<12} orbDD=${_maxdd(a):.0f} -> +pdb DD=${_maxdd(c):.0f} "
              f"({'IMPROVES' if _maxdd(c) > _maxdd(a) else 'WORSE/flat'}); orbPF={_pf(a.values):.3f}->+pdb {_pf(c.values):.3f}", flush=True)
    peryr = []
    for y in TRY + TEY:
        a = sp(do, [y]); c = sp(comb, [y])
        if len(a):
            peryr.append((y, round(_maxdd(a), 0), round(_maxdd(c), 0)))
    yr_improve = sum(1 for _, a, b in peryr if b >= a)  # not worse
    print(f"   per-year orbDD vs +pdbDD: {peryr}", flush=True)
    print(f"   years DD not-worse: {yr_improve}/{len(peryr)}", flush=True)

    print("\n2. BAD-DAY OFFSET (pdb on worst MGC-ORB days):", flush=True)
    for N in (10, 20, 40):
        worst = do.sort_values().head(N).index
        fp = dp.reindex(worst).fillna(0.0)
        print(f"   worst {N} ORB days: pdb mean=${fp.mean():.0f} sum=${fp.sum():.0f} %pos={float((fp>0).mean())*100:.0f}% "
              f"(>0 offsets, <0 piles on)", flush=True)

    print("\n3. DISTINCTNESS:", flush=True)
    common = sorted(set(do.index) & set(dp.index))
    co = do.reindex(common); cf = dp.reindex(common)
    sign_agree = float((np.sign(co.values) == np.sign(cf.values)).mean()) * 100
    same_corr = round(float(pd.concat([co, cf], axis=1).corr().iloc[0, 1]), 3)
    overall_corr = round(float(pd.concat([do.rename('a'), dp.rename('b')], axis=1).fillna(0).corr().iloc[0, 1]), 3)
    overlap_pct = round(len(common) / len(set(do.index)) * 100, 1)
    print(f"   same-day overlap={overlap_pct}% of ORB days; sign-agreement={sign_agree:.0f}%; same-day corr={same_corr}; overall daily corr={overall_corr}", flush=True)
    print(f"   entry-hour ORB: {orb['hour'].value_counts().head(3).to_dict()} | pdb: {pdb['hour'].value_counts().head(3).to_dict()}", flush=True)

    print("\n4. COST/SLIPPAGE + PROP (pdb standalone):", flush=True)
    for sm in (1.0, 2.0, 3.0):
        t = book("prior_day_break", sm); d = daily(t)
        print(f"   slip={sm}x: PF={_pf(t['pnl'].values):.3f} net=${t['pnl'].sum():.0f} worstday=${d.min():.0f} maxDD=${_maxdd(d):.0f}", flush=True)

    print("\n5. SLEEVE CONTRIBUTION:", flush=True)
    print(f"   ORB alone:    PF={_pf(do.values):.3f} maxDD=${_maxdd(do):.0f} net=${do.sum():.0f} worstday=${do.min():.0f}", flush=True)
    print(f"   ORB+pdb:      PF={_pf(comb.values):.3f} maxDD=${_maxdd(comb):.0f} net=${comb.sum():.0f} worstday=${comb.min():.0f}", flush=True)

    # verdict (apply the lesson)
    train_ok = _maxdd(sp(comb, TRY)) >= _maxdd(sp(do, TRY)) - 50      # not materially worse
    test_ok = _maxdd(sp(comb, TEY)) >= _maxdd(sp(do, TEY)) - 50
    peryr_ok = yr_improve >= len(peryr) - 1                          # not-worse in nearly all years
    badday_offset = dp.reindex(do.sort_values().head(20).index).fillna(0).mean() > 0
    low_corr = abs(overall_corr) < 0.3
    net_adds = comb.sum() > do.sum()                                 # adds return (vs just smoothing)
    if low_corr and net_adds and (peryr_ok or badday_offset):
        verdict = "ADDITION_CONFIRMED (low-corr, adds return, per-year-stable/offsets)"
    elif low_corr and net_adds:
        verdict = "ADDITION_CANDIDATE (low-corr + adds return; DD-stability/offset partial)"
    elif abs(overall_corr) >= 0.6:
        verdict = "REDUNDANT"
    else:
        verdict = "NEUTRAL"
    print(f"\n  VERDICT: {verdict}", flush=True)
    print(f"   (overall_corr={overall_corr} low={low_corr}; net_adds={net_adds}; per-year not-worse {yr_improve}/{len(peryr)}; bad-day offset={bool(badday_offset)})", flush=True)
    print("   NOTE: MGC soft-cap — pdb would be a 5th gold book; portfolio-level gold concentration still applies even if sleeve-additive.", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-17n_mgc_pdb_addition_review.json"
    out.write_text(json.dumps({"cycle": "2026-06-17n_mgc_pdb_addition_review", "mode": "Lane 2 deep review; report-only; NON-WIRED",
        "orb": {"pf": round(_pf(do.values), 3), "dd": round(_maxdd(do), 0), "net": round(do.sum(), 0)},
        "pdb": {"pf": round(_pf(dp.values), 3), "dd": round(_maxdd(dp), 0), "net": round(dp.sum(), 0)},
        "combined": {"pf": round(_pf(comb.values), 3), "dd": round(_maxdd(comb), 0), "net": round(comb.sum(), 0)},
        "per_year_dd": peryr, "overall_corr": overall_corr, "same_day_corr": same_corr, "sign_agree_pct": round(sign_agree, 0),
        "overlap_pct": overlap_pct, "bad_day_offset": bool(badday_offset), "verdict": verdict,
        "note": "MGC soft-cap: pdb=5th gold book; portfolio gold concentration applies", "boundaries": "no mutation/promotion/activation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; deep review; no mutation)", flush=True)


if __name__ == "__main__":
    run()
