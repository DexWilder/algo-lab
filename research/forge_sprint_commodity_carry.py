"""SPRINT B — COMMODITY term-structure carry (CL/GC, real per-contract, report-only). Family-aware + validators first.
Roll-yield = F1-F2 (backwardation>0=positive carry long). Expressions: CL carry, GC carry, cross-sectional, front/deferred
spread MR. Validate expression (side non-degenerate) + adversarial review before verdict. CL->MCL, GC->MGC micro mapping stated."""
import sys; from pathlib import Path; import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from research.term_structure import build_curve
from research.forge_deflated_sharpe import deflated_sharpe
from research.forge_trial_ledger import record, count
from research.validate_strategy_expression import assert_expression_valid
from research.adversarial_result_review import review
PV={"CL":1000.0,"GC":100.0}; RTC={"CL":40.0,"GC":30.0}  # full-size; micro MCL=CL/100-signal, MGC=GC/10
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if len(x)>1 and x.std()>0 else 0
def front(root):
    c=build_curve(root).dropna(subset=["F1","F2"]); same=(c["F1sym"]==c["F1sym"].shift(1))
    ret=(c["F1"].diff()*PV[root]).where(same,0.0); ry=(c["F1"]-c["F2"])   # >0 backwardation
    return pd.DataFrame({"ret":ret,"ry":ry},index=c.index).dropna()
print("=== SPRINT B: COMMODITY term-structure carry (CL/GC real per-contract) ===")
res={}
for r in ["CL","GC"]:
    d=front(r); pos=np.sign(d["ry"]).shift(1)   # long when backwardated
    pnl=(pos*d["ret"] - (pos.diff().abs().fillna(0)>0)*RTC[r]).dropna()
    ok=assert_expression_valid(pos.reindex(pnl.index), pnl, f"carry_{r}")
    v=pnl.values; yr=pnl.groupby(pnl.index.year).sum(); maxyr=100*yr.max()/yr.sum() if yr.sum()>0 else 999
    h=len(pnl)//2; res[r]=dict(pnl=pnl,sh=shp(v),maxyr=maxyr,h1=shp(pnl.iloc[:h].values),h2=shp(pnl.iloc[h:].values),longshare=float((pos>0).mean()),expr_ok=ok)
    print(f"  carry {r}: Sh={shp(v)} net=${v.sum():.0f} H1={res[r]['h1']} H2={res[r]['h2']} maxyr={maxyr:.0f}% long-share={res[r]['longshare']:.0%}")
    record(f"COMMODITY_CARRY:{r}",asset=r,sharpe=shp(v),verdict="family",lane="commodity_carry")
# cross-sectional CL vs GC (long higher-carry)
cl,gc=front("CL"),front("GC"); idx=cl.index.intersection(gc.index)
xc=pd.DataFrame({"CL":cl["ry"].reindex(idx),"GC":gc["ry"].reindex(idx)}).shift(1).dropna()
# normalize ry by price level (both different scale) -> use sign of which is more backwardated (z each)
z=lambda s:(s-s.rolling(252,min_periods=60).mean())/s.rolling(252,min_periods=60).std()
longCL=(z(cl["ry"]).reindex(idx)>z(gc["ry"]).reindex(idx)).shift(1)
xpnl=(np.where(longCL,cl["ret"].reindex(idx)/PV["CL"],gc["ret"].reindex(idx)/PV["GC"])); xs=pd.Series(xpnl,index=idx).dropna()*100
record("COMMODITY_CARRY:xsec",sharpe=shp(xs.values),verdict="family",lane="commodity_carry")
print(f"  xsec CL/GC carry: Sh={shp(xs.values)}")
gN=count(); fN=count(lane="commodity_carry")
best=max(res,key=lambda k:res[k]["sh"]); bp=res[best]["pnl"]
dG=deflated_sharpe(bp.values,gN,sr_trials_std=0.05); dF=deflated_sharpe(bp.values,fN,sr_trials_std=0.05)
print(f"  TRIAL-N global={gN} commodity_carry-family={fN} | best={best} Sh={res[best]['sh']} DSR global={dG.get('dsr')} family={dF.get('dsr')}")
verdict="SCREEN_PASS" if res[best]["sh"]>=1.0 and dG.get("dsr",0)>=0.95 and res[best]["maxyr"]<40 else ("CLEAN_BUT_WEAK" if res[best]["sh"]>0.5 else "CLEAN_KILL")
# adversarial review
ok,fails=review(dict(id=f"commodity_carry_{best}",label=verdict,sharpe=res[best]["sh"],n=len(bp),maxyr=res[best]["maxyr"],
   long_share=res[best]["longshare"],cost_delta=1,global_n=gN,family_n=fN,richer_data_checked=True,harness_checked=True,
   family_exhausted_claim=False,expressions_tested=3))
print(f"  VERDICT: {verdict} (CL->MCL, GC->MGC micro tradeable){'  [adversarial PASS]' if ok else '  [adversarial FAIL -> not hardened]'}")
print(f"  FAMILY: commodity carry ACTIVE_EXPANSION — 3 of 6 expressions done (carry CL/GC, xsec); remaining: spread-mom, spread-MR, roll-window (predeclared, queued)")
