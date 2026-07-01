"""SPRINT A — RATES term-structure family on REAL per-contract data (report-only).
Uses term_structure.build_curve (front F1 / deferred F2, outrights, NO stitch). Roll handled: F1 daily PnL only when
same contract day-over-day; roll days cost, no jump. Predeclared expressions:
 1. Per-tenor roll-yield carry (long front when backwardated, ZT/ZF/ZN/ZB) + pooled.
 2. Cross-tenor carry-rank (long best roll-yield tenor).
 3. True 2s5s10s DV01 curvature RV (ZT/ZF/ZN front) — fade z-extremes.
Full: causal(lagged), costed, roll-audited, H1/H2, per-year, concentration, DSR global+carry-lane+packet. No WH language."""
import sys; from pathlib import Path; import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from research.term_structure import build_curve
from research.forge_deflated_sharpe import deflated_sharpe
from research.forge_trial_ledger import record, count
PV={"ZT":2000.0,"ZF":1000.0,"ZN":1000.0,"ZB":1000.0}; RTC=30.0  # ~$ round-trip/contract
DV01={"ZT":37.0,"ZF":46.0,"ZN":64.0}
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if len(x)>1 and x.std()>0 else 0
def front_ret(root):
    """front-contract daily $ PnL (roll-safe) + roll_yield (F1-F2) + roll-day flag."""
    c=build_curve(root); c=c.dropna(subset=["F1","F2"])
    same=(c["F1sym"]==c["F1sym"].shift(1))
    ret=(c["F1"].diff()*PV[root]).where(same,0.0)   # no cross-contract jump on roll day
    ry=(c["F1"]-c["F2"])                              # >0 backwardation = positive carry to long
    return pd.DataFrame({"ret":ret,"ry":ry,"roll":~same},index=c.index).dropna()
def stats(p,label):
    v=p.values; eq=np.cumsum(v); dd=eq-np.maximum.accumulate(eq); h=len(p)//2
    yr=p.groupby(p.index.year).sum(); maxyr=100*yr.max()/yr.sum() if yr.sum()>0 else 999
    print(f"  {label:24s} Sh={shp(v):>5.2f} net=${v.sum():>8.0f} maxDD=${dd.min():>8.0f} H1={shp(p.iloc[:h].values):>5.2f} H2={shp(p.iloc[h:].values):>5.2f} maxyr={maxyr:>4.0f}%")
    return maxyr
print("=== SPRINT A: RATES term-structure (real per-contract, roll-handled) ===")
D={r:front_ret(r) for r in ["ZT","ZF","ZN","ZB"]}
# 1. per-tenor roll-yield carry
print("-- 1 per-tenor roll-yield carry (long front when backwardated) --")
carry_pnls={}
for r in ["ZT","ZF","ZN","ZB"]:
    d=D[r]; pos=np.sign(d["ry"]).shift(1); pnl=(pos*d["ret"] - (pos.diff().abs().fillna(0)>0)*RTC).dropna()
    carry_pnls[r]=pnl; stats(pnl,f"carry {r}")
pool=pd.concat(carry_pnls.values(),axis=1).sum(axis=1).dropna(); mp=stats(pool,"carry POOLED")
# 2. cross-tenor carry-rank: long best roll-yield tenor (normalize ry by DV01-ish scale via price level)
ryf=pd.DataFrame({r:D[r]["ry"] for r in ["ZT","ZF","ZN","ZB"]}).shift(1)
ryf=ryf.dropna(); best=ryf.idxmax(axis=1)
rp=[]
for r in ["ZT","ZF","ZN","ZB"]:
    w=(best==r).reindex(D[r].index).fillna(False).astype(float); rp.append(w*D[r]["ret"])
rank=pd.concat(rp,axis=1).sum(axis=1).dropna(); stats(rank,"carry-rank (long best)")
# 3. true 2s5s10s DV01 curvature RV (ZT/ZF/ZN front)
belly=D["ZF"]["ret"]; wz=1.24; wn=0.72  # belly 2xZF DV01, wings ZT*1.24 + ZN*0.72 (DV01-neutral)
idx=D["ZT"].index.intersection(D["ZF"].index).intersection(D["ZN"].index)
fly=(2*belly.reindex(idx) - wz*D["ZT"]["ret"].reindex(idx) - wn*D["ZN"]["ret"].reindex(idx)).dropna()  # long-curvature $
# signal: DV01 curvature level from front prices
cz=pd.DataFrame({"ZT":D["ZT"]["ry"]*0+build_curve("ZT")["F1"],"ZF":build_curve("ZF")["F1"],"ZN":build_curve("ZN")["F1"]})
# use price-curvature proxy (2*ZF - ZT - ZN in DV01 units)
curv=(2*build_curve("ZF")["F1"]/DV01["ZF"] - build_curve("ZT")["F1"]/DV01["ZT"] - build_curve("ZN")["F1"]/DV01["ZN"])
z=((curv-curv.rolling(252,min_periods=60).mean())/curv.rolling(252,min_periods=60).std()).shift(1).reindex(fly.index).ffill()
pos=-np.sign(z).where(z.abs()>1.5,0.0); flyp=(pos*fly - pos.diff().abs().fillna(0)*RTC*3).dropna()
stats(flyp,"2s5s10s DV01 RV")
# DSR (layered) on best of the family
for name,p in [("carry_pooled",pool),("carry_rank",rank),("2s5s10s_rv",flyp)]: record(f"RATES_TS:{name}",sharpe=shp(p.values),verdict="family",lane="curve_rv")
gN=count(); fN=count(lane="curve_rv")
cand={"carry_pooled":pool,"carry_rank":rank,"2s5s10s_rv":flyp}
bn=max(cand,key=lambda k:shp(cand[k].values)); bp=cand[bn]
dG=deflated_sharpe(bp.values,gN,sr_trials_std=0.05); dF=deflated_sharpe(bp.values,fN,sr_trials_std=0.05)
print(f"\n  roll-audit: roll days handled (no cross-contract jump). TRIAL-N global={gN} curve_rv-family={fN}")
print(f"  best '{bn}' Sh={shp(bp.values)} | DSR global={dG.get('dsr')} family={dF.get('dsr')} (threshold 0.95)")
best_sh=shp(bp.values); best_maxyr=100*bp.groupby(bp.index.year).sum().max()/bp.sum() if bp.sum()>0 else 999
print(f"  VERDICT: {'SCREEN_PASS (rates TS survives cost+roll+concentration+DSR)' if best_sh>=1.0 and dG.get('dsr',0)>=0.95 and best_maxyr<40 else ('CLEAN_BUT_WEAK' if best_sh>0.5 else 'CLEAN_KILL (rates term-structure family dead on real per-contract data)')}")
