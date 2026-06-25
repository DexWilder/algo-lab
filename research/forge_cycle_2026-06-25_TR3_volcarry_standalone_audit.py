"""TRUTH_RESET item 3 — VOL-CARRY standalone point-in-time audit (report-only).
Signal = (VIX3M/VIX - 1).shift(1) > 0  (contango, prior close) -> long short-vol (SVXY return).
Causality-first: (A) future-perturbation invariance on the daily construction; (B) costs wired (ETP round-trip
bps on flips); (C) data sanity. THEN honest standalone metrics in return-space. No 'validated' language.
Label from taxonomy. SVXY is a proxy (ETP decay/leverage-reset) -> vehicle realism is a DEPLOYMENT item, not research."""
import sys, json, urllib.request
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
def yh(s):
    u=f"https://query1.finance.yahoo.com/v8/finance/chart/{s}?range=10y&interval=1d"
    r=json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"}),timeout=20).read()); res=r["chart"]["result"][0]
    return pd.Series(res["indicators"]["quote"][0]["close"],index=pd.to_datetime(res["timestamp"],unit="s").normalize()).dropna().pipe(lambda x:x[~x.index.duplicated()])
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if len(x)>1 and x.std()>0 else 0
vix,vix3m,svxy=yh("^VIX"),yh("^VIX3M"),yh("SVXY")
v=pd.DataFrame({"vix":vix,"vix3m":vix3m,"svxy":svxy}).dropna()
def vc_ret(frame, cost_bps=0.0):
    sig=(frame["vix3m"]/frame["vix"]-1).shift(1).gt(0).astype(float)
    ret=sig*frame["svxy"].pct_change()
    flips=sig.diff().abs().fillna(0)>0
    return (ret - flips*cost_bps/1e4).dropna()
print("=== TR3 vol-carry standalone audit (contango -> short-vol via SVXY) ===")
# (A) causality: perturb FUTURE svxy/vix, assert PAST returns invariant
print("-- (A) future-perturbation invariance --")
T=int(len(v)*0.6); cut=v.index[T]
base=vc_ret(v)
hi=v.copy(); hi.iloc[T+1:, :]=hi.iloc[T+1:, :]*3.0;  rh=vc_ret(hi)
lo=v.copy(); lo.iloc[T+1:, :]=lo.iloc[T+1:, :]*0.33; rl=vc_ret(lo)
common=base.index[base.index<=cut]
pd_diff=int((rh.reindex(common).fillna(0).round(8)!=rl.reindex(common).fillna(0).round(8)).sum())
print(f"     past returns changed by future perturbation = {pd_diff} -> {'CAUSAL_CLEAN' if pd_diff==0 else 'LOOKAHEAD_DETECTED'}")
# (B) cost sensitivity
gross=vc_ret(v,0.0); net=vc_ret(v,10.0)  # 10bps round-trip on flips
print(f"-- (B) cost sensitivity -- gross cumret={gross.sum():.3f} vs costed={net.sum():.3f} flips={int(((v['vix3m']/v['vix']-1).shift(1).gt(0).astype(float).diff().abs()>0).sum())} -> {'COST_WIRED' if abs(gross.sum()-net.sum())>1e-6 else 'NO_TURNOVER'}")
# standalone metrics (return space; $ sizing arbitrary for standalone)
def m(s,label):
    p=s.values; eq=np.cumprod(1+p)-1; dd=eq-np.maximum.accumulate(eq); h=len(s)//2
    print(f"  {label:16s} Sharpe={shp(p):>5.2f} cumret={p.sum()*100:>6.1f}% maxDD(ret)={dd.min()*100:>6.1f}% worstday={s.min()*100:>5.1f}% H1={shp(s.iloc[:h].values):>5.2f} H2={shp(s.iloc[h:].values):>5.2f}")
print("-- standalone metrics (after 10bps flip cost) --")
m(net,"vol-carry")
print("  per-year Sharpe: " + "  ".join(f"{y}:{shp(g.values)}" for y,g in net.groupby(net.index.year)))
yc=net.groupby(net.index.year).sum(); top2=yc.sort_values().iloc[-2:].sum()
print(f"  year-concentration: top-2 years = {100*top2/yc.sum():.0f}% of cumret" if yc.sum()!=0 else "")
print("\n  LABEL assigned in report (CLEAN_RESEARCH_CANDIDATE only if it clears standalone gates; else CLEAN_BUT_WEAK_DIVERSIFIER).")
