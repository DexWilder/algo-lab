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
def tsmom():
    parts=[dclose(a).pipe(lambda c:(np.sign(c.pct_change(126)).shift(1)*c.diff()*get_asset(a)["point_value"]).dropna()) for a in ["MNQ","MES","MGC"]]
    return pd.concat(parts,axis=1).sum(axis=1)
def volcarry():
    v=pd.DataFrame({"vix":yh("^VIX"),"vix3m":yh("^VIX3M"),"svxy":yh("SVXY")}).dropna()
    sig=(v["vix3m"]/v["vix"]-1).shift(1).gt(0).astype(float); flips=sig.diff().abs().fillna(0)>0
    return (sig*v["svxy"].pct_change()-flips*10/1e4).dropna()
def zn_me():
    c=dclose("ZN"); pv=get_asset("ZN")["point_value"]; f=pd.DataFrame({"ret":(c.diff()*pv)}).dropna()
    f["ym"]=f.index.to_period("M"); f["rev"]=f.groupby("ym").cumcount(ascending=False); inwin=f["rev"]<3
    cost=get_asset("ZN")["commission_per_side"]*2+get_asset("ZN")["slippage_ticks"]*2*get_asset("ZN")["tick_size"]*pv
    s=f["ret"].where(inwin,0.0); s.loc[inwin&(f["rev"]==0)]-=cost; return s
def overnight(slip_mult):
    parts=[]
    for a in ["MES","MNQ","MGC"]:
        df=pd.read_csv(ROOT/f"data/processed/{a}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
        df["d"]=df["datetime"].dt.normalize(); df["t"]=df["datetime"].dt.strftime("%H:%M")
        rth=df[(df["t"]>="09:30")&(df["t"]<="15:55")]; g=rth.groupby("d"); o=g["open"].first(); cl=g["close"].last()
        pv=get_asset(a)["point_value"]; cost=get_asset(a)["commission_per_side"]*2+get_asset(a)["slippage_ticks"]*2*slip_mult*get_asset(a)["tick_size"]*pv
        parts.append(((o-cl.shift(1))*pv-cost).dropna())
    return pd.concat(parts,axis=1).sum(axis=1)
T,V,Z=tsmom(),volcarry(),zn_me()
print("=== B2 hostile stress: overnight slippage realism ===")
for sm in [1,2,3]:
    O=overnight(sm)
    df=pd.concat([T.rename("T"),V.rename("V"),Z.rename("Z"),O.rename("O")],axis=1).dropna()
    h=len(df)//2; H1=df.index[:h]
    sc={c:100.0/df[c].reindex(H1).std() for c in df.columns}
    b=sum(df[c]*sc[c] for c in df.columns)
    disp=float(np.std([df[c].reindex(H1).mean()/df[c].reindex(H1).std() for c in df.columns]))
    dsr=deflated_sharpe(b.values,16,sr_trials_std=max(disp,0.005))
    on_net=float((O.reindex(df.index)*sc["O"]).sum()); tot=float(b.sum())
    print(f"  overnight slip x{sm}: basket Sh={shp(b.values):.2f} net=${tot:.0f} DSR={dsr.get('dsr')} -> {dsr.get('verdict')} | overnight contrib={100*on_net/tot:.0f}%")
