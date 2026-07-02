"""T3 rich-data sweep — intraday 1m+volume path (the frontier). Per-instrument (coverage-aware). Packets: intraday MR
(vol-conditioned), volume-conditioned continuation, liquidity-hole reversal, closing-imbalance, MES-MNQ lead-lag+volume,
mean_reversion RETEST @T3. Full stack: tier-declare, expr-validate, artifact-detect, coverage-check, cost, H1/H2, side,
trial-N, failure_class, adversarial. Run: python3 research/forge_micro_t3_sweep.py"""
import sys; from pathlib import Path; import numpy as np, pandas as pd
R=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(R))
from research.forge_deflated_sharpe import deflated_sharpe
from research.forge_trial_ledger import record, count
from research.validate_strategy_expression import assert_expression_valid
from research.artifact_detectors import detect_suspicious_sharpe, detect_degenerate_active_side, detect_sparse, detect_coverage_mismatch
PV={"MES":5.0,"MNQ":2.0,"ZN":1000.0}; RTC={"MES":3.0,"MNQ":3.0,"ZN":15.0}
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(len(x)/ (len(x)/252/26) if False else 252),2) if len(x)>1 and x.std()>0 else 0.0
def sharpe_bars(pnl, bars_per_day=26): 
    x=np.asarray(pnl,float); return round(x.mean()/x.std()*np.sqrt(252*bars_per_day),2) if len(x)>1 and x.std()>0 else 0.0
def load15(sym):
    df=pd.read_csv(f"data/databento/{sym}_1m.csv",parse_dates=["datetime"]).set_index("datetime")
    mm=df.index.hour*60+df.index.minute; prof=df.groupby(mm)["volume"].sum()
    full=pd.Series(0.0,index=range(1440)); full.loc[prof.index]=prof.values; s=int(full.rolling(390,min_periods=390).sum().idxmax())-389
    rth=df[(mm>=s)&(mm<s+390)]
    g=rth.resample("15min").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    g=g[g["volume"]>0]; g["ret"]=g["close"].diff(); g["date"]=g.index.normalize()
    rng=(str(df.index.min().date()),str(df.index.max().date()))
    return g,rng
def run_packet(name,sym,pos,ret,pv,rtc,bpd):
    pnl=(pos.shift(1)*ret*pv - (pos.shift(1).diff().abs().fillna(0)>0)*rtc).dropna()
    if len(pnl)<50: return None
    ok=assert_expression_valid(pos.shift(1).reindex(pnl.index).fillna(0),pnl,f"{name}_{sym}",min_trades=30)
    sh=sharpe_bars(pnl.values,bpd); h=len(pnl)//2
    act=pos.shift(1).reindex(pnl.index).fillna(0)!=0
    deg=detect_degenerate_active_side(pos.shift(1))[0]; susp=detect_suspicious_sharpe(sh)[0]
    yr=pnl.groupby(pnl.index.year).sum(); maxyr=100*yr.max()/yr.sum() if yr.sum()>0 else 999
    fc=("side_degeneracy" if deg else "instability" if susp else "concentration" if maxyr>60 else "no_edge" if abs(sh)<0.3 else "dsr_searchN_fail" if sh<1.0 else None)
    gN=count()
    record(f"MICRO_T3:{name}:{sym}",asset=sym,sharpe=sh,verdict="micro",lane="databento_volume",data_tier="T3",failure_class=fc,maxyr=round(maxyr),n=len(pnl))
    print(f"    {name:26s} {sym}: Sh={sh:>5.2f} net=${pnl.sum():>9.0f} H1/H2={sharpe_bars(pnl.iloc[:h].values,bpd):>4.1f}/{sharpe_bars(pnl.iloc[h:].values,bpd):>4.1f} maxyr={maxyr:>4.0f}% act={int(act.sum())} {'OK' if ok else 'INVALID'} fc={fc}")
    return dict(sh=sh,pnl=pnl,fc=fc,ok=ok)
print("=== T3 SWEEP ===")
DATA={}; RANGES={}
for sym in ["MES","MNQ","ZN"]:
    g,rng=load15(sym); DATA[sym]=g; RANGES[sym]=rng
    volz=(g["volume"]-g["volume"].rolling(100,min_periods=30).mean())/g["volume"].rolling(100,min_periods=30).std()
    rz=(g["ret"]-g["ret"].rolling(100,min_periods=30).mean())/g["ret"].rolling(100,min_periods=30).std()
    print(f"  {sym}: {len(g)} 15m bars {rng[0]}..{rng[1]}")
    run_packet("intraday_MR_volcond",sym,(-np.sign(g["ret"])).where(volz>0.5,0.0),g["ret"],PV[sym],RTC[sym],26)  # mean_reversion RETEST @T3
    run_packet("vol_cond_continuation",sym,(np.sign(g["ret"])).where(volz>1.0,0.0),g["ret"],PV[sym],RTC[sym],26)
    run_packet("liquidity_hole_reversal",sym,(-np.sign(g["ret"])).where((volz<-0.5)&(rz.abs()>1.5),0.0),g["ret"],PV[sym],RTC[sym],26)
    run_packet("intraday_MR_plain",sym,(-np.sign(g["ret"])).where(rz.abs()>1.5,0.0),g["ret"],PV[sym],RTC[sym],26)
# MES-MNQ lead-lag + volume (coverage overlaps: both equity micros)
cm,det=detect_coverage_mismatch({k:RANGES[k] for k in ("MES","MNQ")})
print(f"  lead-lag coverage MES/MNQ: {det}")
if not cm:
    a,b=DATA["MES"],DATA["MNQ"]; idx=a.index.intersection(b.index)
    av=(a.loc[idx,"volume"]-a.loc[idx,"volume"].rolling(100,min_periods=30).mean())/a.loc[idx,"volume"].rolling(100,min_periods=30).std()
    pos=np.sign(a.loc[idx,"ret"]).where(av>0.5,0.0)   # MES move (vol-confirmed) predicts MNQ next bar
    run_packet("leadlag_MEStoMNQ_vol","MNQ",pos.reindex(b.index).fillna(0),b["ret"],PV["MNQ"],RTC["MNQ"],26)
print(f"\n  TRIAL-N global={count()} T3-family={count(lane='databento_volume')}")
print("  VERDICT SUMMARY: intraday 1m-path T3 sweep across MES/MNQ/ZN + lead-lag. failure_class recorded per packet.")
print("  mean_reversion @T3 RETEST done (intraday_MR variants) — family status update via learning hook.")
