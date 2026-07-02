"""Weekly/0DTE ES option OI pull (the RIGHT data for the GEX pin mechanism, which lives at expiry). Parents EW1-4 (Fri
weeklies) + E1A/E3C (Mon/Wed 0DTE). Filters stat_type=9 OI, joins definition for strike/expiry/CP. Chunked monthly + retries."""
import os,sys,json,time
from pathlib import Path
import pandas as pd
R=Path("/Users/chasefisher/projects/Algo Trading/algo-lab")
for l in (R/".env").read_text().splitlines():
    if "=" in l and not l.strip().startswith("#"):
        k,v=l.split("=",1); os.environ.setdefault(k.strip(),v.strip())
import databento as db
c=db.Historical(os.getenv("DATABENTO_API_KEY")); DS="GLBX.MDP3"
PARENTS=["EW1.OPT","EW2.OPT","EW3.OPT","EW4.OPT","E1A.OPT","E3C.OPT"]
START,END=sys.argv[1],sys.argv[2]; months=pd.date_range(START,END,freq="MS")
rows=[]; tot=0.0
for par in PARENTS:
    try:
        dfd=c.timeseries.get_range(dataset=DS,symbols=[par],stype_in="parent",schema="definition",start=START,end=END).to_df()
        idmap=dfd[dfd["instrument_class"].isin(["C","P"])][["instrument_id","instrument_class","strike_price","expiration"]].drop_duplicates("instrument_id").set_index("instrument_id")
    except Exception as e: print(f"  {par} def err {str(e)[:50]}"); continue
    for m in months:
        s=m.strftime("%Y-%m-%d"); e=(m+pd.offsets.MonthBegin(1)).strftime("%Y-%m-%d")
        for att in range(3):
            try:
                cost=c.metadata.get_cost(dataset=DS,symbols=[par],stype_in="parent",schema="statistics",start=s,end=e); 
                st=c.timeseries.get_range(dataset=DS,symbols=[par],stype_in="parent",schema="statistics",start=s,end=e).to_df()
                oi=st[st["stat_type"]==9].join(idmap,on="instrument_id",how="inner")
                oi["date"]=pd.to_datetime(oi["ts_ref"] if "ts_ref" in oi else oi.index,utc=True,errors="coerce").dt.tz_localize(None).dt.normalize()
                rows.append(oi[["date","strike_price","instrument_class","expiration","quantity"]].rename(columns={"quantity":"oi","instrument_class":"cp"}))
                tot+=cost; print(f"  {par} {s}: {len(oi)} OI rows"); break
            except Exception as ex: print(f"  {par} {s} att{att}: {type(ex).__name__}"); time.sleep(2)
if rows:
    a=pd.concat(rows,ignore_index=True); a["date"]=pd.to_datetime(a["date"]); a=a.drop_duplicates(["date","strike_price","cp","expiration"])
    p=R/"data/databento/ES_OPT_weekly_oi.csv"; a.to_csv(p,index=False)
    exp=pd.to_datetime(a["expiration"],utc=True,errors="coerce").dt.tz_localize(None); dte=(exp-a["date"]).dt.days
    print(f"SAVED {len(a)} weekly-OI rows | days {a['date'].nunique()} | DTE<3: {int((dte<3).sum())} rows | ${tot:.2f}")
