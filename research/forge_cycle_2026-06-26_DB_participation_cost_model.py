"""DATABENTO-NATIVE — participation-rate COST-MODEL REASSESSMENT (report-only).
Uses per-bar VOLUME to replace the blunt flat-slippage assumption. NOT a rescue tool.
PREDECLARED cost formula (fixed before running, symmetric to winners & losers, conservative):
  per_side_$ = commission_per_side + HALF_SPREAD_TICKS * hs_mult * liquidity_factor * tick_value
  liquidity_factor = clip( median_bar_volume / bar_volume_at_fill , 0.5, 3.0 )   # illiquid fill -> wider spread
  market impact ~ 0 for 1-contract micros (size << minute volume).
  HALF_SPREAD_TICKS = 0.5 (micros ~1 tick wide). Sensitivity bands hs_mult in {1,2,3} (base/2x/3x).
Applied to: P13 overnight (2 trades/day, cost-sensitive) and P04 ZN month-end (low-turnover, should barely move).
Report which verdicts CHANGE vs the old flat-slippage cost. DSR-at-N intact. No tuning to make anything pass."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.asset_config import get_asset
from research.forge_deflated_sharpe import deflated_sharpe
HALF=0.5
def shp(x,a=252): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(a),2) if len(x)>1 and x.std()>0 else 0
def cfg(a): return get_asset(a)
def tickval(a): c=cfg(a); return c["tick_size"]*c["point_value"]
def flat_rt(a): c=cfg(a); return 2*(c["commission_per_side"]+c["slippage_ticks"]*c["tick_size"]*c["point_value"])  # OLD flat round-trip
def part_side(a, bar_vol, med_vol, hs_mult):
    lf=np.clip(med_vol/np.maximum(bar_vol,1),0.5,3.0)
    return cfg(a)["commission_per_side"] + HALF*hs_mult*lf*tickval(a)
# ---------- P13 overnight under participation cost ----------
def overnight(asset):
    df=pd.read_csv(ROOT/f"data/processed/{asset}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
    df["d"]=df["datetime"].dt.normalize(); df["t"]=df["datetime"].dt.strftime("%H:%M")
    rth=df[(df["t"]>="09:30")&(df["t"]<="15:55")]; g=rth.groupby("d")
    o=g["open"].first(); c=g["close"].last(); ov=g["volume"].first(); cv=g["volume"].last()  # open-bar & close-bar volume
    pv=cfg(asset)["point_value"]
    gross=((o-c.shift(1))*pv).dropna()
    med=cv.median()
    res={}
    for hs in [1,2,3]:
        entry=part_side(asset, cv.shift(1).reindex(gross.index), med, hs)  # enter prev close bar
        exitc=part_side(asset, ov.reindex(gross.index), med, hs)           # exit today open bar
        net=(gross - entry - exitc).dropna()
        res[hs]=net
    flat=(gross - flat_rt(asset)).dropna()
    return gross, flat, res
print("=== Participation cost-model reassessment ===")
print(f"PREDECLARED: per_side=comm + {HALF}*hs_mult*clip(med/vol,0.5,3)*tickval ; impact~0 (micros). bands hs=1/2/3.\n")
print("--- P13 OVERNIGHT (2 trades/day — cost-sensitive) ---")
pooled_part={1:[],2:[],3:[]}; pooled_flat=[]
for a in ["MES","MNQ","MGC"]:
    gross,flat,res=overnight(a)
    print(f"  {a}: GROSS Sh={shp(gross.values)} net=${gross.sum():.0f} | FLAT-cost Sh={shp(flat.values)} net=${flat.sum():.0f} | "
          + " ".join(f"PART{hs}x Sh={shp(res[hs].values)} net=${res[hs].sum():.0f}" for hs in [1,2,3]))
    pooled_flat.append(flat); [pooled_part[hs].append(res[hs]) for hs in [1,2,3]]
pf=pd.concat(pooled_flat);
print(f"\n  POOLED overnight: FLAT Sh={shp(pf.values)} DSR={deflated_sharpe(pf.values,97,sr_trials_std=0.05).get('dsr')}")
for hs in [1,2,3]:
    pp=pd.concat(pooled_part[hs]); d=deflated_sharpe(pp.values,97,sr_trials_std=0.05)
    print(f"  POOLED overnight PARTICIPATION x{hs}: Sh={shp(pp.values)} net=${pp.sum():.0f} DSR={d.get('dsr')} -> {d.get('verdict')}")
# ---------- P04 ZN month-end under participation cost (expect ~no change, low turnover) ----------
print("\n--- P04 ZN MONTH-END (low-turnover — expect ~no change) ---")
def zn_me_cost(hs_mult=None):
    a="ZN"; df=pd.read_csv(ROOT/f"data/processed/{a}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
    d=df.assign(dt=df["datetime"].dt.normalize()).groupby("dt").agg(close=("close","last"),vol=("volume","sum"))
    pv=cfg(a)["point_value"]; ret=(d["close"].diff()*pv)
    f=pd.DataFrame({"ret":ret,"vol":d["vol"]}).dropna(); f["ym"]=f.index.to_period("M"); f["rev"]=f.groupby("ym").cumcount(ascending=False)
    inwin=f["rev"]<3; med=f["vol"].median()
    s=f["ret"].where(inwin,0.0)
    if hs_mult is None: rt=flat_rt(a)  # flat
    else: rt=2*part_side(a, f["vol"][inwin&(f["rev"]==0)].mean(), med, hs_mult)  # approx daily-vol liquidity
    s.loc[inwin&(f["rev"]==0)]-=rt
    return s
flatzn=zn_me_cost(None)
print(f"  ZN-ME FLAT Sh={shp(flatzn.values)} net=${flatzn.sum():.0f} | " + " ".join(f"PART{hs}x Sh={shp(zn_me_cost(hs).values)} net=${zn_me_cost(hs).sum():.0f}" for hs in [1,2,3]))
print("\n  VERDICT-CHANGE REPORT: compare FLAT vs PARTICIPATION DSR. A 'rescue' (flat-fail -> part-pass) requires FULL retest")
print("  before any status change, and only counts if conservative (hs>=2) still clears. Do NOT adopt hs=1 optimistic rescues.")
