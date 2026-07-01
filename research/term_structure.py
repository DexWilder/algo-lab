"""Term-structure loader for per-contract Databento data (rates ZT/ZF/ZN/ZB, commodities CL/GC).
Filters outrights (drops UD: spreads), parses expiry from month-code+year, builds per-date front(F1)/F2/F3 panel
for roll-yield / carry / curve RV. Reusable by FOUNDATION_LOCK data-quality + the strategy sprint."""
import re
from pathlib import Path
import pandas as pd, numpy as np
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab")
MC={"F":1,"G":2,"H":3,"J":4,"K":5,"M":6,"N":7,"Q":8,"U":9,"V":10,"X":11,"Z":12}
def _expiry(sym, root):
    m=re.match(rf"^{root}([FGHJKMNQUVXZ])(\d)$", sym)
    if not m: return None
    mon=MC[m.group(1)]; d=int(m.group(2)); yr=2019 if d==9 else 2020+d
    return pd.Timestamp(yr, mon, 15)   # ~mid-month proxy for ordering
def load_outrights(root):
    f=ROOT/f"data/databento/{root}_percontract_1d.csv"
    df=pd.read_csv(f)
    dc="ts_event" if "ts_event" in df.columns else ("index" if "index" in df.columns else df.columns[0])
    df["date"]=pd.to_datetime(df[dc],utc=True,errors="coerce").dt.tz_localize(None).dt.normalize()
    df=df[df["symbol"].str.match(rf"^{root}[FGHJKMNQUVXZ]\d$", na=False)].copy()
    df["expiry"]=df["symbol"].map(lambda s:_expiry(s,root))
    df=df.dropna(subset=["expiry"])
    return df
def build_curve(root):
    """Per-date front F1/F2/F3 close (nearest un-expired outrights by expiry). Returns DataFrame indexed by date."""
    df=load_outrights(root)
    rows=[]
    for dt,g in df.groupby("date"):
        live=g[g["expiry"]>=dt].sort_values("expiry")
        if len(live)<2: continue
        r={"date":dt,"F1":live.iloc[0]["close"],"F1sym":live.iloc[0]["symbol"],"exp1":live.iloc[0]["expiry"],
           "F2":live.iloc[1]["close"],"F2sym":live.iloc[1]["symbol"]}
        if len(live)>=3: r["F3"]=live.iloc[2]["close"]
        rows.append(r)
    c=pd.DataFrame(rows).set_index("date").sort_index()
    return c
def quality(root):
    df=pd.read_csv(ROOT/f"data/databento/{root}_percontract_1d.csv")
    allc=df["symbol"].nunique(); out=load_outrights(root); curve=build_curve(root)
    dc="ts_event" if "ts_event" in df.columns else df.columns[0]
    dts=pd.to_datetime(df[dc],utc=True,errors="coerce").dt.tz_localize(None).dt.normalize()
    return dict(root=root, rows=len(df), all_symbols=allc, outright_contracts=out["symbol"].nunique(),
               date_min=str(dts.min().date()), date_max=str(dts.max().date()),
               dupes=int(df.duplicated(subset=["ts_event","symbol"]).sum()),
               days_with_F1F2=len(curve), days_with_F3=int(curve["F3"].notna().sum()) if "F3" in curve else 0)
if __name__=="__main__":
    for r in ["ZT","ZF","ZN","ZB","CL","GC"]:
        try: q=quality(r); print(f"  {r}: rows={q['rows']} allSym={q['all_symbols']} outrights={q['outright_contracts']} {q['date_min']}..{q['date_max']} dupes={q['dupes']} F1F2days={q['days_with_F1F2']} F3days={q['days_with_F3']}")
        except Exception as e: print(f"  {r}: ERR {type(e).__name__} {str(e)[:80]}")
