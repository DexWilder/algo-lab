"""Cycle 2026-06-23f — O1-z>1.5 FULL-GATE audit (report-only).

Operator correction (2026-06-23): O1-z>1.0 is mechanism EVIDENCE; O1-z>1.5 is the CANDIDATE (cost-robust).
Promote z>1.5 to main variant and full-gate it BEFORE the result gets excited. Verdict stays
STRUCTURE_FOUND / COST-GATED / REPORT-ONLY unless it clears everything cleanly.

Gates: cadence | date-split | rolling-year | cost-stress to 60bps | top-k dependency | drawdown + per-trade
MAE/tail | crash-regime (2022 + worst BTC DD) | vs unconditional BTC hold | correlation to liquid books
(MNQ/MGC/MES daily) | calendar-regime overlap (month-end / OPEX-week / pre-holiday).
Mechanism (predeclared, NO flip): rich VRP (DVOL−realized z>1.5) -> LONG BTC spot next day.
Report-only; no mutation; capital gate unchanged.
"""
from __future__ import annotations

import datetime as dt
import json
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "research" / "data" / "fql_forge" / "reports"


def _get(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())


def coinbase_daily(prod="BTC-USD", start_year=2021):
    rows = []; ce = dt.datetime.utcnow()
    for _ in range(30):
        cs = ce - dt.timedelta(days=290)
        d = _get(f"https://api.exchange.coinbase.com/products/{prod}/candles?granularity=86400"
                 f"&start={cs.strftime('%Y-%m-%dT%H:%M:%SZ')}&end={ce.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        if not d:
            break
        rows += d; ce = cs
        if cs < dt.datetime(start_year, 1, 1):
            break
        time.sleep(0.15)
    c = pd.DataFrame(rows, columns=["t", "low", "high", "open", "close", "vol"])
    c["day"] = pd.to_datetime(pd.to_numeric(c["t"]), unit="s", utc=True).dt.normalize()
    c["spot"] = pd.to_numeric(c["close"], errors="coerce")
    return c.drop_duplicates("day").set_index("day")["spot"].sort_index()


def asset_daily(sym):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{sym}_5m.csv"); d = pd.to_datetime(df["datetime"])
    r = df.assign(x=d.dt.normalize()).groupby("x")["close"].last().pct_change()
    r.index = pd.to_datetime(r.index).tz_localize("UTC"); return r.rename(sym)


def _pf(a):
    a = np.asarray(a, float); l = -a[a < 0].sum()
    return float(a[a > 0].sum() / l) if l > 0 else float("inf")


def _opex_week(idx):
    # week containing the 3rd Friday of the month
    out = []
    for ts in idx:
        t = ts.tz_localize(None).normalize()
        third_fri = [d for d in pd.date_range(t.replace(day=1), periods=31, freq="D") if d.month == t.month and d.weekday() == 4][2]
        out.append(abs((t - third_fri).days) <= 3)
    return np.array(out)


def _month_end(idx):
    return np.array([ts.day >= 25 or ts.day <= 2 for ts in idx])   # last-week / first-2-days proxy


def _pre_holiday(idx):
    # US market closures (fixed-ish): NYD, MLK, Pres, GoodFri-ish skip, Memorial, Juneteenth, July4, Labor, Thanksgiving, Xmas
    hol = set()
    for y in range(2021, 2027):
        for m, d in [(1, 1), (7, 4), (12, 25), (6, 19)]:
            hol.add(dt.date(y, m, d))
        # Thanksgiving = 4th Thu Nov
        thurs = [dt.date(y, 11, x) for x in range(1, 31) if dt.date(y, 11, x).weekday() == 3]
        hol.add(thurs[3])
    days = pd.to_datetime(sorted(hol))
    out = []
    for ts in idx:
        t = ts.tz_localize(None).normalize()
        out.append(any(0 < (h - t).days <= 2 for h in days))
    return np.array(out)


def run():
    print("Cycle 2026-06-23f — O1-z>1.5 FULL-GATE audit (report-only)\n", flush=True)
    dvol = pd.read_csv(ROOT / "data" / "feeds" / "deribit_DVOL_BTC.csv", index_col=0)
    dvol.index = pd.to_datetime(dvol.index, utc=True); dvol = dvol.iloc[:, 0]
    spot = coinbase_daily()
    mnq, mgc, mes = asset_daily("MNQ"), asset_daily("MGC"), asset_daily("MES")

    df = pd.DataFrame({"spot": spot, "dvol": dvol}).dropna().sort_index()
    df["ret"] = df["spot"].pct_change()
    df["rv"] = df["ret"].rolling(30, min_periods=20).std() * np.sqrt(365) * 100
    df["vrp"] = df["dvol"] - df["rv"]
    df["vz"] = (df["vrp"] - df["vrp"].rolling(120, min_periods=60).mean()) / df["vrp"].rolling(120, min_periods=60).std()
    df["rf"] = df["ret"].shift(-1)
    df = df.dropna(subset=["vz", "rf"])

    Z = 1.5
    t = df[df["vz"] > Z].copy()
    t["pnl10"] = t["rf"] - 0.0010
    p = t["pnl10"].to_numpy(); h = len(p) // 2
    R = {"variant": f"O1 BTC DVOL-VRP z>{Z} LONG", "n": int(len(p))}

    # --- cadence ---
    span_days = (t.index.max() - t.index.min()).days
    R["cadence"] = {"n": int(len(p)), "per_year": round(len(p) / (span_days / 365), 1),
                    "span": f"{t.index.min().date()}..{t.index.max().date()}",
                    "median_gap_days": int(pd.Series(t.index).diff().dt.days.median())}

    # --- core / date-split / cost ---
    R["pf_10bps"] = round(_pf(p), 3); R["mean_bps"] = round(float(p.mean()) * 1e4, 1)
    R["win_pct"] = round(float((p > 0).mean()) * 100, 1)
    R["date_split"] = {"h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3),
                       "h1_mean_bps": round(float(p[:h].mean()) * 1e4, 1), "h2_mean_bps": round(float(p[h:].mean()) * 1e4, 1)}
    R["cost_stress"] = {f"{c}bps": round(_pf((t["rf"] - c / 1e4).to_numpy()), 3) for c in [10, 20, 30, 40, 50, 60]}
    R["cost_stress_mean_bps"] = {f"{c}bps": round(float((t["rf"] - c / 1e4).mean()) * 1e4, 1) for c in [10, 20, 30, 40, 50, 60]}

    # --- rolling year ---
    by_yr = t.assign(yr=t.index.year).groupby("yr")["pnl10"]
    R["per_year"] = {int(y): {"n": int(g.shape[0]), "pf": round(_pf(g.values), 3), "net_pct": round(g.sum() * 100, 1), "mean_bps": round(g.mean() * 1e4, 1)} for y, g in by_yr}
    R["yrs_pos"] = f"{sum(1 for v in R['per_year'].values() if v['net_pct'] > 0)}/{len(R['per_year'])}"

    # --- top-k dependency ---
    gp = np.sort(p[p > 0])[::-1]; gs = gp.sum()
    R["topk_dependency"] = {"max_single_pct": round(gp[0] / gs * 100, 1), "top3_pct": round(gp[:3].sum() / gs * 100, 1),
                            "top5_pct": round(gp[:5].sum() / gs * 100, 1), "pf_ex_top3": round(_pf(np.concatenate([np.sort(p[p > 0])[::-1][3:], p[p <= 0]])), 3)}

    # --- drawdown + per-trade tail / MAE proxy ---
    eq = np.cumsum(p); dd = eq - np.maximum.accumulate(eq)
    R["drawdown"] = {"equity_maxdd_pct": round(float(dd.min()) * 100, 1),
                     "worst_trade_pct": round(float(p.min()) * 100, 2), "best_trade_pct": round(float(p.max()) * 100, 2),
                     "p05_trade_pct": round(float(np.percentile(p, 5)) * 100, 2), "p95_trade_pct": round(float(np.percentile(p, 95)) * 100, 2),
                     "downside_dev_bps": round(float(p[p < 0].std()) * 1e4, 1)}

    # --- crash regime: 2022 + worst BTC drawdown spell ---
    spot_dd = (spot / spot.cummax() - 1)
    crash_mask = spot_dd.reindex(t.index, method="ffill") < -0.50    # BTC >50% off ATH
    cr = t["pnl10"][crash_mask.values]
    R["crash_regime"] = {"yr2022": R["per_year"].get(2022),
                         "deep_btc_dd_gt50pct": {"n": int(len(cr)), "pf": round(_pf(cr.to_numpy()), 3) if len(cr) else None, "net_pct": round(cr.sum() * 100, 1) if len(cr) else None},
                         "note": "fade-rich-DVOL fails when fear is UNDERpriced (structural crash) — see crash guard packet"}

    # --- vs unconditional BTC hold (same window) ---
    base = df.loc[t.index.min():t.index.max(), "rf"]
    R["vs_uncond_hold"] = {"o1_mean_bps": R["mean_bps"], "uncond_mean_bps": round(float(base.mean()) * 1e4, 1),
                           "o1_sharpe_ann": round(float(p.mean()) / float(p.std()) * np.sqrt(len(p) / (span_days / 365)), 2) if p.std() > 0 else None,
                           "uncond_sharpe_ann": round(float(base.mean()) / float(base.std()) * np.sqrt(365), 2) if base.std() > 0 else None,
                           "edge_over_hold": bool(R["mean_bps"] > round(float(base.mean()) * 1e4, 1))}

    # --- correlations to liquid books + calendar-regime overlap ---
    pnl_s = t["pnl10"].rename("o1")
    R["corr_liquid_books"] = {}
    for s in (mnq, mgc, mes):
        al = pd.concat([pnl_s, s], axis=1).dropna()
        R["corr_liquid_books"][s.name] = round(float(al["o1"].corr(al[s.name])), 3) if len(al) > 30 else None
    idx = t.index
    ovl = {"month_end": _month_end(idx), "opex_week": _opex_week(idx), "pre_holiday": _pre_holiday(idx)}
    R["calendar_overlap"] = {k: {"share_of_trades_pct": round(float(m.mean()) * 100, 1),
                                 "pnl_in_window_pct": round(float(t["pnl10"].to_numpy()[m].sum()) * 100, 1),
                                 "pnl_out_window_pct": round(float(t["pnl10"].to_numpy()[~m].sum()) * 100, 1)} for k, m in ovl.items()}
    R["calendar_overlap"]["note"] = "low in-window share => O1 risk does NOT cluster where sparse rates/opex/holiday sleeves live (diversifier). Sparse-sleeve daily Pearson is ~0 by construction; bad-day overlap needs reconstructed sleeve PnL (deferred)."

    # --- verdict (deliberately conservative) ---
    cost40_ok = R["cost_stress"]["40bps"] >= 1.15
    structure_ok = (R["pf_10bps"] >= 1.3 and R["date_split"]["h1_pf"] > 1.0 and R["date_split"]["h2_pf"] > 1.0
                    and R["topk_dependency"]["max_single_pct"] < 35 and "0/" not in R["yrs_pos"]
                    and R["vs_uncond_hold"]["edge_over_hold"] and all(abs(v) < 0.3 for v in R["corr_liquid_books"].values() if v is not None))
    R["verdict"] = "STRUCTURE_FOUND_COST_GATED_REPORT_ONLY"
    R["deployable"] = False
    R["gate_summary"] = {"structure_clean": structure_ok, "cost_robust_to_40bps": cost40_ok,
                         "note": "Candidate, NOT deployable. Forward-clock only AFTER operator pins real BTC-spot execution cost. z>1.0 retained as mechanism evidence."}

    for k, v in R.items():
        print(f"  {k}: {json.dumps(v) if isinstance(v, (dict, list)) else v}", flush=True)
    out = REPORTS / "forge_cycle_2026-06-23f_o1_z15_full_gate.json"
    out.write_text(json.dumps({"cycle": "2026-06-23f_o1_z15_full_gate", "mode": "report-only; NON-WIRED", "result": R,
        "boundaries": "no mutation; no promotion; mechanism-implied direction; z>1.5 candidate / z>1.0 evidence"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; O1-z>1.5 full gate; no mutation)", flush=True)


if __name__ == "__main__":
    run()
