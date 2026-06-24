"""Cycle 2026-06-24m — both-sleeve interaction: TSMOM + vol-carry additive or redundant? (report-only)
Decisive: corr(TSMOM,VX), distinct vs same rescue windows, combined on ORB worst days, allocation grid,
per-year, DSR. If additive+robust -> VALIDATED_RESEARCH_CANDIDATE_SMALL_DIVERSIFIER. Report-only; no mutation."""
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
def bk(x):
    p=x.values; eq=np.cumsum(p); dd=eq-np.maximum.accumulate(eq)
    return dict(sharpe=shp(p), MAR=round(p.sum()/abs(dd.min()),2) if dd.min()<0 else None, maxDD=round(dd.min()), worst=round(x.min()), DLL=int((x<-1100).sum()), net=round(p.sum()))
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
idx=orb.index.intersection(tsmom.index).intersection(vxret.index)
orb=orb.reindex(idx).fillna(0); TS=(0.05*tsmom).reindex(idx).fillna(0); VX=(2000*vxret).reindex(idx).fillna(0)  # at the validated small sizes ($ terms)
# INTERACTION
print(f"=== INTERACTION (sleeves at validated small size, $ terms) ===")
print(f"  corr(TSMOM_sleeve, VX_sleeve) = {np.corrcoef(TS.values,VX.values)[0,1]:.3f}  (low/neg = additive/distinct)")
w20=orb.nsmallest(20).index
print(f"  ORB worst-20: TSMOM ${TS.reindex(w20).mean():.0f}/day  VX ${VX.reindex(w20).mean():.0f}/day  (both>0 = both rescue)")
for ylab,a,b in [("2019","2019-01-01","2019-12-31"),("2020COVID","2020-02-20","2020-03-31"),("2022","2022-01-01","2022-12-31")]:
    m=(idx>=a)&(idx<=b); print(f"  {ylab}: TSMOM ${TS[m].sum():.0f}  VX ${VX[m].sum():.0f}  (distinct contributors?)")
# ALLOCATION GRID
print("\n=== ALLOCATION GRID ===")
print(f"  ORB alone: {bk(orb)}")
for mt in [0.025,0.05,0.10,0.15]:
    print(f"  ORB+{mt}xTSMOM: {bk(orb+mt*tsmom.reindex(idx).fillna(0))}")
for d in [1000,2000,3000]:
    print(f"  ORB+${d}VX: {bk(orb+d*vxret.reindex(idx).fillna(0))}")
print(f"  ORB+0.05TSMOM+$2kVX (both): {bk(orb+TS+VX)}")
print(f"  ORB+0.10TSMOM+$3kVX (both-bigger): {bk(orb+0.10*tsmom.reindex(idx).fillna(0)+3000*vxret.reindex(idx).fillna(0))}")
# DSR on both-sleeve combined daily series
comb=(orb+TS+VX); dsr=deflated_sharpe(comb.values,n_trials=12)
print(f"\n  DSR/PSR on ORB+both daily: {dsr.get('dsr')} ({dsr.get('verdict')})")
# walk-forward both
h=len(orb)//2
print(f"  walk-fwd both: H1 ORB {shp(orb.iloc[:h])} vs +both {shp((orb+TS+VX).iloc[:h])} | H2 ORB {shp(orb.iloc[h:])} vs +both {shp((orb+TS+VX).iloc[h:])}")
