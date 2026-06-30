"""DATABENTO-NATIVE P17 — opening-drive continuation, volume-conditioned (report-only).
Does the first-30min drive predict rest-of-session direction, and does OPENING VOLUME (informed flow) sharpen it?
Uses VOLUME. Causal (uses only first-6-bar info to predict close). Both dirs. Auto trial-ledger. No WH language."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.asset_config import get_asset
from research.forge_deflated_sharpe import deflated_sharpe
from research.forge_trial_ledger import record, count
def analyze(asset):
    df=pd.read_csv(ROOT/f"data/processed/{asset}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
    df["d"]=df["datetime"].dt.normalize(); df["t"]=df["datetime"].dt.strftime("%H:%M")
    df=df[(df["t"]>="09:30")&(df["t"]<="15:55")].copy()
    pv=get_asset(asset)["point_value"]; cost=get_asset(asset)["commission_per_side"]*2+get_asset(asset)["slippage_ticks"]*2*get_asset(asset)["tick_size"]*pv
    rows=[]
    for d,g in df.groupby("d"):
        if len(g)<20: continue
        op=g.iloc[0]["open"]; c6=g.iloc[5]["close"]; cl=g.iloc[-1]["close"]
        ovol=g.iloc[:6]["volume"].sum()
        rows.append((d,np.sign(c6-op),(cl-c6)*pv,ovol))
    r=pd.DataFrame(rows,columns=["d","odir","fwd","ovol"]).set_index("d")
    r["rvol"]=r["ovol"]/r["ovol"].rolling(60,min_periods=20).median()
    r=r.dropna(); r=r[r["odir"]!=0]
    cont=(r["odir"]*r["fwd"]-cost)                       # go WITH opening drive to close
    hi=r["rvol"]>r["rvol"].quantile(0.7)
    def sh(s): return round(s.mean()/s.std(),3) if len(s)>1 and s.std()>0 else 0
    print(f"  [{asset}] open-drive continuation to close: ALL n={len(cont)} perSh={sh(cont)} mean=${cont.mean():.0f} | HIVOL n={int(hi.sum())} perSh={sh(cont[hi])} mean=${cont[hi].mean():.0f}")
    return cont[hi]
print("=== P17 opening-drive continuation (volume-conditioned) ===")
print("PRE-REGISTERED: opening 30min drive continues to close, sharpened by high opening volume. Both dirs, costed.")
allh=[]
for a in ["MES","MNQ","MGC","MCL"]:
    h=analyze(a); allh.append(h); record("P17_opening_drive", asset=a, sharpe=float(h.mean()/h.std()) if len(h)>1 and h.std()>0 else 0, verdict="screen")
pooled=pd.concat(allh); N=count()
d=deflated_sharpe(pooled.values, N, sr_trials_std=0.05)
print(f"\n  pooled hi-vol open-drive: n={len(pooled)} mean=${pooled.mean():.0f} perSh={pooled.mean()/pooled.std():.3f}")
print(f"  DSR at AUTO N={N}: SR={d.get('sr_per_period')} DSR={d.get('dsr')} -> {d.get('verdict')}")
print("  verdict: CLEAN_KILL unless hi-vol clearly positive + beats all-vol + survives DSR.")
