"""UNIT TEST (R2) — assert day-d intraday signals cannot depend on day-d's session close.
Point-in-time invariant: perturbing the FINAL close of day d must NOT change any bar_trend / signal
on day d (or earlier); only day d+1 onward may respond to day d's close. Tests the daily-aggregate
trend filter (the leak site) and confirms the test is MEANINGFUL by showing it FAILS pre-fix.
Run: python3 research/test_no_lookahead_daily_filters.py  -> prints PASS/FAIL. Report-only."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
import research.crossbreeding.crossbreeding_engine as ce
# small slice for a fast deterministic test (enough history for 252-window + EMA warmup)
df=pd.read_csv(ROOT/"data/processed/MNQ_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
df=df.iloc[-16000:].reset_index(drop=True)
dates=df["datetime"].dt.normalize()
udays=sorted(dates.unique())
d=udays[len(udays)//2]                       # a day well past warmup, not the last day
d_next=udays[len(udays)//2+1]
day_d_mask=(dates==d).values; day_next_mask=(dates==d_next).values
last_bar_of_d=np.where(day_d_mask)[0][-1]    # final bar of day d (its session close)
def trend_for(frame):
    ce._FEATURE_CACHE.clear()   # cache key=(len,first_dt,last_dt) ignores close content -> must clear per perturbation
    f=ce.compute_features(frame)
    return np.asarray(f["bar_trend"])
def run_case(label, compute_features_fn):
    ce.compute_features=compute_features_fn
    hi=df.copy(); hi.loc[last_bar_of_d,"close"]=hi.loc[last_bar_of_d,"close"]*3.0   # day-d close forced UP
    lo=df.copy(); lo.loc[last_bar_of_d,"close"]=lo.loc[last_bar_of_d,"close"]*0.33  # day-d close forced DOWN
    bt_hi=trend_for(hi); bt_lo=trend_for(lo)
    changed_d=bool((bt_hi[day_d_mask]!=bt_lo[day_d_mask]).any())       # day-d trend must NOT depend on day-d close
    changed_next=bool((bt_hi[day_next_mask]!=bt_lo[day_next_mask]).any())  # day d+1 SHOULD respond (sanity)
    ok=(not changed_d)
    print(f"  [{label}] day-d trend differs across day-d close UP-vs-DOWN? {changed_d}  (day d+1 responds? {changed_next})  -> {'PASS' if ok else 'FAIL (lookahead!)'}")
    return ok
orig=ce.compute_features
print("=== R2 no-lookahead unit test (perturb day-d session close, check day-d trend) ===")
# 1) FIXED engine (current on-disk, shift applied)
ok_fixed=run_case("FIXED engine (on-disk)", orig)
# 2) reproduce PRE-FIX (un-shift) to prove the test catches the bug
def unshift_cf(frame,*a,**k):
    f=dict(orig(frame,*a,**k))
    dts=pd.to_datetime(f["dates"]).normalize(); bt=np.asarray(f["bar_trend"])
    # rebuild same-day (unshifted) trend from the daily close directly
    dd=pd.DataFrame({"d":dts,"c":f["close"]}).groupby("d")["c"].last()
    sl=dd.ewm(span=20,adjust=False).mean().diff()
    sign={dd_i:(0 if pd.isna(s) else (1 if s>0 else -1)) for dd_i,s in sl.items()}
    f["bar_trend"]=np.array([sign.get(x,0) for x in dts]); return f
ok_prefix_fails=not run_case("PRE-FIX (unshifted, expect FAIL)", unshift_cf)
ce.compute_features=orig
print(f"\n  RESULT: fixed-engine PASS={ok_fixed} ; pre-fix-correctly-FAILS={ok_prefix_fails}")
print("  OVERALL:", "PASS — invariant holds on fixed engine AND test catches the pre-fix leak" if (ok_fixed and ok_prefix_fails) else "FAIL — investigate")
sys.exit(0 if (ok_fixed and ok_prefix_fails) else 1)
