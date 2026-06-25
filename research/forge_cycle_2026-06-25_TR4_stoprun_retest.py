import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
import research.crossbreeding.crossbreeding_engine as ce
from engine.backtest import run_backtest
from engine.asset_config import get_asset
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if len(x)>1 and x.std()>0 else 0
def book(s):
    p=s.values; eq=np.cumsum(p); dd=eq-np.maximum.accumulate(eq)
    return dict(sharpe=shp(p),maxDD=round(float(dd.min())),net=round(float(p.sum())),DLL=int((s<-1100).sum()),days=len(p))
orig=ce.compute_features
def unshift(frame,*a,**k):
    f=dict(orig(frame,*a,**k)); dts=pd.to_datetime(f["dates"]).normalize()
    dd=pd.DataFrame({"d":dts,"c":f["close"]}).groupby("d")["c"].last()
    sl=dd.ewm(span=20,adjust=False).mean().diff()
    sgn={k2:(0 if pd.isna(v) else (1 if v>0 else -1)) for k2,v in sl.items()}
    f["bar_trend"]=np.array([sgn.get(x,0) for x in dts]); return f
a="MNQ"; cfg=get_asset(a); df=pd.read_csv(ROOT/f"data/processed/{a}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
def run():
    sig=ce.generate_crossbred_signals(df,entry_name="stop_run_reversal",exit_name="profit_ladder",filter_name="ema_slope",params={"stop_mult":2.0,"target_mult":4.0,"trail_mult":2.5})
    r=run_backtest(df,sig,mode="both",point_value=cfg["point_value"],tick_size=cfg["tick_size"],commission_per_side=cfg["commission_per_side"],slippage_ticks=cfg["slippage_ticks"])
    t=r["trades_df"];
    if len(t)==0: return pd.Series(dtype=float)
    t=t.copy(); t["day"]=pd.to_datetime(t["entry_time"]).dt.normalize(); return t.groupby("day")["pnl"].sum()
ce._FEATURE_CACHE.clear(); ce.compute_features=orig; clean=run()
ce._FEATURE_CACHE.clear(); ce.compute_features=unshift; contam=run()
ce._FEATURE_CACHE.clear(); ce.compute_features=orig
print("=== stop_run_reversal (Phase 1A paper-prep port) clean vs contaminated, MNQ stop=2.0 ===")
for lab,s in [("CONTAMINATED",contam),("CLEAN(fixed)",clean)]:
    if len(s)==0: print(f"  {lab}: no trades"); continue
    b=book(s); h=len(s)//2
    print(f"  {lab:13s} days={b['days']} Sharpe={b['sharpe']} maxDD={b['maxDD']} DLL={b['DLL']} net={b['net']} H2Sh={shp(s.iloc[h:].values)}")
if len(clean) and len(contam) and contam.sum(): print(f"  -> clean retains {100*clean.sum()/contam.sum():.0f}% of net")
