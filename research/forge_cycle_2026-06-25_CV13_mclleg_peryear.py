"""CV13 — MCL TSMOM-leg keep/drop + per-year worst day/week/month (report-only, dossier open items).
Closes 2 of the 3 remaining dossier items. MCL daily returns are rollover-artifact-prone
(feedback_continuous_contract_rollover_artifacts): MCL has 18 days >8% vs MNQ/MES/MGC ~0-1.
So the MCL leg is BOTH the weakest standalone leg AND the dirtiest data. Test 3 TSMOM pools at
canonical k=0.10 vol-target sizing, evaluated OOS on H2:
  (a) full pool incl raw MCL   (b) pool minus MCL   (c) pool with MCL winsorized at +/-8% daily.
If raw-MCL only helps via un-winsorized artifact spikes -> DROP. Report-only; capital gate unchanged."""
import sys, json, urllib.request
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.backtest import run_backtest
from engine.asset_config import get_asset
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals
def daily(s): df=pd.read_csv(ROOT/f"data/processed/{s}_5m.csv"); dt=pd.to_datetime(df["datetime"]); return df.assign(d=dt.dt.normalize()).groupby("d")["close"].last()
def yh(s):
    u=f"https://query1.finance.yahoo.com/v8/finance/chart/{s}?range=10y&interval=1d"
    r=json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"}),timeout=20).read()); res=r["chart"]["result"][0]
    return pd.Series(res["indicators"]["quote"][0]["close"],index=pd.to_datetime(res["timestamp"],unit="s").normalize()).dropna().pipe(lambda x:x[~x.index.duplicated()])
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if x.std()>0 else 0
def tsmom_leg(a, winsor=None):
    c=daily(a); ret=c.pct_change(); mv=c.diff()
    if winsor is not None:  # cap the daily % move, reconstruct $ move from prior close -> kills roll spikes
        capped=ret.clip(-winsor,winsor); mv=(capped*c.shift(1))
    return (np.sign(c.pct_change(126)).shift(1)*mv*get_asset(a)["point_value"]).dropna()
# ORB primary
cfg=get_asset("MNQ"); df=pd.read_csv(ROOT/"data/processed/MNQ_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
sig=generate_crossbred_signals(df,entry_name="orb_breakout",exit_name="profit_ladder",filter_name="ema_slope",params={"stop_mult":0.5,"target_mult":4.0,"trail_mult":2.5})
r=run_backtest(df,sig,mode="both",point_value=cfg["point_value"],tick_size=cfg["tick_size"],commission_per_side=cfg["commission_per_side"],slippage_ticks=cfg["slippage_ticks"])
t=r["trades_df"].copy(); orb=t.assign(day=pd.to_datetime(t["entry_time"]).dt.normalize()).groupby("day")["pnl"].sum()
# MCL artifact characterization
mcl_ret=daily("MCL").pct_change().dropna(); n_art={a:int((daily(a).pct_change().abs()>0.08).sum()) for a in ["MNQ","MES","MGC","MCL"]}
# TSMOM pool variants
legs={a:tsmom_leg(a) for a in ["MNQ","MES","MGC","MCL"]}
ts_full=pd.concat([legs[a] for a in ["MNQ","MES","MGC","MCL"]],axis=1).sum(axis=1)
ts_noMCL=pd.concat([legs[a] for a in ["MNQ","MES","MGC"]],axis=1).sum(axis=1)
ts_winsMCL=pd.concat([legs["MNQ"],legs["MES"],legs["MGC"],tsmom_leg("MCL",winsor=0.08)],axis=1).sum(axis=1)
# vol-carry
vix,vix3m,svxy=yh("^VIX"),yh("^VIX3M"),yh("SVXY"); v=pd.DataFrame({"vix":vix,"vix3m":vix3m,"svxy":svxy}).dropna()
vcret=((v["vix3m"]/v["vix"]-1).shift(1).gt(0).astype(float)*v["svxy"].pct_change()).dropna()
def align(*series):
    idx=series[0].index
    for s in series[1:]: idx=idx.intersection(s.index)
    return [s.reindex(idx).fillna(0) for s in series], idx
def book(s):
    p=s.values; eq=np.cumsum(p); dd=eq-np.maximum.accumulate(eq)
    return dict(sharpe=shp(p),MAR=round(p.sum()/abs(dd.min()),2) if dd.min()<0 else None,maxDD=round(float(dd.min())),worst=round(float(s.min())),DLL=int((s<-1100).sum()),net=round(float(p.sum())))
# === MCL-leg keep/drop at canonical k=0.10 vol-target, OOS on H2 ===
print("=== CV13 MCL TSMOM-leg keep/drop (k=0.10 vol-target, weights H1-derived, eval OOS H2) ===")
print(f"  rollover-artifact days |move|>8%: "+"  ".join(f"{a}={n}" for a,n in n_art.items())+f"  | MCL max 1d move={mcl_ret.abs().max()*100:.1f}%")
print(f"  MCL TSMOM leg standalone: raw Sharpe={shp(legs['MCL'].values)} net=${legs['MCL'].sum():.0f} | winsor8% Sharpe={shp(tsmom_leg('MCL',0.08).values)} net=${tsmom_leg('MCL',0.08).sum():.0f}")
print(f"  {'pool':16s} {'H2 Sharpe':>9s} {'H2 MAR':>6s} {'H2 maxDD':>9s} {'H2 worst':>8s} {'H2 DLL':>6s} {'H2 net':>7s}")
for name,ts in [("full(+rawMCL)",ts_full),("drop_MCL",ts_noMCL),("winsor_MCL",ts_winsMCL)]:
    (o,tt,vc),idx=align(orb,ts,vcret); h=len(idx)//2; H2=idx[h:]
    so=o.reindex(idx[:h]).std(); st=tt.reindex(idx[:h]).std(); sv=vc.reindex(idx[:h]).std()
    wt=0.10*so/st; wv=0.10*so/sv; c=(o+wt*tt+wv*vc).reindex(H2); b=book(c)
    print(f"  {name:16s} {b['sharpe']:>9.2f} {str(b['MAR']):>6s} {b['maxDD']:>9} {b['worst']:>8} {b['DLL']:>6} {b['net']:>7}")
# === per-year worst day/week/month, canonical book = full pool k=0.10 (FULL sample) ===
(o,tt,vc),idx=align(orb,ts_full,vcret); h=len(idx)//2
so=o.reindex(idx[:h]).std(); st=tt.reindex(idx[:h]).std(); sv=vc.reindex(idx[:h]).std()
combined=o+(0.10*so/st)*tt+(0.10*so/sv)*vc
print("\n=== Per-year worst day / week(5d) / month(21d), combined book (full pool, k=0.10) ===")
print(f"  {'year':6s} {'worst_day':>10s} {'worst_wk':>9s} {'worst_mo':>9s} {'net':>8s} {'sharpe':>6s}")
for y,g in combined.groupby(combined.index.year):
    wd=g.min(); wk=g.rolling(5).sum().min(); mo=g.rolling(21).sum().min()
    print(f"  {y:6d} {wd:>10.0f} {wk:>9.0f} {mo:>9.0f} {g.sum():>8.0f} {shp(g.values):>6.2f}")
g=combined; print(f"  {'ALL':6s} {g.min():>10.0f} {g.rolling(5).sum().min():>9.0f} {g.rolling(21).sum().min():>9.0f} {g.sum():>8.0f} {shp(g.values):>6.2f}")
