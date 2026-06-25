"""CV1/CV2 — principled risk-budgeted sizing of the validated bench (report-only).
Question (NOT weight-optimization): can vol-target/ERC/capped-inv-corr sizing — derived on H1, evaluated on H2 —
reproduce or improve the HAND-TUNED package (ORB + 0.05xTSMOM + $2k vol-carry) without overfitting? No optimizer.
Verdict: PRINCIPLED_SIZING_CONFIRMS / HAND_TUNED_BETTER / OVERFIT_REJECT / VALIDATED_BUT_MANUAL. Report-only."""
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
# components
cfg=get_asset("MNQ"); df=pd.read_csv(ROOT/"data/processed/MNQ_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
sig=generate_crossbred_signals(df,entry_name="orb_breakout",exit_name="profit_ladder",filter_name="ema_slope",params={"stop_mult":0.5,"target_mult":4.0,"trail_mult":2.5})
r=run_backtest(df,sig,mode="both",point_value=cfg["point_value"],tick_size=cfg["tick_size"],commission_per_side=cfg["commission_per_side"],slippage_ticks=cfg["slippage_ticks"])
t=r["trades_df"].copy(); orb=t.assign(day=pd.to_datetime(t["entry_time"]).dt.normalize()).groupby("day")["pnl"].sum()
tsmom=pd.concat([(np.sign(daily(a).pct_change(126)).shift(1)*daily(a).diff()*get_asset(a)["point_value"]).dropna() for a in ["MNQ","MES","MGC","MCL"]],axis=1).sum(axis=1)
vix,vix3m,svxy=yh("^VIX"),yh("^VIX3M"),yh("SVXY"); v=pd.DataFrame({"vix":vix,"vix3m":vix3m,"svxy":svxy}).dropna()
vcret=((v["vix3m"]/v["vix"]-1).shift(1).gt(0).astype(float)*v["svxy"].pct_change()).dropna()  # per-$ return
idx=orb.index.intersection(tsmom.index).intersection(vcret.index)
orb=orb.reindex(idx).fillna(0); tsmom=tsmom.reindex(idx).fillna(0); vcret=vcret.reindex(idx).fillna(0)
h=len(idx)//2; H1=idx[:h]; H2=idx[h:]
def book(s):
    p=s.values; eq=np.cumsum(p); dd=eq-np.maximum.accumulate(eq); yr=s.groupby(s.index.year).sum()
    return dict(sharpe=shp(p),MAR=round(p.sum()/abs(dd.min()),2) if dd.min()<0 else None,maxDD=round(float(dd.min())),worst=round(float(s.min())),DLL=int((s<-1100).sum()),y2019=round(float(s[s.index.year==2019].sum())),net=round(float(p.sum())))
# H1 risk stats (for principled sizing, derived on H1 ONLY)
so=orb.reindex(H1).std(); st=tsmom.reindex(H1).std(); sv=vcret.reindex(H1).std()
ct=abs(np.corrcoef(orb.reindex(H1),tsmom.reindex(H1))[0,1]); cv=abs(np.corrcoef(orb.reindex(H1),vcret.reindex(H1))[0,1])
def combo(wt,wv):  # wt=$mult on tsmom(1-contract), wv=$notional on vcret
    return orb + wt*tsmom + wv*vcret
variants={}
variants["ORB_alone"]=(0,0)
variants["hand_tuned_both(0.05x/$2k)"]=(0.05,2000)
for k in [0.10,0.15]:  # vol-target: each diversifier σ = k*ORB σ (small), derived on H1
    variants[f"voltarget_k{k}"]=(k*so/st, k*so/sv)
# capped inverse-corr (more decorrelated -> more of the small budget), base k=0.12, cap 1.5x
base=0.12; wt_ic=min(base*(cv/ct) if ct>0 else base,1.5*base)*so/st; wv_ic=min(base*(ct/cv) if cv>0 else base,1.5*base)*so/sv
variants["inv_corr_capped"]=(wt_ic,wv_ic)
print(f"=== CV1/CV2 principled sizing — weights derived on H1, EVALUATED on H2 ===")
print(f"  H1 risk: ORB σ=${so:.0f}/d TSMOM σ=${st:.0f} VC σ(per$)={sv:.4f} | |corr ORB-TSMOM|={ct:.2f} |corr ORB-VC|={cv:.2f}")
print(f"  {'variant':28s} {'wt(TSMOM)':>9s} {'wv(VC$)':>8s} | {'FULL Sh':>7s} {'H2 Sh':>6s} {'H2 MAR':>6s} {'H2 maxDD':>9s} {'H2 DLL':>6s} {'H2 net':>7s} {'2019':>6s}")
hand_h2=shp(combo(*variants["hand_tuned_both(0.05x/$2k)"]).reindex(H2).values)
for name,(wt,wv) in variants.items():
    c=combo(wt,wv); fb=shp(c.values); h2=book(c.reindex(H2)); flag=""
    if name.startswith(("voltarget","inv_corr")) and h2["sharpe"]>=hand_h2: flag=" <-- matches/beats hand-tuned OOS"
    print(f"  {name:28s} {wt:>9.3f} {wv:>8.0f} | {fb:>7.2f} {h2['sharpe']:>6.2f} {str(h2['MAR']):>6s} {h2['maxDD']:>9} {h2['DLL']:>6} {h2['net']:>7} {h2['y2019']:>6}{flag}")
print(f"\n  hand-tuned H2 Sharpe={hand_h2} | principled-sizing variants derived on H1 only (no optimizer, no H2 peeking)")
