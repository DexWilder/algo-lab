"""GEX-REGIME PIN TEST (T6, FIRST feasibility screen). Causal: prior-day OI (EOD settlement, known before next session)
-> next-session movement. Proxies (no IV inversion needed for screen): max-OI strike (pin magnet), OI concentration near
spot, distance-to-pin, expiry proximity. Mechanism: high OI concentration near spot -> lower realized movement (pinning) +
drift toward pin. Underlying spot = MES RTH close (same index level as ES). Full stack; label discipline (T6, no strategy claim).
Run: python3 research/forge_gex_regime.py"""
import sys; from pathlib import Path; import numpy as np, pandas as pd
R=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(R))
from research.forge_deflated_sharpe import deflated_sharpe
from research.forge_trial_ledger import count, record
from research.validate_strategy_expression import assert_expression_valid
from research.artifact_detectors import detect_degenerate_active_side, detect_suspicious_sharpe
PV=5.0; RTC=3.0
oi=pd.read_csv(R/"data/databento/ES_OPT_oi_daily.csv",parse_dates=["date"])
# MES daily RTH close (spot proxy = S&P index level)
m=pd.read_csv(R/"data/databento/MES_1m.csv",parse_dates=["datetime"]).set_index("datetime")
mm=m.index.hour*60+m.index.minute; prof=m.groupby(mm)["volume"].sum(); full=pd.Series(0.0,index=range(1440)); full.loc[prof.index]=prof.values
s0=int(full.rolling(390,min_periods=390).sum().idxmax())-389; rth=m[(mm>=s0)&(mm<s0+390)]
day=rth.resample("1D").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna()
day["ret_pts"]=day["close"].diff(); day["range"]=(day["high"]-day["low"])/day["close"]
# per-date OI regime (causal: use date d OI -> predict d+1)
recs=[]
for d,g in oi.groupby("date"):
    if d not in day.index: continue
    spot=day.loc[d,"close"]; near=g[(g["strike_price"]>spot*0.97)&(g["strike_price"]<spot*1.03)]
    if near["oi"].sum()<1000: continue
    by_strike=near.groupby("strike_price")["oi"].sum().sort_values(ascending=False)
    pin=by_strike.index[0]; conc=by_strike.head(3).sum()/by_strike.sum()
    _exp=pd.to_datetime(g["expiration"],utc=True,errors="coerce").dt.tz_localize(None)
    days_to_exp=(_exp.min()-d).days if _exp.notna().any() else 99
    recs.append(dict(date=d,spot=spot,pin=pin,conc=conc,dist=(pin-spot)/spot,dte=max(0,days_to_exp)))
G=pd.DataFrame(recs).set_index("date").sort_index()
G["next_ret"]=day["ret_pts"].reindex(G.index.union(day.index)).shift(-1).reindex(G.index)  # causal next-day
G["next_range"]=day["range"].reindex(G.index.union(day.index)).shift(-1).reindex(G.index)
G=G.dropna(subset=["next_ret","next_range"])
print(f"=== GEX-REGIME PIN TEST (T6, first screen) === n_days={len(G)} {G.index.min().date()}..{G.index.max().date()} (non-contiguous, Mar/Apr gap)")
hi=G["conc"]>G["conc"].median(); print(f"  OI concentration: median top3-share={G['conc'].median():.2f}")
# 1 PIN effect: high-conc days -> lower next-day realized range?
print(f"  [PIN] next-day range: high-conc={G[hi]['next_range'].mean()*100:.3f}% vs low-conc={G[~hi]['next_range'].mean()*100:.3f}% (pin => high<low)")
# 2 DRIFT-to-pin: does price move toward the pin strike next day (on high-conc days)?
drift_corr=np.sign(G[hi]["dist"]).corr(np.sign(G[hi]["next_ret"]))
hit=(np.sign(G[hi]["dist"])==np.sign(G[hi]["next_ret"])).mean()
print(f"  [DRIFT] high-conc: sign(dist-to-pin)==sign(next-ret) hit-rate={hit:.0%} (>>50% => drift-to-pin) corr={drift_corr:.2f}")
# 3 expiry proximity
nearexp=G["dte"]<=5; print(f"  [EXPIRY] <=5DTE next-range={G[nearexp]['next_range'].mean()*100:.3f}% vs >5DTE={G[~nearexp]['next_range'].mean()*100:.3f}% (n_nearexp={nearexp.sum()})")
# tradeable (thin): on high-conc days, bet price drifts to pin
pos=np.sign(G["dist"]).where(hi,0.0); pnl=(pos*G["next_ret"]*PV-(pos.diff().abs().fillna(0)>0)*RTC).dropna()
ok=assert_expression_valid(pos.reindex(pnl.index).fillna(0),pnl,"gex_pin_drift",min_trades=20)
sh=round(pnl.mean()/pnl.std()*np.sqrt(252),2) if pnl.std()>0 else 0; gN=count()
deg=detect_degenerate_active_side(pos)[0]; susp=detect_suspicious_sharpe(sh)[0]
dsr=deflated_sharpe(pnl.values,gN,sr_trials_std=0.05).get("dsr") if len(pnl)>5 else None
print(f"  [TRADEABLE] pin-drift: Sh={sh} net=${pnl.sum():.0f} n_active={int((pos!=0).sum())} DSR@{gN}={dsr}")
# verdict (allowed labels only)
rel = 1 - G[hi]["next_range"].mean()/G[~hi]["next_range"].mean()
effect = (rel>0.05) or (hit>0.55)   # meaningful pinning (>=5% range cut) or real drift-to-pin
expiry_untested = (nearexp.sum()==0)
verdict = ("FEASIBILITY_PASS + weak effect -> RETEST" if effect else "CLEAN_KILL_T6_EXPRESSION_ONLY (naive pin proxy: no effect; options family stays alive)")
if expiry_untested: verdict += " | RETEST_REQUIRED at EXPIRY/0DTE (mechanism's home regime had 0 days in sample)"
if len(G)<40: verdict="DATA_STATUS_UNPROVEN (too few days) -> "+verdict
fc=("no_edge" if "KILL" in verdict else ("insufficient_tier" if "UNPROVEN" in verdict else None))
record("GEX_REGIME:pin_drift:MES/ES",asset="ES",sharpe=sh,verdict="micro",lane="exploratory",data_tier="T6",failure_class=fc,n=len(pnl))
print(f"  VERDICT: {verdict}")
print(f"  (T6 first mechanism test. NOT a strategy claim. Options/OI vein is data-unlocked; expand OI coverage (Mar/Apr/more years) to confirm/deny.)")
