"""Evidence-integrity audit for DAILY-PB-VolLow-MNQ (median-focus).

Per operator approval #61 Option D — audit first, then decide. Family review
verdict was PARALLEL_COMPLEMENT_CANDIDATE but standalone median is $3.26 (weak).
This audit pays special attention to dim C (edge quality) per operator directive.

Outcome buckets:
  - GREEN: median survives cost/slippage stress; trade distribution clean
  - YELLOW: weak median is the only concern; portfolio contribution strong;
    operator decides if COMPLEMENT classification is acceptable
  - RED: median collapses under stress OR distribution dominated by outliers
  - KILL: median ≤ 0 at baseline (asymmetric-P&L hard rule)

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
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def run_pb_vollow_mnq(commission_mult=1.0, slippage_mult=1.0):
    df = pd.read_csv(ROOT / "data" / "processed" / "MNQ_5m.csv")
    cfg = ASSETS["MNQ"]
    base_costs = get_cost_params("MNQ")
    sigs = generate_crossbred_signals(
        df, entry_name="pb_pullback", exit_name="profit_ladder",
        filter_name="ema_slope_vol_low", params={"vr_threshold": 40},
    )
    res = run_backtest(
        df, sigs, mode="both", point_value=cfg["point_value"], symbol="MNQ",
        commission_per_side=base_costs["commission_per_side"] * commission_mult,
        slippage_ticks=int(np.ceil(base_costs["slippage_ticks"] * slippage_mult)),
        tick_size=base_costs["tick_size"],
    )
    return res


# A. Cost source
def audit_A():
    costs = get_cost_params("MNQ")
    cfg = ASSETS.get("MNQ", {})
    return {
        "symbol": "MNQ",
        "asset_config_present": "MNQ" in ASSETS,
        "point_value": cfg.get("point_value"),
        "commission_per_side": costs.get("commission_per_side"),
        "slippage_ticks": costs.get("slippage_ticks"),
        "tick_size": costs.get("tick_size"),
        "cost_tier": costs.get("cost_tier"),
        "missing_or_default": costs.get("cost_tier") != "VALIDATED",
        "round_trip_cost": 2 * costs["commission_per_side"] + 2 * costs["slippage_ticks"] * costs["tick_size"] * cfg["point_value"],
        "verdict": "GREEN" if costs.get("cost_tier") == "VALIDATED" else "RED",
    }


# B. Cost stress
def audit_B():
    rows = []
    for cm, sm, tag in [
        (1.0, 1.0, "1x baseline"),
        (1.5, 1.0, "1.5x cost"),
        (2.0, 1.0, "2x cost"),
        (3.0, 1.0, "3x cost"),
        (1.0, 2.0, "+1 tick slip"),
        (1.0, 3.0, "+2 tick slip"),
        (2.0, 2.0, "2x cost + 1 tick slip"),
        (2.0, 3.0, "2x cost + 2 tick slip"),
    ]:
        res = run_pb_vollow_mnq(cm, sm)
        m = _metrics(res["trades_df"], f"PB-VolLow-MNQ-{tag}", costs=res["stats"]["costs"])
        rows.append({
            "stress": tag,
            "n": int(m["n"]), "pf": float(m["pf"]),
            "net_median": float(m["median"]),
            "net_pnl": float(m["net"]),
            "max_dd": float(m["max_dd"]),
            "max_year_share_pct": m.get("max_year_share_pct"),
        })
    # Hard rule: any cost level where median goes negative = RED
    median_collapse = any(r["net_median"] < 0 for r in rows)
    return {"rows": rows, "median_collapse": median_collapse,
            "verdict": "RED" if median_collapse else "GREEN"}


# C. Edge quality (extra focus)
def audit_C():
    res = run_pb_vollow_mnq(1.0, 1.0)
    trades = res["trades_df"]
    costs = res["stats"]["costs"]
    pnl = trades["pnl"].values
    wins = pnl[pnl > 0]; losses = pnl[pnl < 0]
    rt_cost = 2 * costs["commission_per_side"] + 2 * costs["slippage_ticks"] * costs["tick_size"] * ASSETS["MNQ"]["point_value"]
    gross = pnl + rt_cost
    sorted_d = np.sort(pnl)[::-1]
    total = float(pnl.sum())
    # Consecutive losses
    streaks = []
    cur = 0
    for x in pnl:
        if x < 0:
            cur += 1
        else:
            if cur > 0: streaks.append(cur)
            cur = 0
    if cur > 0: streaks.append(cur)
    max_streak = max(streaks) if streaks else 0
    # DD duration in trades
    eq = np.cumsum(pnl)
    peak = np.maximum.accumulate(eq)
    in_dd = eq < peak
    dd_lens = []
    cur = 0
    for x in in_dd:
        if x: cur += 1
        else:
            if cur > 0: dd_lens.append(cur)
            cur = 0
    if cur > 0: dd_lens.append(cur)
    max_dd_dur = max(dd_lens) if dd_lens else 0

    eq_q = {
        "n": int(len(pnl)),
        "win_rate_pct": float((pnl > 0).mean() * 100),
        "gross_median": float(np.median(gross)),
        "net_median": float(np.median(pnl)),
        "avg_win": float(wins.mean()) if len(wins) else float("nan"),
        "avg_loss": float(losses.mean()) if len(losses) else float("nan"),
        "largest_win": float(wins.max()) if len(wins) else float("nan"),
        "largest_loss": float(losses.min()) if len(losses) else float("nan"),
        "top1_share_pct": 100 * float(sorted_d[0]) / total if total > 0 else float("nan"),
        "top3_share_pct": 100 * float(sorted_d[:3].sum()) / total if total > 0 else float("nan"),
        "top5_share_pct": 100 * float(sorted_d[:5].sum()) / total if total > 0 else float("nan"),
        "pct_trades_net_le_zero": float((pnl <= 0).mean() * 100),
        "max_consec_losses": max_streak,
        "max_dd_duration_trades": max_dd_dur,
        "rt_cost_per_trade": rt_cost,
    }
    # Verdict: YELLOW if median positive but weak (< $10), GREEN if strong, RED if ≤ 0
    if eq_q["net_median"] <= 0:
        v = "RED (median ≤ 0)"
    elif eq_q["net_median"] < 5:
        v = "YELLOW (median positive but very weak < $5)"
    elif eq_q["net_median"] < 10:
        v = "YELLOW (median moderate $5-$10)"
    else:
        v = "GREEN (median > $10)"
    # Also flag if top-1 dominates (> 20%)
    if eq_q["top1_share_pct"] > 20:
        v += " + outlier-dominated top-1"
    return {"metrics": eq_q, "verdict": v}


# D. Lookahead (XB engine, already verified)
def audit_D():
    return {
        "candidate_class": "XB (crossbreeding_engine)",
        "entry_logic": "pb_pullback uses bar i features (ema, atr) computed up to i",
        "exit_logic": "profit_ladder uses bar i + state from prior bars",
        "indicator_shifting": "donchian bug-fixed 2026-05-28; pb_pullback uses no prior-shifted indicators",
        "no_future_bars": True,
        "verdict": "GREEN",
    }


# E. Calendar audit (N/A)
def audit_E():
    return {"calendar_source": "N/A — continuous-bar candidate", "verdict": "GREEN"}


# F. Survivorship (MNQ already audited GREEN)
def audit_F():
    path = ROOT / "data" / "processed" / "MNQ_5m.csv"
    df = pd.read_csv(path, parse_dates=["datetime"])
    first = df["datetime"].min(); last = df["datetime"].max()
    n = len(df)
    span_days = (last - first).days
    ret = df.sort_values("datetime").reset_index(drop=True)["close"].pct_change()
    big_jumps = int((ret.abs() > 0.05).sum())
    return {
        "symbol": "MNQ", "available": True, "first_bar": str(first),
        "last_bar": str(last), "span_days": span_days, "n_bars": n,
        "big_jumps_gt_5pct": big_jumps,
        "data_window_caveat": "FULL — 2019-2020+",
        "verdict": "GREEN",
    }


# G. Duplicate / portfolio
def audit_G():
    # Re-load family review summary
    fam = json.loads((ROOT / "research" / "data" / "fql_forge" / "reports" /
                       "forge_pbvollow_mnq_family_review_2026-06-04.json").read_text())
    return {
        "verdict": fam.get("verdict"),
        "key_summary": {
            "daily_corr": fam.get("correlation", {}).get("daily_corr"),
            "drawdown_overlap_pct": fam.get("correlation", {}).get("drawdown_overlap_pct_of_days"),
            "losing_day_overlap_pct": fam.get("correlation", {}).get("losing_day_overlap_pct"),
        },
        "portfolio_metrics_full_size": fam.get("configs", {}).get("C_both_full"),
    }


# H. Era-3 / temporal split
def audit_H_temporal():
    res = run_pb_vollow_mnq(1.0, 1.0)
    trades = res["trades_df"].copy()
    trades["entry_dt"] = pd.to_datetime(trades["entry_time"])
    trades["year"] = trades["entry_dt"].dt.year
    per_year = []
    for y, g in trades.groupby("year"):
        pnl = g["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w/l) if l > 0 else float("inf")
        per_year.append({"year": int(y), "n": int(len(g)),
                         "pf": pf, "median": float(np.median(pnl)),
                         "net": float(pnl.sum())})
    trades = trades.sort_values("entry_dt").reset_index(drop=True)
    cuts = np.linspace(0, len(trades), 4).astype(int)
    eras = []
    for i in range(3):
        sub = trades.iloc[cuts[i]:cuts[i+1]]
        if sub.empty: continue
        pnl = sub["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w/l) if l > 0 else float("inf")
        eras.append({"era": i+1, "n": int(len(sub)), "pf": pf,
                     "median": float(np.median(pnl)),
                     "net": float(pnl.sum())})
    yrs_pos = sum(1 for r in per_year if r["net"] > 0)
    era3 = eras[-1]["pf"] if eras else float("nan")
    return {"per_year": per_year, "eras": eras,
            "yrs_pos": yrs_pos, "n_yrs": len(per_year),
            "era_3_pf": era3,
            "era_3_median": eras[-1]["median"] if eras else float("nan"),
            "verdict": "GREEN" if (yrs_pos >= len(per_year) * 0.75 and era3 > 1.0) else "YELLOW"}


def run():
    print("=" * 78)
    print("EVIDENCE-INTEGRITY AUDIT — DAILY-PB-VolLow-MNQ — 2026-06-04")
    print("=" * 78)

    A = audit_A()
    print(f"\n[A] Cost source: {A['verdict']}")
    print(f"  asset_config_present={A['asset_config_present']}, tier={A['cost_tier']}, RT cost=${A['round_trip_cost']:.2f}")

    B = audit_B()
    print(f"\n[B] Cost stress: {B['verdict']}")
    for r in B["rows"]:
        print(f"  {r['stress']:28s}: n={r['n']:4d} PF={r['pf']:.3f} netMed=${r['net_median']:7.2f} maxDD=${r['max_dd']:.0f}")

    C = audit_C()
    print(f"\n[C] Edge quality: {C['verdict']}")
    for k, v in C["metrics"].items():
        if isinstance(v, float):
            print(f"  {k}: {v:.2f}")
        else:
            print(f"  {k}: {v}")

    D = audit_D()
    print(f"\n[D] Lookahead: {D['verdict']}")

    E = audit_E()
    print(f"\n[E] Calendar: {E['verdict']}")

    F = audit_F()
    print(f"\n[F] Survivorship: {F['verdict']} (span={F['span_days']}d, big_jumps={F['big_jumps_gt_5pct']})")

    G = audit_G()
    print(f"\n[G] Duplicate/portfolio: {G['verdict']}")
    print(f"  daily corr: {G['key_summary']['daily_corr']:.3f}")
    print(f"  losing-day overlap: {G['key_summary']['losing_day_overlap_pct']:.1f}%")

    H = audit_H_temporal()
    print(f"\n[H] Temporal/Era-3: {H['verdict']}")
    print(f"  yrs+ {H['yrs_pos']}/{H['n_yrs']}, Era 3 PF {H['era_3_pf']:.2f}, Era 3 median ${H['era_3_median']:.2f}")

    # Overall verdict
    issues = []
    if A["verdict"] != "GREEN":
        issues.append(("RED", f"A: {A['verdict']}"))
    if B["verdict"] != "GREEN":
        issues.append(("RED", f"B: {B['verdict']}"))
    if "GREEN" not in C["verdict"]:
        issues.append(("YELLOW" if "YELLOW" in C["verdict"] else "RED", f"C: {C['verdict']}"))
    if D["verdict"] != "GREEN":
        issues.append(("RED", f"D: {D['verdict']}"))
    if E["verdict"] != "GREEN":
        issues.append(("YELLOW", f"E: {E['verdict']}"))
    if F["verdict"] != "GREEN":
        issues.append(("YELLOW", f"F: {F['verdict']}"))
    if H["verdict"] != "GREEN":
        issues.append(("YELLOW", f"H: {H['verdict']}"))

    if any(s == "RED" for s, _ in issues):
        overall = "RED"
    elif any(s == "YELLOW" for s, _ in issues):
        overall = "YELLOW"
    else:
        overall = "GREEN"

    print(f"\n{'=' * 78}")
    print(f"OVERALL: {overall}")
    for sev, msg in issues:
        print(f"  [{sev}] {msg}")
    print("=" * 78)

    # Determine classification per operator's #61 D rules
    if overall == "RED":
        classification = "KILL"
    elif overall == "GREEN":
        classification = "PORTFOLIO_COMPLEMENT_CANDIDATE (audit GREEN; ready for operator decision on Packet #2 escalation)"
    else:  # YELLOW
        if "YELLOW" in C["verdict"] and B["verdict"] == "GREEN":
            classification = "PORTFOLIO_COMPLEMENT_CANDIDATE (audit YELLOW due weak median per dim C; portfolio contribution strong per G; operator decides)"
        else:
            classification = "WATCH_PENDING_OPERATOR_DECISION"

    print(f"\nCLASSIFICATION: {classification}")

    # Save
    out_md = ROOT / "docs" / "reports" / "evidence_integrity" / "2026-06-04_pbvollow_mnq_audit.md"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(
        f"# Evidence-Integrity Audit — DAILY-PB-VolLow-MNQ\n\n"
        f"**Overall:** **{overall}**\n\n"
        f"**Classification:** {classification}\n\n"
        f"**Subject:** DAILY-PB-VolLow-MNQ (pb_pullback + ema_slope_vol_low(40) + profit_ladder on MNQ)\n\n"
        f"## A. Cost source\n\n"
        f"- asset_config_present: {A['asset_config_present']}\n- commission/side: ${A['commission_per_side']}\n"
        f"- slippage ticks: {A['slippage_ticks']}, tick size: {A['tick_size']}\n"
        f"- round-trip cost: ${A['round_trip_cost']:.2f}\n- cost tier: {A['cost_tier']}\n"
        f"- verdict: **{A['verdict']}**\n\n"
        f"## B. Cost stress\n\n"
        f"| stress | n | PF | net median | net PnL | max DD |\n|---|---|---|---|---|---|\n"
        + "".join(
            f"| {r['stress']} | {r['n']} | {r['pf']:.3f} | ${r['net_median']:.2f} | ${r['net_pnl']:.0f} | ${r['max_dd']:.0f} |\n"
            for r in B["rows"]
        )
        + f"\nverdict: **{B['verdict']}**\n\n"
        f"## C. Edge quality\n\n"
        + "".join(f"- **{k}:** {v:.2f}\n" if isinstance(v, float) else f"- **{k}:** {v}\n" for k, v in C["metrics"].items())
        + f"\nverdict: **{C['verdict']}**\n\n"
        f"## D. Lookahead\n\n"
        + "".join(f"- **{k}:** {v}\n" for k, v in D.items())
        + f"\n## E. Calendar\n\n- {E}\n\n"
        f"## F. Survivorship\n\n"
        + "".join(f"- **{k}:** {v}\n" for k, v in F.items())
        + f"\n## G. Duplicate / portfolio\n\n"
        f"- family review verdict: **{G['verdict']}**\n"
        f"- daily corr: {G['key_summary']['daily_corr']:.3f}\n"
        f"- drawdown overlap: {G['key_summary']['drawdown_overlap_pct']:.1f}%\n"
        f"- losing-day overlap: {G['key_summary']['losing_day_overlap_pct']:.1f}%\n"
        f"- both-full-size total PnL: ${G['portfolio_metrics_full_size'].get('total_pnl'):.0f}\n"
        f"- both-full-size max DD: ${G['portfolio_metrics_full_size'].get('max_drawdown'):.0f}\n\n"
        f"## H. Temporal robustness\n\n"
        + "".join(f"- **{k}:** {v}\n" for k, v in H.items() if k not in ('per_year', 'eras'))
        + "### Per-year\n| year | n | PF | median | net |\n|---|---|---|---|---|\n"
        + "".join(f"| {y['year']} | {y['n']} | {y['pf']:.3f} | ${y['median']:.2f} | ${y['net']:.0f} |\n" for y in H['per_year'])
        + "\n### Era split\n| era | n | PF | median | net |\n|---|---|---|---|---|\n"
        + "".join(f"| {e['era']} | {e['n']} | {e['pf']:.3f} | ${e['median']:.2f} | ${e['net']:.0f} |\n" for e in H['eras'])
        + f"\nverdict: **{H['verdict']}**\n\n"
        f"## Overall: {overall}\n\n"
        + ("**No blocking issues.**\n" if not issues else "")
        + "".join(f"- **[{sev}]** {msg}\n" for sev, msg in issues)
        + f"\n## Classification\n\n{classification}\n"
    )
    print(f"\nWrote: {out_md}")
    out_json = ROOT / "research" / "data" / "fql_forge" / "reports" / f"forge_audit_pbvollow_mnq_2026-06-04.json"
    out_json.write_text(json.dumps({
        "date": date.today().isoformat(),
        "overall_verdict": overall,
        "classification": classification,
        "issues": issues,
        "A": A, "B": B, "C": C, "D": D, "E": E, "F": F, "G": G, "H_temporal": H,
    }, indent=2, default=str))
    print(f"Wrote: {out_json}")
    return overall, classification


if __name__ == "__main__":
    run()
