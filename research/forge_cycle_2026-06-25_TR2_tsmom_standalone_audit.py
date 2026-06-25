"""TRUTH_RESET item 2 — TSMOM STANDALONE point-in-time audit (report-only).
TSMOM was only ever measured as an ORB diversifier; ORB is now INVALIDATED, so TSMOM must be re-audited
STANDALONE as a potential primary. Apply causality-first: (A) future-perturbation invariance on the daily
construction (perturb future daily closes -> past daily PnL must be invariant); (B) costs wired (flip costs
actually charged); (C) rollover-artifact scan per leg. THEN honest standalone metrics. No 'validated' language;
output a label from the TRUTH_RESET taxonomy. Capital gate unchanged."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.asset_config import get_asset
LEGS=["MNQ","MES","MGC"]   # MCL dropped earlier (dirtiest + negative); audit the clean pool
LB=126
def daily_close(a):
    df=pd.read_csv(ROOT/f"data/processed/{a}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
    return df.assign(d=df["datetime"].dt.normalize()).groupby("d")["close"].last()
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if len(x)>1 and x.std()>0 else 0
def leg_pnl(close, pv, cost_per_flip=0.0):
    pos=np.sign(close.pct_change(LB)).shift(1)        # point-in-time: position from data thru t-1
    pnl=(pos*close.diff()*pv)                          # applied to t's move
    flips=pos.diff().abs().fillna(0)>0                 # position change -> charge cost
    pnl=pnl - flips*cost_per_flip
    return pnl.dropna()
def book_pnl(cost=True):
    legs=[]
    for a in LEGS:
        cfg=get_asset(a); c=daily_close(a)
        cf=(cfg["commission_per_side"]*2 + cfg["slippage_ticks"]*2*cfg["tick_size"]/cfg["tick_size"]*cfg.get("tick_value",cfg["point_value"]*cfg["tick_size"])) if cost else 0.0
        legs.append(leg_pnl(c,cfg["point_value"],cf))
    return pd.concat(legs,axis=1).sum(axis=1).dropna()
def metrics(s,label):
    p=s.values; eq=np.cumsum(p); dd=eq-np.maximum.accumulate(eq); h=len(s)//2
    print(f"  {label:22s} Sharpe={shp(p):>5.2f} net=${p.sum():>8.0f} maxDD=${dd.min():>8.0f} "
          f"MAR={p.sum()/abs(dd.min()):>5.2f} wd=${s.min():>7.0f} H1={shp(s.iloc[:h].values):>5.2f} H2={shp(s.iloc[h:].values):>5.2f}")
print("=== TR2 TSMOM standalone audit (pool MNQ/MES/MGC, lb126) ===")
# (A) CAUSALITY — perturb FUTURE daily closes, assert PAST daily PnL invariant
print("-- (A) future-perturbation invariance (daily construction) --")
c0=daily_close("MNQ"); pv=get_asset("MNQ")["point_value"]
base=leg_pnl(c0,pv); T=int(len(c0)*0.6); cutdate=c0.index[T]
chi=c0.copy(); chi.iloc[T+1:]=chi.iloc[T+1:]*3.0;  hi=leg_pnl(chi,pv)
clo=c0.copy(); clo.iloc[T+1:]=clo.iloc[T+1:]*0.33; lo=leg_pnl(clo,pv)
common=base.index[base.index<=cutdate]
past_diff=int((hi.reindex(common).fillna(0).round(4)!=lo.reindex(common).fillna(0).round(4)).sum())
print(f"     MNQ leg: past daily-PnL bars changed by future perturbation = {past_diff}  -> {'CAUSAL_CLEAN' if past_diff==0 else 'LOOKAHEAD_DETECTED'}")
# (C) rollover artifacts per leg
print("-- (C) rollover-artifact scan per leg --")
for a in LEGS:
    mv=daily_close(a).pct_change().abs(); na=int((mv>0.08).sum())
    print(f"     {a}: {na} days |move|>8% (max {mv.max()*100:.1f}%) -> {'CLEAN' if na<=5 else 'SUSPECT' if na<=12 else 'CONTAMINATED'}")
# (B)+metrics: gross vs costed standalone
print("-- (B) cost sensitivity + standalone metrics --")
gross=book_pnl(cost=False); net=book_pnl(cost=True)
print(f"     cost wired? gross net=${gross.sum():.0f} vs costed net=${net.sum():.0f} -> {'COST_WIRED' if abs(gross.sum()-net.sum())>1 else 'COST_NOT_CHARGED(low turnover?)'}")
metrics(gross,"TSMOM gross")
metrics(net,"TSMOM costed")
# per-year (costed)
print("  per-year (costed): " + "  ".join(f"{y}:{int(g.sum())}" for y,g in net.groupby(net.index.year)))
print("\n  LABEL: assigned in report after reading causality+artifact+edge (taxonomy: CLEAN_RESEARCH_CANDIDATE / POINT_IN_TIME_PENDING / INVALIDATED).")
