"""P18 — intraday volume-imbalance / order-flow proxy (report-only). Morning OFI predicts afternoon? Uses VOLUME, causal."""
import sys; from pathlib import Path; import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.asset_config import get_asset
from research.forge_deflated_sharpe import deflated_sharpe
from research.forge_trial_ledger import record, count
print("=== P18 volume-imbalance (morning OFI -> afternoon) ===")
allp=[]
for a in ["MES","MNQ","MGC","MCL"]:
    df=pd.read_csv(ROOT/f"data/processed/{a}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
    df["d"]=df["datetime"].dt.normalize(); df["t"]=df["datetime"].dt.strftime("%H:%M")
    df=df[(df["t"]>="09:30")&(df["t"]<="15:55")]; pv=get_asset(a)["point_value"]
    cost=get_asset(a)["commission_per_side"]*2+get_asset(a)["slippage_ticks"]*2*get_asset(a)["tick_size"]*pv
    rows=[]
    for d,g in df.groupby("d"):
        am=g[g["t"]<"12:30"]; pm=g[g["t"]>="12:30"]
        if len(am)<6 or len(pm)<6: continue
        ofi=(np.sign(am["close"]-am["open"])*am["volume"]).sum()
        rows.append((np.sign(ofi),(pm["close"].iloc[-1]-pm["close"].iloc[0])*pv))
    r=pd.DataFrame(rows,columns=["ofi","fwd"]); r=r[r["ofi"]!=0]
    pnl=(r["ofi"]*r["fwd"]-cost); sh=round(pnl.mean()/pnl.std(),3) if pnl.std()>0 else 0
    print(f"  [{a}] n={len(pnl)} perSh={sh} mean=${pnl.mean():.0f}"); allp.append(pnl)
    record("P18_volume_imbalance",asset=a,sharpe=sh,verdict="screen")
pooled=pd.concat(allp); N=count(); d=deflated_sharpe(pooled.values,N,sr_trials_std=0.05)
print(f"  pooled n={len(pooled)} perSh={pooled.mean()/pooled.std():.3f} DSR@N={N}={d.get('dsr')} -> {d.get('verdict')}")
print("VERDICT: CLEAN_KILL" if pooled.mean()/pooled.std()<0.03 else "VERDICT: review")
