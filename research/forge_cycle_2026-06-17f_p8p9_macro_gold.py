"""Cycle 2026-06-17f — P8/P9 macro-driver gold first-cut (report-only).

P8 real-rate-driven gold (DFII10), P9 breakeven-inflation rotation gold<->rates (T10YIE).
Locked sequence: revalidate -> no-lookahead/timestamp audit -> join audit -> coverage ->
predeclared first-cut variants -> MANDATORY date-split OOS (train<=2022 / test>=2023; the
prior gold x ZN-price gate INVERTED OOS, so both halves must agree) -> brutal board ->
STRICT classification -> archive.

CLASSIFICATION (predeclared) for any quality+OOS survivor:
  - GOLD_SLEEVE_ENHANCER         : |corr to long-gold| >= 0.5  (just better gold timing)
  - PORTFOLIO_DIVERSIFIER_CAND   : decorrelated from MNQ (<0.3) but still gold-family
  - WH2_CANDIDATE                : decorrelated from MNQ (<0.3) AND from long-gold (<0.5)
                                   AND daily cadence -> genuinely distinct portfolio behavior
A gold conditioner does NOT get called WH2 unless it adds distinct behavior, not gold timing.

NO sweep, NO synthetic fill, NO edge language pre-evidence, NO mutation.
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

FEEDS = ROOT / "data" / "feeds"


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def daily_close(a):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{a}_5m.csv")
    dt = pd.to_datetime(df["datetime"])
    return df.assign(date=dt.dt.normalize()).groupby("date")["close"].last()


def lag_join(trade_dates, feed_df, col):
    """Attach feed[col] as-of STRICTLY PRIOR day to each trade date (no-lookahead)."""
    td = pd.DataFrame({"date": pd.to_datetime(trade_dates)}).sort_values("date")
    f = feed_df[["date", col]].dropna().sort_values("date").rename(columns={"date": "fdate"})
    m = pd.merge_asof(td, f, left_on="date", right_on="fdate", direction="backward", allow_exact_matches=False)
    assert int((m["fdate"] >= m["date"]).sum()) == 0, "LOOKAHEAD"
    return m.set_index("date")[col]


def stats(p, idx):
    p = np.asarray(p, float); n = len(p)
    if n < 200:
        return {"n": n, "pf": None}
    s = pd.Series(p, index=pd.to_datetime(idx)); h = n // 2
    per_yr = s.groupby(s.index.year).sum()
    return {"n": n, "pf": round(_pf(p), 3), "net": round(float(p.sum()), 0), "median": round(float(np.median(p)), 2),
            "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3),
            "yrs_pos": f"{int((per_yr>0).sum())}/{int(per_yr.shape[0])}"}


def classify(full, train, test, corr_mnq, corr_gold):
    pf = full.get("pf")
    if pf is None:
        return "KILL_low_n"
    quality = pf > 1.2 and full["median"] >= 0 and full["h1_pf"] > 1.0 and full["h2_pf"] > 1.0
    oos_ok = (train.get("pf") or 0) > 1.0 and (test.get("pf") or 0) > 1.0  # both halves agree (no inversion)
    if not quality or not oos_ok:
        return "KILL" if (pf or 0) < 1.05 or not oos_ok else "RETEST"
    if abs(corr_gold) >= 0.5:
        return "GOLD_SLEEVE_ENHANCER"
    if abs(corr_mnq) < 0.3 and abs(corr_gold) < 0.5:
        return "WH2_CANDIDATE"
    return "PORTFOLIO_DIVERSIFIER_CAND"


def corr(a_pnl, a_idx, b_series):
    s = pd.Series(a_pnl, index=pd.to_datetime(a_idx))
    al = pd.concat([s.rename("a"), b_series.rename("b")], axis=1).fillna(0.0)
    return round(float(al["a"].corr(al["b"])), 3)


def run():
    print("Cycle 2026-06-17f — P8/P9 macro-driver gold first-cut (REPORT-ONLY)\n", flush=True)
    rr = pd.read_csv(FEEDS / "real_rates.csv", parse_dates=["date"])
    ie = pd.read_csv(FEEDS / "inflation_expectations.csv", parse_dates=["date"])
    print(f"1. FEEDS: real_rates n={len(rr)} (dfii10 miss={int(rr['dfii10'].isna().sum())}); "
          f"inflation_exp n={len(ie)} (t10yie miss={int(ie['t10yie'].isna().sum())})", flush=True)
    print("2. NO-LOOKAHEAD: DFII10/T10YIE dated D published ~EOD D -> lag 1 trading day (merge_asof "
          "backward, allow_exact_matches=False -> feed_date < trade_date, asserted).", flush=True)

    mgc = daily_close("MGC"); zn = daily_close("ZN")
    mgc = mgc[mgc.index.year >= 2019]; zn = zn[zn.index.year >= 2019]
    mgc_ret = mgc.diff(); zn_ret = zn.diff()
    pvM = ASSETS["MGC"]["point_value"]; pvZ = ASSETS["ZN"]["point_value"]
    cM = get_cost_params("MGC"); cZ = get_cost_params("ZN")
    rtM = 2 * (cM["commission_per_side"] + cM["slippage_ticks"] * cM["tick_size"] * pvM)
    rtZ = 2 * (cZ["commission_per_side"] + cZ["slippage_ticks"] * cZ["tick_size"] * pvZ)
    mnq_ret = daily_close("MNQ").diff()
    gold_bh = (mgc_ret * pvM)  # long-gold reference for correlation

    dfii = lag_join(mgc.index, rr, "dfii10").reindex(mgc.index)
    t10 = lag_join(mgc.index, ie, "t10yie").reindex(mgc.index)
    print(f"3/4. JOIN+COVERAGE: MGC days={len(mgc)} dfii10-matched={int(dfii.notna().sum())} "
          f"t10yie-matched={int(t10.notna().sum())}; years {sorted(set(mgc.index.year))}", flush=True)

    results = {}

    def run_variant(name, pos_series, asset_ret, pv, rt, ref_idx):
        pos = pos_series.shift(0)  # pos for day t decided from lagged feed (already strictly prior)
        valid = pos.notna() & asset_ret.notna()
        pos = pos[valid]; ret = asset_ret[valid]
        pnl = (pos.values * ret.values * pv)
        # cost on position change
        dpos = np.abs(np.diff(np.concatenate([[0], pos.values])))
        pnl = pnl - dpos * rt
        idx = pos.index
        full = stats(pnl, idx)
        tr_mask = idx.year <= 2022; te_mask = idx.year >= 2023
        train = stats(pnl[tr_mask], idx[tr_mask]); test = stats(pnl[te_mask], idx[te_mask])
        c_mnq = corr(pnl, idx, mnq_ret); c_gold = corr(pnl, idx, gold_bh)
        verdict = classify(full, train, test, c_mnq, c_gold)
        results[name] = {**full, "train_pf": train.get("pf"), "test_pf": test.get("pf"),
                         "corr_mnq": c_mnq, "corr_longgold": c_gold, "verdict": verdict}
        print(f"  {name:<28} PF={full.get('pf')} med=${full.get('median')} H1/H2={full.get('h1_pf')}/{full.get('h2_pf')} "
              f"OOS train/test PF={train.get('pf')}/{test.get('pf')} corr(mnq/gold)={c_mnq}/{c_gold} -> {verdict}", flush=True)

    print("\n5/6. P8 real-rate-driven gold (predeclared variants):", flush=True)
    # V1 long/short: long gold when 20d real-yield change < 0 (yields falling), short when > 0
    d_dfii = dfii - dfii.shift(20)
    run_variant("P8_realrate_longshort", -np.sign(d_dfii), mgc_ret, pvM, rtM, mgc.index)
    # V2 long-only gate: long gold when real yield below its 60d mean, else flat
    gate = (dfii < dfii.rolling(60).mean()).astype(float)
    run_variant("P8_realrate_longonly_gate", gate, mgc_ret, pvM, rtM, mgc.index)

    print("\n5/6. P9 breakeven rotation gold<->rates (predeclared):", flush=True)
    # rising breakevens (20d change>0) -> long MGC; falling -> long ZN. Held in one asset.
    d_t10 = t10 - t10.shift(20)
    posM = (d_t10 > 0).astype(float)  # 1 = hold gold, 0 = hold rates
    # build combined daily pnl: gold leg when posM=1, rates leg when posM=0
    valid = posM.notna() & mgc_ret.notna() & zn_ret.notna()
    pm = posM[valid]; idx = pm.index
    pnl = np.where(pm.values == 1, mgc_ret[valid].values * pvM, zn_ret[valid].values * pvZ)
    switch = np.abs(np.diff(np.concatenate([[0], pm.values])))
    pnl = pnl - switch * ((rtM + rtZ) / 2)
    full = stats(pnl, idx)
    train = stats(pnl[idx.year <= 2022], idx[idx.year <= 2022]); test = stats(pnl[idx.year >= 2023], idx[idx.year >= 2023])
    c_mnq = corr(pnl, idx, mnq_ret); c_gold = corr(pnl, idx, gold_bh)
    verdict = classify(full, train, test, c_mnq, c_gold)
    results["P9_breakeven_rotation"] = {**full, "train_pf": train.get("pf"), "test_pf": test.get("pf"),
                                        "corr_mnq": c_mnq, "corr_longgold": c_gold, "verdict": verdict}
    print(f"  P9_breakeven_rotation        PF={full.get('pf')} med=${full.get('median')} H1/H2={full.get('h1_pf')}/{full.get('h2_pf')} "
          f"OOS train/test PF={train.get('pf')}/{test.get('pf')} corr(mnq/gold)={c_mnq}/{c_gold} -> {verdict}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-17f_p8p9_macro_gold.json"
    out.write_text(json.dumps({"cycle": "2026-06-17f_p8p9_macro_gold", "mode": "Lane B report-only; first-cut; date-split OOS; NON-WIRED",
        "classification_rule": "GOLD_SLEEVE_ENHANCER if |corr_longgold|>=0.5; WH2_CANDIDATE if corr_mnq<0.3 AND corr_longgold<0.5; else PORTFOLIO_DIVERSIFIER_CAND; KILL if not quality or OOS-inverts",
        "results": results, "boundaries": "no sweep/synthetic-fill/edge-pre-evidence/mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; first-cut; date-split OOS; no sweep; no mutation)", flush=True)


if __name__ == "__main__":
    run()
