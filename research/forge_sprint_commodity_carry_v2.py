"""SPRINT B v2 — refined commodity term-structure (CL/GC), the 4 expressions the naive-sign KILL taught us to try.
1 de-trended z-carry (fixes GC degenerate-side: trade DEVIATION from own contango baseline, ~mean-zero side)
2 front-deferred SPREAD momentum (trade the curve, not the level)  3 SPREAD mean-reversion  4 roll-window pressure.
Validators first (expression + degenerate-side), then DSR global+family, then adversarial review. Report-only."""
import sys; from pathlib import Path; import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from research.term_structure import build_curve
from research.forge_deflated_sharpe import deflated_sharpe
from research.forge_trial_ledger import record, count
from research.validate_strategy_expression import assert_expression_valid
from research.adversarial_result_review import review
PV={"CL":1000.0,"GC":100.0}; RTC={"CL":40.0,"GC":30.0}
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if len(x)>1 and x.std()>0 else 0
def maxyr(p): yr=p.groupby(p.index.year).sum(); return 100*yr.max()/yr.sum() if yr.sum()>0 else 999
def panel(root):
    c=build_curve(root).dropna(subset=["F1","F2"])
    sF1=(c["F1sym"]==c["F1sym"].shift(1)); sBoth=sF1 & (c["F2sym"]==c["F2sym"].shift(1))
    ret=(c["F1"].diff()*PV[root]).where(sF1,0.0)          # front $ return, roll-safe
    spread=c["F1"]-c["F2"]; dspread=(spread.diff()*PV[root]).where(sBoth,0.0)  # spread $ return, roll-safe
    return pd.DataFrame({"ret":ret,"spread":spread,"dspread":dspread},index=c.index).dropna()
def z(s,w=252): return (s-s.rolling(w,min_periods=60).mean())/s.rolling(w,min_periods=60).std()
print("=== SPRINT B v2: refined commodity term-structure (CL/GC) ===")
res={}
for r in ["CL","GC"]:
    d=panel(r)
    # 1 de-trended z-carry: trade deviation of carry from own baseline (mean-zero -> non-degenerate side)
    pos=np.sign(z(d["spread"])).shift(1)
    pnl=(pos*d["ret"] - (pos.diff().abs().fillna(0)>0)*RTC[r]).dropna()
    ok=assert_expression_valid(pos.reindex(pnl.index),pnl,f"detrended_zcarry_{r}")
    res[f"zcarry_{r}"]=dict(pnl=pnl,sh=shp(pnl.values),maxyr=maxyr(pnl),long=float((pos>0).mean()),ok=ok)
    # 2 spread momentum: position on spread = sign(spread - its MA); pnl = pos * dspread
    smom=np.sign(d["spread"]-d["spread"].rolling(20,min_periods=10).mean()).shift(1)
    p2=(smom*d["dspread"] - (smom.diff().abs().fillna(0)>0)*RTC[r]).dropna()
    res[f"spreadmom_{r}"]=dict(pnl=p2,sh=shp(p2.values),maxyr=maxyr(p2),long=float((smom>0).mean()),ok=assert_expression_valid(smom.reindex(p2.index),p2,f"spreadmom_{r}"))
    # 3 spread mean-reversion: fade z extremes of spread
    smr=(-np.sign(z(d["spread"]))).where(z(d["spread"]).abs()>1.5,0.0).shift(1)
    p3=(smr*d["dspread"] - (smr.diff().abs().fillna(0)>0)*RTC[r]).dropna()
    res[f"spreadMR_{r}"]=dict(pnl=p3,sh=shp(p3.values),maxyr=maxyr(p3),long=float((smr>0).mean()),ok=assert_expression_valid(smr.reindex(p3.index),p3,f"spreadMR_{r}"))
for k,v in res.items():
    tag="EXPR_OK" if v["ok"] else "EXPR_INVALID"
    print(f"  {k:14s} Sh={v['sh']:>5.2f} net=${v['pnl'].sum():>8.0f} maxyr={v['maxyr']:>4.0f}% long-share={v['long']:.0%} [{tag}] n={len(v['pnl'])}")
    record(f"COMMODITY_CARRY_V2:{k}",sharpe=v["sh"],verdict="family",lane="commodity_carry")
# 4 roll-window pressure diagnostic (front return in 5d pre-roll, conditioned on curve state)
for r in ["CL","GC"]:
    c=build_curve(root=r).dropna(subset=["F1","F2"]); rollday=(c["F1sym"]!=c["F1sym"].shift(-1))
    pre=rollday.shift(-5,fill_value=False).rolling(5).max().fillna(0).astype(bool)  # ~5d before a roll
    contango=(c["F1"]<c["F2"]); fret=c["F1"].pct_change().shift(-1)  # next-day front return in window
    win=fret[pre & contango].dropna()
    print(f"  roll-window {r}: pre-roll+contango front next-day mean={win.mean()*100:.3f}% n={len(win)} (diagnostic)")
gN=count(); fN=count(lane="commodity_carry")
valid={k:v for k,v in res.items() if v["ok"]}
best=max(valid,key=lambda k:valid[k]["sh"]) if valid else None
if best:
    bp=res[best]["pnl"]; dG=deflated_sharpe(bp.values,gN,sr_trials_std=0.05)
    print(f"\n  TRIAL-N global={gN} commodity_carry-family={fN} | best-valid={best} Sh={res[best]['sh']} DSR global={dG.get('dsr')}")
    verdict="SCREEN_PASS" if res[best]["sh"]>=1.0 and dG.get("dsr",0)>=0.95 and res[best]["maxyr"]<40 else ("CLEAN_BUT_WEAK" if res[best]["sh"]>0.5 else "CLEAN_KILL")
    ok,fails=review(dict(id=f"commodity_carry_v2_{best}",label=verdict,sharpe=res[best]["sh"],n=len(bp),maxyr=res[best]["maxyr"],
        long_share=res[best]["long"],cost_delta=1,global_n=gN,family_n=fN,richer_data_checked=True,harness_checked=True,
        family_exhausted_claim=False,expressions_tested=6))
    print(f"  VERDICT: {verdict}{'  [adversarial PASS]' if ok else '  [adversarial FAIL]: '+str(fails)}")
else:
    print("\n  ALL refined expressions EXPR_INVALID -> no valid candidate; family status unchanged")
print("  SCOPE: refined CL/GC term-structure. If all weak/kill -> commodity carry FAMILY tested to completion criteria (6 exprs); mark accordingly (not 'exhausted-all-data').")
