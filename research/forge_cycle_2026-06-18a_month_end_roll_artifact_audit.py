"""Cycle 2026-06-18a — ARTIFACT + CLEAN-EVENT AUDIT: month-end rates settlement flow (report-only).

#1 danger: ZF continuous-roll stitch artifact. ZF rolls quarterly (~late Feb/May/Aug/Nov, the
month BEFORE delivery Mar/Jun/Sep/Dec), so the month-end K=3 windows of Feb/May/Aug/Nov sit at
the roll stitch -> a gap in the continuous series could FAKE month-end behavior. Test: does the
edge survive on NON-roll-adjacent month-ends?
  roll-adjacent months = {Feb,May,Aug,Nov}; clean months = the other 8 (incl quarter-ends, which
  are post-roll/clean). If edge concentrates in roll-adjacent -> ARTIFACT; if clean months hold -> REAL.
Also: FOMC overlap (clean-event), leg hierarchy ZF/ZN/ZB, roll-gap detection. Preserve 2021 caveat.
Report-only; no mutation. NOT daily WH2 (event/tail).
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
from engine.backtest import get_cost_params  # noqa: E402
from research.forge_fomc_calendar_official import build_official_fomc_calendar  # noqa: E402

ROLL_ADJ = {2, 5, 8, 11}     # Feb/May/Aug/Nov — ZF rolls here (month before Mar/Jun/Sep/Dec delivery)


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def daily_close(a):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{a}_5m.csv")
    dt = pd.to_datetime(df["datetime"])
    s = df.assign(date=dt.dt.normalize()).groupby("date")["close"].last(); s.index = pd.to_datetime(s.index); return s


def me_events(asset, K=3):
    s = daily_close(asset); s = s[s.index.year >= 2019]
    pv = ASSETS[asset]["point_value"]; cp = get_cost_params(asset)
    rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
    days = list(s.index); d = pd.DataFrame({"date": days}); d["y"] = d["date"].dt.year; d["m"] = d["date"].dt.month
    rows = []
    for (y, m), g in d.groupby([d["y"], d["m"]]):
        gd = list(g["date"])
        if len(gd) < K + 1:
            continue
        me = gd[-1]; entry = gd[-1 - K]
        rows.append({"me": me, "entry": entry, "pnl": float((s.loc[me] - s.loc[entry]) * pv - rt),
                     "year": int(y), "month": int(m), "roll_adj": m in ROLL_ADJ})
    return pd.DataFrame(rows), s, pv


def m(tr):
    if tr is None or len(tr) < 6:
        return {"n": len(tr) if tr is not None else 0, "pf": None}
    p = tr["pnl"].to_numpy(); net = float(p.sum()); gross = float(p[p > 0].sum()); g = np.sort(p[p > 0])[::-1]
    py = tr.groupby("year")["pnl"].sum()
    return {"n": len(p), "pf": round(_pf(p), 3), "net": round(net, 0), "median": round(float(np.median(p)), 2),
            "pos_frac": round(float((p > 0).mean()), 2), "max_single_pct": round(float(g[0]) / gross * 100, 1) if gross > 0 else None,
            "top3_pct": round(float(g[:3].sum()) / gross * 100, 1) if gross > 0 else None,
            "max_year_pct": round(float(py.abs().max() / net * 100), 1) if net else None, "yrs_pos": f"{int((py>0).sum())}/{int(py.shape[0])}"}


def run():
    print("Cycle 2026-06-18a — month-end rates ARTIFACT + clean-event audit (REPORT-ONLY)\n", flush=True)
    print("ROLL-ADJACENT months {Feb,May,Aug,Nov} = ZF rolls here -> stitch-artifact risk. CLEAN = other 8.\n", flush=True)

    for asset in ("ZF", "ZN", "ZB"):
        tr, s, pv = me_events(asset)
        allm = m(tr); roll = m(tr[tr["roll_adj"]]); clean = m(tr[~tr["roll_adj"]])
        print(f"  {asset}:", flush=True)
        print(f"    ALL          : n={allm['n']} PF={allm['pf']} net=${allm['net']} pos={allm['pos_frac']} max-yr={allm['max_year_pct']}% yrs+={allm['yrs_pos']}", flush=True)
        print(f"    roll-adjacent: n={roll['n']} PF={roll['pf']} net=${roll['net']} pos={roll['pos_frac']}   (Feb/May/Aug/Nov - artifact risk)", flush=True)
        print(f"    CLEAN (non-roll): n={clean['n']} PF={clean['pf']} net=${clean['net']} pos={clean['pos_frac']} max-single={clean['max_single_pct']}% top3={clean['top3_pct']}% max-yr={clean['max_year_pct']}% yrs+={clean['yrs_pos']}", flush=True)
        if asset == "ZF":
            zf_clean = clean; zf_roll = roll; zf_all = allm; zf_tr = tr

    # roll-gap detection on ZF: largest abs overnight returns, do they cluster in roll-adjacent month-end windows?
    s = daily_close("ZF"); s = s[s.index.year >= 2019]; ret = s.pct_change().abs()
    big = ret.sort_values(ascending=False).head(20)
    big_in_rolladj_me = 0
    for d, _ in big.items():
        if d.month in ROLL_ADJ and d.day >= 23:   # late-month roll-adjacent
            big_in_rolladj_me += 1
    print(f"\n  ROLL-GAP CHECK: of ZF's 20 largest daily moves, {big_in_rolladj_me} fall in late roll-adjacent months "
          f"({'elevated -> stitch present' if big_in_rolladj_me >= 4 else 'not clustered -> limited stitch contamination'})", flush=True)

    # FOMC overlap on ZF month-end windows
    fomc = [pd.Timestamp(c["actual_date"]) for c in build_official_fomc_calendar()]
    ov = sum(1 for _, e in zf_tr.iterrows() if any(e["entry"] - pd.Timedelta(days=2) <= f <= e["me"] + pd.Timedelta(days=2) for f in fomc))
    print(f"  FOMC OVERLAP: {ov}/{len(zf_tr)} month-end windows overlap a FOMC date "
          f"({'low -> clean of FOMC' if ov/len(zf_tr) < 0.2 else 'material'})", flush=True)

    # verdict on the ARTIFACT question (the decisive one)
    clean_ok = (zf_clean["pf"] or 0) >= 1.3 and (zf_clean["max_year_pct"] or 99) < 50 and zf_clean["pos_frac"] >= 0.55
    print("\n  === ARTIFACT VERDICT ===", flush=True)
    if clean_ok:
        verdict = "ARTIFACT-CLEAN: edge survives on NON-roll-adjacent month-ends -> month-end settlement flow is REAL, not a roll stitch"
    else:
        verdict = "ARTIFACT-SUSPECT: edge weak/absent on clean months -> likely roll-stitch contamination; DOWNGRADE"
    print(f"  ZF clean (non-roll) months: PF={zf_clean['pf']} n={zf_clean['n']} max-yr={zf_clean['max_year_pct']}% pos={zf_clean['pos_frac']}", flush=True)
    print(f"  ZF roll-adjacent months:    PF={zf_roll['pf']} n={zf_roll['n']}", flush=True)
    print(f"  -> {verdict}", flush=True)
    print("  LEG HIERARCHY: ZF primary; ZN secondary; ZB per output above. 2021 caveat preserved. Cadence 12/yr = event/tail NOT daily WH2.", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-18a_month_end_artifact_audit.json"
    out.write_text(json.dumps({"cycle": "2026-06-18a_month_end_artifact_audit", "mode": "Lane 1 audit; report-only; NON-WIRED",
        "zf_all": zf_all, "zf_roll_adjacent": zf_roll, "zf_clean_nonroll": zf_clean,
        "roll_gap_big_moves_in_rolladj_me": big_in_rolladj_me, "fomc_overlap": f"{ov}/{len(zf_tr)}", "verdict": verdict,
        "boundaries": "no mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; artifact audit; no mutation)", flush=True)


if __name__ == "__main__":
    run()
