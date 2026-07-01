"""SPRINT A2 — PROPER cross-sectional DV01-normalized rates carry (market-neutral, report-only).
Fix for the degenerate 'always long duration': rank ZT/ZF/ZN/ZB by DV01-normalized roll-yield (F1-F2)/DV01, LONG top /
SHORT bottom, DV01-neutral (isolates carry SPREAD, ~0 net duration). Runs through validate_strategy_expression FIRST.
Roll-handled, costed, causal, layered-N. No WH language."""
import sys; from pathlib import Path; import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from research.term_structure import build_curve
from research.forge_deflated_sharpe import deflated_sharpe
from research.forge_trial_ledger import record, count
from research.validate_strategy_expression import assert_expression_valid
PV={"ZT":2000.0,"ZF":1000.0,"ZN":1000.0,"ZB":1000.0}; DV01={"ZT":37.0,"ZF":46.0,"ZN":64.0,"ZB":120.0}; RTC=30.0
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if len(x)>1 and x.std()>0 else 0
def front(root):
    c=build_curve(root).dropna(subset=["F1","F2"]); same=(c["F1sym"]==c["F1sym"].shift(1))
    ret=(c["F1"].diff()*PV[root]).where(same,0.0)
    ncarry=(c["F1"]-c["F2"])/DV01[root]           # DV01-normalized roll-yield
    return pd.DataFrame({"ret":ret,"ncarry":ncarry},index=c.index).dropna()
D={r:front(r) for r in ["ZT","ZF","ZN","ZB"]}
idx=D["ZT"].index
for r in ["ZF","ZN","ZB"]: idx=idx.intersection(D[r].index)
carry=pd.DataFrame({r:D[r]["ncarry"].reindex(idx) for r in D}).shift(1).dropna()   # lagged=causal
longleg=carry.idxmax(axis=1); shortleg=carry.idxmin(axis=1)
print("=== SPRINT A2: cross-sectional DV01 rates carry (long top / short bottom) ===")
# long-leg rotation check (is it really cross-sectional or always one tenor?)
lshare=longleg.value_counts(normalize=True)
print(f"  long-leg rotation: {dict(lshare.round(2))}  short-leg: {dict(shortleg.value_counts(normalize=True).round(2))}")
# PnL: DV01-neutral long-short ($ per unit-DV01 exposure), roll-handled
rows=[]
for d in carry.index:
    lt=longleg[d]; st=shortleg[d]
    if lt==st: rows.append((d,0.0)); continue
    # 1 unit DV01 each leg: contracts = 1/DV01 ; $ = ret/DV01
    pnl=D[lt]["ret"].get(d,0.0)/DV01[lt] - D[st]["ret"].get(d,0.0)/DV01[st]
    rows.append((d,pnl*100))   # scale to ~$/100-DV01
s=pd.Series(dict(rows)).dropna()
# cost when legs change
chg=((longleg!=longleg.shift(1))|(shortleg!=shortleg.shift(1))).reindex(s.index).fillna(True)
s=s - chg.astype(float)*(RTC/DV01["ZN"]*100)*2
# expression validation FIRST (the missing control) — validate long-leg rotation as the 'signal'
sigpos=longleg.map({"ZT":1,"ZF":2,"ZN":3,"ZB":4}).reindex(s.index)  # non-constant if it rotates
ok=assert_expression_valid(sigpos, s, "xsec_carry", intended_side="long_short")
maxshare=float(lshare.max())
if maxshare>0.90: print(f"  ** EXPR WARNING: long-leg is {maxshare:.0%} one tenor -> collapses to directional (not truly cross-sectional)")
# metrics
v=s.values; eq=np.cumsum(v); dd=eq-np.maximum.accumulate(eq); h=len(s)//2
yr=s.groupby(s.index.year).sum(); maxyr=100*yr.max()/yr.sum() if yr.sum()>0 else 999
record("RATES_XSEC:dv01_carry",sharpe=shp(v),verdict="family",lane="carry")
gN=count(); fN=count(lane="carry"); dG=deflated_sharpe(v,gN,sr_trials_std=0.05); dF=deflated_sharpe(v,fN,sr_trials_std=0.05)
print(f"  Sh={shp(v)} net={v.sum():.0f} maxDD={dd.min():.0f} H1={shp(s.iloc[:h].values)} H2={shp(s.iloc[h:].values)} maxyr={maxyr:.0f}%")
print(f"  TRIAL-N global={gN} carry-family={fN} | DSR global={dG.get('dsr')} family={dF.get('dsr')}")
verdict="SCREEN_PASS" if shp(v)>=1.0 and dG.get('dsr',0)>=0.95 and maxyr<40 else ("CLEAN_BUT_WEAK" if shp(v)>0.5 else "CLEAN_KILL")
print(f"  VERDICT: {verdict}{' (expr valid)' if ok else ' — EXPR_INVALID, result not trusted'}")
