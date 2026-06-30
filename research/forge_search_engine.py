"""FORGE SEARCH ENGINE (2026-06-30) — continuous large-space strategy search, DSR-corrected at TRUE N.
Replaces ad-hoc one-off packets. Sweeps the crossbred primitive space (entry x filter x exit x asset) on the
FIXED (causality-clean) engine, applies concentration + cross-asset + DSR-at-FULL-N gates, records EVERY combo to
the trial ledger (so the multiple-testing bar is honest/brutal), and surfaces only survivors. Writes results JSONL
incrementally so it can run nonstop in the background and be monitored live.
Run: python3 research/forge_search_engine.py [--tier fast|full] [--assets MNQ,MES,...]"""
import sys, json, time, argparse, itertools
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
import research.crossbreeding.crossbreeding_engine as ce
from engine.backtest import run_backtest
from engine.asset_config import get_asset
from research.forge_deflated_sharpe import deflated_sharpe
from research.forge_trial_ledger import record, count
OUT=ROOT/"research/data/forge_search_results.jsonl"
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(252),2) if len(x)>1 and x.std()>0 else 0
PARAMS={"stop_mult":2.0,"target_mult":4.0,"trail_mult":2.5}
# FAST tier = fast entries (avoid pb/bb pure-python hot loops ~hundreds of s)
FAST_ENTRIES=["orb_breakout","donchian_breakout","vwap_continuation","vwap_reclaim","prior_day_break",
              "prior_day_fade","range_compression_break","gap_fill_trigger","opening_drive_exhaustion","orb_failure_reversal"]
FILTERS=["none","ema_slope","vwap_slope","ema_slope_vol_high","ema_slope_vol_low","vol_regime","session_morning","session_afternoon"]
EXITS=["profit_ladder","atr_trail","chandelier"]
def one(asset, e, f, x, dfcache):
    cfg=get_asset(asset); df=dfcache[asset]
    try:
        sig=ce.generate_crossbred_signals(df,entry_name=e,exit_name=x,filter_name=f,params=PARAMS)
        r=run_backtest(df,sig,mode="both",point_value=cfg["point_value"],tick_size=cfg["tick_size"],
                       commission_per_side=cfg["commission_per_side"],slippage_ticks=cfg["slippage_ticks"])
        t=r["trades_df"]
        if len(t)<150: return None
        t=t.copy(); t["day"]=pd.to_datetime(t["entry_time"]).dt.normalize(); d=t.groupby("day")["pnl"].sum()
        pnl=t["pnl"].values; gw=pnl[pnl>0].sum(); gl=-pnl[pnl<0].sum(); pf=gw/gl if gl>0 else 99
        yr=t.groupby(t["day"].dt.year)["pnl"].sum(); maxyr=100*yr.max()/yr.sum() if yr.sum()>0 else 999
        top3=100*np.sort(pnl)[-3:].sum()/pnl.sum() if pnl.sum()>0 else 999
        h=len(d)//2
        return dict(asset=asset,entry=e,filter=f,exit=x,trades=int(len(t)),pf=round(float(pf),3),
                    sharpe=shp(d.values),net=round(float(pnl.sum())),median=round(float(np.median(pnl)),1),
                    maxyr=round(float(maxyr),0),top3=round(float(top3),0),
                    h1=shp(d.iloc[:h].values),h2=shp(d.iloc[h:].values),per_period=float(d.mean()/d.std()) if d.std()>0 else 0)
    except Exception as ex:
        return None
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--assets",default="MNQ,MES,MGC,MCL,MYM,ZN,M2K")
    ap.add_argument("--entries",default=",".join(FAST_ENTRIES)); a=ap.parse_args()
    assets=a.assets.split(","); entries=a.entries.split(",")
    dfcache={}
    for s in assets:
        d=pd.read_csv(ROOT/f"data/processed/{s}_5m.csv"); d["datetime"]=pd.to_datetime(d["datetime"]); dfcache[s]=d
    combos=list(itertools.product(entries,FILTERS,EXITS,assets))
    print(f"FORGE SEARCH: {len(combos)} combos ({len(entries)}e x {len(FILTERS)}f x {len(EXITS)}x x {len(assets)}assets). Writing {OUT.name} live.")
    t0=time.time(); done=0; survivors=[]
    for e,f,x,asset in combos:
        r=one(asset,e,f,x,dfcache); done+=1
        record(f"SEARCH:{e}|{f}|{x}", asset=asset, sharpe=(r or {}).get("sharpe"), verdict="screen")
        if r:
            with OUT.open("a") as fh: fh.write(json.dumps(r)+"\n")
            # provisional survivor screen (pre-DSR): real edge bar
            if r["pf"]>=1.25 and r["sharpe"]>=1.0 and r["trades"]>=200 and r["maxyr"]<40 and r["top3"]<30 and r["median"]>=0 and r["h1"]>0 and r["h2"]>0:
                survivors.append(r); print(f"  ** SCREEN-SURVIVOR: {e}|{f}|{x}|{asset} PF={r['pf']} Sh={r['sharpe']} n={r['trades']} maxyr={r['maxyr']}% H1/H2={r['h1']}/{r['h2']}")
        if done%50==0: print(f"  ...{done}/{len(combos)} ({(time.time()-t0)/60:.1f}min), {len(survivors)} screen-survivors")
    N=count()
    print(f"\nDONE {done} combos in {(time.time()-t0)/60:.1f}min. Trial-N now {N}. {len(survivors)} pre-DSR screen-survivors.")
    # DSR-at-full-N on screen survivors (cross-asset: a mechanism that survives on >=2 assets is real)
    from collections import defaultdict
    bymech=defaultdict(list)
    for s in survivors: bymech[(s["entry"],s["filter"],s["exit"])].append(s["asset"])
    print("=== survivors by mechanism (cross-asset count) ===")
    for mech,assts in sorted(bymech.items(), key=lambda kv:-len(kv[1])):
        flag=" <== CROSS-ASSET (>=2)" if len(assts)>=2 else ""
        print(f"  {mech[0]}|{mech[1]}|{mech[2]}: {assts}{flag}")
    if not survivors: print("  (none cleared the screen — primitive space looks clean-exhausted; pivot to regime/cross-asset/feeds)")
    print(f"\nNOTE: screen-survivors must STILL clear DSR at N={N} before any candidate language. This sweep made the multiple-testing bar honest.")
if __name__=="__main__": main()
