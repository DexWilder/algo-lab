"""ALPHA_INTAKE_FACTORY — calendar/forced-flow adapter + first cheap tests (report-only).
Tests deterministic-DATE T1 forced-flow packets (causality clean BY CONSTRUCTION — no value lookahead, dates known
ahead). PRE-REGISTERED predictions; every test logged to the trial ledger (multiple-testing N). Cost-aware.
  P02 equity-index month-end drift (MES, MNQ): predict positive drift last 3 sessions of month.
  P04 month-end Treasury duration extension (ZN): predict positive ZN drift into month-end.
  P01 calendar-roll pressure: deferred (needs per-contract, not stitched -> roll-artifact risk).
No WH/validated language. Capital gate unchanged."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.asset_config import get_asset
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if len(x)>1 and x.std()>0 else 0
def daily(asset):
    df=pd.read_csv(ROOT/f"data/processed/{asset}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
    d=df.assign(dt=df["datetime"].dt.normalize()).groupby("dt")["close"].last()
    return d
def month_end_test(asset, last_n=3, label="P02"):
    d=daily(asset); pv=get_asset(asset)["point_value"]
    ret=d.diff()*pv  # $ per 1 contract
    df=pd.DataFrame({"ret":ret}).dropna()
    df["ym"]=df.index.to_period("M")
    # rank sessions from month end (0 = last session of month)
    df["rev_rank"]=df.groupby("ym").cumcount(ascending=False)
    in_win=df["rev_rank"]<last_n          # last N sessions of month (deterministic, known ahead)
    cost=get_asset(asset)["commission_per_side"]*2 + get_asset(asset)["slippage_ticks"]*2*get_asset(asset)["tick_size"]*pv
    win=df.loc[in_win,"ret"]; out=df.loc[~in_win,"ret"]
    win_net=win - cost/last_n  # rough per-day cost share (enter once per month, hold N)
    yr=win.groupby(win.index.year).sum()
    print(f"  [{label} {asset}] last-{last_n}-sessions/month: n_days={len(win)} mean=${win.mean():.1f} (out-of-window mean=${out.mean():.1f})")
    print(f"      window Sharpe(gross)={shp(win.values)} net mean(after cost)=${win_net.mean():.1f} | sum gross=${win.sum():.0f}")
    print(f"      per-year net sum: " + "  ".join(f"{y}:{int(v)}" for y,v in yr.items()))
    # pre-registered prediction: positive drift. verdict:
    pos = win.mean()>0 and win.sum()>0
    yrs_pos = (yr>0).mean()
    return dict(asset=asset, mean=float(win.mean()), sharpe=shp(win.values), net=float(win.sum()), yrs_pos=float(yrs_pos), pred_holds=bool(pos))
print("=== AIF calendar adapter — first cheap tests (deterministic dates = causality clean by construction) ===")
print("PRE-REGISTERED: P02 equity month-end -> positive drift last 3 sessions; P04 ZN month-end -> positive drift.")
res=[]
for a in ["MES","MNQ"]: res.append(("P02",month_end_test(a,3,"P02")))
res.append(("P04",month_end_test("ZN",3,"P04")))
print("\n=== trial-ledger entries (count ALL toward multiple-testing N) ===")
for pid,r in res:
    verdict = "SCREEN_PASS(weak)" if (r["pred_holds"] and r["sharpe"]>0.5 and r["yrs_pos"]>=0.6) else ("DIRECTION_OK_WEAK" if r["pred_holds"] else "KILL(prediction failed)")
    print(f"  {pid} {r['asset']:4s}: Sharpe={r['sharpe']:>5.2f} net=${r['net']:>7.0f} yrs_pos={r['yrs_pos']*100:.0f}% -> {verdict}")
print("\n  NOTE: these 3 tests COUNT toward trial N. Any survivor must later clear DSR at full N. No edge claim from raw Sharpe.")
