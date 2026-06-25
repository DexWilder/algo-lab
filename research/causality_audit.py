"""UNIVERSAL POINT-IN-TIME CAUSALITY AUDIT HARNESS (TRUTH_RESET, locked 2026-06-25).

MANDATORY PREFLIGHT. No strategy may be called WH / primary / validated / deployable / dossier-ready /
research-candidate until it passes this harness. Built because the ORB ema_slope same-day-close lookahead
reached dossiers and portfolio framing before the (too-late) audit. The research gate now runs FIRST.

Core principle: a signal at bar T may depend ONLY on data known at/before bar T. So perturbing any bar
AFTER T must NOT change any signal at or before T. We test this directly with two opposite future
perturbations (×3 up vs ×0.33 down on all bars > T) and assert signals[:T+1] are identical.

This is strategy-agnostic: pass any signal_fn(df)->DataFrame-with-'signal'-column.

Checks:
  A. FUTURE-PERTURBATION INVARIANCE (core lookahead test; includes pre-session-close splits to stress daily aggs)
  B. COST SENSITIVITY (PnL must change under cost stress when turnover>0; catches silent zero-cost / cost-not-wired)
  C. ROLLOVER-ARTIFACT scan (continuous-future daily |move|>8% count; flags roll-stitch contamination)
Verdict: CAUSAL_CLEAN (A passes) gates everything; B/C are quality flags reported alongside.
NOTE: clears compute_features _FEATURE_CACHE around perturbations (cache key ignores close content)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
import research.crossbreeding.crossbreeding_engine as ce

def _clear_cache():
    try: ce._FEATURE_CACHE.clear()
    except Exception: pass

def audit_signal_causality(df, signal_fn, label="strategy", n_splits=10, verbose=True):
    """Check A — signals[:T+1] must be invariant to any change in bars after T. Returns dict."""
    df=df.reset_index(drop=True); n=len(df)
    dates=pd.to_datetime(df["datetime"]).dt.normalize().values
    # split points: spread across [warmup, n-30] PLUS several 'one bar before a session close' (stress daily aggs)
    lo=int(n*0.4)
    splits=set(int(x) for x in np.linspace(lo, n-30, n_splits//2))
    udays=pd.Index(dates).unique()
    for d in udays[len(udays)//2 : len(udays)//2 + n_splits//2]:
        bars=np.where(dates==d)[0]
        if len(bars)>2 and bars[-1] < n-2: splits.add(int(bars[-1]-1))  # just before that day's close
    splits=sorted(s for s in splits if lo<=s<n-2)
    leaks=[]
    for T in splits:
        _clear_cache()
        a=df.copy(); m=a.index>T
        for c in ["open","high","low","close"]: a.loc[m,c]=a.loc[m,c]*3.0
        sigA=np.asarray(signal_fn(a)["signal"].values)
        _clear_cache()
        b=df.copy(); m2=b.index>T
        for c in ["open","high","low","close"]: b.loc[m2,c]=b.loc[m2,c]*0.33
        sigB=np.asarray(signal_fn(b)["signal"].values)
        diff_mask=sigA[:T+1]!=sigB[:T+1]
        nd=int(diff_mask.sum())
        if nd>0:
            first=int(np.where(diff_mask)[0][0])
            leaks.append({"split_T":T,"n_signals_changed_at_or_before_T":nd,"first_leaked_bar":first,
                          "first_leaked_date":str(pd.to_datetime(df['datetime']).iloc[first])})
    _clear_cache()
    verdict="CAUSAL_CLEAN" if not leaks else "LOOKAHEAD_DETECTED"
    if verbose:
        print(f"  [A future-perturbation invariance] {label}: {verdict}  ({len(splits)} splits, {len(leaks)} leaking)")
        for lk in leaks[:3]: print(f"      LEAK: future change altered {lk['n_signals_changed_at_or_before_T']} signals at/<=T={lk['split_T']}; first at bar {lk['first_leaked_bar']} ({lk['first_leaked_date']})")
    return {"check":"future_perturbation_invariance","label":label,"verdict":verdict,"n_splits":len(splits),"leaks":leaks}

def audit_cost_sensitivity(df, signal_fn, config, label="strategy"):
    """Check B — net PnL must change when costs rise (if there is turnover). Catches unwired costs."""
    from engine.backtest import run_backtest
    _clear_cache(); sig=signal_fn(df)
    def net(commission, slip):
        r=run_backtest(df,sig,mode="both",point_value=config["point_value"],tick_size=config["tick_size"],
                       commission_per_side=commission,slippage_ticks=slip)
        t=r["trades_df"]; return (float(t["pnl"].sum()), len(t))
    n0,tr=net(0.0,0); n1,_=net(config["commission_per_side"]*3,4)
    ok = (tr==0) or (abs(n0-n1)>1e-6)
    verdict="COST_WIRED" if ok else "COST_NOT_WIRED_OR_NO_TURNOVER"
    print(f"  [B cost sensitivity] {label}: {verdict}  (0-cost net=${n0:.0f} vs stressed net=${n1:.0f}, trades={tr})")
    return {"check":"cost_sensitivity","verdict":verdict,"net_zero":n0,"net_stressed":n1,"trades":tr}

def audit_rollover_artifacts(asset, label=None):
    """Check C — continuous-future roll-stitch artifacts (daily |move|>8%)."""
    df=pd.read_csv(ROOT/f"data/processed/{asset}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
    dc=df.assign(d=df["datetime"].dt.normalize()).groupby("d")["close"].last()
    mv=dc.pct_change().abs(); n_art=int((mv>0.08).sum()); mx=float(mv.max()*100)
    verdict="CLEAN" if n_art<=5 else ("SUSPECT" if n_art<=12 else "CONTAMINATED")
    print(f"  [C rollover artifacts] {asset}: {verdict}  ({n_art} days |move|>8%, max {mx:.1f}%)")
    return {"check":"rollover_artifacts","asset":asset,"n_artifact_days":n_art,"max_move_pct":round(mx,1),"verdict":verdict}

# ── CERTIFICATION: prove the harness PASSES the fixed ORB and CATCHES the contaminated ORB ──
if __name__=="__main__":
    from engine.asset_config import get_asset
    asset="MGC"; cfg=get_asset(asset)
    df=pd.read_csv(ROOT/f"data/processed/{asset}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
    df=df.iloc[-18000:].reset_index(drop=True)  # representative slice w/ history
    recipe=dict(entry_name="orb_breakout",exit_name="profit_ladder",filter_name="ema_slope",
                params={"stop_mult":2.0,"target_mult":4.0,"trail_mult":2.5})
    def orb_signal(frame): return ce.generate_crossbred_signals(frame, **recipe)
    orig=ce.compute_features
    def unshift_cf(frame,*a,**k):  # reproduce PRE-FIX same-day lookahead
        f=dict(orig(frame,*a,**k)); dts=pd.to_datetime(f["dates"]).normalize()
        dd=pd.DataFrame({"d":dts,"c":f["close"]}).groupby("d")["c"].last()
        sl=dd.ewm(span=20,adjust=False).mean().diff()
        sgn={k2:(0 if pd.isna(v) else (1 if v>0 else -1)) for k2,v in sl.items()}
        f["bar_trend"]=np.array([sgn.get(x,0) for x in dts]); return f
    print("=== CAUSALITY HARNESS CERTIFICATION (ORB on MGC slice) ===")
    print("-- 1) FIXED engine (on-disk) — expect CAUSAL_CLEAN --")
    ce.compute_features=orig;       r_fixed=audit_signal_causality(df, orb_signal, "ORB-fixed")
    print("-- 2) CONTAMINATED engine (un-shifted) — expect LOOKAHEAD_DETECTED --")
    ce.compute_features=unshift_cf; r_contam=audit_signal_causality(df, orb_signal, "ORB-contaminated")
    ce.compute_features=orig
    print("-- 3) cost sensitivity + rollover (fixed) --")
    audit_cost_sensitivity(df, orb_signal, cfg, "ORB-fixed"); audit_rollover_artifacts(asset)
    ok = (r_fixed["verdict"]=="CAUSAL_CLEAN" and r_contam["verdict"]=="LOOKAHEAD_DETECTED")
    print(f"\nHARNESS CERTIFIED: {ok}  (fixed CLEAN={r_fixed['verdict']=='CAUSAL_CLEAN'}, catches contaminated={r_contam['verdict']=='LOOKAHEAD_DETECTED'})")
    sys.exit(0 if ok else 1)
