"""POST-PULL DATA VALIDATOR (2026-07-01). Catches the CL/GC date-column-dropped bug class. Every new Databento pull
must pass before 'usable'. Call validate_data_file(path, needs_symbol=True)."""
import sys, pandas as pd
from pathlib import Path
def validate_data_file(path, needs_symbol=True, needs_volume=False):
    p=Path(path); flags=[]
    if not p.exists(): return False, [f"MISSING {path}"]
    df=pd.read_csv(p)
    datecol=next((c for c in df.columns if c.lower() in ("ts_event","date","datetime","day","index") or "time" in c.lower()), None)
    if datecol is None: flags.append("NO_DATE_COLUMN")
    else:
        dts=pd.to_datetime(df[datecol],utc=True,errors="coerce")
        if dts.isna().mean()>0.5: flags.append(f"DATE_UNPARSEABLE ({datecol})")
    if needs_symbol and "symbol" not in df.columns: flags.append("NO_SYMBOL_COLUMN")
    if not any(c in df.columns for c in ("close","last","settle","px")): flags.append("NO_PRICE_COLUMN")
    if needs_volume and "volume" not in df.columns: flags.append("NO_VOLUME")
    if len(df)<50: flags.append(f"TOO_FEW_ROWS {len(df)}")
    if datecol and "symbol" in df.columns:
        d=int(df.duplicated(subset=[datecol,"symbol"]).sum())
        if d>0: flags.append(f"DUP_ROWS {d}")
    ok=not any(f.split()[0] in ("MISSING","NO_DATE_COLUMN","NO_PRICE_COLUMN","DATE_UNPARSEABLE") for f in flags)
    return ok, flags
if __name__=="__main__":
    import glob
    for f in glob.glob("data/databento/*_percontract_1d.csv"):
        ok,flags=validate_data_file(f)
        print(f"  {Path(f).name}: {'PASS' if ok else 'FAIL'} {flags if flags else ''}")
