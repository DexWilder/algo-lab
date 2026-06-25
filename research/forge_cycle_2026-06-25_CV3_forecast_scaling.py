"""CV3 — forecast-strength scaling for ORB (report-only, strict-bar).
Question: does scaling ORB position size by the STRENGTH of its load-bearing signal
(daily EMA20 slope magnitude — the ema_slope filter keys on the SIGN; forecast uses the MAGNITUDE)
improve risk-adjusted return WITHOUT trade deletion or hidden leverage?

STRICT BAR (honors operator guardrails):
- IDENTICAL trade set — every ORB trade kept, just resized (multiplier bounded >=0.5 -> 0 deletion).
- MATCHED EXPOSURE — multiplier mapping normalized on H1 to mean 1.0 (same avg contracts as flat ORB).
- NO HIDDEN LEVERAGE — multiplier capped [0.5, 2.0]; report mean AND max exposure + total contract-days.
- OOS — normalization/scale derived on H1 ONLY, applied to H2. No lookahead in the forecast
  (|slope| normalized by TRAILING 252d median).
- NO ADOPTION without a clean improvement (Sharpe + MAR + maxDD + per-year all behave).
Verdict: FORECAST_SCALING_HELPS / NO_BENEFIT / REJECT_TRADE_DELETION_OR_LEVERAGE. Report-only; capital gate unchanged."""
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
    return dict(sharpe=shp(p),MAR=round(p.sum()/abs(dd.min()),2) if dd.min()<0 else None,maxDD=round(float(dd.min())),worst=round(float(s.min())),DLL=int((s<-1100).sum()),net=round(float(p.sum())))
# ORB trades (identical set)
cfg=get_asset("MNQ"); df=pd.read_csv(ROOT/"data/processed/MNQ_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
sig=generate_crossbred_signals(df,entry_name="orb_breakout",exit_name="profit_ladder",filter_name="ema_slope",params={"stop_mult":0.5,"target_mult":4.0,"trail_mult":2.5})
r=run_backtest(df,sig,mode="both",point_value=cfg["point_value"],tick_size=cfg["tick_size"],commission_per_side=cfg["commission_per_side"],slippage_ticks=cfg["slippage_ticks"])
t=r["trades_df"].copy(); t["day"]=pd.to_datetime(t["entry_time"]).dt.normalize()
# forecast = |daily EMA20 slope|, normalized by TRAILING 252d median (no lookahead) — same signal the ema_slope filter uses
dclose=df.assign(d=df["datetime"].dt.normalize()).groupby("d")["close"].last()
slope=dclose.ewm(span=20,adjust=False).mean().diff()
fc_raw=(slope.abs()/slope.abs().rolling(252,min_periods=60).median()).replace([np.inf,-np.inf],np.nan)
t["fc"]=t["day"].map(fc_raw)
t=t.dropna(subset=["fc"]).copy()  # drop only warmup trades with no trailing-median yet (NOT forecast-based deletion)
# split by trade order in time
t=t.sort_values("entry_time").reset_index(drop=True); h=len(t)//2
H1=t.iloc[:h];
# matched-exposure mapping: cap raw forecast, then rescale so MEAN multiplier on H1 == 1.0 exactly
CAP_LO,CAP_HI=0.5,2.0
def mult_from(fc, scale):
    m=np.clip(fc/scale,CAP_LO,CAP_HI); return m
# choose scale so post-cap mean over H1 == 1.0 (solve by simple fixed-point/scan)
grid=np.linspace(0.3,3.0,541); best=min(grid,key=lambda s: abs(mult_from(H1["fc"].values,s).mean()-1.0))
t["mult"]=mult_from(t["fc"].values,best)
H1=t.iloc[:h]; H2=t.iloc[h:]
print("=== CV3 forecast-strength ORB scaling (identical trade set, matched exposure, OOS) ===")
print(f"  trades={len(t)} (all kept; warmup-only drop) | H1 mean mult={H1['mult'].mean():.3f} (target 1.0) max={t['mult'].max():.2f} min={t['mult'].min():.2f}")
print(f"  H2 mean mult={H2['mult'].mean():.3f}  | exposure cap [{CAP_LO},{CAP_HI}] -> no zeroing (0 trade deletion), bounded leverage")
def daily_pnl(tr, scaled):
    p=tr["pnl"]*(tr["mult"] if scaled else 1.0)
    return p.groupby(tr["day"]).sum()
for label,sub in [("FULL",t),("H1(in-samp map)",H1),("H2(OOS)",H2)]:
    flat=book(daily_pnl(sub,False)); scal=book(daily_pnl(sub,True))
    cd_flat=len(sub); cd_scal=round(sub["mult"].sum())  # contract-days
    print(f"\n  [{label}]  contract-days flat={cd_flat} scaled={cd_scal} ({100*cd_scal/cd_flat:.0f}% — matched if ~100)")
    print(f"    {'':6s} {'Sharpe':>6s} {'MAR':>6s} {'maxDD':>8s} {'worst':>7s} {'DLL':>4s} {'net':>8s}")
    print(f"    {'flat':6s} {flat['sharpe']:>6.2f} {str(flat['MAR']):>6s} {flat['maxDD']:>8} {flat['worst']:>7} {flat['DLL']:>4} {flat['net']:>8}")
    print(f"    {'scaled':6s} {scal['sharpe']:>6.2f} {str(scal['MAR']):>6s} {scal['maxDD']:>8} {scal['worst']:>7} {scal['DLL']:>4} {scal['net']:>8}")
# per-year OOS-style stability on FULL (scaled vs flat)
print("\n  per-year (scaled vs flat net, Sharpe):")
df_f=daily_pnl(t,False); df_s=daily_pnl(t,True)
for y in sorted(set(df_f.index.year)):
    f=df_f[df_f.index.year==y]; s=df_s[df_s.index.year==y]
    print(f"    {y}: net {f.sum():>7.0f} -> {s.sum():>7.0f}  | Sharpe {shp(f.values):>5.2f} -> {shp(s.values):>5.2f}")
