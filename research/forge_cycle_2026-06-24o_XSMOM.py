"""Cycle 2026-06-24o — XSMOM cross-sectional/relative-strength momentum (report-only).
Distinct from TSMOM (absolute trend): rank micros by trailing return, long top-2/short bottom-2, dollar-
neutral, weekly rebalance. Market-neutral-ish → could be decorrelated from BOTH ORB and TSMOM (3rd regime).
Test: standalone Sharpe/PF/per-year, corr to ORB PnL AND to TSMOM, DSR. If decorrelated+positive → allocation
curve next. No flip. Report-only; no mutation."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.asset_config import get_asset
from engine.backtest import run_backtest
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals
sys.path.insert(0,str(ROOT/"research")); from forge_deflated_sharpe import deflated_sharpe
ASSETS=["MNQ","MES","MGC","MCL","M2K"]
def daily(s):
    df=pd.read_csv(ROOT/f"data/processed/{s}_5m.csv"); dt=pd.to_datetime(df["datetime"]); return df.assign(d=dt.dt.normalize()).groupby("d")["close"].last()
def shp(x): x=np.asarray(x,float); x=x[~np.isnan(x)]; return round(x.mean()/x.std()*np.sqrt(252),2) if x.std()>0 else 0
def _pf(a): a=np.asarray(a,float); a=a[~np.isnan(a)]; l=-a[a<0].sum(); return round(a[a>0].sum()/l,3) if l>0 else 9.9
# returns panel
rets=pd.DataFrame({a: daily(a).pct_change() for a in ASSETS}).dropna()
def xsmom(lb, rebal=5):
    trail=pd.DataFrame({a: daily(a).pct_change(lb) for a in ASSETS}).reindex(rets.index)
    pnl=[]
    pos=pd.Series(0.0,index=ASSETS)
    for i,(dt_,row) in enumerate(trail.iterrows()):
        if i%rebal==0 and row.notna().all():
            r=row.rank(); pos=pd.Series(0.0,index=ASSETS)
            pos[r>=4]=0.5   # top-2 long (ranks 4,5)
            pos[r<=2]=-0.5  # bottom-2 short (ranks 1,2)
        # next-day portfolio return = pos . today's return (pos set from prior close = no lookahead)
        pnl.append(float((pos*rets.loc[dt_]).sum()))
    return pd.Series(pnl,index=trail.index).shift(0).dropna()
# ORB + TSMOM for correlation
cfg=get_asset("MNQ"); df=pd.read_csv(ROOT/"data/processed/MNQ_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
sig=generate_crossbred_signals(df,entry_name="orb_breakout",exit_name="profit_ladder",filter_name="ema_slope",params={"stop_mult":0.5,"target_mult":4.0,"trail_mult":2.5})
r=run_backtest(df,sig,mode="both",point_value=cfg["point_value"],tick_size=cfg["tick_size"],commission_per_side=cfg["commission_per_side"],slippage_ticks=cfg["slippage_ticks"])
t=r["trades_df"].copy(); t["day"]=pd.to_datetime(t["entry_time"]).dt.normalize(); orb=t.groupby("day")["pnl"].sum()
tsmom=pd.concat([(np.sign(daily(a).pct_change(126)).shift(1)*daily(a).diff()*get_asset(a)["point_value"]).dropna() for a in ["MNQ","MES","MGC","MCL"]],axis=1).sum(axis=1)
print("=== XSMOM cross-sectional (long top-2 / short bottom-2, weekly rebal, 5 micros) ===")
for lb in [21,63,126]:
    x=xsmom(lb); xc=(x-0.0002*(x!=0)) # ~2bps cost proxy per active day
    yr=x.groupby(x.index.year).sum()
    co=pd.concat([x.rename("x"),orb.rename("o")],axis=1).dropna(); ct=pd.concat([x.rename("x"),tsmom.rename("t")],axis=1).dropna()
    corr_orb=round(float(co["x"].corr(co["o"])),3) if len(co)>30 else None
    corr_tsmom=round(float(ct["x"].corr(ct["t"])),3) if len(ct)>30 else None
    dsr=deflated_sharpe(x.values,n_trials=3)
    print(f"  lb{lb}: Sharpe={shp(x)} PF={_pf(x.values)} mean={x.mean()*1e4:.1f}bps yrs+={int((yr>0).sum())}/{yr.shape[0]} corr-to-ORB={corr_orb} corr-to-TSMOM={corr_tsmom} PSR={dsr.get('dsr')}")
