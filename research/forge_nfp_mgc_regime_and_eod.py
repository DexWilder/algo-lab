"""NFP-MGC regime overlay (H fix) + EOD sibling variant deep-screen.

Per operator approvals 2026-06-04 (#33 + #34).

H regime overlay: previously errored on `to_timestamp("end")` — pandas freq
string issue. Fix by using `to_timestamp(how="end")` or `freq` correctly.
Diagnostic only; do not add a filter that shrinks sample dangerously.

EOD variant: exit at +72 bars (~6h late session) instead of +24 bars. Full
8-dimension deep-screen against base 2h candidate.

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

from research.event_window_engine import generate_event_window_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from research.forge_nfp_calendar_verify import (  # noqa: E402
    build_verified_nfp_calendar, _events_with_time,
)
from research.fundamentals_cache import load_series  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest  # noqa: E402


def _bake_calendar():
    cal = build_verified_nfp_calendar(2019, 2026)
    return [c["actual_date"] for c in cal]


def _run(events, exit_bars=24, entry_bars=1, commission_mult=1.0, slippage_mult=1.0,
         label="EVT-NFP-MGC"):
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    cfg = ASSETS["MGC"]
    sigs = generate_event_window_signals(
        df, events=events, entry_offset_bars=entry_bars,
        exit_offset_bars=exit_bars, direction="long",
    )
    res = run_backtest(
        df, sigs, mode="both", point_value=cfg["point_value"], symbol="MGC",
        commission_per_side=0.62 * commission_mult,
        slippage_ticks=int(np.ceil(1 * slippage_mult)), tick_size=0.1,
    )
    m = _metrics(res["trades_df"], label, costs=res["stats"]["costs"])
    return m, res["trades_df"]


# ─────────────────────────────────────────────────────────────────────────────
# H. Regime overlay (fixed)
# ─────────────────────────────────────────────────────────────────────────────

def regime_overlay(trades: pd.DataFrame):
    """Diagnostic-only regime splits — do not add a filter."""
    print("\n=== H. REGIME OVERLAYS (diagnostic) ===")
    df = trades.copy()
    df["entry_dt"] = pd.to_datetime(df["entry_time"])
    # Map each trade to its month-end Timestamp for joining with monthly series
    df["month_end"] = df["entry_dt"].dt.to_period("M").apply(
        lambda p: pd.Timestamp(p.year, p.month, 1) + pd.offsets.MonthEnd(0)
    )
    out = {}

    # 1. DXY rising vs falling month
    try:
        dxy = load_series("usd_broad")
        d_dxy = dxy.diff()
        rising_mask = df["month_end"].map(lambda t: bool(d_dxy.get(t, 0) > 0))
        for label, mask in [("dxy_rising", rising_mask), ("dxy_falling", ~rising_mask)]:
            sub = df[mask]
            if len(sub) < 5:
                out[label] = {"n": int(len(sub)), "verdict": "insufficient sample"}
                continue
            pnl = sub["pnl"].values
            w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
            pf = float(w/l) if l > 0 else float("inf")
            out[label] = {"n": int(len(sub)), "pf": pf,
                          "median": float(np.median(pnl)), "net": float(pnl.sum())}
            print(f"  {label:20s}: n={out[label]['n']:3d} PF={pf:.3f} median=${out[label]['median']:.2f}")
    except Exception as e:
        out["dxy_error"] = str(e)
        print(f"  DXY overlay error: {e}")

    # 2. Realized vol of MGC monthly returns: above vs below median
    try:
        mgc_5m = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
        mgc_5m["datetime"] = pd.to_datetime(mgc_5m["datetime"])
        mgc_monthly = mgc_5m.set_index("datetime")["close"].resample("ME").last()
        rets = np.log(mgc_monthly / mgc_monthly.shift(1))
        rv = rets.rolling(6).std()
        rv_median = rv.median()
        hi_mask = df["month_end"].map(lambda t: bool(rv.get(t, 0) > rv_median))
        for label, mask in [("vol_above_median", hi_mask), ("vol_below_median", ~hi_mask)]:
            sub = df[mask]
            if len(sub) < 5:
                out[label] = {"n": int(len(sub)), "verdict": "insufficient sample"}
                continue
            pnl = sub["pnl"].values
            w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
            pf = float(w/l) if l > 0 else float("inf")
            out[label] = {"n": int(len(sub)), "pf": pf,
                          "median": float(np.median(pnl)), "net": float(pnl.sum())}
            print(f"  {label:20s}: n={out[label]['n']:3d} PF={pf:.3f} median=${out[label]['median']:.2f}")
    except Exception as e:
        out["vol_error"] = str(e)
        print(f"  Vol overlay error: {e}")

    # 3. Real yield rising vs falling (from fundamentals_cache)
    try:
        ry = load_series("real_yield_10y")
        d_ry = ry.diff()
        rising = df["month_end"].map(lambda t: bool(d_ry.get(t, 0) > 0))
        for label, mask in [("real_yield_rising", rising), ("real_yield_falling", ~rising)]:
            sub = df[mask]
            if len(sub) < 5:
                out[label] = {"n": int(len(sub)), "verdict": "insufficient sample"}
                continue
            pnl = sub["pnl"].values
            w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
            pf = float(w/l) if l > 0 else float("inf")
            out[label] = {"n": int(len(sub)), "pf": pf,
                          "median": float(np.median(pnl)), "net": float(pnl.sum())}
            print(f"  {label:20s}: n={out[label]['n']:3d} PF={pf:.3f} median=${out[label]['median']:.2f}")
    except Exception as e:
        out["realyield_error"] = str(e)

    return out


# ─────────────────────────────────────────────────────────────────────────────
# EOD sibling deep-screen
# ─────────────────────────────────────────────────────────────────────────────

def eod_deep_screen(events):
    """Full deep-screen on EVT-NFP-MGC-Long-EOD (exit at +72 bars)."""
    print("\n========== EVT-NFP-MGC-Long-EOD (sibling) deep-screen ==========")

    # Baseline (1x cost, +72 bar exit)
    m_base, trades = _run(events, exit_bars=72, label="EVT-NFP-MGC-Long-EOD")
    print(f"\nBaseline (verified cal, exit +72): n={m_base['n']} PF={m_base['pf']:.3f} "
          f"median=${m_base['median']:.2f} max-yr={m_base.get('max_year_share_pct'):.1f}%")

    # Cost stress
    print("\nCost stress:")
    cost_rows = []
    for label, cm, sm in [("baseline", 1.0, 1.0), ("1.5x", 1.5, 1.0),
                          ("2x", 2.0, 1.0), ("3x", 3.0, 1.0),
                          ("2slip", 1.0, 2.0), ("2c2s", 2.0, 2.0)]:
        m, _ = _run(events, exit_bars=72, commission_mult=cm, slippage_mult=sm,
                    label=f"EOD-{label}")
        cost_rows.append({"label": label, "n": m["n"], "pf": float(m["pf"]),
                          "median": float(m["median"]), "net": float(m["net"])})
        print(f"  {label:10s}: n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f}")
    survives_2x = next(r["pf"] >= 1.30 and r["median"] > 0 for r in cost_rows if r["label"] == "2x")

    # Temporal robustness
    df = trades.copy()
    df["entry_dt"] = pd.to_datetime(df["entry_time"])
    df["year"] = df["entry_dt"].dt.year
    per_year = []
    for y, g in df.groupby("year"):
        pnl = g["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w/l) if l > 0 else float("inf")
        per_year.append({"year": int(y), "n": int(len(g)), "pf": pf, "net": float(pnl.sum())})
    yrs_pos = sum(1 for r in per_year if r["net"] > 0)
    df = df.sort_values("entry_dt").reset_index(drop=True)
    cuts = np.linspace(0, len(df), 4).astype(int)
    eras = []
    for i in range(3):
        sub = df.iloc[cuts[i]:cuts[i+1]]
        if sub.empty: continue
        pnl = sub["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w/l) if l > 0 else float("inf")
        eras.append({"era": i+1, "n": int(len(sub)), "pf": pf, "net": float(pnl.sum())})
    print("\nTemporal:")
    yr_str = ", ".join(f"{r['year']}: PF={r['pf']:.2f}" for r in per_year)
    print(f"  per-year: {yrs_pos}/{len(per_year)} positive ({yr_str})")
    era_str = " | ".join(f"E{e['era']}: PF={e['pf']:.2f}" for e in eras)
    print(f"  eras: {era_str}")

    # Year-exclusion
    base_w = df["pnl"][df["pnl"]>0].sum(); base_l = -df["pnl"][df["pnl"]<0].sum()
    base_pf = float(base_w/base_l)
    year_excl = []
    for y in sorted(df["year"].unique()):
        sub = df[df["year"] != y]
        w = sub.loc[sub["pnl"]>0,"pnl"].sum(); l = -sub.loc[sub["pnl"]<0,"pnl"].sum()
        pf = float(w/l) if l > 0 else float("inf")
        year_excl.append({"excluded": int(y), "n": int(len(sub)), "pf": pf,
                          "median": float(np.median(sub["pnl"].values))})
    excl_pfs = [r["pf"] for r in year_excl if np.isfinite(r["pf"])]
    print(f"  year-exclusion PF range: [{min(excl_pfs):.3f}, {max(excl_pfs):.3f}]")

    # Rolling 12-event
    pnl_arr = df["pnl"].values
    roll = []
    for i in range(12, len(pnl_arr)+1):
        win = pnl_arr[i-12:i]
        w = win[win > 0].sum(); l = -win[win < 0].sum()
        pf = w/l if l > 0 else float("inf")
        roll.append(pf)
    rp = np.array(roll)
    rp_finite = rp[np.isfinite(rp)]
    worst = float(rp_finite.min())
    pct_gt_1 = float((rp > 1.0).mean() * 100)
    pct_gt_12 = float((rp > 1.2).mean() * 100)
    print(f"  rolling 12-event: worst PF={worst:.3f}, %>1.0={pct_gt_1:.0f}%, %>1.2={pct_gt_12:.0f}%")

    # Trade level
    pnl = trades["pnl"].values
    sorted_d = np.sort(pnl)[::-1]
    top1 = float(sorted_d[0])
    top3 = float(sorted_d[:3].sum())
    top1_share = 100 * top1 / pnl.sum() if pnl.sum() > 0 else float("nan")
    top3_share = 100 * top3 / pnl.sum() if pnl.sum() > 0 else float("nan")
    win_rate = 100 * (pnl > 0).mean()
    print(f"\nTrade-level: win rate={win_rate:.1f}%, top-1 share={top1_share:.1f}%, top-3={top3_share:.1f}%")

    # Entry-delay stability (sample 3 points)
    print("\nEntry-delay stability:")
    delay_rows = []
    for ed, tag in [(1, "+1bar"), (3, "+3bar"), (6, "+6bar")]:
        m, _ = _run(events, exit_bars=72, entry_bars=ed, label=f"EOD-{tag}")
        delay_rows.append({"entry": tag, "n": m["n"], "pf": float(m["pf"]), "median": float(m["median"])})
        print(f"  entry {tag} exit +72: n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f}")
    entry_stable = all(r["pf"] > 1.5 and r["median"] > 0 for r in delay_rows)

    # Compare to 2h base
    m_2h, _ = _run(events, exit_bars=24, label="EVT-NFP-MGC-Long-2h")
    print(f"\nVs 2h base: 2h PF={m_2h['pf']:.3f} median=${m_2h['median']:.2f} | EOD PF={m_base['pf']:.3f} median=${m_base['median']:.2f}")

    # Verdict per operator rule
    # - If EOD stronger AND equally robust → SIBLING
    # - If EOD higher PF but more concentrated → WATCH not better
    # - If depends on one year/few trades → ARCHITECTURAL_REJECT
    max_yr_eod = m_base.get("max_year_share_pct", 100)
    if yrs_pos < len(per_year) * 0.6:
        verdict = "ARCHITECTURAL_REJECT (< 60% yrs positive)"
    elif top1_share > 30:
        verdict = "ARCHITECTURAL_REJECT (top-1 trade > 30%)"
    elif any(e["pf"] < 1.0 and np.isfinite(e["pf"]) for e in eras):
        verdict = "ARCHITECTURAL_REJECT (losing era)"
    elif min(excl_pfs) < 1.5:
        verdict = "WATCH (year-exclusion shows concentration vs 2h base)"
    elif (m_base["pf"] > m_2h["pf"] and survives_2x and entry_stable
          and yrs_pos >= len(per_year) * 0.75 and max_yr_eod < 50):
        verdict = "PAPER_PACKET_DRAFT_CANDIDATE_SIBLING"
    elif m_base["pf"] >= 1.30 and m_base["median"] > 0:
        verdict = "WATCH (passes basic gates but does not improve on 2h)"
    else:
        verdict = "KILL"

    print(f"\nFINAL EOD verdict: {verdict}")

    return {"baseline": dict(m_base), "cost_rows": cost_rows,
            "per_year": per_year, "eras": eras,
            "year_exclusion": year_excl,
            "rolling12": {"worst": worst, "pct_gt_1": pct_gt_1, "pct_gt_1p2": pct_gt_12},
            "trade_level": {"win_rate": win_rate, "top1_share": top1_share, "top3_share": top3_share},
            "entry_delay": delay_rows, "entry_stable": entry_stable,
            "vs_2h_base": {"pf_2h": float(m_2h["pf"]), "pf_eod": float(m_base["pf"])},
            "verdict": verdict}


def run():
    events_str = _bake_calendar()
    events = _events_with_time(events_str)

    # Re-pull baseline trades for regime overlay
    m_base, trades_base = _run(events, exit_bars=24, label="EVT-NFP-MGC-Long-2h-base")
    H = regime_overlay(trades_base)
    EOD = eod_deep_screen(events)

    out_dir = ROOT / "research" / "data" / "fql_forge" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_iso = date.today().isoformat()
    payload = {
        "date": date_iso,
        "approvals": ["#33 fix regime overlay", "#34 NFP-MGC-EOD variant"],
        "regime_overlay_2h_base": H,
        "eod_sibling_deep_screen": EOD,
    }
    (out_dir / f"forge_nfp_mgc_regime_eod_{date_iso}.json").write_text(
        json.dumps(payload, indent=2, default=str)
    )
    print(f"\nWrote: forge_nfp_mgc_regime_eod_{date_iso}.json")
    return payload


if __name__ == "__main__":
    run()
