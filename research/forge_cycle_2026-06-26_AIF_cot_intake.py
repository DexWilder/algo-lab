"""ALPHA_INTAKE_FACTORY — CFTC COT positioning intake + strict test (report-only, NEW DATA VEIN).
Legacy futures-only (commercials vs non-commercials). STRICT per operator:
- timing: positions as-of Tuesday, released Friday -> signal effective next Monday (report_date+6d); NO same-week leakage.
- participant classes separated: non-comm (specs) net, comm (hedgers) net; percentile-ranked (156wk).
- BOTH sides separate: crowded-long-unwind AND crowded-short-squeeze (one good side must NOT hide a bad side).
- per INSTRUMENT before pooling. predeclared horizons 1/2/4 weeks (all counted toward N).
- causality (lag), cost, H1/H2, per-year, side+instrument contribution, concentration, DSR-at-full-N.
Verdicts: CLEAN_KILL/DATA_LIMITED/CLEAN_BUT_WEAK/RETEST_REQUIRED/SCREEN_PASS. No WH/validated/primary/candidate."""
import sys, json, urllib.request, urllib.parse
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(ROOT))
from engine.asset_config import get_asset
BASE="https://publicreporting.cftc.gov/resource/6dca-aqww.json"
NF="market_and_exchange_names"
# instrument -> (CFTC market name, our futures csv asset, dirty_flag)
MAP={
 "Gold":("GOLD - COMMODITY EXCHANGE INC.","MGC",False),
 "10yrNote":("10-YEAR U.S. TREASURY NOTES - CHICAGO BOARD OF TRADE","ZN",False),
 "EuroFX":("EURO FX - CHICAGO MERCANTILE EXCHANGE","6E",False),
 "Yen":("JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE","6J",False),
 "Pound":("BRITISH POUND - CHICAGO MERCANTILE EXCHANGE","6B",False),
 "SP500":("E-MINI S&P 500 STOCK INDEX - CHICAGO MERCANTILE EXCHANGE","MES",False),
 "Nasdaq":("NASDAQ-100 STOCK INDEX (MINI) - CHICAGO MERCANTILE EXCHANGE","MNQ",False),
 "Crude":("CRUDE OIL, LIGHT SWEET - NEW YORK MERCANTILE EXCHANGE","MCL",True),
}
def fetch_cot(market):
    q=BASE+"?$where="+urllib.parse.quote(f"{NF}='{market}'")+"&$limit=2000&$order=report_date_as_yyyy_mm_dd"
    r=urllib.request.urlopen(urllib.request.Request(q,headers={"User-Agent":"Mozilla/5.0"}),timeout=30)
    d=json.loads(r.read())
    if not d: return None
    df=pd.DataFrame(d)
    dt=pd.to_datetime(df["report_date_as_yyyy_mm_dd"])
    for c in ["noncomm_positions_long_all","noncomm_positions_short_all","comm_positions_long_all","comm_positions_short_all","open_interest_all"]:
        df[c]=pd.to_numeric(df[c],errors="coerce")
    out=pd.DataFrame({"report_date":dt,
        "spec_net":df["noncomm_positions_long_all"]-df["noncomm_positions_short_all"],
        "comm_net":df["comm_positions_long_all"]-df["comm_positions_short_all"],
        "oi":df["open_interest_all"]}).dropna().sort_values("report_date")
    return out
def daily_close(asset):
    df=pd.read_csv(ROOT/f"data/processed/{asset}_5m.csv"); df["datetime"]=pd.to_datetime(df["datetime"])
    return df.assign(d=df["datetime"].dt.normalize()).groupby("d")["close"].last()
def shp(x): x=np.asarray(x,float); return round(x.mean()/x.std()*np.sqrt(52),2) if len(x)>1 and x.std()>0 else 0  # weekly ann
print("=== CFTC COT positioning intake + strict test (legacy futures-only) ===")
print("timing: Tue positions, Fri release -> signal effective report_date+6d (next Mon). spec_net %ile over 156wk.")
results=[]
for label,(market,asset,dirty) in MAP.items():
    cot=fetch_cot(market)
    if cot is None or len(cot)<160:
        print(f"\n[{label}/{asset}] DATA_LIMITED (cot rows={0 if cot is None else len(cot)})"); continue
    cot["spec_pct"]=cot["spec_net"].rolling(156,min_periods=104).apply(lambda x:(x.iloc[-1]>=x).mean(),raw=False)
    cot["eff_date"]=cot["report_date"]+pd.Timedelta(days=6)  # next Monday — no same-week leakage
    cot=cot.dropna(subset=["spec_pct"])
    # weekly forward returns of OUR futures, aligned to eff_date
    px=daily_close(asset)
    # for each eff_date, entry = first px on/after eff_date; fwd returns 1/2/4 weeks
    pxw=px.resample("W-FRI").last().dropna()  # weekly price
    sig=cot.set_index("eff_date")["spec_pct"].reindex(pxw.index, method="ffill")
    fwd={h: (pxw.shift(-h)/pxw-1.0) for h in [1,2,4]}
    n=int(sig.notna().sum())
    row={"label":label,"asset":asset,"dirty":dirty,"n_weeks":n}
    for side,mask_name in [("crowded_long",sig>0.9),("crowded_short",sig<0.1)]:
        for h in [1,2,4]:
            m=mask_name & fwd[h].notna()
            fr=fwd[h][m]
            # crowded_long -> predict DOWN (fade): edge = -mean(fwd); crowded_short -> predict UP: edge=+mean(fwd)
            sgn=-1 if side=="crowded_long" else 1
            edge=sgn*fr.mean() if len(fr)>3 else np.nan
            row[f"{side}_{h}w_n"]=len(fr); row[f"{side}_{h}w_edge%"]=round(edge*100,2) if not np.isnan(edge) else None
    results.append((row,sig,pxw,fwd,asset))
    print(f"\n[{label}/{asset}] cot_weeks={len(cot)} aligned_weeks={n}{' (DIRTY return data)' if dirty else ''}")
    for side in ["crowded_long","crowded_short"]:
        print(f"   {side:13s}: "+"  ".join(f"{h}w n={row[f'{side}_{h}w_n']} edge={row[f'{side}_{h}w_edge%']}%" for h in [1,2,4]))
print("\n=== both-sides read: a real signal needs BOTH crowded-long-fade AND crowded-short-squeeze positive, not one-sided ===")
print("(positive edge% = positioning-reversal predicts price in the faded direction. Per-instrument; pooling/DSR next step if any side-consistent.)")
