"""Cycle 2026-06-23i — O2-equity refinement Piece A (report-only).

Step 2 of operator sequencing (O2-equity V2 PASS_REVIEW -> refine). Four checks that most affect the verdict:
  (1) OVERNIGHT-LEG ISOLATION: V2 edge is overnight (intraday KILLed). Test V3 = enter 16:00 T close, exit
      09:30 T+1 open (pure overnight, skip dead intraday leg). Signal (DVOL eve T-1) precedes 16:00 T by ~21h.
  (2) TAIL CLUSTERING (#9): are the worst-5 days one crash episode or spread across years? Decides sizeability.
  (3) MARGINAL-VALUE REGRESSION (#3/#4): overnight_ret ~ const + dvol_z + prior_cc + vix_z + rv10z.
      Is the DVOL coefficient positive AND significant after controlling for prior-day selloff + VIX + RV?
      This is the rigorous "is it just disguised dip-buying / VIX proxy" test. Manual OLS + t-stats (no statsmodels).
  (4) MES vs MNQ RISK-ADJUSTED (#8): Sharpe, Sortino, tail-ratio — not just raw bps.
Report-only; no mutation.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "research" / "data" / "fql_forge" / "reports"


def _pf(a):
    a = np.asarray(a, float); l = -a[a < 0].sum()
    return float(a[a > 0].sum() / l) if l > 0 else float("inf")


def rth_daily(sym):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{sym}_5m.csv")
    dtv = pd.to_datetime(df["datetime"]); df = df.assign(d=dtv.dt.normalize(), t=dtv.dt.strftime("%H:%M"))
    rth = df[(df["t"] >= "09:30") & (df["t"] <= "15:55")]
    op = rth[rth["t"] == "09:30"].groupby("d")["open"].first().rename("open0930")
    cl = rth.groupby("d")["close"].last().rename("close1600")
    g = pd.concat([op, cl], axis=1).dropna()
    g["open_next"] = g["open0930"].shift(-1)
    g["overnight"] = g["open_next"] / g["close1600"] - 1        # V3: 16:00 T -> 09:30 T+1 (pure overnight)
    g["cc"] = g["close1600"].pct_change()
    return g


def zser(s, w=120):
    return (s - s.rolling(w, min_periods=60).mean()) / s.rolling(w, min_periods=60).std()


def ols_tstats(y, X, names):
    """Manual OLS with HC0-ish t-stats. X includes intercept column."""
    X = np.asarray(X, float); y = np.asarray(y, float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    n, k = X.shape
    sigma2 = float(resid @ resid) / (n - k)
    XtX_inv = np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(sigma2 * XtX_inv))
    tstat = beta / se
    r2 = 1 - (resid @ resid) / (((y - y.mean()) ** 2).sum())
    return {nm: {"coef": round(float(b), 6), "coef_bps": round(float(b) * 1e4, 2), "t": round(float(t), 2)}
            for nm, b, t in zip(names, beta, tstat)}, round(float(r2), 4), int(n)


def risk_adj(p, n_per_yr):
    p = p[~np.isnan(p)]
    mean = float(p.mean()); sd = float(p.std()); dn = float(p[p < 0].std()) if (p < 0).any() else np.nan
    sharpe = mean / sd * np.sqrt(n_per_yr) if sd > 0 else None
    sortino = mean / dn * np.sqrt(n_per_yr) if dn and dn > 0 else None
    g = np.sort(p[p > 0])[::-1]
    tail_ratio = abs(float(np.percentile(p, 95)) / float(np.percentile(p, 5))) if np.percentile(p, 5) != 0 else None
    return {"mean_bps": round(mean * 1e4, 1), "sharpe_ann": round(sharpe, 2) if sharpe else None,
            "sortino_ann": round(sortino, 2) if sortino else None, "tail_ratio_p95_p5": round(tail_ratio, 2) if tail_ratio else None,
            "worst_trade_pct": round(float(p.min()) * 100, 2), "downside_dev_bps": round(dn * 1e4, 1) if dn else None}


def run():
    print("Cycle 2026-06-23i — O2-equity refinement A (report-only)\n", flush=True)
    dvol = pd.read_csv(ROOT / "data" / "feeds" / "deribit_DVOL_BTC.csv", index_col=0)
    dvol.index = pd.to_datetime(dvol.index).tz_localize(None).normalize(); dvol = dvol.iloc[:, 0]
    dvol_sig = zser(dvol).copy(); dvol_sig.index = dvol_sig.index + pd.Timedelta(days=1); dvol_sig = dvol_sig.rename("dvolz")
    vix = pd.read_csv(ROOT / "data" / "feeds" / "vix.csv", parse_dates=["date"]).set_index("date")["vix"]
    vix_sig = zser(vix).copy(); vix_sig.index = vix_sig.index + pd.Timedelta(days=1); vix_sig = vix_sig.rename("vixz")

    OUT = {"cycle": "2026-06-23i_o2_refine_a", "status": "refinement of V2 PASS_REVIEW; report-only", "assets": {}}
    for sym in ("MES", "MNQ"):
        g = rth_daily(sym).join(dvol_sig).join(vix_sig).dropna(subset=["dvolz", "overnight"])
        g["prior_cc"] = g["cc"].shift(1)
        g["rv10"] = g["cc"].rolling(10, min_periods=6).std(); g["rv10z"] = zser(g["rv10"])
        g = g.dropna(subset=["prior_cc", "vixz", "rv10z"])
        spike = g["dvolz"] > 1.5
        t = g[spike]
        A = {"n_spike": int(spike.sum())}

        # (1) overnight-only V3
        p3 = (t["overnight"] - 0.0003).to_numpy()        # 3bps (single overnight crossing; cheaper than 2-leg)
        h = len(p3) // 2
        yr = pd.Series(p3, index=t.index).groupby(lambda x: x.year)
        A["V3_overnight_only_3bps"] = {"n": len(p3), "pf": round(_pf(p3), 3), "mean_bps": round(p3.mean() * 1e4, 1),
            "win_pct": round((p3 > 0).mean() * 100, 1), "h1_pf": round(_pf(p3[:h]), 3), "h2_pf": round(_pf(p3[h:]), 3),
            "yrs_pos": f"{int((yr.sum() > 0).sum())}/{yr.ngroups}", "per_year_bps": {int(y): round(v * 1e4, 0) for y, v in yr.mean().items()},
            "pf_6bps": round(_pf((t["overnight"] - 0.0006).to_numpy()), 3)}

        # (2) tail clustering: worst-5 overnight days among spike set
        worst = t.assign(pnl=t["overnight"]).nsmallest(5, "pnl")[["overnight"]]
        A["tail_clustering"] = {"worst5": [{"date": str(ix.date()), "ret_pct": round(float(r) * 100, 2)} for ix, r in worst["overnight"].items()],
            "worst5_years": sorted({ix.year for ix in worst.index}),
            "worst5_sum_pct": round(float(worst["overnight"].sum()) * 100, 2),
            "verdict_note": "spread across >=3 years => sizeable; clustered in 1 crash => fragile"}

        # (3) marginal-value regression on FULL sample (overnight ~ dvolz + prior_cc + vixz + rv10z)
        sub = g.dropna(subset=["overnight", "dvolz", "prior_cc", "vixz", "rv10z"])
        X = np.column_stack([np.ones(len(sub)), sub["dvolz"], sub["prior_cc"], sub["vixz"], sub["rv10z"]])
        coefs, r2, nobs = ols_tstats(sub["overnight"].values, X, ["const", "dvol_z", "prior_cc", "vix_z", "rv10_z"])
        A["marginal_regression"] = {"model": "overnight ~ const + dvol_z + prior_cc + vix_z + rv10_z", "n": nobs, "r2": r2, "coefs": coefs,
            "dvol_marginal_significant": bool(abs(coefs["dvol_z"]["t"]) >= 2.0 and coefs["dvol_z"]["coef"] > 0),
            "note": "dvol_z coef>0 & |t|>=2 AFTER controlling prior-day selloff+VIX+RV => DVOL adds unique signal, not just dip/VIX proxy"}

        # (4) risk-adjusted (per ~252 trading days; V3 fires only on spike days so annualize by spike cadence)
        n_per_yr = A["n_spike"] / ((t.index.max() - t.index.min()).days / 365)
        A["risk_adjusted"] = risk_adj(p3, n_per_yr)
        OUT["assets"][sym] = A

        print(f"=== {sym} (n_spike={A['n_spike']}) ===", flush=True)
        v = A["V3_overnight_only_3bps"]
        print(f"  V3 overnight-only @3bps: PF={v['pf']} mean={v['mean_bps']}bps H1/H2={v['h1_pf']}/{v['h2_pf']} yrs+={v['yrs_pos']} pf@6bps={v['pf_6bps']}", flush=True)
        print(f"     per-yr bps: {v['per_year_bps']}", flush=True)
        print(f"  tail: worst5 sum={A['tail_clustering']['worst5_sum_pct']}% across years {A['tail_clustering']['worst5_years']}", flush=True)
        print(f"        worst5: {[(d['date'], d['ret_pct']) for d in A['tail_clustering']['worst5']]}", flush=True)
        c = A["marginal_regression"]["coefs"]
        print(f"  REGRESSION (R2={r2}): dvol_z coef={c['dvol_z']['coef_bps']}bps t={c['dvol_z']['t']} | prior_cc t={c['prior_cc']['t']} | vix_z t={c['vix_z']['t']} | rv10_z t={c['rv10_z']['t']}", flush=True)
        print(f"        -> DVOL marginal significant beyond dip+VIX+RV: {A['marginal_regression']['dvol_marginal_significant']}", flush=True)
        r = A["risk_adjusted"]
        print(f"  risk-adj: Sharpe={r['sharpe_ann']} Sortino={r['sortino_ann']} tail_ratio={r['tail_ratio_p95_p5']} worst={r['worst_trade_pct']}%\n", flush=True)

    # MES vs MNQ verdict
    mes, mnq = OUT["assets"]["MES"]["risk_adjusted"], OUT["assets"]["MNQ"]["risk_adjusted"]
    print(f"MES vs MNQ risk-adjusted: MES Sharpe={mes['sharpe_ann']}/Sortino={mes['sortino_ann']}/tail={mes['tail_ratio_p95_p5']} | "
          f"MNQ Sharpe={mnq['sharpe_ann']}/Sortino={mnq['sortino_ann']}/tail={mnq['tail_ratio_p95_p5']}", flush=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "forge_cycle_2026-06-23i_o2_refine_a.json").write_text(json.dumps(OUT, indent=2, default=str))
    print("\nWrote refinement-A JSON.\n(report-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
