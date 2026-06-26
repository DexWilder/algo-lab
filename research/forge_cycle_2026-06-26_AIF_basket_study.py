"""ALPHA_INTAKE_FACTORY — no-optimizer forced-flow BASKET study (report-only, strict).
Q: do the clean-but-weak decorrelated legs combine into a book that clears DSR-at-N where none does alone?
STRICT: predeclared legs (already-counted), NO weight optimization, equal-RISK (inverse-vol on H1 applied unchanged
to H2), costs at leg level, DSR at full factory N incl basket, kill if one-leg/one-year/hidden-leverage driven.
PREDECLARED baskets: B1={TSMOM,vol-carry,ZN-monthend}; B2=B1+overnight-net. Both counted. No post-hoc leg-dropping.
Verdict: CLEAN_BASKET_CANDIDATE (clears DSR-at-N+cost+concentration+DD) else BASKET_FAIL. No WH language."""
import sys, json, urllib.request
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.asset_config import get_asset
from research.forge_deflated_sharpe import deflated_sharpe
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if len(x)>1 and x.std()>0 else 0
def dclose(a):
    df=pd.read_csv(ROOT/f"data/processed/{a}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
    return df.assign(d=df["datetime"].dt.normalize()).groupby("d")["close"].last()
def yh(s):
    u=f"https://query1.finance.yahoo.com/v8/finance/chart/{s}?range=10y&interval=1d"
    r=json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"}),timeout=20).read()); res=r["chart"]["result"][0]
    return pd.Series(res["indicators"]["quote"][0]["close"],index=pd.to_datetime(res["timestamp"],unit="s").normalize()).dropna().pipe(lambda x:x[~x.index.duplicated()])
# ---- legs (daily $ or return series; costed at leg level) ----
def leg_tsmom():
    parts=[]
    for a in ["MNQ","MES","MGC"]:
        c=dclose(a); pv=get_asset(a)["point_value"]
        parts.append((np.sign(c.pct_change(126)).shift(1)*c.diff()*pv).dropna())
    return pd.concat(parts,axis=1).sum(axis=1).rename("TSMOM")
def leg_volcarry():
    vix,vix3m,svxy=yh("^VIX"),yh("^VIX3M"),yh("SVXY"); v=pd.DataFrame({"vix":vix,"vix3m":vix3m,"svxy":svxy}).dropna()
    sig=(v["vix3m"]/v["vix"]-1).shift(1).gt(0).astype(float)
    flips=sig.diff().abs().fillna(0)>0
    return (sig*v["svxy"].pct_change() - flips*10/1e4).dropna().rename("VolCarry")  # return space, 10bps flip cost
def leg_zn_monthend():
    c=dclose("ZN"); pv=get_asset("ZN")["point_value"]; ret=(c.diff()*pv)
    f=pd.DataFrame({"ret":ret}).dropna(); f["ym"]=f.index.to_period("M"); f["rev"]=f.groupby("ym").cumcount(ascending=False)
    inwin=f["rev"]<3; cost=get_asset("ZN")["commission_per_side"]*2+get_asset("ZN")["slippage_ticks"]*2*get_asset("ZN")["tick_size"]*pv
    s=f["ret"].where(inwin,0.0); s.loc[inwin&(f["rev"]==0)]-=cost
    return s.rename("ZN_ME")
def leg_overnight():
    parts=[]
    for a in ["MES","MNQ","MGC"]:
        df=pd.read_csv(ROOT/f"data/processed/{a}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
        df["d"]=df["datetime"].dt.normalize(); df["t"]=df["datetime"].dt.strftime("%H:%M")
        rth=df[(df["t"]>="09:30")&(df["t"]<="15:55")]; g=rth.groupby("d"); o=g["open"].first(); cl=g["close"].last()
        pv=get_asset(a)["point_value"]; cost=get_asset(a)["commission_per_side"]*2+get_asset(a)["slippage_ticks"]*2*get_asset(a)["tick_size"]*pv
        parts.append(((o-cl.shift(1))*pv - cost).dropna())
    return pd.concat(parts,axis=1).sum(axis=1).rename("Overnight_net")
legs={"TSMOM":leg_tsmom(),"VolCarry":leg_volcarry(),"ZN_ME":leg_zn_monthend(),"Overnight_net":leg_overnight()}
# align on common dates
df=pd.concat(legs.values(),axis=1).dropna()
h=len(df)//2; H1=df.index[:h]; H2=df.index[h:]
print(f"=== BASKET STUDY — common dates n={len(df)} ({df.index[0].date()}..{df.index[-1].date()}) ===")
print("-- leg correlation matrix (full) --"); print(df.corr().round(2).to_string())
# equal-RISK: scale each leg to target daily vol using H1 std (applied unchanged to H2)
TARGET=100.0
scale={c: TARGET/df[c].reindex(H1).std() for c in df.columns}
print("-- equal-risk scales (inverse-vol on H1, applied to H2) --", {k:round(v,4) for k,v in scale.items()})
scaled=pd.DataFrame({c: df[c]*scale[c] for c in df.columns})
def report(cols, name, n_trials):
    b=scaled[cols].sum(axis=1)
    p=b.values; eq=np.cumsum(p); dd=eq-np.maximum.accumulate(eq)
    yr=b.groupby(b.index.year).sum(); maxyr=100*yr.max()/yr.sum() if yr.sum()>0 else 0
    contrib={c: round(float(scaled[c].sum())) for c in cols}
    disp=float(np.std([df[c].reindex(H1).mean()/df[c].reindex(H1).std() for c in cols]))
    dsr=deflated_sharpe(p, n_trials, sr_trials_std=max(disp,0.005))
    print(f"\n  [{name}] legs={cols}")
    print(f"    FULL Sh={shp(p):.2f} net=${p.sum():.0f} maxDD=${dd.min():.0f} MAR={p.sum()/abs(dd.min()):.2f} wd=${b.min():.0f} wk=${b.rolling(5).sum().min():.0f} mo=${b.rolling(21).sum().min():.0f}")
    print(f"    H1 Sh={shp(b.reindex(H1).values):.2f}  H2(OOS) Sh={shp(b.reindex(H2).values):.2f}  max-year={maxyr:.0f}%")
    print(f"    per-year: " + "  ".join(f"{y}:{int(v)}" for y,v in yr.items()))
    print(f"    leg contribution ($, equal-risk): {contrib}")
    print(f"    DSR at N={n_trials}: ann SR={dsr.get('sr_annualized_252')} sr0={dsr.get('sr0_benchmark')} DSR={dsr.get('dsr')} -> {dsr.get('verdict')}")
    return dsr, shp(b.reindex(H2).values), maxyr
print("\n=== PREDECLARED BASKETS (both counted toward trial N) ===")
d1=report(["TSMOM","VolCarry","ZN_ME"], "B1 (3 clean-net legs)", 15)
d2=report(["TSMOM","VolCarry","ZN_ME","Overnight_net"], "B2 (+overnight-net)", 16)
print("\n  VERDICT: CLEAN_BASKET_CANDIDATE only if DSR>=0.95 at full N AND H2>0 AND max-year<40 AND not one-leg-driven; else BASKET_FAIL.")
