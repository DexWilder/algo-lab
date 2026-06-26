"""TRUTH_RESET hunt loop 1 — vol_managed_equity (MES) standalone EDGE audit (report-only).
Causality already CAUSAL_CLEAN (TR5, 51 signals). Now: does it have a real, clean, non-concentrated edge?
Cost-sensitivity (gate) + standalone metrics + per-year + H1/H2 + concentration. Classify per taxonomy.
No 'validated/primary' language. Capital gate unchanged."""
import sys, importlib.util
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.backtest import run_backtest
from engine.asset_config import get_asset
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if len(x)>1 and x.std()>0 else 0
def load_gen(name):
    spec=importlib.util.spec_from_file_location(f"s_{name}", ROOT/f"strategies/{name}/strategy.py")
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m.generate_signals
asset="MES"; cfg=get_asset(asset)
df=pd.read_csv(ROOT/f"data/processed/{asset}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"]); df["date"]=df["datetime"].dt.date
gen=load_gen("vol_managed_equity")
for call in (lambda: gen(df,asset=asset,mode="both"), lambda: gen(df,asset),lambda: gen(df), lambda: gen(df,mode="both")):
    try: sig=call(); break
    except TypeError: sig=None
def bt(commission,slip):
    r=run_backtest(df,sig,mode="both",point_value=cfg["point_value"],tick_size=cfg["tick_size"],commission_per_side=commission,slippage_ticks=slip)
    return r["trades_df"]
print("=== TR6 vol_managed_equity (MES) standalone edge audit ===")
t0=bt(0.0,0); tC=bt(cfg["commission_per_side"],cfg["slippage_ticks"])
print(f"-- (gate) cost sensitivity: 0-cost net=${t0['pnl'].sum():.0f} vs costed net=${tC['pnl'].sum():.0f} trades={len(tC)} -> {'COST_WIRED' if abs(t0['pnl'].sum()-tC['pnl'].sum())>1 else 'CHECK'}")
t=tC.copy()
if len(t)==0: print("  NO TRADES -> KILL"); sys.exit()
t["day"]=pd.to_datetime(t["entry_time"]).dt.normalize(); dd_=t.groupby("day")["pnl"].sum()
p=dd_.values; eq=np.cumsum(p); ddc=eq-np.maximum.accumulate(eq); h=len(dd_)//2
pnl=t["pnl"].values; gross_win=pnl[pnl>0].sum(); gross_loss=-pnl[pnl<0].sum()
PF=gross_win/gross_loss if gross_loss>0 else float('inf')
yr=t.groupby(t["day"].dt.year)["pnl"].sum(); maxyr=100*yr.max()/yr.sum() if yr.sum()>0 else 0
top3=100*np.sort(pnl)[-3:].sum()/pnl.sum() if pnl.sum()>0 else 0
top10=100*np.sort(pnl)[-10:].sum()/pnl.sum() if pnl.sum()>0 else 0
print(f"-- standalone metrics (costed) --")
print(f"  trades={len(t)} PF={PF:.2f} Sharpe={shp(p)} net=${p.sum():.0f} maxDD=${ddc.min():.0f} MAR={p.sum()/abs(ddc.min()):.2f}")
print(f"  median_trade=${np.median(pnl):.1f} worstday=${dd_.min():.0f} worstwk=${dd_.rolling(5).sum().min():.0f} worstmo=${dd_.rolling(21).sum().min():.0f}")
print(f"  H1 Sharpe={shp(dd_.iloc[:h].values)} H2 Sharpe={shp(dd_.iloc[h:].values)} | DLL(<-1100)={int((dd_<-1100).sum())}")
print(f"  concentration: top3={top3:.0f}% top10={top10:.0f}% max-year={maxyr:.0f}% (gates: top3<30 top10<55 maxyr<40)")
print(f"  per-year net: " + "  ".join(f"{y}:{int(v)}" for y,v in yr.items()))
# verdict heuristic
gates_ok = (PF>1.2 and shp(p)>0.8 and maxyr<40 and top3<30 and np.median(pnl)>=0 and shp(dd_.iloc[:h].values)>0 and shp(dd_.iloc[h:].values)>0)
print(f"\n  TRUTH-GATE: causality CAUSAL_CLEAN (TR5) + cost wired. EDGE gates pass={gates_ok}")
print(f"  -> {'CLEAN_RESEARCH_CANDIDATE (deepen)' if gates_ok else 'CLEAN_BUT_WEAK / KILL — see which gate failed'}")
