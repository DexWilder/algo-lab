"""Cycle 2026-06-24r — FX rate-differential carry (report-only).
Reachable carry leg: 6E(EUR)/6J(JPY)/6B(GBP) futures (USD-quoted), 3yr. Carry = long high-rate / short low-rate
currency. 2024-26 dominant carry = SHORT JPY (funding currency). Test: (a) standalone short-6J, (b) cross-
sectional long-top1/short-bottom1 by trailing return (carry+momentum proxy). 3yr = expect DATA_LIMITED caveat.
Report-only; no mutation."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
def daily(s):
    df=pd.read_csv(ROOT/f"data/processed/{s}_5m.csv"); dt=pd.to_datetime(df["datetime"]); return df.assign(d=dt.dt.normalize()).groupby("d")["close"].last()
def shp(x): x=np.asarray(x,float); x=x[~np.isnan(x)]; return round(x.mean()/x.std()*np.sqrt(252),2) if x.std()>0 else 0
def _pf(a): a=np.asarray(a,float); a=a[~np.isnan(a)]; l=-a[a<0].sum(); return round(a[a>0].sum()/l,3) if l>0 else 9.9
FX=["6E","6J","6B"]
rets=pd.DataFrame({a:daily(a).pct_change() for a in FX}).dropna()
yrs=sorted(set(rets.index.year))
print(f"=== FX carry — 6E/6J/6B, {len(rets)}d {rets.index.min().date()}..{rets.index.max().date()} ({len(yrs)}yr) ===")
print(f"  per-currency ann return: "+" ".join(f"{a}={daily(a).pct_change().mean()*252*100:+.1f}%" for a in FX))
# (a) standalone short-JPY (funding-currency carry; short 6J = long USD vs JPY)
sj=(-rets["6J"]).dropna(); yr=sj.groupby(sj.index.year).sum()
print(f"\n  (a) short-6J (JPY funding carry): Sharpe={shp(sj)} ann={sj.mean()*252*100:+.1f}% PF={_pf(sj.values)} yrs+={int((yr>0).sum())}/{yr.shape[0]} per-yr%="+" ".join(f"{y}:{sj[sj.index.year==y].sum()*100:+.0f}" for y in yrs))
# (b) cross-sectional long-top1/short-bottom1 by trailing 63d, weekly rebal
trail=pd.DataFrame({a:daily(a).pct_change(63) for a in FX}).reindex(rets.index)
pos=pd.Series(0.0,index=FX); pnl=[]
for i,(dt_,row) in enumerate(trail.iterrows()):
    if i%5==0 and row.notna().all():
        r=row.rank(); pos=pd.Series(0.0,index=FX); pos[r==3]=1.0; pos[r==1]=-1.0
    pnl.append(float((pos*rets.loc[dt_]).sum()))
xs=pd.Series(pnl,index=trail.index).dropna(); yr2=xs.groupby(xs.index.year).sum()
print(f"  (b) XS long-top1/short-bottom1 (63d): Sharpe={shp(xs)} ann={xs.mean()*252*100:+.1f}% PF={_pf(xs.values)} yrs+={int((yr2>0).sum())}/{yr2.shape[0]}")
print(f"\n  VERDICT: DATA_LIMITED (only {len(yrs)}yr, 3 currencies) — directional read only; not bankable. "+
      ("short-JPY carry shows persistent positive (known 2024-26 regime)" if shp(sj)>0.5 else "no robust FX carry edge in window"))
