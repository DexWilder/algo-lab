"""GEX REGIME FEATURE (durable INDEX_REGIME_INPUT ingredient — NOT a standalone strategy). The GEX compression regime
survived full OOS (pos-GEX ~40% lower next-day realized vol, all 3 years). This exposes it as a reusable FEATURE for WH1
tests: per-date signed-GEX, sign, magnitude bucket, compression/expansion flag, DTE bucket. Causal: prior-settlement OI.
Usage: from research.gex_regime_feature import gex_regime; g = gex_regime()  # DataFrame indexed by date"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
R=Path("/Users/chasefisher/projects/Algo Trading/algo-lab")
def _mes_open():
    m=pd.read_csv(R/"data/databento/MES_1m.csv",parse_dates=["datetime"]).set_index("datetime")
    mm=m.index.hour*60+m.index.minute;prof=m.groupby(mm)["volume"].sum();full=pd.Series(0.0,index=range(1440));full.loc[prof.index]=prof.values
    s0=int(full.rolling(390,min_periods=390).sum().idxmax())-389;rth=m[(mm>=s0)&(mm<s0+390)].copy();rth["d"]=rth.index.normalize()
    return rth.groupby("d")["open"].first()
def gex_regime(oi_path=None):
    oi=pd.read_csv(oi_path or R/"data/databento/ES_OPT_weekly_oi.csv",parse_dates=["date"])
    oi["exp"]=pd.to_datetime(oi["expiration"],utc=True,errors="coerce").dt.tz_localize(None);oi["dte"]=(oi["exp"]-oi["date"]).dt.days
    opn=_mes_open();recs=[]
    for d,g in oi.groupby("date"):
        front=g[(g["dte"]>=1)&(g["dte"]<=5)]
        if front.empty or d not in opn.index:continue
        E=front["exp"].min();ch=front[front["exp"]==E];spot=opn.loc[d]
        near=ch[(ch["strike_price"]>spot*0.97)&(ch["strike_price"]<spot*1.03)]
        if near["oi"].sum()<500:continue
        w=np.exp(-0.5*((near["strike_price"]-spot)/(0.007*spot))**2)
        gexv=float((w*near["oi"]*np.where(near["cp"]=="C",1,-1)).sum())
        bs=near.groupby("strike_price")["oi"].sum()
        recs.append(dict(date=d,gex=gexv,dte=int((E-d).days),dist_to_pin=abs(bs.idxmax()-spot)/spot))
    G=pd.DataFrame(recs).set_index("date").sort_index()
    med=G["gex"].median()
    G["gex_sign"]=np.where(G["gex"]>med,"pos","neg")          # pos=long-gamma=compression; neg=short-gamma=expansion
    G["regime"]=np.where(G["gex"]>med,"compression","expansion")
    G["mag_bucket"]=pd.qcut(G["gex"].abs(),3,labels=["lo","mid","hi"],duplicates="drop")
    return G
if __name__=="__main__":
    g=gex_regime();print(f"gex_regime feature: {len(g)} days | compression {int((g['regime']=='compression').sum())} / expansion {int((g['regime']=='expansion').sum())}")
    print(g[["gex","regime","dte"]].tail(3).to_string())
