"""2023 GEX OI extension — EW1+EW2, 2023 months, INCREMENTAL SAVE per chunk, DONE marker on completion. Extends trade
sample to 2023 (index 1m already merged) for DSR power (n=77 -> target >=120). Bounded 2 attempts/chunk."""
import os,time,json
from pathlib import Path
import pandas as pd
R=Path("/Users/chasefisher/projects/Algo Trading/algo-lab")
for l in (R/".env").read_text().splitlines():
    if "=" in l and not l.strip().startswith("#"):
        k,v=l.split("=",1);os.environ.setdefault(k.strip(),v.strip())
import databento as db
c=db.Historical(os.getenv("DATABENTO_API_KEY")); DS="GLBX.MDP3"; OUT=R/"data/databento/ES_OPT_weekly_oi.csv"
months=[f"2023-{m:02d}-01" for m in range(1,13)]; ok=fail=0
for par in ["EW1.OPT","EW2.OPT"]:
  for s in months:
    e=(pd.Timestamp(s)+pd.offsets.MonthBegin(1)).strftime("%Y-%m-%d")
    for att in range(2):
        try:
            dfd=c.timeseries.get_range(dataset=DS,symbols=[par],stype_in="parent",schema="definition",start=s,end=e).to_df()
            idm=dfd[dfd["instrument_class"].isin(["C","P"])][["instrument_id","instrument_class","strike_price","expiration"]].drop_duplicates("instrument_id").set_index("instrument_id")
            st=c.timeseries.get_range(dataset=DS,symbols=[par],stype_in="parent",schema="statistics",start=s,end=e).to_df()
            oi=st[st["stat_type"]==9].join(idm,on="instrument_id",how="inner")
            oi["date"]=pd.to_datetime(oi["ts_ref"] if "ts_ref" in oi else oi.index,utc=True,errors="coerce").dt.tz_localize(None).dt.normalize()
            new=oi[["date","strike_price","instrument_class","expiration","quantity"]].rename(columns={"quantity":"oi","instrument_class":"cp"})
            cur=pd.read_csv(OUT,parse_dates=["date"]) if OUT.exists() else pd.DataFrame()
            a=pd.concat([cur,new],ignore_index=True) if len(cur) else new;a["date"]=pd.to_datetime(a["date"]);a=a.drop_duplicates(["date","strike_price","cp","expiration"])
            a.to_csv(OUT,index=False);ok+=1;print(f"  {par} {s[:7]}: +{len(new)} -> {a['date'].nunique()} days [SAVED]");break
        except Exception: time.sleep(3)
    else: fail+=1
a=pd.read_csv(OUT,parse_dates=["date"]);exp=pd.to_datetime(a["expiration"],utc=True,errors="coerce").dt.tz_localize(None);dte=(exp-a["date"]).dt.days
(R/"research/data/gex_oos_2023_DONE.json").write_text(json.dumps({"completed":time.strftime("%Y-%m-%d %H:%M"),"ok":ok,"fail":fail,"days":int(a['date'].nunique()),"le5dte_days":int(a[dte<=5]['date'].nunique()),"range":f"{a['date'].min().date()}..{a['date'].max().date()}"},indent=2))
print(f"2023 OI EXTEND DONE: ok={ok} fail={fail} total {a['date'].nunique()} days {a['date'].min().date()}..{a['date'].max().date()}")
