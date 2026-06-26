"""TRUTH_RESET item 5 — causality audit of the 5 non-ORB probation books (report-only).
Point the universal harness at each strategy's generate_signals. Future-perturbation invariance catches any
same-day/future leak automatically (these build daily aggregates via groupby(date).agg -> prime leak site).
Classify each: CAUSAL_CLEAN vs LOOKAHEAD_DETECTED vs HARNESS_INCOMPATIBLE(needs bespoke audit). Capital gate unchanged."""
import sys, importlib.util, traceback
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from research.causality_audit import audit_signal_causality
BOOKS=[("zn_afternoon_reversion","ZN"),("treasury_rolldown_carry","ZN"),("nfp_level_breakout","MNQ"),
       ("vol_managed_equity","MES"),("fx_daily_trend","MGC")]
def load_gen(name):
    spec=importlib.util.spec_from_file_location(f"strat_{name}", ROOT/f"strategies/{name}/strategy.py")
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m.generate_signals
def prep(asset):
    df=pd.read_csv(ROOT/f"data/processed/{asset}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
    df=df.iloc[-16000:].reset_index(drop=True)
    df["date"]=df["datetime"].dt.date   # several modules group by 'date'
    return df
def make_sigfn(gen, asset):
    def f(frame):
        fr=frame.copy(); fr["date"]=pd.to_datetime(fr["datetime"]).dt.date
        for call in (lambda: gen(fr), lambda: gen(fr, asset=asset), lambda: gen(fr, asset), lambda: gen(fr, mode="both")):
            try: out=call(); break
            except TypeError: out=None
        if out is None: out=gen(fr)
        if isinstance(out, pd.DataFrame):
            col="signal" if "signal" in out.columns else next((c for c in out.columns if "signal" in c.lower()), None)
            if col is None: raise ValueError(f"no signal column in {list(out.columns)}")
            s=out[[col]].rename(columns={col:"signal"})
            if len(s)!=len(frame): s=s.reindex(range(len(frame))).fillna(0)
            return s.reset_index(drop=True)
        raise ValueError(f"generate_signals returned {type(out)}")
    return f
print("=== TR5 non-ORB probation books — causality audit ===")
results={}
for name, asset in BOOKS:
    print(f"\n--- {name} ({asset}) ---")
    try:
        gen=load_gen(name); df=prep(asset); sigfn=make_sigfn(gen, asset)
        probe=sigfn(df)  # smoke test
        nz=int((probe["signal"]!=0).sum())
        print(f"    signal smoke: {nz} nonzero signals / {len(probe)} bars")
        r=audit_signal_causality(df, sigfn, name, n_splits=8)
        results[name]=r["verdict"]
    except Exception as e:
        print(f"    HARNESS_INCOMPATIBLE: {type(e).__name__}: {e}")
        results[name]="HARNESS_INCOMPATIBLE (needs bespoke audit)"
print("\n=== SUMMARY ===")
for name,_ in BOOKS: print(f"  {name:26s} -> {results.get(name,'?')}")
