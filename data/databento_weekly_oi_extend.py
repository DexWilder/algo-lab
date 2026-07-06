"""Extend weekly ES-option OI coverage (gates the signed-GEX compression retest). Per retry policy: single-parent/single-month,
4x backoff, MERGE with existing file (never overwrite/lose partials). EW1-4 across a wider window for a proper n>=60."""
import os,sys,time
from pathlib import Path
import pandas as pd
R=Path("/Users/chasefisher/projects/Algo Trading/algo-lab")
for l in (R/".env").read_text().splitlines():
    if "=" in l and not l.strip().startswith("#"):
        k,v=l.split("=",1); os.environ.setdefault(k.strip(),v.strip())
import databento as db
c=db.Historical(os.getenv("DATABENTO_API_KEY")); DS="GLBX.MDP3"
OUT=R/"data/databento/ES_OPT_weekly_oi.csv"
existing=pd.read_csv(OUT,parse_dates=["date"]) if OUT.exists() else pd.DataFrame()
rows=[existing] if len(existing) else []
months=pd.date_range("2024-09-01","2025-06-01",freq="MS")
ok=fail=0
for par in ["EW1.OPT","EW2.OPT","EW3.OPT","EW4.OPT"]:
    for m in months:
        s=m.strftime("%Y-%m-%d"); e=(m+pd.offsets.MonthBegin(1)).strftime("%Y-%m-%d")
        for att in range(4):
            try:
                dfd=c.timeseries.get_range(dataset=DS,symbols=[par],stype_in="parent",schema="definition",start=s,end=e).to_df()
                idm=dfd[dfd["instrument_class"].isin(["C","P"])][["instrument_id","instrument_class","strike_price","expiration"]].drop_duplicates("instrument_id").set_index("instrument_id")
                st=c.timeseries.get_range(dataset=DS,symbols=[par],stype_in="parent",schema="statistics",start=s,end=e).to_df()
                oi=st[st["stat_type"]==9].join(idm,on="instrument_id",how="inner")
                oi["date"]=pd.to_datetime(oi["ts_ref"] if "ts_ref" in oi else oi.index,utc=True,errors="coerce").dt.tz_localize(None).dt.normalize()
                rows.append(oi[["date","strike_price","instrument_class","expiration","quantity"]].rename(columns={"quantity":"oi","instrument_class":"cp"}))
                ok+=1; break
            except Exception: time.sleep(2*(att+1))
        else: fail+=1
a=pd.concat(rows,ignore_index=True); a["date"]=pd.to_datetime(a["date"]); a=a.drop_duplicates(["date","strike_price","cp","expiration"])
a.to_csv(OUT,index=False)
exp=pd.to_datetime(a["expiration"],utc=True,errors="coerce").dt.tz_localize(None); dte=(exp-a["date"]).dt.days
print(f"EXTEND done: chunks ok={ok} fail={fail} | total {len(a)} rows, {a['date'].nunique()} days, {a[dte<=5]['date'].nunique()} days<=5DTE | {a['date'].min().date()}..{a['date'].max().date()}")
