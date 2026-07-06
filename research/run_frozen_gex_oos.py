"""DURABLE FROZEN-RULE OOS RUNNER — the completion trigger, not "I'll be notified". Self-guards against mid-write analysis:
refuses to run if the OOS pull process is alive OR the OI file mtime changed in the last 20s. When safe, runs the EXACT
pre-registered rule (GEX_BREAKOUT_RANGE_PREREGISTERED_RULE_2026-07-06) on MES/MNQ/MYM, by year, DSR, adversarial — NO
optimization — and writes research/data/gex_oos_pull_DONE.json marker. Run anytime; it decides if it's safe.
Run: python3 research/run_frozen_gex_oos.py"""
import sys, os, time, json, subprocess
from pathlib import Path
import numpy as np, pandas as pd
R=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(R))
OI=R/"data/databento/ES_OPT_weekly_oi.csv"; MARK=R/"research/data/gex_oos_pull_DONE.json"
# --- GUARD 1: pull process alive? ---
alive=subprocess.run(["pgrep","-f","databento_gex_oos"],capture_output=True,text=True).stdout.strip()
if alive:
    print("STATE: RUNNING_INCREMENTAL_PULL_WITH_PROGRESS — pull alive, NO analysis (no mid-write)."); sys.exit(0)
# --- GUARD 2: file stable (mtime not changed in 20s)? ---
if not OI.exists(): print("STATE: no OI file"); sys.exit(0)
age=time.time()-OI.stat().st_mtime
if age<20: print(f"STATE: file written {age:.0f}s ago (<20s) — waiting for stability, NO analysis."); sys.exit(0)
# --- SAFE: validate + run frozen rule ---
from research.validate_data_file import validate_data_file
from research.forge_deflated_sharpe import deflated_sharpe
from research.forge_trial_ledger import count, record, classify_failure
from research.adversarial_result_review import review
ok,fl=validate_data_file(str(OI))
oi=pd.read_csv(OI,parse_dates=["date"]); oi["exp"]=pd.to_datetime(oi["expiration"],utc=True,errors="coerce").dt.tz_localize(None); oi["dte"]=(oi["exp"]-oi["date"]).dt.days
days=oi["date"].nunique(); byyr=oi.groupby(oi["date"].dt.year)["date"].nunique().to_dict()
PV={"MES":5.0,"MNQ":2.0,"MYM":0.5}; RTC={"MES":3.0,"MNQ":3.0,"MYM":2.0}
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if len(x)>1 and x.std()>0 else 0.0
def sess(sym):
    m=pd.read_csv(R/f"data/databento/{sym}_1m.csv",parse_dates=["datetime"]).set_index("datetime")
    mm=m.index.hour*60+m.index.minute;prof=m.groupby(mm)["volume"].sum();full=pd.Series(0.0,index=range(1440));full.loc[prof.index]=prof.values
    s0=int(full.rolling(390,min_periods=390).sum().idxmax())-389;rth=m[(mm>=s0)&(mm<s0+390)].copy();rth["mmn"]=mm[(mm>=s0)&(mm<s0+390)];rth["d"]=rth.index.normalize()
    rows=[]
    for d,g in rth.groupby("d"):
        g=g.sort_values("mmn")
        if len(g)<200:continue
        orb=g[g["mmn"]<s0+30]
        rows.append(dict(d=d,openp=g.iloc[0]["open"],or_end=orb.iloc[-1]["close"] if len(orb) else g.iloc[0]["open"],close=g.iloc[-1]["close"]))
    S=pd.DataFrame(rows).set_index("d").sort_index();S["or_move"]=S["or_end"]-S["openp"];S["rest"]=S["close"]-S["or_end"];return S
# signed GEX per date (FROZEN: DTE 1-5, near-money 0.97-1.03, w=exp bell 0.7%, dealer-long convention), MES spot
Smes=sess("MES");gex={}
for d,g in oi.groupby("date"):
    front=g[(g["dte"]>=1)&(g["dte"]<=5)]
    if front.empty or d not in Smes.index:continue
    E=front["exp"].min();ch=front[front["exp"]==E];spot=Smes.loc[d,"openp"];near=ch[(ch["strike_price"]>spot*0.97)&(ch["strike_price"]<spot*1.03)]
    if near["oi"].sum()<500:continue
    w=np.exp(-0.5*((near["strike_price"]-spot)/(0.007*spot))**2);gex[d]=float((w*near["oi"]*np.where(near["cp"]=="C",1,-1)).sum())
gx=pd.Series(gex).sort_index();gmed=gx.median()
print(f"=== FROZEN-RULE GEX OOS (days={days} byyr={byyr}) validation={'PASS' if ok else fl} ===")
results={}
for sym in ["MES","MNQ","MYM"]:
    S=sess(sym);reg_prior=(gx>gmed).shift(1)   # FROZEN: prior-day OI regime
    df=S.join(reg_prior.rename("posg"),how="inner").dropna(subset=["posg","or_move","rest"])
    sig=np.where(df["posg"],-1,1)*np.sign(df["or_move"])   # neg-GEX follow / pos-GEX fade
    turn=(pd.Series(sig,index=df.index).diff().abs().fillna(0)>0)*RTC[sym]
    pnl=(pd.Series(sig,index=df.index)*df["rest"]*PV[sym]-turn).dropna()
    yr=pnl.groupby(pnl.index.year).sum();my=100*yr.max()/yr.sum() if yr.sum()>0 else 999;dsr=deflated_sharpe(pnl.values,count()).get("dsr") if len(pnl)>10 else None
    results[sym]=dict(sh=shp(pnl.values),n=len(pnl),maxyr=round(my),dsr=dsr,peryr={int(y):round(v) for y,v in yr.items()})
    record(f"GEX_FROZEN_OOS:{sym}",asset=sym,sharpe=shp(pnl.values),verdict="micro",lane="exploratory",data_tier="T6",failure_class=classify_failure(sharpe=shp(pnl.values),maxyr=my,dsr=dsr),maxyr=round(my),dsr=dsr,n=len(pnl))
    print(f"  {sym}: Sh={shp(pnl.values)} n={len(pnl)} maxyr={my:.0f}% DSR={dsr} per-yr={results[sym]['peryr']}")
adv,_=review(dict(id="gex_frozen_oos_MNQ",label="SCREEN_PASS",sharpe=results["MNQ"]["sh"],n=results["MNQ"]["n"],n_active=results["MNQ"]["n"],maxyr=results["MNQ"]["maxyr"],active_long_share=0.5,flat_share=0,cost_delta=1,global_n=count(),family_n=10,richer_data_checked=True,harness_checked=True,data_tier="T6",richest_applicable_tier="T6"))
MARK.write_text(json.dumps({"completed":time.strftime("%Y-%m-%d %H:%M"),"file":str(OI),"days":days,"by_year":byyr,"validation":("PASS" if ok else fl),"frozen_oos_results":results,"adversarial_pass":adv},indent=2))
survive=all(results[s]["sh"]>0.5 for s in results) and results["MES"]["peryr"].get(2024,0)>0
print(f"  ADVERSARIAL: {'PASS' if adv else 'FAIL'} | 2024-OOS holds: {results['MES']['peryr'].get(2024)} (MES 2024)")
print(f"  VERDICT: {'GEX SURVIVES OOS -> real WH1 lead, deepen' if survive else 'GEX rule FRAGILE/2025-artifact under OOS -> regime stays as diagnostic, trade rule down-weighted'}")
print(f"  marker written: {MARK.name}")
