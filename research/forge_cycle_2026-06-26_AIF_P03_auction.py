"""ALPHA_INTAKE_FACTORY P03 — Treasury 10y auction concession + post-auction reversal (report-only, free data).
Forced-flow: dealers demand price CONCESSION into the auction (ZN cheapens), then REVERSAL after as supply clears.
Auction dates scheduled in advance -> causality clean by construction. Both directions tested separately, predeclared
windows {into: T-3->T0, T-1->T0; after: T0->T+3, T0->T+1}, cost, per-year, DSR-at-full-N. Verdicts per taxonomy."""
import sys, json, urllib.request
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.asset_config import get_asset
from research.forge_deflated_sharpe import deflated_sharpe
def auctions():
    u="https://www.treasurydirect.gov/TA_WS/securities/auctioned?type=Note&days=3000"
    d=json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"}),timeout=30).read())
    tens=[x for x in d if x.get("securityTerm","").startswith("10-Year") or x.get("originalSecurityTerm","").startswith("10-Year")]
    return sorted(set(pd.to_datetime(x["auctionDate"][:10]) for x in tens))
def zn_daily():
    df=pd.read_csv(ROOT/"data/processed/ZN_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
    return df.assign(d=df["datetime"].dt.normalize()).groupby("d")["close"].last()
pv=get_asset("ZN")["point_value"]; cost=get_asset("ZN")["commission_per_side"]*2+get_asset("ZN")["slippage_ticks"]*2*get_asset("ZN")["tick_size"]*pv
px=zn_daily(); idx=px.index; aucs=auctions()
def nearest_pos(date):
    pos=idx.searchsorted(date)
    return pos if pos<len(idx) else None
print("=== P03 ZN 10y auction concession + reversal ===")
print(f"auctions={len(aucs)} ZN daily from {idx[0].date()}..{idx[-1].date()}; cost/RT=${cost:.0f}")
def leg(into, a, b, predict_sign, label):
    # return $ pnl per auction over window [a,b] trading-days relative to auction day; predict_sign*move - cost
    pnls=[]; dates=[]
    for A in aucs:
        p=nearest_pos(A)
        if p is None or p+max(a,b,0)>=len(idx) or p+min(a,b,0)<0: continue
        c0=px.iloc[p+a]; c1=px.iloc[p+b]
        pnl=predict_sign*(c1-c0)*pv - cost
        pnls.append(pnl); dates.append(idx[p])
    s=pd.Series(pnls,index=pd.DatetimeIndex(dates))
    if len(s)<10: print(f"  {label}: n={len(s)} DATA_LIMITED"); return None
    sr=s.mean()/s.std() if s.std()>0 else 0
    yr=s.groupby(s.index.year).sum(); yrs_pos=(yr>0).mean()
    print(f"  {label}: n={len(s)} mean=${s.mean():.0f} netSh(per-event)={sr:.2f} total=${s.sum():.0f} yrs+={int(yrs_pos*100)}% per-yr={dict((y,int(v)) for y,v in yr.items())}")
    return s
print("-- CONCESSION (predict ZN DOWN into auction -> short, sign=-1) --")
c1=leg(True,-3,0,-1,"into T-3->T0 short"); c2=leg(True,-1,0,-1,"into T-1->T0 short")
print("-- REVERSAL (predict ZN UP after auction -> long, sign=+1) --")
r1=leg(True,0,3,1,"after T0->T+3 long"); r2=leg(True,0,1,1,"after T0->T+1 long")
# DSR on best per-event series at full factory N (~64 COT + 16 + 4 here = ~84)
best=None
for s in [c1,c2,r1,r2]:
    if s is not None and (best is None or s.mean()/ (s.std()+1e-9) > best.mean()/(best.std()+1e-9)): best=s
if best is not None:
    d=deflated_sharpe(best.values, 84, sr_trials_std=0.05)
    print(f"\n  best leg DSR at N~84: per-event SR={d.get('sr_per_period')} DSR={d.get('dsr')} -> {d.get('verdict')}")
print("\n  both-sides read: a real auction edge wants concession (short into) AND reversal (long after) BOTH positive.")
print("  Verdict per taxonomy after reading both sides + DSR. No WH/candidate language.")
