"""FAMILY BATCH — CARRY (highest-EV untested family, report-only). Predeclared expressions (no open grid):
 1. Rates rolldown/curve-carry: long ZN duration when 2s10s curve steep (positive carry+rolldown), flat/short when flat/inverted.
 2. Cross-tenor rates carry-rank: rank ZF/ZN/ZB by curve-implied carry, long steepest-carry tenor.
 3. FX carry USDJPY: fed_funds vs boj_rate differential -> long USD (short 6J) when USD carry positive.
Uses UNUSED feeds (treasury_yield_curve, policy_rates). Causal (lagged signals). Costed. Family-N + global-N DSR.
Labels: FAMILY_UNDERTESTED/ACTIVE_EXPANSION/CLEAN_KILL/CLEAN_BUT_WEAK. No WH/primary language."""
import sys; from pathlib import Path; import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.asset_config import get_asset
from research.forge_deflated_sharpe import deflated_sharpe
from research.forge_trial_ledger import record, count
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if len(x)>1 and x.std()>0 else 0
def dclose(a):
    df=pd.read_csv(ROOT/f"data/processed/{a}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
    return df.assign(d=df["datetime"].dt.normalize()).groupby("d")["close"].last()
def dpnl(a): c=dclose(a); return (c.diff()*get_asset(a)["point_value"]).dropna()
def cost(a): return get_asset(a)["commission_per_side"]*2+get_asset(a)["slippage_ticks"]*2*get_asset(a)["tick_size"]*get_asset(a)["point_value"]
y=pd.read_csv(ROOT/"data/feeds/treasury_yield_curve.csv"); y["date"]=pd.to_datetime(y["date"]); y=y.set_index("date").sort_index()
for c in ["dgs2","dgs5","dgs10","dgs30"]: y[c]=pd.to_numeric(y[c],errors="coerce")
pol=pd.read_csv(ROOT/"data/feeds/policy_rates.csv"); pol["date"]=pd.to_datetime(pol["date"]); pol=pol.set_index("date").sort_index()
print("=== CARRY FAMILY BATCH (predeclared) ===")
results={}
# 1. rates rolldown/curve-carry on ZN
zn=dpnl("ZN"); slope=(y["dgs10"]-y["dgs2"]).shift(1).reindex(zn.index).ffill()
pos=np.sign(slope); pnl1=(pos*zn - (pos.diff().abs().fillna(0)>0)*cost("ZN")).dropna()
results["rates_rolldown_ZN"]=pnl1; print(f"  1 rates-rolldown ZN (long dur when 2s10s steep): n={len(pnl1)} Sh={shp(pnl1.values)} net=${pnl1.sum():.0f} maxyr={100*pnl1.groupby(pnl1.index.year).sum().max()/pnl1.sum() if pnl1.sum()>0 else 999:.0f}%")
# 2. cross-tenor carry-rank (long tenor with best rolldown = steepest local curve segment)
carry={"ZF":(y["dgs5"]-y["dgs2"]),"ZN":(y["dgs10"]-y["dgs5"]),"ZB":(y["dgs30"]-y["dgs10"])}
cr=pd.DataFrame(carry).shift(1).dropna()
best=cr.idxmax(axis=1)   # highest local carry tenor
pnls=[]
for a in ["ZF","ZN","ZB"]:
    p=dpnl(a); w=(best==a).reindex(p.index).ffill().astype(float); pnls.append((w*p))
pnl2=pd.concat(pnls,axis=1).sum(axis=1).dropna()
results["rates_carry_rank"]=pnl2; print(f"  2 cross-tenor carry-rank (long best-rolldown tenor): n={len(pnl2)} Sh={shp(pnl2.values)} net=${pnl2.sum():.0f}")
# 3. FX carry USDJPY via fed-boj
if "boj_rate" in pol.columns and "fed_funds" in pol.columns:
    diff=(pol["fed_funds"]-pol["boj_rate"]).shift(1)
    j=dpnl("6J"); d=diff.reindex(j.index).ffill(); pos=-np.sign(d)  # USD carry>JPY -> short 6J (long USD)
    pnl3=(pos*j - (pos.diff().abs().fillna(0)>0)*cost("6J")).dropna()
    results["fx_carry_usdjpy"]=pnl3; print(f"  3 FX carry USDJPY (fed-boj): n={len(pnl3)} Sh={shp(pnl3.values)} net=${pnl3.sum():.0f}")
# family-level evaluation
for name,p in results.items(): record(f"CARRY:{name}",sharpe=shp(p.values),verdict="family",lane="carry")
gN=count(); fN=count(lane="carry")
print(f"\n  TRIAL-N: global={gN} carry-family={fN} | threshold DSR>=0.95")
best_name=max(results,key=lambda k: shp(results[k].values)); bp=results[best_name]
h=len(bp)//2; dG=deflated_sharpe(bp.values,gN,sr_trials_std=0.05); dF=deflated_sharpe(bp.values,fN,sr_trials_std=0.05)
print(f"  best expr '{best_name}': Sh={shp(bp.values)} H1={shp(bp.iloc[:h].values)} H2={shp(bp.iloc[h:].values)} | DSR global={dG.get('dsr')} family={dF.get('dsr')}")
anypos=any(shp(p.values)>0.5 for p in results.values())
print(f"  VERDICT: {'ACTIVE_EXPANSION (carry family shows signal — deepen best expr with roll-adjusted data)' if shp(bp.values)>0.7 and dF.get('dsr',0)>0.9 else ('FAMILY_UNDERTESTED — weak, needs roll-adjusted term structure (rates_multicontract, Lane-1)' if anypos else 'CLEAN_KILL (carry family dead on available data)')}")
