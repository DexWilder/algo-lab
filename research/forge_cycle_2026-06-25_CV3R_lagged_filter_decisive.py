"""DECISIVE — true no-lookahead ORB via lagged ema_slope filter (report-only, NO on-disk engine change).
The ema_slope filter uses date_trend[d]=sign(EMA20 slope on day d's session CLOSE) for intraday bars on
day d -> same-day-close lookahead. Conservative audit: 17% of trades 'leaky', 60% of net PnL.
This runs the REAL counterfactual: monkeypatch compute_features (IN THIS PROCESS ONLY) so bar_trend
becomes the PRIOR-trading-day sign (known before the session opens). That both ADDS trades a lagged
filter newly permits AND removes leaky ones -> the true no-lookahead ORB. Compare to as-is baseline.
The on-disk engine file is NOT modified; tonight's scheduled 19:00 loop is unaffected. Capital gate unchanged."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
import research.crossbreeding.crossbreeding_engine as ce
from engine.backtest import run_backtest
from engine.asset_config import get_asset
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if x.std()>0 else 0
def book(s):
    p=s.values; eq=np.cumsum(p); dd=eq-np.maximum.accumulate(eq)
    return dict(sharpe=shp(p),MAR=round(p.sum()/abs(dd.min()),2) if dd.min()<0 else None,maxDD=round(float(dd.min())),DLL=int((s<-1100).sum()),net=round(float(p.sum())),wd=round(float(s.min())),trades=len(p))
cfg=get_asset("MNQ"); df=pd.read_csv(ROOT/"data/processed/MNQ_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
PARAMS=dict(entry_name="orb_breakout",exit_name="profit_ladder",filter_name="ema_slope",params={"stop_mult":0.5,"target_mult":4.0,"trail_mult":2.5})
def run():
    sig=ce.generate_crossbred_signals(df,**PARAMS)
    r=run_backtest(df,sig,mode="both",point_value=cfg["point_value"],tick_size=cfg["tick_size"],commission_per_side=cfg["commission_per_side"],slippage_ticks=cfg["slippage_ticks"])
    t=r["trades_df"].copy(); t["day"]=pd.to_datetime(t["entry_time"]).dt.normalize()
    return t.groupby("day")["pnl"].sum(), len(t)
# 1) as-is baseline (same-day lookahead filter)
base,nb=run()
# 2) monkeypatch compute_features -> bar_trend := prior-trading-day sign (no lookahead)
orig=ce.compute_features
def patched(dfin,*a,**k):
    f=dict(orig(dfin,*a,**k))
    dates=pd.to_datetime(f["dates"]).normalize(); bt=np.asarray(f["bar_trend"])
    d2s={}
    for d,s in zip(dates,bt): d2s[d]=s           # same-day sign per date
    od=sorted(d2s); lag={od[i]:d2s[od[i-1]] for i in range(1,len(od))}; lag[od[0]]=0
    f["bar_trend"]=np.array([lag.get(d,0) for d in dates])
    return f
ce.compute_features=patched
lagged,nl=run()
ce.compute_features=orig  # restore
idx=base.index.union(lagged.index); base=base.reindex(idx).fillna(0); lagged=lagged.reindex(idx).fillna(0)
print("=== DECISIVE: true no-lookahead ORB (lagged ema_slope) vs as-is baseline (MNQ) ===")
print(f"  {'book':34s} {'trades':>6s} {'Sharpe':>6s} {'MAR':>6s} {'maxDD':>7s} {'DLL':>4s} {'net':>8s} {'worstday':>8s}")
h=len(idx)//2
for name,s in [("AS-IS baseline (same-day filter)",base),("LAGGED filter (no-lookahead)",lagged)]:
    b=book(s); print(f"  {name:34s} {b['trades']:>6} {b['sharpe']:>6.2f} {str(b['MAR']):>6s} {b['maxDD']:>7} {b['DLL']:>4} {b['net']:>8} {b['wd']:>8}")
    bh=book(s.iloc[h:]); print(f"     {'  -> H2 (OOS half)':32s} {bh['trades']:>6} {bh['sharpe']:>6.2f} {str(bh['MAR']):>6s} {bh['maxDD']:>7} {bh['DLL']:>4} {bh['net']:>8} {bh['wd']:>8}")
print(f"\n  net retained by no-lookahead filter: {100*lagged.sum()/base.sum():.0f}% (${lagged.sum():.0f} of ${base.sum():.0f})")
print(f"  Sharpe: {shp(base.values)} -> {shp(lagged.values)}")
print("\n  Per-year net & Sharpe (as-is -> lagged):")
for y in sorted(set(idx.year)):
    a=base[base.index.year==y]; l=lagged[lagged.index.year==y]
    print(f"    {y}: net {a.sum():>7.0f} -> {l.sum():>7.0f} | Sharpe {shp(a.values):>5.2f} -> {shp(l.values):>5.2f}")
