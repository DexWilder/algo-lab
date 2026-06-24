"""Cycle 2026-06-24p — month-end rebalance drift (report-only).
Mechanism (Harris/flow): pension/balanced-fund rebalancing at month-end → predictable equity drift, direction
conditioned on intra-month equity-vs-bond divergence (rebalancers SELL winners / BUY losers). No-lookahead:
month equity-vs-bond divergence known by ~2 days before month-end → trade last-2-day window. Predeclared:
high divergence (equity≫bond) → month-end equity SELL pressure → SHORT equity; low/neg → LONG. No flip.
Test: MES last-2-day-of-month return conditioned on divergence; both sides, per-year, cost. Report-only."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
def daily(s):
    df=pd.read_csv(ROOT/f"data/processed/{s}_5m.csv"); dt=pd.to_datetime(df["datetime"]); return df.assign(d=dt.dt.normalize()).groupby("d")["close"].last()
def _pf(a): a=np.asarray(a,float); a=a[~np.isnan(a)]; l=-a[a<0].sum(); return round(a[a>0].sum()/l,3) if l>0 else 9.9
mes=daily("MES"); zn=daily("ZN")
df=pd.DataFrame({"mes":mes,"zn":zn}).dropna()
df["ym"]=df.index.to_period("M")
# last-2-trading-days of each month
last2=df.groupby("ym").tail(2).index
df["is_me"]=df.index.isin(last2)
# month-end window equity return (entry = 3rd-last day close, exit = last day close)
me_ret={}
div={}
for ym,g in df.groupby("ym"):
    if len(g)<5: continue
    entry=g["mes"].iloc[-3]; exit_=g["mes"].iloc[-1]   # hold last 2 days
    me_ret[ym]=exit_/entry-1
    # intra-month divergence through entry (known): equity vs bond return month-start→entry
    e0=g["mes"].iloc[0]; b0=g["zn"].iloc[0]; be=g["zn"].iloc[-3]
    div[ym]=(entry/e0-1)-(be/b0-1)
me=pd.Series(me_ret); dv=pd.Series(div)
m=pd.DataFrame({"me_ret":me,"div":dv}).dropna()
m["yr"]=m.index.year
print(f"=== MONTH-END DRIFT (MES last-2-day window, n={len(m)} months) ===")
print(f"  unconditional last-2-day equity return: mean={m['me_ret'].mean()*1e4:.1f}bps PF={_pf(m['me_ret'].values)} pos%={100*(m['me_ret']>0).mean():.0f}%")
# rebalance hypothesis: high divergence -> SHORT (fade), low/neg -> LONG
dz=(m["div"]-m["div"].mean())/m["div"].std()
m["pos"]=np.where(dz>0.5,-1,np.where(dz<-0.5,1,0))
t=m[m["pos"]!=0].copy(); t["pnl"]=t["pos"]*t["me_ret"]-0.0003
longs=t[t["pos"]==1]["pnl"]; shorts=t[t["pos"]==-1]["pnl"]
yr=t.groupby("yr")["pnl"].sum()
print(f"  rebalance-conditioned (div z>0.5 short / <-0.5 long): n={len(t)} PF={_pf(t['pnl'].values)} mean={t['pnl'].mean()*1e4:.1f}bps yrs+={int((yr>0).sum())}/{yr.shape[0]}")
print(f"     long(low-div) n={len(longs)} PF={_pf(longs.values)} | short(high-div) n={len(shorts)} PF={_pf(shorts.values)}")
# correlation check: is divergence actually predictive? (sign of div vs sign of me_ret)
corr=np.corrcoef(m["div"],m["me_ret"])[0,1]
print(f"  corr(intra-month divergence, month-end equity return) = {corr:.3f}  (rebalance hypothesis wants NEGATIVE)")
v = "WATCH_calendar" if _pf(t["pnl"].values)>=1.2 and int((yr>0).sum())/max(1,yr.shape[0])>=0.6 else ("KILL_no_rebalance_drift" if abs(corr)<0.1 else "KILL")
print(f"  -> VERDICT: {v}")
