"""DATABENTO-NATIVE P15 — volume-confirmed intraday momentum (report-only).
P14 showed intraday CONTINUES (reversion loses). Q: does VOLUME confirm continuation? i.e. do high-RVOL momentum
moves follow through more than low-RVOL? Uses VOLUME (the underused dimension). Causal: momentum over prior bars,
RVOL trailing, forward return ahead. Both directions. Predeclared RVOL buckets. Cost. DSR-at-N. No WH language."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.asset_config import get_asset
from research.forge_deflated_sharpe import deflated_sharpe
M=12; H=12   # 1h momentum lookback, 1h forward (5m bars)
def analyze(asset):
    df=pd.read_csv(ROOT/f"data/processed/{asset}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
    df["d"]=df["datetime"].dt.normalize(); df["t"]=df["datetime"].dt.strftime("%H:%M")
    df=df[(df["t"]>="09:30")&(df["t"]<="15:55")].copy()
    pv=get_asset(asset)["point_value"]; cost=get_asset(asset)["commission_per_side"]*2+get_asset(asset)["slippage_ticks"]*2*get_asset(asset)["tick_size"]*pv
    g=df.groupby("d")
    df["mom"]=g["close"].transform(lambda s: s-s.shift(M))          # prior 1h move
    df["volwin"]=g["volume"].transform(lambda s: s.rolling(M).sum()) # vol over the move window
    df["volmed"]=df["volwin"].rolling(300,min_periods=60).median()   # trailing baseline (causal)
    df["rvol"]=df["volwin"]/df["volmed"]
    df["fwd"]=(g["close"].shift(-H)-df["close"])*pv                  # next 1h $
    df=df.dropna(subset=["mom","rvol","fwd"])
    df=df[df["mom"]!=0]
    direction=np.sign(df["mom"])
    mompnl=direction*df["fwd"]                                       # go WITH momentum
    hi=df["rvol"]>df["rvol"].quantile(0.70); lo=df["rvol"]<df["rvol"].quantile(0.30)
    def sh(s): return round(s.mean()/s.std(),3) if len(s)>1 and s.std()>0 else 0
    allm=(mompnl-cost); him=(mompnl[hi]-cost); lom=(mompnl[lo]-cost)
    print(f"  [{asset}] momentum follow-through (per-trade $, costed):")
    print(f"     ALL rvol : n={len(allm)} mean=${allm.mean():.1f} perSh={sh(allm)}")
    print(f"     HIGH rvol: n={len(him)} mean=${him.mean():.1f} perSh={sh(him)}  <- volume-confirmed")
    print(f"     LOW rvol : n={len(lom)} mean=${lom.mean():.1f} perSh={sh(lom)}")
    return him, lom
print("=== P15 volume-confirmed intraday momentum (uses VOLUME) ===")
print("PRE-REGISTERED: high-RVOL momentum follows through MORE than low-RVOL (volume confirms). Both dirs, costed.")
his=[]
for a in ["MES","MNQ","MGC"]:
    h,l=analyze(a); his.append(h)
pooled=pd.concat(his)
d=deflated_sharpe(pooled.values, 95, sr_trials_std=0.05)
print(f"\n  pooled HIGH-rvol momentum: n={len(pooled)} mean=${pooled.mean():.1f} perSh={pooled.mean()/pooled.std():.3f}")
print(f"  DSR at N~95: per-trade SR={d.get('sr_per_period')} DSR={d.get('dsr')} -> {d.get('verdict')}")
print("\n  read: volume CONFIRMS momentum only if HIGH-rvol perSh > LOW-rvol AND > 0 net + survives DSR. Else KILL/weak.")
