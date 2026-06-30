"""P21 — cross-asset VOLUME CONFIRMATION (not direction): when MES+MNQ agree on a high-RVOL directional bar, does the
move continue next H bars? Volume-as-confirmation lane (Databento). Causal, costed, DSR at lane-N + global. Report-only."""
import sys; from pathlib import Path; import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.asset_config import get_asset
from research.forge_deflated_sharpe import deflated_sharpe
from research.forge_trial_ledger import record, count
def load(a):
    df=pd.read_csv(ROOT/f"data/processed/{a}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
    df["t"]=df["datetime"].dt.strftime("%H:%M"); df=df[(df["t"]>="09:30")&(df["t"]<="15:55")].copy()
    df["rvol"]=df["volume"]/df["volume"].rolling(78,min_periods=20).median()
    df["dir"]=np.sign(df["close"]-df["open"]); return df.set_index("datetime")
H=6; print("=== P21 cross-asset volume confirmation (MES+MNQ agree, high RVOL -> continue?) ===")
mes=load("MES"); mnq=load("MNQ"); pv=get_asset("MNQ")["point_value"]
cost=get_asset("MNQ")["commission_per_side"]*2+get_asset("MNQ")["slippage_ticks"]*2*get_asset("MNQ")["tick_size"]*pv
idx=mes.index.intersection(mnq.index)
both=pd.DataFrame({"mdir":mes["dir"].reindex(idx),"mrv":mes["rvol"].reindex(idx),"ndir":mnq["dir"].reindex(idx),
                   "nrv":mnq["rvol"].reindex(idx),"nclose":mnq["close"].reindex(idx)}).dropna()
both["fwd"]=(both["nclose"].shift(-H)-both["nclose"])*pv
agree=(both["mdir"]==both["ndir"])&(both["mrv"]>1.5)&(both["nrv"]>1.5)
sig=both[agree].dropna(subset=["fwd"])
pnl=(sig["ndir"]*sig["fwd"]-cost)
per=pnl.mean()/pnl.std() if pnl.std()>0 else 0
record("P21_cross_asset_volume",asset="MNQ",sharpe=round(per*np.sqrt(252),2),verdict="screen",lane="databento_volume")
gN=count(); lN=count(lane="databento_volume")
dG=deflated_sharpe(pnl.values,gN,sr_trials_std=0.05); dL=deflated_sharpe(pnl.values,lN,sr_trials_std=0.05)
print(f"  n={len(pnl)} perSh={per:.3f} annSh={per*np.sqrt(252):.2f} mean=${pnl.mean():.0f}")
print(f"  DSR global-N={gN}: {dG.get('dsr')} | DSR lane-N(volume)={lN}: {dL.get('dsr')} -> {dL.get('verdict')}")
print("VERDICT: CLEAN_KILL" if per*np.sqrt(252)<0.5 else "VERDICT: review")
