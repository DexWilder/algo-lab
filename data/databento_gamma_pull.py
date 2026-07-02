"""GAMMA/OI feasibility SAMPLE pull (T6 unlock, operator-approved <=$25). Cost-check first; pull a SMALL sample (definition
=strikes/expiries/C-P + statistics OI) for ES options to prove OI/GEX is computable. No full history (that 504-timed-out ->
needs chunked loader). Records cost/schema/path/validation/purpose to data_budget.json. Report-only."""
import os, sys, json
from pathlib import Path
import pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab")
for l in (ROOT/".env").read_text().splitlines():
    if "=" in l and not l.strip().startswith("#"):
        k,v=l.split("=",1); os.environ.setdefault(k.strip(),v.strip())
import databento as db
c=db.Historical(os.getenv("DATABENTO_API_KEY"))
DS="GLBX.MDP3"; START="2025-06-02"; END="2025-06-07"  # 1 week sample
OUT=ROOT/"data/databento"; mode=sys.argv[1] if len(sys.argv)>1 else "cost"
tot=0.0; costs={}
for schema in ["definition","statistics"]:
    try:
        cost=c.metadata.get_cost(dataset=DS,symbols=["ES.OPT"],stype_in="parent",schema=schema,start=START,end=END)
        costs[schema]=cost; tot+=cost; print(f"  ES.OPT {schema} {START}..{END}: ${cost:.3f}")
    except Exception as e: print(f"  {schema} cost err: {str(e)[:80]}")
print(f"TOTAL gamma sample cost: ${tot:.2f} (auto-approve cap $25)")
if mode=="pull" and tot<=25:
    for schema in ["definition","statistics"]:
        try:
            data=c.timeseries.get_range(dataset=DS,symbols=["ES.OPT"],stype_in="parent",schema=schema,start=START,end=END)
            df=data.to_df(); p=OUT/f"ES_OPT_{schema}_sample.csv"; df.to_csv(p); print(f"  PULLED {schema}: {len(df)} rows -> {p.name} | cols: {list(df.columns)[:12]}")
        except Exception as e: print(f"  {schema} pull err: {type(e).__name__}: {str(e)[:120]}")
    # record to budget
    b=json.loads((ROOT/"research/data/data_budget.json").read_text()); b["pulls"].append(
        {"date":"2025-06-02/07-sample","asset":"ES.OPT","schemas":["definition","statistics"],"cost_usd":round(tot,2),
         "path":"data/databento/ES_OPT_*_sample.csv","purpose":"GEX feasibility memo","validation":"pending"})
    (ROOT/"research/data/data_budget.json").write_text(json.dumps(b,indent=2))
elif mode=="pull": print(f"  BLOCKED: ${tot:.2f} > $25 auto cap — ask operator.")
else: print("(run 'pull' to download if <=$25)")
