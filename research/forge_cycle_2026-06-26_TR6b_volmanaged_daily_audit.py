"""TR6b — vol_managed_equity (MES) BESPOKE daily audit (report-only).
vol_managed is DAILY (signal=1 long MES, weight=vol-target multiplier). The intraday run_backtest and the
position-reindex harness wrapper don't fit -> bespoke. (A) date-aligned future-perturbation causality (perturb
FUTURE 5m bars, regenerate, compare PAST daily signal+weight by DATE). (B) point-in-time PnL (position=shift(1)),
edge metrics + per-year + H1/H2 + concentration. Classify per taxonomy. Capital gate unchanged."""
import sys, importlib.util
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.asset_config import get_asset
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if len(x)>1 and x.std()>0 else 0
spec=importlib.util.spec_from_file_location("vm", ROOT/"strategies/vol_managed_equity/strategy.py")
vm=importlib.util.module_from_spec(spec); spec.loader.exec_module(vm)
cfg=get_asset("MES"); PV=cfg["point_value"]
raw=pd.read_csv(ROOT/"data/processed/MES_5m.csv"); raw["datetime"]=pd.to_datetime(raw["datetime"]); raw["date"]=raw["datetime"].dt.date
def gen(frame):
    for call in (lambda: vm.generate_signals(frame,asset="MES",mode="both"), lambda: vm.generate_signals(frame,"MES"), lambda: vm.generate_signals(frame)):
        try: return call()
        except TypeError: continue
    return vm.generate_signals(frame)
base=gen(raw); base["d"]=pd.to_datetime(base["datetime"]).dt.normalize()
print("=== TR6b vol_managed_equity (MES) bespoke daily audit ===")
# (A) date-aligned future-perturbation causality
n=len(raw); T=int(n*0.6); cutdate=pd.to_datetime(raw["datetime"]).dt.normalize().iloc[T]
hi=raw.copy(); m=hi.index>T
for c in ["open","high","low","close"]: hi.loc[m,c]*=3.0
lo=raw.copy();
for c in ["open","high","low","close"]: lo.loc[m,c]*=0.33
gh=gen(hi); gh["d"]=pd.to_datetime(gh["datetime"]).dt.normalize()
gl=gen(lo); gl["d"]=pd.to_datetime(gl["datetime"]).dt.normalize()
def past(g): return g[g["d"]<=cutdate].set_index("d")[["signal","weight"]].round(6)
ph,pl=past(gh),past(gl); common=ph.index.intersection(pl.index)
diff=int((ph.loc[common]!=pl.loc[common]).any(axis=1).sum())
print(f"-- (A) causality (date-aligned): past daily signal/weight changed by future perturbation = {diff}/{len(common)} -> {'CAUSAL_CLEAN' if diff==0 else 'LOOKAHEAD_DETECTED'}")
# (B) point-in-time PnL: position from PRIOR day
b=base.dropna(subset=["close"]).copy().sort_values("d")
ret_usd=b["close"].diff()*PV
pos=(b["signal"]*b["weight"]).shift(1)           # prior-day position -> point-in-time
flips=pos.diff().abs().fillna(0)
costpf=(cfg["commission_per_side"]*2 + cfg["slippage_ticks"]*2*cfg["tick_size"]*PV)
pnl=(pos*ret_usd - flips*costpf).dropna(); pnl.index=b["d"].iloc[-len(pnl):].values
p=pnl.values; eq=np.cumsum(p); dd=eq-np.maximum.accumulate(eq); h=len(pnl)//2
yr=pnl.groupby(pd.DatetimeIndex(pnl.index).year).sum(); maxyr=100*yr.max()/yr.sum() if yr.sum()>0 else 0
print(f"-- (B) point-in-time edge metrics (costed, vol-scaled position) --")
print(f"  days={len(pnl)} Sharpe={shp(p)} net=${p.sum():.0f} maxDD=${dd.min():.0f} MAR={p.sum()/abs(dd.min()):.2f}")
print(f"  worstday=${pnl.min():.0f} worstwk=${pnl.rolling(5).sum().min():.0f} worstmo=${pnl.rolling(21).sum().min():.0f}")
print(f"  H1 Sharpe={shp(pnl.iloc[:h].values)} H2 Sharpe={shp(pnl.iloc[h:].values)} max-year={maxyr:.0f}%")
print(f"  per-year: " + "  ".join(f"{y}:{int(v)}" for y,v in yr.items()))
# context: vs buy-and-hold MES (is the vol-management actually adding anything, or is it just long beta?)
bh=(ret_usd).reindex(b.index).dropna(); bh.index=b["d"].iloc[-len(bh):].values
print(f"  context: plain long-1-MES Sharpe={shp(bh.values)} net=${bh.sum():.0f} (is vol-mgmt better than just long beta?)")
print(f"\n  NOTE: signal is ALWAYS long (=1) -> this is vol-targeted LONG EQUITY BETA, not a market-neutral edge.")
print(f"  Classify in report: causality + whether it beats long-beta risk-adjusted decides CLEAN_BUT_WEAK vs KILL vs LONG_BETA_ONLY.")
