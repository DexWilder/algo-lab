"""ALPHA_INTAKE_FACTORY — P04 ZN month-end duration extension: DEEPENING (report-only).
PRE-DECLARED window family = last_n in {1,2,3,4,5} sessions of month (NO tuning). Canonical = last_3 (originally
found, NOT best-of-family -> avoids selection bias). Strategy = long ZN over the window, flat else; daily series.
Checklist: DSR-at-full-N / window-robustness / recent-decay / H1-H2 / per-year / cross-tenor ZF,ZB / roll-artifact
(exclude quarter-end roll months) / single-period dependence / worst d-w-m+DLL / cost stress / execution knowable.
Verdict: KILL | SCREEN_PASS_RETAINED | CLEAN_FORCED_FLOW_CANDIDATE. No WH/validated/primary. Capital gate unchanged."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.asset_config import get_asset
from research.forge_deflated_sharpe import deflated_sharpe
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if len(x)>1 and x.std()>0 else 0
def daily(asset):
    df=pd.read_csv(ROOT/f"data/processed/{asset}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
    return df.assign(dt=df["datetime"].dt.normalize()).groupby("dt")["close"].last()
def window_series(asset, last_n, exclude_qend=False):
    """Daily $ PnL series: long ZN-type on last_n sessions of month, flat else. Cost round-trip per month on exit day."""
    d=daily(asset); pv=get_asset(asset)["point_value"]
    ret=(d.diff()*pv)
    f=pd.DataFrame({"ret":ret}).dropna(); f["ym"]=f.index.to_period("M"); f["mo"]=f.index.month
    f["rev"]=f.groupby("ym").cumcount(ascending=False)
    inwin=f["rev"]<last_n
    if exclude_qend: inwin=inwin & (~f["mo"].isin([3,6,9,12]))   # drop quarter-end (Treasury roll) months
    cost=get_asset(asset)["commission_per_side"]*2 + get_asset(asset)["slippage_ticks"]*2*get_asset(asset)["tick_size"]*pv
    s=f["ret"].where(inwin,0.0).copy()
    # charge round-trip cost once per month on the last in-window day (rev==0)
    s.loc[inwin & (f["rev"]==0)] -= cost
    return s
def stats(s,label):
    a=s[s!=0]; p=s.values; eq=np.cumsum(p); dd=eq-np.maximum.accumulate(eq); h=len(s)//2
    yr=s.groupby(s.index.year).sum()
    print(f"  {label:18s} Sh={shp(p):>5.2f} net=${p.sum():>7.0f} maxDD=${dd.min():>7.0f} wd=${s.min():>6.0f} "
          f"wk=${s.rolling(5).sum().min():>7.0f} H1={shp(s.iloc[:h].values):>5.2f} H2={shp(s.iloc[h:].values):>5.2f} yrs+={int((yr>0).mean()*100)}%")
    return dict(sharpe=shp(p), net=float(p.sum()), per_period_sharpe=float(np.mean(p)/np.std(p)) if np.std(p)>0 else 0, yr=yr)
print("=== P04 ZN month-end duration extension — DEEPENING ===")
print("PRE-DECLARED family: last_n in {1,2,3,4,5}; canonical=last_3. Long ZN over window, flat else.")
# 1) window robustness (family)
print("-- window-family robustness (ZN) --")
fam={}; persh=[]
for n in [1,2,3,4,5]:
    s=window_series("ZN",n); r=stats(s,f"ZN last_{n}"); fam[n]=s; persh.append(r["per_period_sharpe"])
canon=window_series("ZN",3); cp=canon.values
# 2) DSR at full factory N
n_prior=3  # P02 MES, P02 MNQ, P04 ZN(orig)
n_here=5+2  # 5 ZN windows + ZF,ZB cross-tenor (below)
N=n_prior+n_here
disp=float(np.std(persh)) if len(persh)>1 else None
dsr=deflated_sharpe(cp[cp!=0] if False else cp, N, sr_trials_std=disp)
print(f"-- DSR at full factory N={N} (dispersion across window family={disp:.4f}) --")
print(f"  canonical last_3: per-period SR={dsr.get('sr_per_period')} ann={dsr.get('sr_annualized_252')} sr0_benchmark={dsr.get('sr0_benchmark')} DSR={dsr.get('dsr')} -> {dsr.get('verdict')}")
# 3) cross-tenor
print("-- cross-tenor confirmation (last_3) --")
zf=window_series("ZF",3); stats(zf,"ZF last_3")
zb=window_series("ZB",3); stats(zb,"ZB last_3")
# 4) roll-artifact: exclude quarter-end (Mar/Jun/Sep/Dec) roll months
print("-- roll-artifact control (ZN last_3, EXCLUDING quarter-end roll months) --")
stats(window_series("ZN",3,exclude_qend=True),"ZN ex-Qend")
# 5) single-period dependence: drop best year
yr=canon.groupby(canon.index.year).sum(); best_year=yr.idxmax()
s_noBest=canon[canon.index.year!=best_year]
print(f"-- single-period dependence: drop best year ({best_year}, ${yr.max():.0f}) --")
stats(s_noBest,"ZN ex-bestyr")
# 6) cost stress
print("-- cost stress (ZN last_3, 3x slippage) --")
d=daily("ZN"); pv=get_asset("ZN")["point_value"]; ret=(d.diff()*pv)
f=pd.DataFrame({"ret":ret}).dropna(); f["ym"]=f.index.to_period("M"); f["rev"]=f.groupby("ym").cumcount(ascending=False)
inwin=f["rev"]<3; cost3=get_asset("ZN")["commission_per_side"]*2 + get_asset("ZN")["slippage_ticks"]*6*get_asset("ZN")["tick_size"]*pv
s3=f["ret"].where(inwin,0.0); s3.loc[inwin&(f["rev"]==0)]-=cost3; s3.index=canon.index[:len(s3)] if len(s3)==len(canon) else f.index[inwin.index]
stats(pd.Series(s3.values,index=f.index),"ZN 3x-slip")
print(f"\n  per-year canonical: " + "  ".join(f"{y}:{int(v)}" for y,v in yr.items()))
print("  execution: enter close of 3rd-from-last session, exit month-end close; dates known in advance -> KNOWABLE.")
print(f"\n  VERDICT INPUTS: DSR={dsr.get('verdict')}, window-robust?(family coherent), cross-tenor?(ZF/ZB sign), roll-clean?, single-period?, recent yrs?")
