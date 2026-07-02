"""CHUNKED OI LOADER (T6 unlock) — pulls ES.OPT definition (id->strike/expiry/CP, once) + statistics MONTH-BY-MONTH,
filters to stat_type=9 (Open Interest) on ingest and DISCARDS the rest (avoids the 504 that killed the 5-month bulk pull).
Builds a compact daily OI-per-strike table. Report-only; cost recorded to data_budget.json. Run: python3 data/databento_gex_loader.py START END"""
import os, sys, json
from pathlib import Path
import pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab")
for l in (ROOT/".env").read_text().splitlines():
    if "=" in l and not l.strip().startswith("#"):
        k,v=l.split("=",1); os.environ.setdefault(k.strip(),v.strip())
import databento as db
c=db.Historical(os.getenv("DATABENTO_API_KEY")); DS="GLBX.MDP3"
START=sys.argv[1] if len(sys.argv)>1 else "2024-09-01"; END=sys.argv[2] if len(sys.argv)>2 else "2025-03-01"
OUT=ROOT/"data/databento"
months=pd.date_range(START,END,freq="MS")
# 1) definition once (id -> strike/expiry/CP)
print(f"pulling definition {START}..{END} ...")
dfd=c.timeseries.get_range(dataset=DS,symbols=["ES.OPT"],stype_in="parent",schema="definition",start=START,end=END).to_df()
idmap=dfd[dfd["instrument_class"].isin(["C","P"])][["instrument_id","raw_symbol","instrument_class","strike_price","expiration"]].drop_duplicates("instrument_id").set_index("instrument_id")
print(f"  definition: {len(idmap)} call/put instruments")
rows=[]; tot=0.0
for m in months:
    s=m.strftime("%Y-%m-%d"); e=(m+pd.offsets.MonthBegin(1)).strftime("%Y-%m-%d")
    try:
        cost=c.metadata.get_cost(dataset=DS,symbols=["ES.OPT"],stype_in="parent",schema="statistics",start=s,end=e); tot+=cost
        st=c.timeseries.get_range(dataset=DS,symbols=["ES.OPT"],stype_in="parent",schema="statistics",start=s,end=e).to_df()
        oi=st[st["stat_type"]==9]
        oi=oi.join(idmap,on="instrument_id",how="inner")
        oi["date"]=pd.to_datetime(oi["ts_ref"] if "ts_ref" in oi else oi.index,utc=True,errors="coerce").dt.tz_localize(None).dt.normalize()
        keep=oi[["date","strike_price","instrument_class","expiration","quantity"]].rename(columns={"quantity":"oi","instrument_class":"cp"})
        rows.append(keep); print(f"  {s}: {len(st)} stat rows -> {len(keep)} OI rows (${cost:.3f})")
    except Exception as ex: print(f"  {s}: ERR {type(ex).__name__} {str(ex)[:80]}")
if rows:
    allrows=pd.concat(rows,ignore_index=True); p=OUT/"ES_OPT_oi_daily.csv"; allrows.to_csv(p,index=False)
    print(f"SAVED {len(allrows)} daily OI rows -> {p.name} | dates {allrows['date'].min().date()}..{allrows['date'].max().date()} | ${tot:.2f}")
    b=json.loads((ROOT/"research/data/data_budget.json").read_text())
    b["pulls"].append({"date":f"{START}/{END}","asset":"ES.OPT","schemas":["definition","statistics-OI"],"cost_usd":round(tot,2),"path":"data/databento/ES_OPT_oi_daily.csv","purpose":"GEX-regime pin test","validation":"OI rows>0"})
    (ROOT/"research/data/data_budget.json").write_text(json.dumps(b,indent=2))
