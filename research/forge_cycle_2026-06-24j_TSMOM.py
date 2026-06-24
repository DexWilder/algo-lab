"""Cycle 2026-06-24j — TSMOM (time-series momentum) different-premium test (report-only).

COT-commercial SKIPPED (comm_net ~ -spec_net, corr -0.99 = redundant with the already-killed spec-fade).
TSMOM = trailing-return-sign trend-following, held (Moskowitz/Ilmanen). Mechanistically DIFFERENT from intraday
ORB (slow multi-month trend, holds overnight vs ORB intraday-flat). Question: decorrelated from ORB AND a
positive premium after cost? Predeclared lookbacks 21/63/126d, no flip. Strict: per-year, cost, DSR, corr-to-ORB.
Report-only; no mutation.
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
ASSETS = ["MNQ", "MES", "MGC", "MCL"]
LOOKBACKS = [21, 63, 126]


def daily(sym):
    df = pd.read_csv(ROOT / f"data/processed/{sym}_5m.csv"); dtv = pd.to_datetime(df["datetime"])
    return df.assign(d=dtv.dt.normalize()).groupby("d")["close"].last()


def _pf(a):
    a = np.asarray(a, float); a = a[~np.isnan(a)]; l = -a[a < 0].sum()
    return float(a[a > 0].sum() / l) if l > 0 else float("inf")


def orb_daily_pnl():
    from engine.backtest import run_backtest
    from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals
    cfg = get_asset("MNQ"); df = pd.read_csv(ROOT / "data/processed/MNQ_5m.csv"); df["datetime"] = pd.to_datetime(df["datetime"])
    sig = generate_crossbred_signals(df, entry_name="orb_breakout", exit_name="profit_ladder", filter_name="ema_slope", params={"stop_mult": 0.5, "target_mult": 4.0, "trail_mult": 2.5})
    r = run_backtest(df, sig, mode="both", point_value=cfg["point_value"], tick_size=cfg["tick_size"], commission_per_side=cfg["commission_per_side"], slippage_ticks=cfg["slippage_ticks"])
    t = r["trades_df"].copy(); t["day"] = pd.to_datetime(t["entry_time"]).dt.normalize(); return t.groupby("day")["pnl"].sum()


def run():
    print("Cycle 2026-06-24j — TSMOM different-premium (report-only)\n", flush=True)
    orb = orb_daily_pnl()
    OUT = {"cycle": "2026-06-24j_TSMOM", "assets": {}}
    pooled_by_lb = {lb: [] for lb in LOOKBACKS}
    for a in ASSETS:
        cfg = get_asset(a); px = daily(a); ret = px.diff()  # price change in points
        res = {}
        for lb in LOOKBACKS:
            sig = np.sign(px.pct_change(lb)).shift(1)        # trailing-lb return sign, known prior close
            pnl = (sig * ret * cfg["point_value"]).dropna()
            flips = sig.diff().abs().fillna(0)
            cost = flips * (cfg["commission_per_side"] * 2 + cfg["tick_size"] * cfg["slippage_ticks"] * cfg["point_value"])
            pnl = (pnl - cost.reindex(pnl.index).fillna(0))
            p = pnl.values; yr = pnl.groupby(pnl.index.year).sum()
            res[f"lb{lb}"] = {"pf": round(_pf(p), 3), "net_$": round(float(p.sum()), 0), "sharpe": round(float(p.mean())/p.std()*np.sqrt(252), 2) if p.std()>0 else None,
                              "yrs_pos": f"{int((yr>0).sum())}/{yr.shape[0]}", "maxDD_$": round(float((np.cumsum(p)-np.maximum.accumulate(np.cumsum(p))).min()), 0)}
            pooled_by_lb[lb].append(pnl.rename(f"{a}_{lb}"))
        OUT["assets"][a] = res
        print(f"  {a}: " + " | ".join(f"lb{lb}: PF={res[f'lb{lb}']['pf']} Sharpe={res[f'lb{lb}']['sharpe']} net=${res[f'lb{lb}']['net_$']} yrs+={res[f'lb{lb}']['yrs_pos']}" for lb in LOOKBACKS), flush=True)

    # pooled TSMOM (equal-weight across assets) per lookback + decorrelation to ORB
    print("", flush=True)
    OUT["pooled"] = {}
    for lb in LOOKBACKS:
        comb = pd.concat(pooled_by_lb[lb], axis=1).sum(axis=1)   # equal-notional sum across assets
        p = comb.values; yr = comb.groupby(comb.index.year).sum()
        al = pd.concat([comb.rename("a"), orb.rename("b")], axis=1).dropna(); corr = round(float(al["a"].corr(al["b"])), 3) if len(al) > 30 else None
        dsr = deflated_sharpe(p[p != 0], n_trials=len(ASSETS) * len(LOOKBACKS))   # ~12 trials
        sh = round(float(p.mean())/p.std()*np.sqrt(252), 2) if p.std() > 0 else None
        OUT["pooled"][f"lb{lb}"] = {"pf": round(_pf(p), 3), "sharpe": sh, "net_$": round(float(p.sum()), 0),
                                    "yrs_pos": f"{int((yr>0).sum())}/{yr.shape[0]}", "corr_to_ORB": corr, "psr_or_dsr": dsr.get("dsr"), "dsr_verdict": dsr.get("verdict")}
        print(f"  POOLED lb{lb}: PF={OUT['pooled'][f'lb{lb}']['pf']} Sharpe={sh} net=${OUT['pooled'][f'lb{lb}']['net_$']} yrs+={OUT['pooled'][f'lb{lb}']['yrs_pos']} corr-to-ORB={corr} DSR/PSR={dsr.get('dsr')}", flush=True)

    # verdict: best pooled lookback decorrelated + positive + DSR-credible?
    best = max(OUT["pooled"].items(), key=lambda kv: (kv[1]["sharpe"] or 0))
    bl = best[1]
    decorr = bl["corr_to_ORB"] is not None and abs(bl["corr_to_ORB"]) < 0.4
    if (bl["sharpe"] or 0) > 0.5 and bl["pf"] >= 1.1 and decorr and "0/" not in bl["yrs_pos"]:
        v = "WATCH_tsmom_premium" + ("_credible" if "PASS" in str(bl["dsr_verdict"]) else "")
    elif (bl["sharpe"] or 0) > 0.3 and decorr:
        v = "WATCH_marginal"
    else:
        v = "KILL"
    OUT["verdict"] = v; OUT["best_lookback"] = best[0]
    print(f"\n  -> VERDICT: {v} (best={best[0]} Sharpe={bl['sharpe']} corr-to-ORB={bl['corr_to_ORB']} decorr={decorr})", flush=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "forge_cycle_2026-06-24j_TSMOM.json").write_text(json.dumps(OUT, indent=2, default=str))
    print("\nWrote TSMOM JSON.\n(report-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
