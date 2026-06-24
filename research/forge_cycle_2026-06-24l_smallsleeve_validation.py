"""Cycle 2026-06-24l — small-sleeve validation: is the improvement per-year-stable + out-of-sample? (report-only)
TSMOM-0.05x & vol-carry-$2k improved the combined book at full-sample. Test: (1) per-year combined Sharpe vs
ORB-alone (improve most years or one?); (2) walk-forward — pick best allocation on H1, apply to H2, does H2
improve OOS? Distinguishes real small-sleeve improver from curve-fit. Report-only; no mutation."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.asset_config import get_asset
from engine.backtest import run_backtest
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals
def daily(s):
    df=pd.read_csv(ROOT/f"data/processed/{s}_5m.csv"); dt=pd.to_datetime(df["datetime"]); return df.assign(d=dt.dt.normalize()).groupby("d")["close"].last()
def yh(sym):
    import urllib.request; u=f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=10y&interval=1d"
    r=json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"}),timeout=25).read()); res=r["chart"]["result"][0]
    return pd.Series(res["indicators"]["quote"][0]["close"],index=pd.to_datetime(res["timestamp"],unit="s").normalize()).dropna().pipe(lambda s:s[~s.index.duplicated()])
def shp(x):
    x=x.values; return round(x.mean()/x.std()*np.sqrt(252),2) if x.std()>0 else 0
cfg=get_asset("MNQ"); df=pd.read_csv(ROOT/"data/processed/MNQ_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
sig=generate_crossbred_signals(df,entry_name="orb_breakout",exit_name="profit_ladder",filter_name="ema_slope",params={"stop_mult":0.5,"target_mult":4.0,"trail_mult":2.5})
r=run_backtest(df,sig,mode="both",point_value=cfg["point_value"],tick_size=cfg["tick_size"],commission_per_side=cfg["commission_per_side"],slippage_ticks=cfg["slippage_ticks"])
t=r["trades_df"].copy(); t["day"]=pd.to_datetime(t["entry_time"]).dt.normalize(); orb=t.groupby("day")["pnl"].sum()
ts=[]
for a in ["MNQ","MES","MGC","MCL"]:
    c=get_asset(a); px=daily(a); ts.append((np.sign(px.pct_change(126)).shift(1)*px.diff()*c["point_value"]).dropna())
tsmom=pd.concat(ts,axis=1).sum(axis=1)
vix,vix3m,svxy=yh("^VIX"),yh("^VIX3M"),yh("SVXY"); v=pd.DataFrame({"vix":vix,"vix3m":vix3m,"svxy":svxy}).dropna()
vx=((v["vix3m"]/v["vix"]-1).shift(1).gt(0).astype(float)*v["svxy"].pct_change()).dropna()
idx=orb.index.intersection(tsmom.index).intersection(vx.index); orb=orb.reindex(idx).fillna(0); tsmom=tsmom.reindex(idx).fillna(0); vx=vx.reindex(idx).fillna(0)
cands={"ORB+0.05xTSMOM":orb+0.05*tsmom, "ORB+$2k_VX":orb+2000*vx, "ORB+both":orb+0.05*tsmom+2000*vx}
print("=== PER-YEAR combined Sharpe (ORB-alone vs +sleeve) ===")
yrs=sorted(set(orb.index.year))
hdr="year   ORB  "+"  ".join(f"{k.split('+')[1]:>14s}" for k in cands); print(hdr)
for y in yrs:
    m=orb.index.year==y; row=f"{y}  {shp(orb[m]):>5.2f}"
    for k,s in cands.items(): row+=f"  {shp(s[m]):>14.2f}"
    print(row)
print(f"\nFULL   {shp(orb):>5.2f}"+"".join(f"  {shp(s):>14.2f}" for s in cands.values()))
n_improve={k:sum(1 for y in yrs if shp(s[orb.index.year==y])>shp(orb[orb.index.year==y])) for k,s in cands.items()}
print("years improved vs ORB:",{k:f"{v}/{len(yrs)}" for k,v in n_improve.items()})
# walk-forward: choose TSMOM mult on H1 maximizing combined Sharpe, apply to H2
h=len(orb)//2; o1,o2=orb.iloc[:h],orb.iloc[h:]; t1,t2=tsmom.iloc[:h],tsmom.iloc[h:]
mults=[0,0.03,0.05,0.08,0.10,0.15,0.20]
best=max(mults,key=lambda m:shp(o1+m*t1)); 
print(f"\nWALK-FWD TSMOM: H1-optimal mult={best} (H1 Sharpe {shp(o1+best*t1)} vs ORB {shp(o1)}) -> H2 OOS: ORB+{best}xTSMOM Sharpe {shp(o2+best*t2)} vs ORB-alone {shp(o2)} -> OOS_improves={shp(o2+best*t2)>shp(o2)}")
