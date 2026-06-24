"""Cycle 2026-06-24n — V-crash guard (general, NOT COVID-tuned) + finer DSR on package (report-only).
TSMOM whipsawed in 2020 V-reversal. Test a SIMPLE general crisis guard: flatten TSMOM when VIX>35 (a
pre-existing crisis level, applied to ALL years). Does it help 2020 WITHOUT hurting other years (= useful)
or only help 2020 (= overfit, reject)? Plus DSR with proper trial-dispersion across the allocation grid.
Report-only; no mutation."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.asset_config import get_asset
from engine.backtest import run_backtest
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals
sys.path.insert(0,str(ROOT/"research")); from forge_deflated_sharpe import deflated_sharpe
def daily(s):
    df=pd.read_csv(ROOT/f"data/processed/{s}_5m.csv"); dt=pd.to_datetime(df["datetime"]); return df.assign(d=dt.dt.normalize()).groupby("d")["close"].last()
def yh(sym):
    import urllib.request; u=f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=10y&interval=1d"
    r=json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"}),timeout=25).read()); res=r["chart"]["result"][0]
    return pd.Series(res["indicators"]["quote"][0]["close"],index=pd.to_datetime(res["timestamp"],unit="s").normalize()).dropna().pipe(lambda s:s[~s.index.duplicated()])
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if x.std()>0 else 0
cfg=get_asset("MNQ"); df=pd.read_csv(ROOT/"data/processed/MNQ_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
sig=generate_crossbred_signals(df,entry_name="orb_breakout",exit_name="profit_ladder",filter_name="ema_slope",params={"stop_mult":0.5,"target_mult":4.0,"trail_mult":2.5})
r=run_backtest(df,sig,mode="both",point_value=cfg["point_value"],tick_size=cfg["tick_size"],commission_per_side=cfg["commission_per_side"],slippage_ticks=cfg["slippage_ticks"])
t=r["trades_df"].copy(); t["day"]=pd.to_datetime(t["entry_time"]).dt.normalize(); orb=t.groupby("day")["pnl"].sum()
ts=[]
for a in ["MNQ","MES","MGC","MCL"]:
    c=get_asset(a); px=daily(a); ts.append((np.sign(px.pct_change(126)).shift(1)*px.diff()*c["point_value"]).dropna())
tsmom=pd.concat(ts,axis=1).sum(axis=1)
vix,vix3m,svxy=yh("^VIX"),yh("^VIX3M"),yh("SVXY"); v=pd.DataFrame({"vix":vix,"vix3m":vix3m,"svxy":svxy}).dropna()
vxret=((v["vix3m"]/v["vix"]-1).shift(1).gt(0).astype(float)*v["svxy"].pct_change()).dropna()
vixd=vix.copy()
idx=orb.index.intersection(tsmom.index).intersection(vxret.index)
orb=orb.reindex(idx).fillna(0); tsmom=tsmom.reindex(idx).fillna(0); vxret=vxret.reindex(idx).fillna(0)
guard=(vixd.reindex(idx).ffill()>35).shift(1).fillna(False)  # flatten TSMOM when prior-close VIX>35 (general)
tsmom_g=tsmom.copy(); tsmom_g[guard.values]=0.0
print(f"=== V-CRASH GUARD (VIX>35 flatten TSMOM, general) — guard active {int(guard.sum())} days ({100*guard.mean():.1f}%) ===")
print("year   ORB   +0.05TSMOM   +0.05TSMOM_GUARDED")
for y in sorted(set(idx.year)):
    m=idx.year==y; print(f"  {y}  {shp(orb[m]):>5.2f}   {shp((orb+0.05*tsmom)[m]):>9.2f}   {shp((orb+0.05*tsmom_g)[m]):>9.2f}")
print(f"  FULL {shp(orb):>5.2f}   {shp(orb+0.05*tsmom):>9.2f}   {shp(orb+0.05*tsmom_g):>9.2f}")
# package with guarded TSMOM
pkg=orb+0.05*tsmom+2000*vxret; pkg_g=orb+0.05*tsmom_g+2000*vxret
def mdd(x): eq=np.cumsum(x.values); return round((eq-np.maximum.accumulate(eq)).min())
print(f"\n  PACKAGE unguarded: Sharpe {shp(pkg)} maxDD ${mdd(pkg)} 2020Sharpe {shp(pkg[idx.year==2020])}")
print(f"  PACKAGE guarded:   Sharpe {shp(pkg_g)} maxDD ${mdd(pkg_g)} 2020Sharpe {shp(pkg_g[idx.year==2020])}")
# finer DSR with proper trial-dispersion (std of Sharpes across the allocation grid tried ~12)
grid_sharpes=[shp(orb+m*tsmom) for m in [0,0.025,0.05,0.10,0.15,0.20]]+[shp(orb+d*vxret) for d in [0,1000,2000,3000,5000]]
sr_disp=float(np.std([s/np.sqrt(252) for s in grid_sharpes]))  # per-period Sharpe dispersion across trials
dsr=deflated_sharpe(pkg.values,n_trials=12,sr_trials_std=sr_disp)
print(f"\n  DSR (proper trial-dispersion {sr_disp:.4f}, 12 trials): {dsr.get('dsr')} ({dsr.get('verdict')}) deflated={dsr.get('deflation_applied')}")
