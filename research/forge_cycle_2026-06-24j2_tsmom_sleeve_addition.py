import json, sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0, str(ROOT))
from engine.asset_config import get_asset
from engine.backtest import run_backtest
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals
def daily(s):
    df=pd.read_csv(ROOT/f"data/processed/{s}_5m.csv"); dt=pd.to_datetime(df["datetime"]); return df.assign(d=dt.dt.normalize()).groupby("d")["close"].last()
def _pf(a): a=np.asarray(a,float); l=-a[a<0].sum(); return float(a[a>0].sum()/l) if l>0 else 9.9
# ORB
cfg=get_asset("MNQ"); df=pd.read_csv(ROOT/"data/processed/MNQ_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
sig=generate_crossbred_signals(df,entry_name="orb_breakout",exit_name="profit_ladder",filter_name="ema_slope",params={"stop_mult":0.5,"target_mult":4.0,"trail_mult":2.5})
r=run_backtest(df,sig,mode="both",point_value=cfg["point_value"],tick_size=cfg["tick_size"],commission_per_side=cfg["commission_per_side"],slippage_ticks=cfg["slippage_ticks"])
t=r["trades_df"].copy(); t["day"]=pd.to_datetime(t["entry_time"]).dt.normalize(); orb=t.groupby("day")["pnl"].sum()
# TSMOM lb126 pooled
ts=[]
for a in ["MNQ","MES","MGC","MCL"]:
    c=get_asset(a); px=daily(a); s=np.sign(px.pct_change(126)).shift(1); pnl=(s*px.diff()*c["point_value"]).dropna(); ts.append(pnl)
tsmom=pd.concat(ts,axis=1).sum(axis=1)
idx=orb.index.intersection(tsmom.index); orb=orb.reindex(idx).fillna(0); tsmom=tsmom.reindex(idx).fillna(0)
def book(x):
    p=x.values; eq=np.cumsum(p); dd=eq-np.maximum.accumulate(eq); sd=p.std(); yr=x.groupby(x.index.year).sum()
    return dict(net=round(p.sum()), sharpe=round(p.mean()/sd*np.sqrt(252),2), maxDD=round(dd.min()), worst=round(x.min()), DLL=int((x<-1100).sum()), MAR=round(p.sum()/abs(dd.min()),2), yrs=f"{int((yr>0).sum())}/{yr.shape[0]}")
print(f"corr(ORB,TSMOM)={np.corrcoef(orb.values,tsmom.values)[0,1]:.3f}")
wd=orb.nsmallest(20).index; print(f"TSMOM on ORB worst20: ${tsmom.reindex(wd).mean():.0f}/day -> offsets={tsmom.reindex(wd).mean()>0}")
oa=book(orb); print("ORB alone:",oa)
for w in [0.5,1.0,2.0]:
    print(f"ORB+{w}xTSMOM:",book(orb+w*tsmom))
