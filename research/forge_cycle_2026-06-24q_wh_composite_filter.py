"""Cycle 2026-06-24q — WH composite-filter sweep (engine-routed, report-only).
Does a COMPOSITE filter beat the single ema_slope on the deployed ORB family? Engine entry×filter×exit only,
NOT raw screens. Baseline = orb_breakout|ema_slope|profit_ladder. Require: beats baseline on >=2 assets AND not
a one-off spike. Report-only; no mutation."""
import sys, itertools
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.backtest import run_backtest
from engine.asset_config import get_asset
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals
P={"stop_mult":0.5,"target_mult":4.0,"trail_mult":2.5}; ASSETS=["MNQ","MES","MGC"]
FILTERS={"ema_slope(base)":"ema_slope","ema_slope_vol_high":"ema_slope_vol_high","ema_slope_vol_low":"ema_slope_vol_low",
         "ema_slope+session_morning":["ema_slope","session_morning"],"ema_slope+session_afternoon":["ema_slope","session_afternoon"],
         "ema_slope+bandwidth_squeeze":["ema_slope","bandwidth_squeeze"]}
_c={}
def load(a):
    if a not in _c: d=pd.read_csv(ROOT/f"data/processed/{a}_5m.csv"); d["datetime"]=pd.to_datetime(d["datetime"]); _c[a]=d
    return _c[a]
def _pf(s): s=np.asarray(s,float); l=-s[s<0].sum(); return round(s[s>0].sum()/l,3) if l>0 else 9.9
def one(a,filt):
    cfg=get_asset(a); df=load(a)
    sig=generate_crossbred_signals(df,entry_name="orb_breakout",exit_name="profit_ladder",filter_name=filt,params=P)
    r=run_backtest(df,sig,mode="both",point_value=cfg["point_value"],tick_size=cfg["tick_size"],commission_per_side=cfg["commission_per_side"],slippage_ticks=cfg["slippage_ticks"])
    t=r["trades_df"]
    if t is None or len(t)<50: return None
    p=t["pnl"].to_numpy(); t2=t.copy(); t2["entry_time"]=pd.to_datetime(t2["entry_time"]); yr=t2.assign(y=t2["entry_time"].dt.year).groupby("y")["pnl"].sum()
    return {"pf":round(_pf(p),3),"n":len(p),"median":round(float(np.median(p)),1),"net":round(float(p.sum())),"yrs":f"{int((yr>0).sum())}/{yr.shape[0]}"}
print(f"{'filter':30s} "+" ".join(f"{a:>16s}" for a in ASSETS))
base={}
res={}
for fn,fv in FILTERS.items():
    row=[]; res[fn]={}
    for a in ASSETS:
        try: m=one(a,fv)
        except Exception as e: m=None
        res[fn][a]=m
        if fn=="ema_slope(base)": base[a]=m
        row.append(f"PF{m['pf']}/n{m['n']}" if m else "n/a")
    print(f"{fn:30s} "+" ".join(f"{r:>16s}" for r in row))
print("\n=== composites that BEAT ema_slope baseline on >=2 assets (PF) ===")
beat_any=False
for fn,fv in FILTERS.items():
    if fn=="ema_slope(base)": continue
    nbeat=sum(1 for a in ASSETS if res[fn][a] and base.get(a) and res[fn][a]["pf"]>base[a]["pf"])
    detail=" ".join(f"{a}:{res[fn][a]['pf'] if res[fn][a] else 'na'}vs{base[a]['pf'] if base.get(a) else 'na'}" for a in ASSETS)
    flag=" <-- beats base on >=2" if nbeat>=2 else ""
    if nbeat>=2: beat_any=True
    print(f"  {fn}: beats base on {nbeat}/3 | {detail}{flag}")
print(f"\nVERDICT: {'composite filter(s) beat baseline cross-asset -> investigate (decorrelation/robustness)' if beat_any else 'NO composite beats single ema_slope cross-asset -> ema_slope baseline CONFIRMED best; composite filters do not improve ORB'}")
