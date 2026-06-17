"""Cycle 2026-06-16n — Daily Workhorse #2 deep validation: MGC prior_day_break (report-only).

Targeted hunt (NOT vanity grid) for a SECOND daily workhorse that is NOT an MNQ-cousin.
Candidate selected from the gap map: MGC `prior_day_break` + `ema_slope` + `profit_ladder`
— the only non-MNQ, non-ORB entry that cleared the cheap-screen workhorse gates
(PASS_TO_FORWARD_CLOCK, n=405 PF 1.341 H1 1.325 H2 1.349 max-yr 26.4%). Different
instrument (gold), different mechanism (prior-day structural level, not opening-range),
different driver (real rates/USD/geopolitics, not equity beta).

The cheap-screen is only the FIRST gate. This runs the FULL workhorse gauntlet +
the decisive test the cheap-screen never ran: CORRELATION to the MNQ workhorses (a
"diversifier" that co-moves with MNQ is not a diversifier). Report-only; NO mutation.
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
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402


def _pf(pnl):
    a = np.asarray(pnl, float); w = a[a > 0].sum(); l = -a[a < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def run_xb(asset, entry, exit_name, filter_name, label):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]; costs = get_cost_params(asset)
    sigs = generate_crossbred_signals(df, entry_name=entry, exit_name=exit_name, filter_name=filter_name, params={})
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol=asset,
                       commission_per_side=costs["commission_per_side"], slippage_ticks=costs["slippage_ticks"],
                       tick_size=costs["tick_size"])
    return _metrics(res["trades_df"], label, costs=res["stats"]["costs"]), res["trades_df"]


def concentration(trades):
    g = trades[trades["pnl"] > 0]["pnl"].sort_values(ascending=False)
    gross = float(g.sum())
    top = lambda k: round(float(g.head(k).sum()) / gross * 100, 1) if gross > 0 else None
    return {"top3_pct": top(3), "top5_pct": top(5), "top10_pct": top(10), "gross_profit": round(gross, 0)}


def drawdown(trades):
    eq = trades.sort_values("entry_dt")["pnl"].cumsum().to_numpy()
    peak = np.maximum.accumulate(eq); dd = eq - peak
    max_dd = float(dd.min())
    # duration: longest run below a prior peak (in trades)
    below = dd < 0; longest = cur = 0
    for b in below:
        cur = cur + 1 if b else 0
        longest = max(longest, cur)
    return {"max_dd_usd": round(max_dd, 0), "max_dd_duration_trades": int(longest)}


def daily_corr(a, b):
    da = a.copy(); da["date"] = pd.to_datetime(da["entry_time"]).dt.date
    db = b.copy(); db["date"] = pd.to_datetime(db["entry_time"]).dt.date
    pa = da.groupby("date")["pnl"].sum(); pb = db.groupby("date")["pnl"].sum()
    aligned = pd.concat([pa, pb], axis=1, keys=["a", "b"]).fillna(0.0)
    corr = float(aligned["a"].corr(aligned["b"]))
    overlap_days = len(set(da["date"]) & set(db["date"]))
    return round(corr, 3), overlap_days


def run():
    print("Cycle 2026-06-16n — Daily Workhorse #2: MGC prior_day_break deep validation (REPORT-ONLY)\n", flush=True)

    m, trades = run_xb("MGC", "prior_day_break", "profit_ladder", "ema_slope", "MGC-prior_day_break-WH2")
    trades = trades.copy(); trades["entry_dt"] = pd.to_datetime(trades["entry_time"]); trades["year"] = trades["entry_dt"].dt.year
    net = float(trades["pnl"].sum())
    print(f"BASELINE: n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f} net=${net:.0f} "
          f"win%={m['win_rate']*100:.1f} cost_ratio={m['cost_ratio_pct']}% archetype={m['archetype']} verdict={m['gate_verdict']}", flush=True)
    print(f"  H1/H2 PF: {m['h1_pf']:.3f}/{m['h2_pf']:.3f}  | max-year share: {m['max_year_share_pct']:.1f}%  | "
          f"years +: {m['years_positive']}/{m['n_years']}", flush=True)

    conc = concentration(trades)
    print(f"  CONCENTRATION: top3={conc['top3_pct']}% top5={conc['top5_pct']}% top10={conc['top10_pct']}% "
          f"(gates: <30/<45/<55)", flush=True)

    dd = drawdown(trades)
    print(f"  DRAWDOWN: max_dd=${dd['max_dd_usd']:.0f}  duration={dd['max_dd_duration_trades']} trades", flush=True)

    # year exclusion
    yr_excl = {}
    for y in sorted(trades["year"].unique()):
        sub = trades[trades["year"] != y]["pnl"]
        yr_excl[int(y)] = round(_pf(sub), 3)
    print(f"  YEAR-EXCL PF range: [{min(yr_excl.values()):.3f}, {max(yr_excl.values()):.3f}]", flush=True)

    # era thirds
    st = trades.sort_values("entry_dt").reset_index(drop=True); cuts = np.linspace(0, len(st), 4).astype(int)
    eras = []
    for i in range(3):
        sub = st.iloc[cuts[i]:cuts[i+1]]["pnl"]; eras.append(round(_pf(sub), 3))
    print(f"  ERA thirds PF: {eras}", flush=True)

    # single-event impact
    mx = trades["pnl"].max(); mn = trades["pnl"].min()
    pf_no_max = _pf(trades[trades["pnl"] != mx]["pnl"]); max_share = round(max(abs(mx), abs(mn)) / net * 100, 1) if net else None
    print(f"  SINGLE-EVENT: largest win ${mx:+.0f} (remove→PF {pf_no_max:.3f}); largest loss ${mn:+.0f}; "
          f"max abs share {max_share}%", flush=True)

    # rolling 60-trade blocks
    nb = len(st) // 60; bpf = [_pf(st.iloc[i*60:(i+1)*60]["pnl"]) for i in range(nb)]
    bpf = [p for p in bpf if not np.isinf(p)]; pct_pos = round(float(np.mean([p > 1.0 for p in bpf]) * 100), 0) if bpf else 0
    print(f"  ROLLING 60-blocks: {nb} blocks, {pct_pos:.0f}% > 1.0 PF, worst {min(bpf):.3f}" if bpf else "  ROLLING: n/a", flush=True)

    # ---- DECISIVE: correlation to MNQ workhorses ----
    print("\n  CORRELATION vs MNQ workhorses (daily PnL):", flush=True)
    corrs = {}
    for label, entry in [("MNQ-ORB(live)", "orb_breakout"), ("MNQ-stop_run_reversal(new WH)", "stop_run_reversal")]:
        _, mnq_tr = run_xb("MNQ", entry, "profit_ladder", "ema_slope", label)
        mnq_tr = mnq_tr.copy(); mnq_tr["entry_time"] = mnq_tr["entry_time"]
        c, ov = daily_corr(trades.rename(columns={"entry_dt": "_dt"}).assign(entry_time=trades["entry_time"]), mnq_tr)
        corrs[label] = {"daily_pnl_corr": c, "overlap_days": ov}
        print(f"    {label:>32}: corr={c:+.3f}  (overlap {ov} days)", flush=True)

    # ---- workhorse gate verdict ----
    gates = {
        "PF>1.2": m["pf"] > 1.2,
        "median>=0": m["median"] >= 0,
        "H1>1.0 & H2>1.0": (m["h1_pf"] > 1.0 and m["h2_pf"] > 1.0),
        "top3<30": (conc["top3_pct"] is not None and conc["top3_pct"] < 30),
        "top5<45": (conc["top5_pct"] is not None and conc["top5_pct"] < 45),
        "top10<55": (conc["top10_pct"] is not None and conc["top10_pct"] < 55),
        "max_year<40": m["max_year_share_pct"] < 40,
        "years_pos>=75%": (m["n_years"] > 0 and m["years_positive"] / m["n_years"] >= 0.75),
        "era_all>1.0": all(e > 1.0 for e in eras),
        "yr_excl_all>1.2": min(yr_excl.values()) > 1.2,
        "single_event<25%": (max_share is not None and max_share < 25),
        "decorrelated_<0.3": all(abs(v["daily_pnl_corr"]) < 0.3 for v in corrs.values()),
    }
    passed = sum(gates.values()); total = len(gates)
    fails = [k for k, v in gates.items() if not v]
    print(f"\n  WORKHORSE GATES: {passed}/{total} pass", flush=True)
    for k, v in gates.items():
        print(f"    [{'PASS' if v else 'FAIL'}] {k}", flush=True)

    if passed == total:
        verdict = "WORKHORSE2_CANDIDATE_CONFIRMED — advance to forward clock (gated)"
    elif not gates["decorrelated_<0.3"]:
        verdict = "WORKHORSE2_REJECT_CORRELATED — co-moves with MNQ; not a diversifier"
    elif passed >= total - 2:
        verdict = f"WORKHORSE2_WATCH — clears most gates; blockers: {fails}"
    else:
        verdict = f"WORKHORSE2_FAIL — blockers: {fails}"
    print(f"\n  VERDICT: {verdict}", flush=True)
    print("  (report-only; no activation/registry/scheduler/portfolio/order mutation)", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-16n_daily_workhorse2_mgc_priorday.json"
    out.write_text(json.dumps({"cycle": "2026-06-16n_daily_workhorse2_mgc_priorday",
        "mode": "Lane B report-only; targeted WH2 hunt; NON-WIRED",
        "candidate": "MGC prior_day_break + ema_slope + profit_ladder",
        "baseline": {k: m.get(k) for k in ("n", "pf", "median", "win_rate", "cost_ratio_pct", "h1_pf", "h2_pf",
                                            "max_year_share_pct", "n_years", "years_positive", "archetype", "gate_verdict")},
        "net": round(net, 0), "concentration": conc, "drawdown": dd, "year_exclusion_pf": yr_excl,
        "era_thirds_pf": eras, "single_event_max_abs_share_pct": max_share, "single_event_pf_no_max": round(pf_no_max, 3),
        "rolling_60_pct_pos": pct_pos, "correlation_to_mnq": corrs, "gates": gates, "gates_passed": f"{passed}/{total}",
        "verdict": verdict, "boundaries": "no activation/registry/scheduler/portfolio/order mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
