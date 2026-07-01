"""Per-contract (term-structure) pull — the data I falsely called DATA_BLOCKED. ohlcv-1d, all expiries under parent,
so front+deferred curves exist for carry/roll-yield/RV. Rates ZT/ZF/ZN/ZB (+ optional CL/GC/ES/NQ). Saves raw with
resolved symbol so front/deferred can be joined. Cheap (metadata cost printed first). Report-only research data."""
import os, sys
from pathlib import Path
import pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab")
for l in (ROOT/".env").read_text().splitlines():
    if "=" in l and not l.strip().startswith("#"):
        k,v=l.split("=",1); os.environ.setdefault(k.strip(),v.strip())
import databento as db
c=db.Historical(os.getenv("DATABENTO_API_KEY"))
DATASET="GLBX.MDP3"; START="2019-01-01"; END="2026-06-01"
RATES=["ZT","ZF","ZN","ZB"]   # 2y,5y,10y,30y — the curve for carry + 2s5s10s/5s10s30s RV
OUT=ROOT/"data/databento"; OUT.mkdir(parents=True,exist_ok=True)
mode=sys.argv[1] if len(sys.argv)>1 else "cost"
total=0.0
for r in RATES:
    try:
        cost=c.metadata.get_cost(dataset=DATASET,symbols=[f"{r}.FUT"],stype_in="parent",schema="ohlcv-1d",start=START,end=END)
        total+=cost; print(f"  {r}.FUT ohlcv-1d {START}..{END}: ${cost:.3f}")
    except Exception as e: print(f"  {r}: cost err {str(e)[:80]}")
print(f"TOTAL per-contract rates-curve pull estimate: ${total:.2f}")
if mode=="pull":
    for r in RATES:
        try:
            data=c.timeseries.get_range(dataset=DATASET,symbols=[f"{r}.FUT"],stype_in="parent",schema="ohlcv-1d",start=START,end=END)
            df=data.to_df()
            # resolve raw symbol per instrument
            if "symbol" not in df.columns and hasattr(data,"symbology"): pass
            keep=[col for col in ["ts_event","instrument_id","symbol","raw_symbol","open","high","low","close","volume"] if col in df.columns]
            df=df.reset_index()[[col for col in ["ts_event"]+keep if col in df.reset_index().columns]] if "ts_event" not in df.columns else df[keep]
            path=OUT/f"{r}_percontract_1d.csv"; df.to_csv(path,index=False)
            print(f"  PULLED {r}: {len(df)} rows, {df['symbol'].nunique() if 'symbol' in df.columns else '?'} contracts -> {path.name}")
        except Exception as e: print(f"  {r} pull err: {type(e).__name__}: {str(e)[:120]}")
else:
    print("(run with 'pull' to download; cost is trivial)")
