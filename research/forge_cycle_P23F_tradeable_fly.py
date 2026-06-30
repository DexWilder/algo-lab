"""P23-F — TRADEABLE DV01-weighted rates butterfly (ZF/ZN/ZB = 5s10s30s) vs the FRED-yield signal (report-only).
P23 found 2s5s10s YIELD curvature mean-reverts (research-grade, not tradeable). We hold ZF(5y)/ZN(10y)/ZB(30y) futures
(NOT ZT 2y) -> the tradeable fly is 5s10s30s. Continuous .c.0 series carry ROLL artifacts -> winsorize + flag (proper
test needs rates_multicontract.csv = Lane-1 #1). Full hostile: DV01-weighted, costed, roll-winsorized, H1/H2, per-year,
worst d/w/m, concentration, margin/notional sanity, FRED-vs-futures compare, DSR at global+family+lane N. Verdict ladder."""
import sys; from pathlib import Path; import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.asset_config import get_asset
from research.forge_deflated_sharpe import deflated_sharpe
from research.forge_trial_ledger import record, count
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if len(x)>1 and x.std()>0 else 0
def dclose(a):
    df=pd.read_csv(ROOT/f"data/processed/{a}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
    return df.assign(d=df["datetime"].dt.normalize()).groupby("d")["close"].last()
# DV01 ($/bp/contract, approx): ZF 5y~42, ZN 10y~64, ZB 30y~180. DV01-neutral 5s10s30s fly: belly=2 ZN, wings split by DV01.
DV01={"ZF":42.0,"ZN":64.0,"ZB":180.0}
w_zn=2.0; wing_dv01=(w_zn*DV01["ZN"])/2.0; w_zf=wing_dv01/DV01["ZF"]; w_zb=wing_dv01/DV01["ZB"]   # each wing hedges half belly DV01
print("=== P23-F tradeable DV01 fly (ZF/ZN/ZB = 5s10s30s) ===")
print(f"  DV01-neutral weights (contracts): ZN(belly)={w_zn} ZF={w_zf:.2f} ZB={w_zb:.2f}")
legs={}
for a in ["ZF","ZN","ZB"]:
    c=dclose(a); pv=get_asset(a)["point_value"]; mv=(c.diff()*pv)
    mv=mv.clip(mv.quantile(0.005),mv.quantile(0.995))   # winsorize roll spikes (continuous .c.0 caveat)
    legs[a]=mv
idx=legs["ZF"].index.intersection(legs["ZN"].index).intersection(legs["ZB"].index)
fly_pnl=(w_zn*legs["ZN"].reindex(idx) - w_zf*legs["ZF"].reindex(idx) - w_zb*legs["ZB"].reindex(idx)).dropna()  # long-curvature $ pnl/day
# FRED 5s10s30s curvature signal (matches the futures fly point on the curve)
y=pd.read_csv(ROOT/"data/feeds/treasury_yield_curve.csv"); y["date"]=pd.to_datetime(y["date"]); y=y.set_index("date").sort_index()
for c in ["dgs5","dgs10","dgs30"]: y[c]=pd.to_numeric(y[c],errors="coerce")
curv=2*y["dgs10"]-y["dgs5"]-y["dgs30"]
z=((curv-curv.rolling(252,min_periods=60).mean())/curv.rolling(252,min_periods=60).std()).shift(1).reindex(fly_pnl.index).ffill()
cost_rt=sum(get_asset(a)["commission_per_side"]*2+get_asset(a)["slippage_ticks"]*2*get_asset(a)["tick_size"]*get_asset(a)["point_value"] for a in ["ZF","ZN","ZB"])
pos=-np.sign(z).where(z.abs()>1.5,0.0)              # fade curvature extremes (causal: z lagged)
flips=pos.diff().abs().fillna(0)
pnl=(pos*fly_pnl - flips*cost_rt).dropna()
active=pnl[pos.reindex(pnl.index)!=0]
p=pnl.values; eq=np.cumsum(p); dd=eq-np.maximum.accumulate(eq); h=len(pnl)//2
yr=pnl.groupby(pnl.index.year).sum(); maxyr=100*yr.max()/yr.sum() if yr.sum()>0 else 999
record("P23F_tradeable_fly",asset="ZF/ZN/ZB",sharpe=shp(p),verdict="hostile",lane="forced_flow")
gN=count(); fN=count(lane="forced_flow")
dG=deflated_sharpe(p,gN,sr_trials_std=0.05); dF=deflated_sharpe(p,fN,sr_trials_std=0.05)
print(f"  active days={len(active)} (|z|>1.5) | FULL Sh={shp(p)} net=${p.sum():.0f} maxDD=${dd.min():.0f} MAR={p.sum()/abs(dd.min()) if dd.min()<0 else 0:.2f}")
print(f"  wd=${pnl.min():.0f} wk=${pnl.rolling(5).sum().min():.0f} mo=${pnl.rolling(21).sum().min():.0f} | H1={shp(pnl.iloc[:h].values)} H2={shp(pnl.iloc[h:].values)} max-year={maxyr:.0f}%")
print(f"  per-year: " + "  ".join(f"{y_}:{int(v)}" for y_,v in yr.items()))
notional=w_zn*100000+w_zf*100000+w_zb*100000  # ~$100k face/contract
print(f"  margin/notional sanity: ~${notional:,.0f} face; est margin ~${0.02*notional:,.0f}; 3-leg fly, intraday-held days only")
print(f"  TRIAL-N: global={gN} forced_flow_family={fN} packet=1 | DSR threshold=0.95")
print(f"  DSR global-N={gN}: {dG.get('dsr')} ({dG.get('verdict')}) | DSR family-N={fN}: {dF.get('dsr')}")
print(f"  COMPARE: FRED-yield-signal (P23) annSh~1.63 (curvature units, untradeable) vs THIS futures-$ Sh={shp(p)}")
# verdict ladder
if shp(p)<0.3 or maxyr>50:
    print("VERDICT: CLEAN_KILL (futures expression dies / concentration)" )
elif dG.get("dsr",0)>=0.95 and maxyr<40 and shp(p)>=1.0:
    print("VERDICT: SCREEN_PASS (tradeable fly survives costs+roll-winsor+concentration+DSR-global) — RESEARCH candidate, not WH/primary")
else:
    print("VERDICT: RETEST_REQUIRED (continuous .c.0 roll-contaminated; needs rates_multicontract.csv per Lane-1 #1 for clean DV01 legs)")
