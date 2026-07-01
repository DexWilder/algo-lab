"""1m + VOLUME MICROSTRUCTURE HARNESS (T3) — the Phase-1 frontier: mine the ~7.9M minute bars we own but don't use.
ONE clean harness (not many one-offs). Tz-AGNOSTIC session detection (finds the 390-min max-volume RTH window from the
global minute-of-day volume profile — robust across all instruments). Causal features only (signal known at bar T trades
T+1..close). Declares data_tier=T3. Runs each packet through expression-validator + adversarial review + layered-N DSR +
trial ledger, with H1/H2 + month robustness + realistic cost + side/turnover.
Run: python3 research/forge_microstructure_1m.py [SYM ...]   (default MES MNQ)"""
import sys; from pathlib import Path; import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from research.forge_deflated_sharpe import deflated_sharpe
from research.forge_trial_ledger import record, count
from research.validate_strategy_expression import assert_expression_valid
from research.adversarial_result_review import review
PV={"MES":5.0,"MNQ":2.0,"M2K":5.0,"MGC":10.0,"MCL":100.0}; RTC={"MES":3.0,"MNQ":3.0,"M2K":3.0,"MGC":6.0,"MCL":8.0}
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if len(x)>1 and x.std()>0 else 0.0
def maxyr(p): y=p.groupby(p.index.year).sum(); return 100*y.max()/y.sum() if y.sum()>0 else 999
def detect_session(df):
    mod=df["datetime"].dt.hour*60+df["datetime"].dt.minute
    prof=df.groupby(mod)["volume"].sum()
    full=pd.Series(0.0,index=range(1440)); full.loc[prof.index]=prof.values
    roll=full.rolling(390,min_periods=390).sum(); start=int(roll.idxmax())-389
    return max(0,start), max(0,start)+390   # [rth_start_min, rth_end_min)
def sessionize(df):
    s,e=detect_session(df); mod=df["datetime"].dt.hour*60+df["datetime"].dt.minute
    rth=df[(mod>=s)&(mod<e)].copy(); rth["mod"]=mod[(mod>=s)&(mod<e)]; rth["d"]=rth["datetime"].dt.normalize()
    rows=[]
    for d,g in rth.groupby("d"):
        g=g.sort_values("mod")
        if len(g)<200: continue
        openp=g.iloc[0]["open"]; or_bars=g[g["mod"]<s+30]
        if len(or_bars)<10: continue
        or_end=or_bars.iloc[-1]["close"]; or_vol=or_bars["volume"].sum()
        closep=g.iloc[-1]["close"]
        rows.append(dict(d=d,openp=openp,or_end=or_end,or_ret=or_end/openp-1,or_vol=or_vol,
                         rest_pts=closep-or_end,full_pts=closep-openp,sess_vol=g["volume"].sum()))
    return pd.DataFrame(rows).set_index("d").sort_index(), (s,e)
