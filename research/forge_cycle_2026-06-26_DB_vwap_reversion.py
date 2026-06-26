"""DATABENTO-NATIVE factory P14 — VWAP-deviation reversion (report-only, FIRST volume-native test).
We have ignored VOLUME entirely. This uses true volume-weighted session VWAP. Mechanism: intraday price extension
from VWAP reverts (liquidity provision / mean-reversion to fair value). Causality clean (VWAP cumulative to bar i).
Both sides (above->fade short, below->fade long) SEPARATELY. Predeclared z-thresholds + horizons. Cost. DSR-at-N.
Verdict per taxonomy. No WH/validated language."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.asset_config import get_asset
from research.forge_deflated_sharpe import deflated_sharpe
def analyze(asset, k=2.0, H=12):
    df=pd.read_csv(ROOT/f"data/processed/{asset}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
    df["d"]=df["datetime"].dt.normalize(); df["t"]=df["datetime"].dt.strftime("%H:%M")
    df=df[(df["t"]>="09:30")&(df["t"]<="15:55")].copy()   # RTH only (clean VWAP session)
    pv=get_asset(asset)["point_value"]; cost=get_asset(asset)["commission_per_side"]*2+get_asset(asset)["slippage_ticks"]*2*get_asset(asset)["tick_size"]*pv
    df["vol_c"]=df["volume"].clip(lower=1)
    df["tpv"]=((df["high"]+df["low"]+df["close"])/3.0)*df["vol_c"]
    g=df.groupby("d")
    df["cum_tpv"]=g["tpv"].cumsum(); df["cum_v"]=g["vol_c"].cumsum()
    df["vwap"]=df["cum_tpv"]/df["cum_v"]
    df["dev"]=df["close"]-df["vwap"]
    # session-expanding std of dev (causal)
    df["dev_std"]=g["dev"].transform(lambda s: s.expanding(min_periods=10).std())
    df["z"]=df["dev"]/df["dev_std"]
    # forward H-bar return in $ (close_i -> close_{i+H}), within-day via groupby shift
    df["fwd"]=(g["close"].shift(-H)-df["close"])*pv
    df=df.dropna(subset=["z","fwd"])
    above=df[df["z"]>k]; below=df[df["z"]<-k]
    # fade: above -> expect down (edge = -fwd - cost); below -> expect up (edge = +fwd - cost)
    sh_a=(-above["fwd"]-cost); sh_b=(below["fwd"]-cost)
    def m(s): return (len(s), round(s.mean(),1), round((s.mean()/s.std()) if len(s)>1 and s.std()>0 else 0,3))
    na,ma,sa=m(sh_a); nb,mb,sb=m(sh_b)
    print(f"  [{asset} k={k} H={H}bars] ABOVE-fade(short): n={na} mean=${ma} perSh={sa} | BELOW-fade(long): n={nb} mean=${mb} perSh={sb}")
    return sh_a, sh_b
print("=== P14 VWAP-deviation reversion (FIRST volume-native test) ===")
print("PRE-REGISTERED: extension from volume-VWAP reverts; BOTH sides positive needed. k=2.0, H=12 bars (~1h). RTH only.")
allser=[]
for a in ["MES","MNQ","MGC"]:
    sa,sb=analyze(a,2.0,12); allser+=[("ABOVE_"+a,sa),("BELOW_"+a,sb)]
# pooled both-sides (per-trade $), DSR at factory N (~84 prior + 6 here ~90)
pooled=pd.concat([s for _,s in allser])
d=deflated_sharpe(pooled.values, 90, sr_trials_std=0.05)
print(f"\n  pooled both-sides per-trade: n={len(pooled)} mean=${pooled.mean():.1f} perSh={pooled.mean()/pooled.std():.3f}")
print(f"  DSR at N~90: per-trade SR={d.get('sr_per_period')} DSR={d.get('dsr')} -> {d.get('verdict')}")
print("\n  read: a real VWAP-reversion needs BOTH above-fade AND below-fade positive per-asset, surviving cost + DSR.")
print("  (first volume-native test; if it dies, next volume packet: volume-imbalance / RVOL-filter / volume-climax.)")
