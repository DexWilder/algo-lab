"""DATABENTO-NATIVE P16 — volume-climax exhaustion reversal (report-only).
Distinct from P14(VWAP-revert) and P15(momentum-confirm): hypothesis = an EXTREME volume spike (RVOL climax) on a
large directional bar marks EXHAUSTION -> short-term reversal. Uses VOLUME. Causal (RVOL trailing, climax at bar i,
forward return after). Both directions. Auto trial-ledger (DSR-at-N). No WH language."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.asset_config import get_asset
from research.forge_deflated_sharpe import deflated_sharpe
from research.forge_trial_ledger import record, count
H=6   # ~30min forward reversal window
def analyze(asset):
    df=pd.read_csv(ROOT/f"data/processed/{asset}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
    df["d"]=df["datetime"].dt.normalize(); df["t"]=df["datetime"].dt.strftime("%H:%M")
    df=df[(df["t"]>="09:30")&(df["t"]<="15:55")].copy()
    pv=get_asset(asset)["point_value"]; cost=get_asset(asset)["commission_per_side"]*2+get_asset(asset)["slippage_ticks"]*2*get_asset(asset)["tick_size"]*pv
    g=df.groupby("d")
    df["rvol"]=df["volume"]/df["volume"].rolling(78,min_periods=20).median()   # vs ~1 session median (causal)
    df["bar"]=(df["close"]-df["open"])                                          # bar direction/size
    df["fwd"]=(g["close"].shift(-H)-df["close"])*pv                             # forward $ (within day via groupby shift)
    df=df.dropna(subset=["rvol","fwd"])
    clim=df[(df["rvol"]>df["rvol"].quantile(0.95)) & (df["bar"]!=0)]            # top-5% volume bars
    bardir=np.sign(clim["bar"])
    rev=(-bardir*clim["fwd"]-cost)                                              # fade the climax bar direction
    up=clim[clim["bar"]>0]; dn=clim[clim["bar"]<0]
    def sh(s): return round(s.mean()/s.std(),3) if len(s)>1 and s.std()>0 else 0
    rev_up=(-1*up["fwd"]-cost); rev_dn=(1*dn["fwd"]-cost)
    print(f"  [{asset}] climax bars n={len(clim)} | fade-up(short after up-climax) n={len(up)} perSh={sh(rev_up)} mean=${rev_up.mean():.1f} | fade-dn(long after dn-climax) n={len(dn)} perSh={sh(rev_dn)} mean=${rev_dn.mean():.1f}")
    return rev
print("=== P16 volume-climax exhaustion reversal (uses VOLUME) ===")
print("PRE-REGISTERED: extreme-RVOL climax bar -> short-term REVERSAL; BOTH sides positive needed. H=6 bars, costed.")
allr=[]
for a in ["MES","MNQ","MGC"]:
    r=analyze(a); allr.append(r); record("P16_volume_climax", asset=a, sharpe=float(r.mean()/r.std()) if r.std()>0 else 0, verdict="pending")
pooled=pd.concat(allr); N=count()
d=deflated_sharpe(pooled.values, N, sr_trials_std=0.05)
print(f"\n  pooled climax-fade: n={len(pooled)} mean=${pooled.mean():.1f} perSh={pooled.mean()/pooled.std():.3f}")
print(f"  DSR at AUTO trial-N={N}: per-trade SR={d.get('sr_per_period')} DSR={d.get('dsr')} -> {d.get('verdict')}")
print("  read: real exhaustion-reversal needs BOTH sides positive + survive DSR. Else CLEAN_KILL.")
