"""Cycle 2026-06-24f — C1 cointegration / relative-value: ZN-ZF (report-only).

DIFFERENT premium (mean-reversion/relative-value, NOT momentum). STRICT construction-first per operator:
audit -> rolling no-lookahead hedge ratio -> stationarity/half-life -> z-band strategy (both sides, dollar-risk
costs both legs) -> per-year (esp 2022 regime shift) -> ORB-correlation/bad-day-offset -> DSR. Do NOT overfit a
spread into existence. WTI-Brent deprioritized (no tradable Brent leg). Report-only; no mutation.

Economic basis: ZN(10y)/ZF(5y) are Treasury curve points driven by the same rate factor -> cointegrated.
RISK: the 5s10s curve TRENDS with Fed cycles (2022 inversion) -> naive reversion likely fails the crisis test.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.asset_config import get_asset
sys.path.insert(0, str(ROOT / "research"))
from forge_deflated_sharpe import deflated_sharpe

REPORTS = ROOT / "research" / "data" / "fql_forge" / "reports"
PV = 1000.0  # ZN & ZF point_value


def daily_close(sym):
    df = pd.read_csv(ROOT / f"data/processed/{sym}_5m.csv"); dtv = pd.to_datetime(df["datetime"])
    return df.assign(d=dtv.dt.normalize()).groupby("d")["close"].last()


def _pf(a):
    a = np.asarray(a, float); a = a[~np.isnan(a)]; l = -a[a < 0].sum()
    return float(a[a > 0].sum() / l) if l > 0 else float("inf")


def adf_stat(x):
    """Quick ADF-ish: regress Δx on x_lag; t-stat of the lag coef (more negative = more stationary)."""
    x = np.asarray(x, float); dx = np.diff(x); xl = x[:-1]
    X = np.column_stack([np.ones(len(xl)), xl]); b, *_ = np.linalg.lstsq(X, dx, rcond=None)
    resid = dx - X @ b; se = np.sqrt((resid @ resid) / (len(dx) - 2) * np.linalg.inv(X.T @ X)[1, 1])
    return float(b[1] / se), float(b[1])  # (t, gamma); half-life = -ln(2)/ln(1+gamma)


def run():
    print("Cycle 2026-06-24f — C1 cointegration ZN-ZF (report-only)\n", flush=True)
    zn, zf = daily_close("ZN"), daily_close("ZF")
    d = pd.DataFrame({"ZN": zn, "ZF": zf}).dropna().sort_index()

    # === CONSTRUCTION AUDIT ===
    print("=== CONSTRUCTION AUDIT ===", flush=True)
    gaps = d.index.to_series().diff().dt.days
    print(f"  aligned days: {len(d)} {d.index.min().date()}..{d.index.max().date()} | missing-bar gaps>4d: {int((gaps>4).sum())} | max gap {int(gaps.max())}d", flush=True)
    print(f"  ZN range {d['ZN'].min():.2f}-{d['ZN'].max():.2f} | ZF range {d['ZF'].min():.2f}-{d['ZF'].max():.2f} | level corr {d['ZN'].corr(d['ZF']):.3f}", flush=True)
    print(f"  point_value both ${PV}; hedge via rolling OLS beta (price sensitivity), dollar-risk PnL both legs", flush=True)

    # === ROLLING HEDGE RATIO (no lookahead: beta from trailing 120d only) + SPREAD ===
    W = 120
    beta = pd.Series(index=d.index, dtype=float)
    for i in range(W, len(d)):
        yv = d["ZN"].iloc[i - W:i].values; xv = d["ZF"].iloc[i - W:i].values
        X = np.column_stack([np.ones(W), xv]); b, *_ = np.linalg.lstsq(X, yv, rcond=None)
        beta.iloc[i] = b[1]
    d["beta"] = beta
    d = d.dropna(subset=["beta"])
    d["spread"] = d["ZN"] - d["beta"] * d["ZF"]
    d["sz"] = (d["spread"] - d["spread"].rolling(60, min_periods=30).mean()) / d["spread"].rolling(60, min_periods=30).std()
    d = d.dropna(subset=["sz"])

    # === STATIONARITY ===
    t_adf, gamma = adf_stat(d["spread"].values)
    half_life = -np.log(2) / np.log(1 + gamma) if -1 < gamma < 0 else np.inf
    beta_stab = float(d["beta"].rolling(60).std().mean())
    print(f"\n=== STATIONARITY === ADF-t(spread)={t_adf:.2f} (more neg=stationary; ~<-2.9 = 95%) | half-life={half_life:.1f}d | rolling-beta std(avg)={beta_stab:.3f} mean-beta={d['beta'].mean():.3f}", flush=True)

    # === STRATEGY: z-band reversion, both sides, dollar-risk costs both legs ===
    # signal known at prior close; trade next day. z>2 -> short spread (short ZN/long beta*ZF); z<-2 -> long spread
    d["pos"] = 0
    d.loc[d["sz"] > 2, "pos"] = -1
    d.loc[d["sz"] < -2, "pos"] = 1
    # hold until |z|<0.5 (reversion) — forward-fill position with exit
    pos = []
    cur = 0
    for z, raw in zip(d["sz"].values, d["pos"].values):
        if cur == 0 and raw != 0:
            cur = raw
        elif cur != 0 and abs(z) < 0.5:
            cur = 0
        pos.append(cur)
    d["position"] = pd.Series(pos, index=d.index).shift(1).fillna(0)   # act next day
    # daily PnL ($): position * d(spread)*PV ; spread uses CURRENT beta (held); cost on position changes
    d["dspread"] = d["spread"].diff()
    cost_rt = (get_asset("ZN")["commission_per_side"] * 2 + get_asset("ZN")["tick_size"] * get_asset("ZN")["slippage_ticks"] * PV) \
              + (get_asset("ZF")["commission_per_side"] * 2 + get_asset("ZF")["tick_size"] * get_asset("ZF")["slippage_ticks"] * PV)
    trades_change = d["position"].diff().abs() > 0
    d["pnl"] = d["position"] * d["dspread"] * PV - trades_change * cost_rt
    s = d["pnl"].dropna(); s = s[d["position"] != 0] if False else s    # keep full series for equity
    active = s[s != 0]
    if len(active) < 60:
        print(f"\n  insufficient active days ({len(active)}) -> DATA-LIMITED"); return

    p = s.values; h = len(p) // 2; eq = np.cumsum(p); dd = eq - np.maximum.accumulate(eq)
    yr = s.groupby(s.index.year).sum()
    longs = d["pnl"][d["position"] == 1]; shorts = d["pnl"][d["position"] == -1]
    # ORB correlation (MNQ daily proxy)
    mnq = daily_close("MNQ").pct_change()
    al = pd.concat([s.rename("a"), mnq.rename("b")], axis=1).dropna()
    corr_mnq = round(float(al["a"].corr(al["b"])), 3) if len(al) > 30 else None
    sp = np.sort(p[p > 0])[::-1]; tot = sp.sum()
    R = {"adf_t": round(t_adf, 2), "half_life_d": round(half_life, 1), "beta_stability": round(beta_stab, 3),
         "n_active_days": int((d["position"] != 0).sum()), "n_trades": int(trades_change.sum()),
         "pf": round(_pf(p), 3), "net_$": round(float(p.sum()), 0), "mean_$_day": round(float(p.mean()), 2),
         "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3),
         "maxDD_$": round(float(dd.min()), 0), "worst_day_$": round(float(s.min()), 0),
         "long_pf": round(_pf(longs.values), 3) if len(longs) else None, "short_pf": round(_pf(shorts.values), 3) if len(shorts) else None,
         "top5_pct": round(float(sp[:5].sum()) / tot * 100, 1) if tot > 0 else None,
         "yrs_pos": f"{int((yr>0).sum())}/{yr.shape[0]}", "per_year_$": {int(y): round(float(v), 0) for y, v in yr.items()},
         "corr_to_MNQ_ORBproxy": corr_mnq, "cost_rt_$": round(cost_rt, 2)}
    R["DSR"] = deflated_sharpe(p[p != 0], n_trials=4)   # few pair/param choices
    # verdict
    stationary = t_adf < -2.5 and half_life < 120
    robust = R["pf"] >= 1.2 and R["h1_pf"] > 1.0 and R["h2_pf"] > 1.0 and "0/" not in R["yrs_pos"] and (R["long_pf"] or 0) > 1 and (R["short_pf"] or 0) > 1
    decorr = corr_mnq is not None and abs(corr_mnq) < 0.3
    if stationary and robust and decorr and R["DSR"].get("passes"):
        v = "PASS_REVIEW_relative_value"
    elif R["pf"] >= 1.1 and stationary:
        v = "WATCH"
    elif not stationary:
        v = "KILL_not_stationary"
    else:
        v = "KILL"
    R["verdict"] = v
    print(f"\n=== STRATEGY (z>2 fade, exit |z|<0.5, both sides, dollar-risk costs ${cost_rt:.0f}/rt) ===", flush=True)
    print(f"  PF={R['pf']} net=${R['net_$']} mean=${R['mean_$_day']}/day H1/H2={R['h1_pf']}/{R['h2_pf']} long_pf={R['long_pf']} short_pf={R['short_pf']}", flush=True)
    print(f"  active_days={R['n_active_days']} trades={R['n_trades']} maxDD=${R['maxDD_$']} worstday=${R['worst_day_$']} top5={R['top5_pct']}% yrs+={R['yrs_pos']} corrMNQ={corr_mnq}", flush=True)
    print(f"  per-year $: {R['per_year_$']}", flush=True)
    print(f"  DSR: {R['DSR'].get('dsr')} ({R['DSR'].get('verdict')}) | stationary={stationary} robust={robust} decorr={decorr}", flush=True)
    print(f"  -> VERDICT: {v}", flush=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "forge_cycle_2026-06-24f_C1_cointegration_zn_zf.json").write_text(json.dumps({"cycle": "2026-06-24f_C1_cointegration_zn_zf", "result": R,
        "note": "ZN-ZF rolling-beta cointegration reversion; construction-audited; relative-value premium; report-only"}, indent=2, default=str))
    print("\nWrote C1 JSON.\n(report-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
