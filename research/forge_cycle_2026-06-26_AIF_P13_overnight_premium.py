"""ALPHA_INTAKE_FACTORY P13 — overnight vs intraday (RTH) return premium (report-only).
Documented structural anomaly: equity-index returns accrue OVERNIGHT (close->open), not during RTH (open->close).
Plausible flow: risk-transfer/settlement/hedging concentrated outside RTH. T1-ish structural.
PRE-REGISTERED prediction: overnight cumulative >> intraday; long-overnight (enter RTH close, exit next RTH open)
positive AND beats long-intraday. Causality clean BY CONSTRUCTION (overnight uses prior close + today open, both
known at the RTH-close entry). Cost matters (2 trades/day). Counts toward trial N. No WH/validated language."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.asset_config import get_asset
from research.forge_deflated_sharpe import deflated_sharpe
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if len(x)>1 and x.std()>0 else 0
def rth_open_close(asset):
    df=pd.read_csv(ROOT/f"data/processed/{asset}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
    df["d"]=df["datetime"].dt.normalize(); df["t"]=df["datetime"].dt.strftime("%H:%M")
    rth=df[(df["t"]>="09:30")&(df["t"]<="15:55")]
    g=rth.groupby("d"); o=g["open"].first(); c=g["close"].last()
    return pd.DataFrame({"open":o,"close":c}).dropna()
def analyze(asset):
    pv=get_asset(asset)["point_value"]; oc=rth_open_close(asset)
    intraday=(oc["close"]-oc["open"])*pv                 # RTH open->close
    overnight=(oc["open"]-oc["close"].shift(1))*pv       # prior RTH close -> today RTH open
    df=pd.DataFrame({"intra":intraday,"overnight":overnight}).dropna()
    cost=get_asset(asset)["commission_per_side"]*2 + get_asset(asset)["slippage_ticks"]*2*get_asset(asset)["tick_size"]*pv
    on_net=df["overnight"]-cost                          # long overnight, round-trip cost each day
    print(f"  [{asset}] n={len(df)}")
    print(f"     overnight: Sh={shp(df['overnight'].values):>5.2f} net=${df['overnight'].sum():>8.0f} mean=${df['overnight'].mean():.2f}")
    print(f"     intraday : Sh={shp(df['intra'].values):>5.2f} net=${df['intra'].sum():>8.0f} mean=${df['intra'].mean():.2f}")
    print(f"     overnight NET of cost (2 trades/day): Sh={shp(on_net.values):>5.2f} net=${on_net.sum():>8.0f} mean=${on_net.mean():.2f}")
    yr=df["overnight"].groupby(df.index.year).sum()
    print(f"     overnight per-year (gross): " + "  ".join(f"{y}:{int(v)}" for y,v in yr.items()))
    return df["overnight"], on_net, df["intra"]
print("=== P13 overnight vs intraday return premium ===")
print("PRE-REGISTERED: overnight >> intraday; long-overnight positive & beats intraday; cost is the killer (2 trades/day).")
res={}
for a in ["MES","MNQ","MGC"]:
    g,n,intr=analyze(a); res[a]=(g,n,intr)
# DSR on the strongest GROSS overnight (MES typical), at trial N (factory running ~10 + these 3 = 13)
best=max(res, key=lambda a: res[a][0].sum())
g,n_net,_=res[best]
N=13
dsr_gross=deflated_sharpe(g.values, N, sr_trials_std=0.02)
dsr_net=deflated_sharpe(n_net.values, N, sr_trials_std=0.02)
print(f"\n-- DSR at factory N={N} (best gross={best}) --")
print(f"  GROSS overnight: ann SR={dsr_gross.get('sr_annualized_252')} DSR={dsr_gross.get('dsr')} -> {dsr_gross.get('verdict')}")
print(f"  NET overnight (after 2 trades/day cost): ann SR={dsr_net.get('sr_annualized_252')} DSR={dsr_net.get('dsr')} -> {dsr_net.get('verdict')}")
print("\n  VERDICT: structural effect real if overnight>>intraday GROSS; tradeability depends on NET surviving cost.")
print("  Note: overnight capture needs close+open execution (slippage at open is worse than modeled) -> NET is optimistic.")
