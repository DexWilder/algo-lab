"""R4 — ORB family point-in-time revalidation (clean vs contaminated), DEPLOYED config (report-only).
On-disk engine is now FIXED (ema_slope shifted 1 day). This re-runs the ORB family at the DEPLOYED
stop_mult=2.0 and compares CLEAN (fixed engine) vs CONTAMINATED (monkeypatched un-shift = old same-day
lookahead) across MNQ/MES/MGC/MCL/MYM. Full metrics: Sharpe/MAR/maxDD/worst d-w-m/DLL/net/trades, H1/H2.
This establishes the TRUE point-in-time ORB baseline. NO promotion — truth repair only. Capital gate unchanged."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
import research.crossbreeding.crossbreeding_engine as ce
from engine.backtest import run_backtest
from engine.asset_config import get_asset
ASSETS=["MNQ","MES","MGC","MCL","MYM"]; STOP=2.0
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if len(x)>1 and x.std()>0 else 0
def book(s):
    p=s.values; eq=np.cumsum(p); dd=eq-np.maximum.accumulate(eq) if len(p) else np.array([0])
    return dict(sharpe=shp(p),MAR=round(p.sum()/abs(dd.min()),2) if dd.min()<0 else None,maxDD=round(float(dd.min())),
                wd=round(float(s.min())) if len(p) else 0,wk=round(float(s.rolling(5).sum().min())) if len(p)>5 else 0,
                mo=round(float(s.rolling(21).sum().min())) if len(p)>21 else 0,DLL=int((s<-1100).sum()),net=round(float(p.sum())),days=len(p))
orig=ce.compute_features
def unshift_cf(frame,*a,**k):   # reproduce PRE-FIX same-day-close lookahead
    f=dict(orig(frame,*a,**k))
    dts=pd.to_datetime(f["dates"]).normalize()
    dd=pd.DataFrame({"d":dts,"c":f["close"]}).groupby("d")["c"].last()
    sl=dd.ewm(span=20,adjust=False).mean().diff()  # NO shift = leak
    sign={k2:(0 if pd.isna(v) else (1 if v>0 else -1)) for k2,v in sl.items()}
    f["bar_trend"]=np.array([sign.get(x,0) for x in dts]); return f
def daily_pnl(asset):
    cfg=get_asset(asset); df=pd.read_csv(ROOT/f"data/processed/{asset}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
    sig=ce.generate_crossbred_signals(df,entry_name="orb_breakout",exit_name="profit_ladder",filter_name="ema_slope",params={"stop_mult":STOP,"target_mult":4.0,"trail_mult":2.5})
    r=run_backtest(df,sig,mode="both",point_value=cfg["point_value"],tick_size=cfg["tick_size"],commission_per_side=cfg["commission_per_side"],slippage_ticks=cfg["slippage_ticks"])
    t=r["trades_df"].copy()
    if len(t)==0: return pd.Series(dtype=float)
    t["day"]=pd.to_datetime(t["entry_time"]).dt.normalize(); return t.groupby("day")["pnl"].sum().sort_index()
print(f"=== R4 ORB family point-in-time revalidation @ deployed stop_mult={STOP} (CLEAN vs CONTAMINATED) ===")
print(f"  {'asset':5s} {'variant':12s} {'days':>5s} {'Sharpe':>6s} {'MAR':>6s} {'maxDD':>7s} {'wd':>6s} {'wk':>7s} {'mo':>7s} {'DLL':>4s} {'net':>8s} {'H2 Sh':>5s}")
for a in ASSETS:
    ce._FEATURE_CACHE.clear(); ce.compute_features=orig;        clean=daily_pnl(a)
    ce._FEATURE_CACHE.clear(); ce.compute_features=unshift_cf;  contam=daily_pnl(a)
    ce._FEATURE_CACHE.clear(); ce.compute_features=orig
    for lab,s in [("CONTAMINATED",contam),("CLEAN(fixed)",clean)]:
        if len(s)==0: print(f"  {a:5s} {lab:12s}  (no trades)"); continue
        b=book(s); h=len(s)//2; h2=shp(s.iloc[h:].values)
        print(f"  {a:5s} {lab:12s} {b['days']:>5} {b['sharpe']:>6.2f} {str(b['MAR']):>6s} {b['maxDD']:>7} {b['wd']:>6} {b['wk']:>7} {b['mo']:>7} {b['DLL']:>4} {b['net']:>8} {h2:>5.2f}")
    print(f"     -> {a} net retained by clean filter: {100*clean.sum()/contam.sum():.0f}%  (clean ${clean.sum():.0f} vs contam ${contam.sum():.0f})" if len(clean) and len(contam) and contam.sum()!=0 else "")
print("\n  NOTE: CONTAMINATED = old same-day lookahead (invalid for decisions). CLEAN = point-in-time fixed engine.")
print("  Deployed strategy ignores target/trail (profit_ladder fixed 1R/2R/3R); stop_mult=2.0 is the live param.")
