"""FOCUSED OOS GEX pull — EW1 only, OOS-critical months (2024 early + 2026), INCREMENTAL SAVE per chunk (no limbo, visible
progress, partials always persisted). Bounded 2 attempts/chunk."""
import os,time
from pathlib import Path
import pandas as pd
R=Path("/Users/chasefisher/projects/Algo Trading/algo-lab")
for l in (R/".env").read_text().splitlines():
    if "=" in l and not l.strip().startswith("#"):
        k,v=l.split("=",1);os.environ.setdefault(k.strip(),v.strip())
import databento as db
c=db.Historical(os.getenv("DATABENTO_API_KEY")); DS="GLBX.MDP3"; OUT=R/"data/databento/ES_OPT_weekly_oi.csv"
months=["2024-03-01","2024-04-01","2024-05-01","2024-06-01","2024-07-01","2024-08-01","2024-09-01","2026-01-01","2026-02-01"]
for s in months:
    e=(pd.Timestamp(s)+pd.offsets.MonthBegin(1)).strftime("%Y-%m-%d")
    for att in range(2):
        try:
            dfd=c.timeseries.get_range(dataset=DS,symbols=["EW1.OPT"],stype_in="parent",schema="definition",start=s,end=e).to_df()
            idm=dfd[dfd["instrument_class"].isin(["C","P"])][["instrument_id","instrument_class","strike_price","expiration"]].drop_duplicates("instrument_id").set_index("instrument_id")
            st=c.timeseries.get_range(dataset=DS,symbols=["EW1.OPT"],stype_in="parent",schema="statistics",start=s,end=e).to_df()
            oi=st[st["stat_type"]==9].join(idm,on="instrument_id",how="inner")
            oi["date"]=pd.to_datetime(oi["ts_ref"] if "ts_ref" in oi else oi.index,utc=True,errors="coerce").dt.tz_localize(None).dt.normalize()
            new=oi[["date","strike_price","instrument_class","expiration","quantity"]].rename(columns={"quantity":"oi","instrument_class":"cp"})
            cur=pd.read_csv(OUT,parse_dates=["date"]) if OUT.exists() else pd.DataFrame()
            a=pd.concat([cur,new],ignore_index=True) if len(cur) else new
            a["date"]=pd.to_datetime(a["date"]);a=a.drop_duplicates(["date","strike_price","cp","expiration"])
            a.to_csv(OUT,index=False)   # INCREMENTAL SAVE per chunk
            print(f"  {s[:7]}: +{len(new)} rows -> total {a['date'].nunique()} days [SAVED]"); break
        except Exception: time.sleep(3)
    else: print(f"  {s[:7]}: FAIL (2 att)")
print("FOCUSED OOS done")
