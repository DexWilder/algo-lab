"""GEX EXPIRY PIN TEST (T6, correct surface) — weekly/near-expiry ES option OI. Causal: prior-day OI at the soonest weekly
expiry (1-5 DTE, known at settlement) -> next-session movement toward max-OI strike (pin) + realized-range compression.
This is the mechanism's HOME regime (monthly sample had 0 near-expiry days). Full stack + label discipline (allowed:
FEASIBILITY_PASS/CLEAN_KILL_T6_EXPRESSION_ONLY/SCREEN_PASS/RETEST_REQUIRED/DATA_STATUS_UNPROVEN)."""
import sys; from pathlib import Path; import numpy as np, pandas as pd
R=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(R))
from research.forge_deflated_sharpe import deflated_sharpe
from research.forge_trial_ledger import count, record, classify_failure
from research.validate_strategy_expression import assert_expression_valid
from research.artifact_detectors import detect_degenerate_active_side, detect_suspicious_sharpe
PV=5.0; RTC=3.0
oi=pd.read_csv(R/"data/databento/ES_OPT_weekly_oi.csv",parse_dates=["date"])
oi["exp"]=pd.to_datetime(oi["expiration"],utc=True,errors="coerce").dt.tz_localize(None); oi["dte"]=(oi["exp"]-oi["date"]).dt.days
m=pd.read_csv(R/"data/databento/MES_1m.csv",parse_dates=["datetime"]).set_index("datetime")
mm=m.index.hour*60+m.index.minute; prof=m.groupby(mm)["volume"].sum(); full=pd.Series(0.0,index=range(1440)); full.loc[prof.index]=prof.values
s0=int(full.rolling(390,min_periods=390).sum().idxmax())-389; rth=m[(mm>=s0)&(mm<s0+390)]
day=rth.resample("1D").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna()
day["ret"]=day["close"].diff(); day["rng"]=(day["high"]-day["low"])/day["close"]
recs=[]
for d,g in oi.groupby("date"):
    if d not in day.index: continue
    front=g[(g["dte"]>=1)&(g["dte"]<=5)]
    if front.empty: continue
    E=front["exp"].min(); chain=front[front["exp"]==E]; spot=day.loc[d,"close"]
    near=chain[(chain["strike_price"]>spot*0.98)&(chain["strike_price"]<spot*1.02)]
    if near["oi"].sum()<500: continue
    bs=near.groupby("strike_price")["oi"].sum().sort_values(ascending=False)
    pin=bs.index[0]; conc=bs.head(3).sum()/bs.sum()
    recs.append(dict(date=d,spot=spot,pin=pin,dist=(pin-spot)/spot,conc=conc,dte=int((E-d).days)))
G=pd.DataFrame(recs).set_index("date").sort_index()
G["next_ret"]=day["ret"].reindex(G.index.union(day.index)).shift(-1).reindex(G.index)
G["next_rng"]=day["rng"].reindex(G.index.union(day.index)).shift(-1).reindex(G.index)
G=G.dropna(subset=["next_ret","next_rng"])
print(f"=== GEX EXPIRY PIN TEST (T6, weekly/near-expiry) === n_days={len(G)} DTE range {G['dte'].min()}-{G['dte'].max()} (median {int(G['dte'].median())})")
hi=G["conc"]>G["conc"].median()
print(f"  [PIN/COMPRESSION] next-day range: high-conc={G[hi]['next_rng'].mean()*100:.3f}% vs low-conc={G[~hi]['next_rng'].mean()*100:.3f}% (pin=>high<low)")
hit=(np.sign(G[hi]["dist"])==np.sign(G[hi]["next_ret"])).mean(); corr=np.sign(G[hi]["dist"]).corr(np.sign(G[hi]["next_ret"]))
print(f"  [DRIFT-to-pin] high-conc: sign(dist)==sign(next-ret) hit={hit:.0%} corr={corr:.2f} (>55% => drift-to-pin)")
# tightest expiry subset (dte<=2)
le2=G[G["dte"]<=2]
if len(le2)>10:
    h2=(np.sign(le2["dist"])==np.sign(le2["next_ret"])).mean()
    print(f"  [<=2DTE] n={len(le2)} drift-hit={h2:.0%} range={le2['next_rng'].mean()*100:.3f}%")
# tradeable: bet drift to pin on high-conc near-expiry days
pos=np.sign(G["dist"]).where(hi,0.0); pnl=(pos*G["next_ret"]*PV-(pos.diff().abs().fillna(0)>0)*RTC).dropna()
ok=assert_expression_valid(pos.reindex(pnl.index).fillna(0),pnl,"gex_expiry_pin",min_trades=15)
sh=round(pnl.mean()/pnl.std()*np.sqrt(252),2) if pnl.std()>0 else 0; gN=count()
deg=detect_degenerate_active_side(pos)[0]; susp=detect_suspicious_sharpe(sh)[0]; dsr=deflated_sharpe(pnl.values,gN,sr_trials_std=0.05).get("dsr") if len(pnl)>5 else None
print(f"  [TRADEABLE] pin-drift: Sh={sh} net=${pnl.sum():.0f} n_active={int((pos!=0).sum())} DSR@{gN}={dsr}")
effect=(G[hi]["next_rng"].mean() < G[~hi]["next_rng"].mean()*0.95) or (hit>0.55)
verdict=("SCREEN_PASS (real pin effect)" if (effect and sh>0.5 and (dsr or 0)>0.9) else
         "FEASIBILITY_PASS + weak conditional effect -> RETEST larger coverage" if effect else
         "CLEAN_KILL_T6_EXPRESSION_ONLY (weekly pin-drift proxy: no effect even at near-expiry; try gamma-flip/wall variant)")
fc=classify_failure(sharpe=sh,maxyr=None,degenerate=deg,suspicious=susp,dsr=dsr) if "KILL" in verdict else None
record("GEX_EXPIRY:pin_drift:ES",asset="ES",sharpe=sh,verdict="micro",lane="exploratory",data_tier="T6",failure_class=fc,n=len(pnl),dsr=dsr)
print(f"  VERDICT: {verdict}")
print(f"  (Correct surface tested. Options family: {'PIN EFFECT PRESENT -> deepen' if effect else 'naive pin-drift dead; next=gamma-flip range asymmetry / call-put wall (queued)'})")