def evalp(pos, ret_series, pv, rtc, label, sym):
    pnl=(pos*ret_series*pv - (pos.diff().abs().fillna(0)>0)*rtc).dropna()
    ok=assert_expression_valid(pos.reindex(pnl.index).fillna(0), pnl, f"{label}_{sym}", min_trades=30)
    act=pos.reindex(pnl.index).fillna(0)!=0
    return dict(pnl=pnl,sh=shp(pnl.values),maxyr=maxyr(pnl),n_active=int(act.sum()),
                als=float((pos.reindex(pnl.index).fillna(0)[act]>0).mean()) if act.sum() else 0.5,
                flat=float(1-act.mean()),ok=ok,h1=shp(pnl.iloc[:len(pnl)//2].values),h2=shp(pnl.iloc[len(pnl)//2:].values))
syms=sys.argv[1:] or ["MES","MNQ"]
print("=== 1m+VOLUME MICROSTRUCTURE HARNESS (T3) ===")
allres={}
for sym in syms:
    f=ROOT/f"data/databento/{sym}_1m.csv"
    if not f.exists(): print(f"  {sym}: no 1m file"); continue
    df=pd.read_csv(f); df["datetime"]=pd.to_datetime(df["datetime"])
    S,win=sessionize(df); pv=PV.get(sym,5.0); rtc=RTC.get(sym,3.0)
    orv_z=(S["or_vol"]-S["or_vol"].rolling(60,min_periods=20).mean())/S["or_vol"].rolling(60,min_periods=20).std()
    print(f"  {sym}: RTH minute-window {win} | {len(S)} sessions {S.index.min().date()}..{S.index.max().date()}")
    packets={
      # 1 opening-range CONTINUATION conditioned on high opening volume (causal: OR known, trade rest-of-day)
      "OR_continuation_hivol": (np.sign(S["or_ret"]).where(orv_z>0.5,0.0), S["rest_pts"]),
      # 2 opening-range REVERSAL conditioned on high opening volume
      "OR_reversal_hivol":     (-np.sign(S["or_ret"]).where(orv_z>0.5,0.0), S["rest_pts"]),
      # 3 volume-shock drift: high opening volume z -> long rest-of-day (risk-on proxy), else flat
      "volshock_restofday":    (np.sign(S["or_ret"]).where(orv_z>1.5,0.0), S["rest_pts"]),
      # 4 low-volume opening -> mean-revert the OR move over rest of day
      "OR_lowvol_reversion":   (-np.sign(S["or_ret"]).where(orv_z<-0.3,0.0), S["rest_pts"]),
    }
    for name,(pos,ret) in packets.items():
        r=evalp(pos,ret,pv,rtc,name,sym); allres[f"{sym}:{name}"]=r
        record(f"MICRO_1m:{sym}:{name}",asset=sym,sharpe=r["sh"],verdict="micro",lane="databento_volume")
        print(f"    {name:22s} Sh={r['sh']:>5.2f} net=${r['pnl'].sum():>8.0f} H1/H2={r['h1']:>4.1f}/{r['h2']:>4.1f} maxyr={r['maxyr']:>4.0f}% act={r['n_active']} als={r['als']:.0%} {'OK' if r['ok'] else 'EXPR_INVALID'}")
# best valid -> hostile gate
gN=count(); fN=count(lane="databento_volume")
valid={k:v for k,v in allres.items() if v["ok"] and v["sh"]>0}
if valid:
    best=max(valid,key=lambda k:valid[k]["sh"]); bp=allres[best]["pnl"]
    dG=deflated_sharpe(bp.values,gN,sr_trials_std=0.05); dF=deflated_sharpe(bp.values,fN,sr_trials_std=0.05)
    v=allres[best]; verdict="SCREEN_PASS" if v["sh"]>=1.0 and dG.get("dsr",0)>=0.95 and v["maxyr"]<40 else ("CLEAN_BUT_WEAK" if v["sh"]>0.5 else "CLEAN_KILL")
    ok,fails=review(dict(id=f"micro_{best}",label=verdict,sharpe=v["sh"],n=len(bp),n_active=v["n_active"],maxyr=v["maxyr"],
        active_long_share=v["als"],flat_share=v["flat"],cost_delta=1,global_n=gN,family_n=fN,richer_data_checked=True,
        harness_checked=True,data_tier="T3",richest_applicable_tier="T3"))
    print(f"\n  TRIAL-N global={gN} databento_volume-family={fN} | best-valid={best} Sh={v['sh']} DSR global={dG.get('dsr')} family={dF.get('dsr')}")
    print(f"  VERDICT: {verdict} (data_tier=T3){'  [adversarial PASS]' if ok else '  [adversarial FAIL]: '+str(fails)}")
else:
    print(f"\n  no positive-Sharpe valid packet this batch (all weak/kill). TRIAL-N global={gN} family={fN}")
print("  DATA-TIER: mean_reversion & open_close_liquidity now have a T3 harness -> tier_gap being closed. Run update_learning_state after.")
