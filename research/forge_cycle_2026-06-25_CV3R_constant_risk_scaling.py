"""CV3-R — CONSTANT-RISK forecast scaling for ORB (report-only, strict-bar).
CV3 found EMA-slope strength is informative but naive matched-MEAN-exposure scaling failed the
risk bar (maxDD +53%, DLL 0->2) because it sized UP in high-vol regimes where per-trade $-risk is
already large (it omitted Carver's instrument_risk denominator). CV3-R restores it:
   size_d  proportional to  forecast_d / regime_risk_d ,  then globally scaled so H1 daily
   volatility == flat-ORB H1 daily volatility (CONSTANT RISK, derived on H1, applied OOS to H2).

STRICT BAR: same ORB trade set; forecast = EMA20 slope magnitude; NO trade deletion; NO hidden
leverage (per-day multiplier capped, exposure distribution + max reported); constant RISK not
constant mean-exposure; compare vs flat ORB AND naive CV3; report net/Sharpe/MAR/maxDD/worst
day-week-month/DLL/per-year/H1-H2/exposure-distribution/risk-contribution-by-forecast-bucket.
Verdict: ADVANCE (preserves/improves risk envelope while improving return/risk) /
FEATURE_ONLY (signal predictive but no safe sizing) / REJECT (still fattens tails). Capital gate unchanged."""
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
    wk=s.rolling(5).sum().min(); mo=s.rolling(21).sum().min()
    return dict(sharpe=shp(p),MAR=round(p.sum()/abs(dd.min()),2) if dd.min()<0 else None,maxDD=round(float(dd.min())),
                wd=round(float(s.min())),wk=round(float(wk)),mo=round(float(mo)),DLL=int((s<-1100).sum()),net=round(float(p.sum())),vol=round(float(s.std()),1))
# ORB trades -> flat daily PnL
cfg=get_asset("MNQ"); df=pd.read_csv(ROOT/"data/processed/MNQ_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
sig=generate_crossbred_signals(df,entry_name="orb_breakout",exit_name="profit_ladder",filter_name="ema_slope",params={"stop_mult":0.5,"target_mult":4.0,"trail_mult":2.5})
r=run_backtest(df,sig,mode="both",point_value=cfg["point_value"],tick_size=cfg["tick_size"],commission_per_side=cfg["commission_per_side"],slippage_ticks=cfg["slippage_ticks"])
t=r["trades_df"].copy(); t["day"]=pd.to_datetime(t["entry_time"]).dt.normalize()
P=t.groupby("day")["pnl"].sum().sort_index()                       # flat ORB daily PnL (1 contract)
# forecast = |EMA20 slope| / trailing-252 median (no lookahead in the normalizer)
dclose=df.assign(d=df["datetime"].dt.normalize()).groupby("d")["close"].last()
slope=dclose.ewm(span=20,adjust=False).mean().diff()
fc_same=(slope.abs()/slope.abs().rolling(252,min_periods=60).median()).reindex(P.index)   # same-day (CV3 convention)
fc_lag =fc_same.shift(1)                                                                   # strict no-lookahead robustness
# regime risk = trailing EWMA std of flat ORB daily PnL, known at start of day (shift 1)
sigma=P.ewm(span=21,adjust=False).std().shift(1).reindex(P.index)
D=pd.DataFrame({"P":P,"fc":fc_same,"fcl":fc_lag,"sig":sigma}).dropna()
days=D.index; h=len(days)//2; H1=days[:h]; H2=days[h:]
def metrics_block(title, m):  # m = per-day multiplier Series aligned to D.index
    sc=D["P"]*m
    print(f"\n  [{title}] mean mult={m.mean():.3f} max={m.max():.2f} min={m.min():.2f} | exposure pctl 10/50/90={np.percentile(m,10):.2f}/{np.percentile(m,50):.2f}/{np.percentile(m,90):.2f}")
    for lab,dd in [("FULL",days),("H1",H1),("H2(OOS)",H2)]:
        b=book(sc.reindex(dd))
        print(f"    {lab:8s} Sh={b['sharpe']:>5.2f} MAR={str(b['MAR']):>6s} maxDD={b['maxDD']:>7} wd={b['wd']:>6} wk={b['wk']:>7} mo={b['mo']:>7} DLL={b['DLL']} net={b['net']:>7} vol={b['vol']}")
    return sc
print("=== CV3-R constant-risk forecast scaling (vs flat ORB, vs naive CV3) ===")
# flat baseline
flat=metrics_block("FLAT ORB (mult=1)", pd.Series(1.0,index=D.index))
# naive CV3 reproduction (daily): cap[0.5,2.0], mean over H1 == 1.0 (constant MEAN exposure)
grid=np.linspace(0.3,3.0,541)
mn=lambda s: np.clip(D["fc"]/s,0.5,2.0)
best_n=min(grid,key=lambda s: abs(mn(s).reindex(H1).mean()-1.0)); m_naive=mn(best_n)
naive=metrics_block("NAIVE CV3 (matched MEAN exposure)", m_naive)
# CV3-R: raw = forecast / (regime risk normalized), cap, then global c so H1 daily VOL == flat H1 vol (constant RISK)
def cv3r(fc_col, cap=(0.33,3.0)):
    signorm=D["sig"]/D["sig"].reindex(H1).median()
    raw=np.clip(D[fc_col]/signorm,*cap)
    c=D["P"].reindex(H1).std()/ (D["P"]*raw).reindex(H1).std()    # constant-risk: match H1 daily vol
    return c*raw
m_r=cv3r("fc"); cv3r_book=metrics_block("CV3-R constant-risk (same-day fc)", m_r)
m_rl=cv3r("fcl"); _=metrics_block("CV3-R constant-risk (LAGGED fc, strict no-lookahead)", m_rl)
# risk contribution by forecast bucket (terciles): share of variance (sum of squared daily PnL)
print("\n  Risk contribution by forecast tercile (share of sum-of-squares daily PnL):")
buck=pd.qcut(D["fc"],3,labels=["lowFC","midFC","highFC"])
for name,sc in [("flat",flat),("naiveCV3",naive),("CV3-R",cv3r_book)]:
    ss=(sc**2).groupby(buck,observed=False).sum(); frac=(ss/ss.sum()*100).round(0)
    netb=sc.groupby(buck,observed=False).sum().round(0)
    print(f"    {name:9s} risk%% low/mid/high={int(frac['lowFC'])}/{int(frac['midFC'])}/{int(frac['highFC'])}  | net low/mid/high={int(netb['lowFC'])}/{int(netb['midFC'])}/{int(netb['highFC'])}")
# per-year flat vs CV3-R
print("\n  Per-year net & Sharpe (flat -> CV3-R):")
for y in sorted(set(days.year)):
    f=flat[flat.index.year==y]; s=cv3r_book[cv3r_book.index.year==y]
    print(f"    {y}: net {f.sum():>7.0f} -> {s.sum():>7.0f} | Sharpe {shp(f.values):>5.2f} -> {shp(s.values):>5.2f} | maxDD flat={int((np.cumsum(f.values)-np.maximum.accumulate(np.cumsum(f.values))).min())} R={int((np.cumsum(s.values)-np.maximum.accumulate(np.cumsum(s.values))).min())}")
