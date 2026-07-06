"""OOS GEX coverage extension — bounded (2 attempts/chunk), append-merge, targets early-2024 + late-2025 + 2026 to test if
the frozen rule holds OUTSIDE 2025. Single-slice per policy; no thrash."""
import os,time
from pathlib import Path
import pandas as pd
R=Path("/Users/chasefisher/projects/Algo Trading/algo-lab")
for l in (R/".env").read_text().splitlines():
    if "=" in l and not l.strip().startswith("#"):
        k,v=l.split("=",1);os.environ.setdefault(k.strip(),v.strip())
import databento as db
c=db.Historical(os.getenv("DATABENTO_API_KEY")); DS="GLBX.MDP3"
OUT=R/"data/databento/ES_OPT_weekly_oi.csv"
rows=[pd.read_csv(OUT,parse_dates=["date"])] if OUT.exists() else []
months=[f"2024-{m:02d}-01" for m in range(1,11)]+[f"2025-{m:02d}-01" for m in range(5,13)]+[f"2026-{m:02d}-01" for m in range(1,4)]
ok=fail=0
for par in ["EW1.OPT","EW2.OPT"]:
  for i,s in enumerate(months):
    e=(pd.Timestamp(s)+pd.offsets.MonthBegin(1)).strftime("%Y-%m-%d")
    done=False
    for att in range(2):
        try:
            dfd=c.timeseries.get_range(dataset=DS,symbols=[par],stype_in="parent",schema="definition",start=s,end=e).to_df()
            idm=dfd[dfd["instrument_class"].isin(["C","P"])][["instrument_id","instrument_class","strike_price","expiration"]].drop_duplicates("instrument_id").set_index("instrument_id")
            st=c.timeseries.get_range(dataset=DS,symbols=[par],stype_in="parent",schema="statistics",start=s,end=e).to_df()
            oi=st[st["stat_type"]==9].join(idm,on="instrument_id",how="inner")
            oi["date"]=pd.to_datetime(oi["ts_ref"] if "ts_ref" in oi else oi.index,utc=True,errors="coerce").dt.tz_localize(None).dt.normalize()
            rows.append(oi[["date","strike_price","instrument_class","expiration","quantity"]].rename(columns={"quantity":"oi","instrument_class":"cp"}))
            ok+=1;done=True;break
        except Exception: time.sleep(3)
    if not done: fail+=1
a=pd.concat(rows,ignore_index=True);a["date"]=pd.to_datetime(a["date"]);a=a.drop_duplicates(["date","strike_price","cp","expiration"])
a.to_csv(OUT,index=False)
exp=pd.to_datetime(a["expiration"],utc=True,errors="coerce").dt.tz_localize(None);dte=(exp-a["date"]).dt.days
print(f"OOS EXTEND: ok={ok} fail={fail} | total {a['date'].nunique()} days {a['date'].min().date()}..{a['date'].max().date()} | <=5DTE {a[dte<=5]['date'].nunique()} days")
