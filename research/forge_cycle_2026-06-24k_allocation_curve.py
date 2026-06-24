"""Cycle 2026-06-24k — allocation curve for TSMOM & vol-carry vs ORB (report-only).
Corrects the overreach: a low-Sharpe diversifier can still help via SMALL sizing / tail / MAR, not just Sharpe.
Fine allocation grid; report Sharpe, MAR, maxDD, worst day/wk/mo, DLL, net, ORB-worst20 offset. Find any small
allocation that improves tail/MAR without DLL deterioration -> WATCH_TAIL_OVERLAY. Report-only; no mutation."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0, str(ROOT))
from engine.asset_config import get_asset
from engine.backtest import run_backtest
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals
DLL=1100.0
def daily(s):
    df=pd.read_csv(ROOT/f"data/processed/{s}_5m.csv"); dt=pd.to_datetime(df["datetime"]); return df.assign(d=dt.dt.normalize()).groupby("d")["close"].last()
def yahoo(sym):
    import urllib.request
    u=f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=10y&interval=1d"
    r=json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"}),timeout=25).read()); res=r["chart"]["result"][0]
    return pd.Series(res["indicators"]["quote"][0]["close"],index=pd.to_datetime(res["timestamp"],unit="s").normalize()).dropna().pipe(lambda s:s[~s.index.duplicated()])
def bk(x):
    p=x.values; eq=np.cumsum(p); dd=eq-np.maximum.accumulate(eq); sd=p.std()
    return dict(sharpe=round(p.mean()/sd*np.sqrt(252),2), MAR=round(p.sum()/abs(dd.min()),2) if dd.min()<0 else None,
        maxDD=round(dd.min()), worst_d=round(x.min()), worst_w=round(x.resample("W").sum().min()), worst_m=round(x.resample("ME").sum().min()),
        DLL=int((x<-DLL).sum()), net=round(p.sum()))
# ORB
cfg=get_asset("MNQ"); df=pd.read_csv(ROOT/"data/processed/MNQ_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
sig=generate_crossbred_signals(df,entry_name="orb_breakout",exit_name="profit_ladder",filter_name="ema_slope",params={"stop_mult":0.5,"target_mult":4.0,"trail_mult":2.5})
r=run_backtest(df,sig,mode="both",point_value=cfg["point_value"],tick_size=cfg["tick_size"],commission_per_side=cfg["commission_per_side"],slippage_ticks=cfg["slippage_ticks"])
t=r["trades_df"].copy(); t["day"]=pd.to_datetime(t["entry_time"]).dt.normalize(); orb=t.groupby("day")["pnl"].sum()
# TSMOM lb126 pooled $
ts=[]
for a in ["MNQ","MES","MGC","MCL"]:
    c=get_asset(a); px=daily(a); ts.append((np.sign(px.pct_change(126)).shift(1)*px.diff()*c["point_value"]).dropna())
tsmom=pd.concat(ts,axis=1).sum(axis=1)
# vol-carry SVXY-contango timed return -> $ via allocation
vix,vix3m,svxy=yahoo("^VIX"),yahoo("^VIX3M"),yahoo("SVXY")
v=pd.DataFrame({"vix":vix,"vix3m":vix3m,"svxy":svxy}).dropna(); v["reg"]=(v["vix3m"]/v["vix"]-1).shift(1).gt(0).astype(float)
vx=(v["reg"]*v["svxy"].pct_change()).dropna()
idx=orb.index.intersection(tsmom.index).intersection(vx.index)
orb=orb.reindex(idx).fillna(0); tsmom=tsmom.reindex(idx).fillna(0); vx=vx.reindex(idx).fillna(0)
w20=orb.nsmallest(20).index
oa=bk(orb); print("ORB alone:",oa,"\n")
print("=== TSMOM allocation curve (xN of pooled-1-contract) ===")
for m in [0.05,0.10,0.15,0.25,0.50,1.0]:
    b=bk(orb+m*tsmom); b["TSMOM_on_ORBworst20_$"]=round((m*tsmom).reindex(w20).mean()); b["tail_better"]=b["MAR"]>=oa["MAR"] and b["worst_d"]>=oa["worst_d"] and b["DLL"]<=oa["DLL"]
    print(f"  {m:.2f}x: {b}")
print("\n=== vol-carry (SVXY-contango) allocation curve ($ notional) ===")
for d in [500,1000,2000,3000,5000]:
    b=bk(orb+d*vx); b["VX_on_ORBworst20_$"]=round((d*vx).reindex(w20).mean()); b["tail_better"]=b["MAR"]>=oa["MAR"] and b["worst_d"]>=oa["worst_d"] and b["DLL"]<=oa["DLL"]
    print(f"  ${d}: {b}")
