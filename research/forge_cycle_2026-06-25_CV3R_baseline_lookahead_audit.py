"""AUDIT — does the ORB ema_slope filter carry a same-day-close lookahead, and does it inflate the baseline?
The filter uses date_trend[d]=sign(EMA20 slope on day d's CLOSE) for intraday bars on day d -> embeds
the session close an intraday entry can't know. Sign flips same-day-vs-prior-day on 12.2% of MNQ days.
CONSERVATIVE bound: of the EXISTING ORB trades (all permitted by same-day sign==side), how much net PnL
came from trades where the HONEST prior-day trend sign != side (i.e. only the same-day leak let them in)?
The 'honest-subset' (drop leaky trades) is a LOWER bound on a true lagged-filter ORB (can't recover trades
the lagged filter would newly ALLOW). Report-only; capital gate unchanged; NO engine mutation."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.backtest import run_backtest
from engine.asset_config import get_asset
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if x.std()>0 else 0
def book(s):
    p=s.values; eq=np.cumsum(p); dd=eq-np.maximum.accumulate(eq)
    return dict(sharpe=shp(p),maxDD=round(float(dd.min())),DLL=int((s<-1100).sum()),net=round(float(p.sum())),wd=round(float(s.min())))
cfg=get_asset("MNQ"); df=pd.read_csv(ROOT/"data/processed/MNQ_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
sig=generate_crossbred_signals(df,entry_name="orb_breakout",exit_name="profit_ladder",filter_name="ema_slope",params={"stop_mult":0.5,"target_mult":4.0,"trail_mult":2.5})
r=run_backtest(df,sig,mode="both",point_value=cfg["point_value"],tick_size=cfg["tick_size"],commission_per_side=cfg["commission_per_side"],slippage_ticks=cfg["slippage_ticks"])
t=r["trades_df"].copy(); t["day"]=pd.to_datetime(t["entry_time"]).dt.normalize()
dclose=df.assign(d=df["datetime"].dt.normalize()).groupby("d")["close"].last()
slope=dclose.ewm(span=20,adjust=False).mean().diff()
sign_same=np.sign(slope); sign_lag=np.sign(slope.shift(1))
t["side_sign"]=t["side"].map({"long":1,"short":-1})
t["s_same"]=t["day"].map(sign_same); t["s_lag"]=t["day"].map(sign_lag)
t=t.dropna(subset=["s_lag"]).copy()
# sanity: every trade should have s_same==side_sign (same-day filter). report any exceptions.
mismatch_same=int((t["s_same"]!=t["side_sign"]).sum())
t["honest"]=(t["s_lag"]==t["side_sign"])   # prior-day trend agrees with trade side
clean=t[t["honest"]]; leaky=t[~t["honest"]]
print("=== ORB ema_slope same-day-close lookahead audit (MNQ) ===")
print(f"  trades={len(t)} | same-day-filter sanity mismatches (s_same!=side)={mismatch_same} (expect ~0)")
print(f"  HONEST (prior-day trend == side): {len(clean)} trades ({100*len(clean)/len(t):.0f}%), net=${clean['pnl'].sum():.0f}")
print(f"  LEAKY  (only same-day let them in): {len(leaky)} trades ({100*len(leaky)/len(t):.0f}%), net=${leaky['pnl'].sum():.0f}")
print(f"  -> leaky share of total net PnL: {100*leaky['pnl'].sum()/t['pnl'].sum():.1f}%")
full=t.groupby("day")["pnl"].sum(); cleanb=clean.groupby("day")["pnl"].sum().reindex(full.index).fillna(0)
print(f"\n  {'book':18s} {'Sharpe':>6s} {'maxDD':>7s} {'DLL':>4s} {'net':>8s} {'worstday':>8s}")
for name,s in [("FULL ORB (as-is)",full),("HONEST-subset (lower bound)",cleanb)]:
    b=book(s); print(f"  {name:18s} {b['sharpe']:>6.2f} {b['maxDD']:>7} {b['DLL']:>4} {b['net']:>8} {b['wd']:>8}")
# per-year leaky share
print("\n  per-year leaky net share:")
for y in sorted(set(t['day'].dt.year)):
    ty=t[t['day'].dt.year==y]; ly=ty[~ty['honest']]
    tot=ty['pnl'].sum(); print(f"    {y}: total ${tot:>7.0f} | leaky ${ly['pnl'].sum():>7.0f} ({100*ly['pnl'].sum()/tot if tot else 0:>5.1f}%)")
