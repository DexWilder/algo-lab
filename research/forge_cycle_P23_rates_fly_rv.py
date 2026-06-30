"""P23 — 2s5s10s butterfly relative-value (UNUSED feed treasury_yield_curve.csv). RESEARCH-GRADE (FRED yields, not
directly tradeable -> RESEARCH_ONLY even if positive). RV mechanism, NOT a primitive grid. Fade fly z-extremes; does
the fly mean-revert? Causal (lagged signal). Lane=forced_flow/RV. Report-only."""
import sys; from pathlib import Path; import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from research.forge_deflated_sharpe import deflated_sharpe
from research.forge_trial_ledger import record, count
y=pd.read_csv(ROOT/"data/feeds/treasury_yield_curve.csv"); y["date"]=pd.to_datetime(y["date"]); y=y.set_index("date").sort_index()
for c in ["dgs2","dgs5","dgs10"]: y[c]=pd.to_numeric(y[c],errors="coerce")
y=y.dropna(subset=["dgs2","dgs5","dgs10"])
fly=2*y["dgs5"]-y["dgs2"]-y["dgs10"]                       # 2s5s10s butterfly (bps of curvature)
z=((fly-fly.rolling(252,min_periods=60).mean())/fly.rolling(252,min_periods=60).std()).shift(1)  # lagged signal
dfly_fwd=fly.diff(5).shift(-5)                            # forward 5d change in fly
pos=-np.sign(z)                                            # fade extreme curvature
pnl=(pos*dfly_fwd).dropna(); pnl=pnl[z.reindex(pnl.index).abs()>1.5]   # only extremes
print("=== P23 rates 2s5s10s butterfly RV (research-grade) ===")
per=pnl.mean()/pnl.std() if pnl.std()>0 else 0
record("P23_rates_fly_rv",asset="UST",sharpe=round(per*np.sqrt(252),2),verdict="screen",lane="forced_flow")
gN=count(); lN=count(lane="forced_flow"); d=deflated_sharpe(pnl.values,lN,sr_trials_std=0.05)
print(f"  fly-extreme fade: n={len(pnl)} perSh={per:.3f} annSh={per*np.sqrt(252):.2f} (bps curvature units)")
print(f"  DSR global-N={gN} | DSR forced-flow-lane-N={lN}: {d.get('dsr')} -> {d.get('verdict')}")
print(f"  VERDICT: {'CLEAN_KILL' if abs(per)*np.sqrt(252)<0.5 else 'RESEARCH_ONLY flicker (FRED yields not tradeable; needs ZN/ZF/ZT spread expression + costs)'}")
