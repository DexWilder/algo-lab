"""Cycle 2026-06-23g — O2: DVOL as cross-asset regime/risk-state OVERLAY (report-only).

Operator priority #2. Execution-cost-FREE: gates books we ALREADY trade (no crypto execution).
Framing (overlay, NOT standalone forced-flow): crypto trades 24/7 -> DVOL (BTC implied-vol index) can
register overnight/weekend risk shifts BEFORE the equity open -> test DVOL state as a LEADING risk-state
filter on existing equity/gold daily behavior. Judged like the MGC low-vol exclusion overlay: does
conditioning on DVOL regime improve an existing sleeve's edge, or cleanly separate good/bad days?

No-lookahead: DVOL_t known at end of day t (UTC, ~hours before US t+1 open) -> condition day t+1 asset return.
Regimes: DVOL level percentile (rolling 120d), DVOL 10d change (rising/falling). Report next-day asset
return mean/PF by regime + the conditioning lift vs unconditional. MNQ/MGC/MES daily. Report-only; no mutation.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def asset_daily(sym):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{sym}_5m.csv"); d = pd.to_datetime(df["datetime"])
    r = df.assign(x=d.dt.normalize()).groupby("x")["close"].last().pct_change()
    r.index = pd.to_datetime(r.index).tz_localize("UTC"); return r.rename(sym)


def _pf(a):
    a = np.asarray(a, float); l = -a[a < 0].sum()
    return float(a[a > 0].sum() / l) if l > 0 else float("inf")


def run():
    print("Cycle 2026-06-23g — O2 DVOL cross-asset regime overlay (report-only)\n", flush=True)
    dvol = pd.read_csv(ROOT / "data" / "feeds" / "deribit_DVOL_BTC.csv", index_col=0)
    dvol.index = pd.to_datetime(dvol.index, utc=True); dvol = dvol.iloc[:, 0].rename("dvol")
    d = pd.DataFrame({"dvol": dvol})
    d["pct"] = d["dvol"].rolling(120, min_periods=60).rank(pct=True)      # level percentile
    d["chg10"] = d["dvol"] - d["dvol"].shift(10)                           # rising/falling
    d["z"] = (d["dvol"] - d["dvol"].rolling(120, min_periods=60).mean()) / d["dvol"].rolling(120, min_periods=60).std()

    res = {}
    for sym in ("MNQ", "MES", "MGC"):
        a = asset_daily(sym)
        m = pd.concat([d, a], axis=1).dropna(subset=["pct", "chg10", sym])
        m["fwd"] = m[sym].shift(-1)                                        # next-day asset return (no lookahead)
        m = m.dropna(subset=["fwd"])
        uncond_mean = float(m["fwd"].mean()) * 1e4
        regimes = {
            "DVOL_high_pct>0.8": m["pct"] > 0.8,
            "DVOL_low_pct<0.2": m["pct"] < 0.2,
            "DVOL_rising_chg10>0": m["chg10"] > 0,
            "DVOL_falling_chg10<0": m["chg10"] < 0,
            "DVOL_spike_z>1.5": m["z"] > 1.5,
        }
        rr = {"n_total": int(len(m)), "uncond_mean_bps": round(uncond_mean, 1), "uncond_pf": round(_pf(m["fwd"].values), 3)}
        for name, mask in regimes.items():
            f = m["fwd"][mask.values]
            if len(f) < 30:
                rr[name] = {"n": int(len(f)), "note": "too few"}; continue
            rr[name] = {"n": int(len(f)), "mean_bps": round(float(f.mean()) * 1e4, 1), "pf": round(_pf(f.values), 3),
                        "win_pct": round(float((f > 0).mean()) * 100, 1),
                        "lift_vs_uncond_bps": round(float(f.mean()) * 1e4 - uncond_mean, 1)}
        res[sym] = rr
        print(f"  {sym}: n={rr['n_total']} uncond_mean={rr['uncond_mean_bps']}bps", flush=True)
        for name in regimes:
            v = rr[name]
            if "mean_bps" in v:
                flag = " <<<" if abs(v["lift_vs_uncond_bps"]) >= 15 else ""
                print(f"    {name:24s}: n={v['n']:4d} mean={v['mean_bps']:7.1f}bps pf={v['pf']:.3f} win={v['win_pct']}% lift={v['lift_vs_uncond_bps']:+.1f}bps{flag}", flush=True)
            else:
                print(f"    {name:24s}: {v['note']}", flush=True)

    # interpretation
    print("\n  Looking for: a DVOL regime that cleanly separates good/bad next-day risk days across MNQ+MES (equity),", flush=True)
    print("  which could gate the ORB momentum sleeves. Gold (MGC) opposite-sign in risk-off would add hedge value.", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-23g_o2_dvol_regime_overlay.json"
    out.write_text(__import__("json").dumps({"cycle": "2026-06-23g_o2_dvol_regime_overlay", "mode": "report-only; overlay screen; NON-WIRED",
        "results": res, "note": "DVOL regime conditioning on existing equity/gold daily returns; overlay not standalone; no-lookahead DVOL_t -> ret_t+1",
        "boundaries": "no mutation; no promotion; execution-cost-free overlay study"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; O2 overlay; no mutation)", flush=True)


if __name__ == "__main__":
    run()
