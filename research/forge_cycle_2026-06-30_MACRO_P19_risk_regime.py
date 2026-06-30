"""P19 — macro risk-on/off regime (UNUSED FEEDS: credit_oas, dollar_index, copper_gold) -> predict MES/MGC/ZN (report-only).
Risk-off = high HY-OAS + strong USD + low copper/gold. Lagged 1d (causal). Does macro regime predict next-day futures?"""
import sys; from pathlib import Path; import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.asset_config import get_asset
from research.forge_deflated_sharpe import deflated_sharpe
from research.forge_trial_ledger import record, count
def feed(f,col):
    d=pd.read_csv(ROOT/f"data/feeds/{f}.csv"); d["date"]=pd.to_datetime(d["date"]); return d.set_index("date")[col]
oas=feed("credit_oas","hy_oas"); usd=feed("dollar_index","usd_broad"); cuau=feed("copper_gold_ratio_yahoo","cu_au")
def z(s): return (s-s.rolling(252,min_periods=60).mean())/s.rolling(252,min_periods=60).std()
risk_off=(z(oas)+z(usd)-z(cuau)).shift(1)  # lagged -> known at today's open
def dclose(a):
    df=pd.read_csv(ROOT/f"data/processed/{a}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
    return df.assign(d=df["datetime"].dt.normalize()).groupby("d")["close"].last()
print("=== P19 macro risk-regime (credit_oas+dollar+copper_gold) -> next-day futures ===")
allp=[]
for a,sgn in [("MES",-1),("MGC",1),("ZN",1)]:   # risk-off: short equity, long gold/bonds
    c=dclose(a); pv=get_asset(a)["point_value"]; ret=(c.diff()*pv)
    ro=risk_off.reindex(c.index).ffill()
    pos=sgn*np.sign(ro)                          # extreme-regime directional
    pnl=(pos*ret).dropna(); pnl=pnl[ro.abs().reindex(pnl.index)>1.0]   # only strong-regime days
    sh=round(pnl.mean()/pnl.std()*np.sqrt(252),2) if pnl.std()>0 else 0
    print(f"  [{a}] strong-regime days n={len(pnl)} annSh={sh} net=${pnl.sum():.0f}"); allp.append(pnl)
    record("P19_macro_regime",asset=a,sharpe=sh,verdict="screen")
pooled=pd.concat(allp); N=count(); per=pooled.mean()/pooled.std() if pooled.std()>0 else 0
d=deflated_sharpe(pooled.values,N,sr_trials_std=0.05)
print(f"  pooled n={len(pooled)} annSh={round(per*np.sqrt(252),2)} DSR@N={N}={d.get('dsr')} -> {d.get('verdict')}")
print("VERDICT: CLEAN_KILL" if abs(per)*np.sqrt(252)<0.5 else "VERDICT: review (macro regime has signal)")
