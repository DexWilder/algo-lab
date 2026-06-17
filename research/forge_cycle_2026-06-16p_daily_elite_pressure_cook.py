"""Cycle 2026-06-16p — DAILY-ELITE pressure-cooker cheap-screen (report-only).

Screens two tranches against the daily-elite target profile, brutal kill rules:
  T1 = EXISTING engine primitives never broadly screened off-MNQ (orb_failure_reversal,
       opening_drive_exhaustion, vwap_reclaim, afternoon_continuation, donchian_breakout,
       vwap_continuation) — map to wishlist (failed-break, first-hour failed drive, reclaim,
       afternoon continuation, post-trend exhaustion).
  T2 = NEW self-contained daily-structure primitives (inside_day_expansion,
       narrow_range_expansion, outside_day_reversal, prior_close_reclaim,
       post_large_loss_snapback) injected into ENTRY_MAP at runtime (no production change).

Every candidate: full WH2 board (PF/median/H1H2/concentration/year/era/yr-excl/single-event/
DD/cost) + correlation to BOTH MNQ workhorses + cadence tier. Reversion mechanisms use
filter=none (filter pre-flight rule). NO mutation, NO activation, NON-WIRED.
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
import research.crossbreeding.crossbreeding_engine as ce  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from research.wh2_daily_primitives import NEW_PRIMITIVES, build_daily_map  # noqa: E402

# inject new primitives into a runtime copy of ENTRY_MAP (no production mutation)
for _name, (_fn, _filt) in NEW_PRIMITIVES.items():
    ce.ENTRY_MAP[_name] = _fn

_DAILY_MAP_CACHE = {}


def _pf(p):
    a = np.asarray(p, float); w = a[a > 0].sum(); l = -a[a < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def run_xb(asset, entry, filter_name="ema_slope", needs_daily_map=False):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]; costs = get_cost_params(asset)
    params = {}
    if needs_daily_map:
        if asset not in _DAILY_MAP_CACHE:
            _DAILY_MAP_CACHE[asset] = build_daily_map(df)
        params["daily_map"] = _DAILY_MAP_CACHE[asset]
    sigs = ce.generate_crossbred_signals(df, entry_name=entry, exit_name="profit_ladder",
                                          filter_name=filter_name, params=params)
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol=asset,
                       commission_per_side=costs["commission_per_side"], slippage_ticks=costs["slippage_ticks"],
                       tick_size=costs["tick_size"])
    return _metrics(res["trades_df"], f"{asset}-{entry}", costs=res["stats"]["costs"]), res["trades_df"]


def conc(tr):
    g = tr[tr["pnl"] > 0]["pnl"].sort_values(ascending=False); gp = float(g.sum())
    t = lambda k: round(float(g.head(k).sum()) / gp * 100, 1) if gp > 0 else None
    return t(3), t(5), t(10)


def dd_dur(tr):
    eq = tr.sort_values("entry_dt")["pnl"].cumsum().to_numpy()
    dd = eq - np.maximum.accumulate(eq); longest = cur = 0
    for b in (dd < 0):
        cur = cur + 1 if b else 0; longest = max(longest, cur)
    return round(float(dd.min()), 0), int(longest)


def dcorr(a, b):
    a = a.copy(); a["d"] = pd.to_datetime(a["entry_time"]).dt.date
    b = b.copy(); b["d"] = pd.to_datetime(b["entry_time"]).dt.date
    al = pd.concat([a.groupby("d")["pnl"].sum(), b.groupby("d")["pnl"].sum()], axis=1, keys=["a", "b"]).fillna(0.0)
    return round(float(al["a"].corr(al["b"])), 3)


def board(asset, entry, filt, needs_dm, mnq_orb, mnq_srr):
    try:
        m, tr = run_xb(asset, entry, filt, needs_dm)
    except Exception as e:
        return {"asset": asset, "mechanism": entry, "verdict": "ERROR", "err": str(e)[:140]}
    if tr is None or tr.empty or m["n"] < 40:
        return {"asset": asset, "mechanism": entry, "n": int(m.get("n", 0)), "verdict": "KILL_low_n", "filter": filt}
    tr = tr.copy(); tr["entry_dt"] = pd.to_datetime(tr["entry_time"]); tr["year"] = tr["entry_dt"].dt.year
    net = float(tr["pnl"].sum()); ny = int(tr["year"].nunique()); tpy = round(m["n"] / max(ny, 1), 1)
    t3, t5, t10 = conc(tr); maxdd, ddur = dd_dur(tr)
    yx = [round(_pf(tr[tr["year"] != y]["pnl"]), 3) for y in sorted(tr["year"].unique())]
    st = tr.sort_values("entry_dt").reset_index(drop=True); cuts = np.linspace(0, len(st), 4).astype(int)
    eras = [round(_pf(st.iloc[cuts[i]:cuts[i + 1]]["pnl"]), 3) for i in range(3)]
    mx = tr["pnl"].max(); mn = tr["pnl"].min(); single = round(max(abs(mx), abs(mn)) / net * 100, 1) if net else None
    c_orb = dcorr(tr, mnq_orb); c_srr = dcorr(tr, mnq_srr); cmax = max(abs(c_orb), abs(c_srr))
    cadence = "true-daily" if (tpy >= 120 and m["n"] >= 500) else ("near-daily" if tpy >= 90 else ("weekly-frequent" if tpy >= 30 else "sparse"))
    quality = (m["pf"] > 1.2 and m["median"] >= 0 and m["h1_pf"] > 1.0 and m["h2_pf"] > 1.0
               and (t3 or 99) < 30 and (t5 or 99) < 45 and (t10 or 99) < 55 and m["max_year_share_pct"] < 40
               and (m["years_positive"] / max(m["n_years"], 1)) >= 0.75 and all(e > 1.0 for e in eras)
               and min(yx) > 1.15 and (single or 99) < 25)
    decor = cmax < 0.3; lite = cmax >= 0.5
    if lite and asset in ("MES", "MYM", "M2K"):
        v = "REJECT_MNQ_COUSIN"
    elif not quality:
        v = "KILL"
    elif not decor:
        v = "WATCH_corr"
    elif cadence in ("true-daily", "near-daily"):
        v = "PACKET_CANDIDATE" if cadence == "true-daily" else "FORWARD_CLOCK_CREDIBLE"
    else:
        v = "FORWARD_CLOCK_CREDIBLE"
    return {"asset": asset, "mechanism": entry, "filter": filt, "n": m["n"], "trades_per_yr": tpy, "cadence": cadence,
            "pf": round(m["pf"], 3), "net": round(net, 0), "median": round(m["median"], 2),
            "h1_pf": round(m["h1_pf"], 3), "h2_pf": round(m["h2_pf"], 3), "max_year_pct": round(m["max_year_share_pct"], 1),
            "years_pos": f"{m['years_positive']}/{m['n_years']}", "top3": t3, "top5": t5, "top10": t10,
            "max_dd": maxdd, "dd_dur": ddur, "cost_ratio_pct": m["cost_ratio_pct"], "era_pf": eras, "yr_excl_min": min(yx),
            "single_event_pct": single, "corr_orb": c_orb, "corr_srr": c_srr, "verdict": v}


def run():
    print("Cycle 2026-06-16p — DAILY-ELITE pressure-cooker (REPORT-ONLY)\n", flush=True)
    print("MNQ workhorse references...", flush=True)
    _, mnq_orb = run_xb("MNQ", "orb_breakout"); _, mnq_srr = run_xb("MNQ", "stop_run_reversal")

    ASSETS_INTRADAY = ["MGC", "MES", "MYM", "MCL"]
    ASSETS_ALL = ["MGC", "MES", "MYM", "MCL", "ZN", "ZF"]
    T1 = [  # (entry, filter, assets) — existing primitives, wishlist-mapped
        ("orb_failure_reversal", "none", ASSETS_ALL),
        ("opening_drive_exhaustion", "none", ASSETS_INTRADAY),
        ("vwap_reclaim", "none", ASSETS_INTRADAY),
        ("afternoon_continuation", "ema_slope", ASSETS_INTRADAY),
        ("donchian_breakout", "ema_slope", ASSETS_ALL),
        ("vwap_continuation", "ema_slope", ASSETS_INTRADAY),
    ]
    T2 = [(name, filt, ASSETS_ALL) for name, (_fn, filt) in NEW_PRIMITIVES.items()]

    rows = []
    for tranche, spec in [("T1", T1), ("T2", T2)]:
        print(f"\n--- {tranche} ---", flush=True)
        for entry, filt, assets in spec:
            needs_dm = entry in NEW_PRIMITIVES
            for a in assets:
                r = board(a, entry, filt, needs_dm, mnq_orb, mnq_srr); r["tranche"] = tranche; rows.append(r)
                if r["verdict"] in ("ERROR",) or r["verdict"].startswith("KILL"):
                    print(f"  {a:>4} {entry:<26} {filt:<9} -> {r['verdict']} (n={r.get('n','?')})", flush=True)
                else:
                    print(f"  {a:>4} {entry:<26} {filt:<9} -> {r['verdict']:<22} n={r['n']:>4} {r['trades_per_yr']:>5}/yr "
                          f"PF={r['pf']:.2f} med=${r['median']:.1f} H1/H2={r['h1_pf']:.2f}/{r['h2_pf']:.2f} "
                          f"t3/10={r['top3']}/{r['top10']} corr={max(abs(r['corr_orb']),abs(r['corr_srr'])):+.2f}", flush=True)

    survivors = [r for r in rows if r["verdict"] in ("PACKET_CANDIDATE", "FORWARD_CLOCK_CREDIBLE", "WATCH_corr")]
    print("\n=== SURVIVOR BOARD ===", flush=True)
    if not survivors:
        print("  (none cleared the daily-elite gauntlet this cycle)", flush=True)
    for r in sorted(survivors, key=lambda r: (r["verdict"], -r["pf"])):
        print(f"  {r['verdict']:<22} {r['asset']}-{r['mechanism']:<26} PF {r['pf']:.2f} {r['trades_per_yr']}/yr "
              f"[{r['cadence']}] corr {max(abs(r['corr_orb']),abs(r['corr_srr'])):.2f}", flush=True)

    from collections import Counter
    tally = Counter(r["verdict"] for r in rows)
    print(f"\n  TALLY: {dict(tally)}  (total {len(rows)} screened)", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-16p_daily_elite_pressure_cook.json"
    out.write_text(json.dumps({"cycle": "2026-06-16p_daily_elite_pressure_cook",
        "mode": "Lane B report-only; daily-elite pressure-cooker; NON-WIRED",
        "screened": rows, "survivors": survivors, "tally": dict(tally),
        "boundaries": "no activation/registry/scheduler/portfolio/order mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)
    print("(report-only; no activation/registry/scheduler/portfolio/order mutation)", flush=True)


if __name__ == "__main__":
    run()
