"""BATCH-SCREEN ENGINE — the high-throughput discovery funnel (VC model: manufacture hundreds, most die instantly = success).
Generates mechanism x instrument x param grids, runs each as a CAUSAL cheap screen on daily bars, records ALL to the trial
ledger (honest multiple-testing N), then DEDUPS survivors by return-correlation (keep only orthogonal return streams).
Deep validation is reserved for the few survivors. Run: python3 research/forge_batch_screen.py [instr ...]"""
import sys; from pathlib import Path; import numpy as np, pandas as pd
R=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(R))
from research.forge_trial_ledger import record, count
INSTR=["MES","MNQ","MYM","M2K","MGC","MCL","ZN","ZF","ZB","6E","6J","6B"]
def shp(x): x=np.asarray(x,float); return x.mean()/x.std()*np.sqrt(252) if len(x)>2 and x.std()>0 else 0.0
def pf(x): x=np.asarray(x,float); g=x[x>0].sum(); l=-x[x<0].sum(); return g/l if l>0 else 99.0
def daily(sym):
    df=pd.read_csv(R/f"data/databento/{sym}_1m.csv",parse_dates=["datetime"]).set_index("datetime")
    g=df.resample("1D").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    g=g[g["volume"]>0]; g["ret"]=g["close"].diff(); g["pret"]=g["close"].pct_change(); return g
FAMILIES=["momentum","meanrev","breakout","gap","vol_conditioned","calendar","channel","acceleration","vol_state","realvol"]
def mechanisms(g):
    """causal position generators across MANY families -> dict name: position series (to be shift(1)'d).
    NOTE: this is ONE generator; a null here means THIS generator found nothing, NOT that the domain is dead."""
    out={}; c=g["close"]; r=g["pret"]; gap=g["open"]-c.shift(1); hi=g["high"]; lo=g["low"]; vol=g["volume"]
    volz=(vol-vol.rolling(60,min_periods=20).mean())/vol.rolling(60,min_periods=20).std()
    rv=r.rolling(20).std(); rvz=(rv-rv.rolling(120,min_periods=40).mean())/rv.rolling(120,min_periods=40).std()  # realized-vol state
    for N in [1,2,3,5,10,20]:
        out[f"momentum_mom{N}"]=np.sign(c-c.shift(N)); out[f"meanrev_mr{N}"]=-np.sign(c-c.shift(N))
        rz=(r-r.rolling(60,min_periods=20).mean())/r.rolling(60,min_periods=20).std()
        out[f"meanrev_mrX{N}"]=(-np.sign(c-c.shift(N))).where(rz.abs()>1.5,0.0)
        out[f"acceleration_acc{N}"]=np.sign((c-c.shift(N))-(c.shift(N)-c.shift(2*N)))  # momentum-of-momentum
    for N in [5,10,20,40]:
        out[f"breakout_brk{N}"]=np.where(c>hi.rolling(N).max().shift(1),1,np.where(c<lo.rolling(N).min().shift(1),-1,0))
        ch=(c-lo.rolling(N).min())/(hi.rolling(N).max()-lo.rolling(N).min())  # position in channel 0..1
        out[f"channel_pos{N}"]=(2*ch-1).clip(-1,1)                    # continuous: high-in-range=long
        out[f"channel_fade{N}"]=-(2*ch-1).clip(-1,1)                  # fade channel extremes
    out["gap_fade"]=-np.sign(gap); out["gap_follow"]=np.sign(gap)
    for N in [3,5,10]:
        out[f"vol_conditioned_vmom{N}"]=(np.sign(c-c.shift(N))).where(volz>0.5,0.0)
        out[f"vol_conditioned_vmr{N}"]=(-np.sign(c-c.shift(N))).where(volz>0.5,0.0)
        # vol-STATE conditioning: momentum in low-realvol, mean-rev in high-realvol
        out[f"vol_state_lowvolmom{N}"]=(np.sign(c-c.shift(N))).where(rvz<-0.3,0.0)
        out[f"vol_state_hivolmr{N}"]=(-np.sign(c-c.shift(N))).where(rvz>0.5,0.0)
    dom=g.index.day; dow=g.index.dayofweek
    out["calendar_turnofmonth"]=pd.Series(np.where((dom<=2)|(dom>=27),1,0),index=g.index)
    out["calendar_midmonth_fade"]=pd.Series(np.where((dom>=13)&(dom<=17),-np.sign(r.shift(1)).fillna(0),0),index=g.index)
    for d in range(5): out[f"calendar_dow{d}"]=pd.Series(np.where(dow==d,1,0),index=g.index)
    out["realvol_expansion"]=np.sign(r).where(rvz>1.0,0.0)  # follow moves when realvol expanding
    return {k:(pd.Series(v,index=g.index) if not isinstance(v,pd.Series) else v) for k,v in out.items()}
def cross_sectional(dailies):
    """cross-sectional RV/momentum across a pooled group (a DIFFERENT family than single-instrument)."""
    out={}
    if len(dailies)<3: return out
    px=pd.DataFrame({s:g["pret"] for s,g in dailies.items()}).dropna(how="all")
    for N in [5,20,60]:
        mom=px.rolling(N).sum()
        rank=mom.rank(axis=1,pct=True)  # cross-sectional momentum rank
        # long top-third / short bottom-third, next-day pooled return (avg across the L/S book)
        w=(rank>0.66).astype(float)-(rank<0.34).astype(float)
        pnl=(w.shift(1)*px).mean(axis=1).dropna()
        out[f"xsec_mom{N}"]=pnl
        out[f"xsec_rev{N}"]=(-w.shift(1)*px).mean(axis=1).dropna()
    return out
def run(instr):
    survivors=[]; n_screen=0; fams=set(); dailies={}
    for sym in instr:
        try: g=daily(sym); dailies[sym]=g
        except Exception: print(f"  {sym}: no data"); continue
        if len(g)<250: continue
        mechs=mechanisms(g); rng=g["ret"]
        for name,pos in mechs.items():
            pnl=(pos.shift(1)*rng).dropna(); n_screen+=1; fams.add(name.split("_")[0])
            if len(pnl)<200: continue
            s=shp(pnl.values); yr=pnl.groupby(pnl.index.year).sum(); my=100*yr.max()/yr.sum() if yr.sum()>0 else 999
            p=pf(pnl.values); act=int((pos.shift(1).reindex(pnl.index).fillna(0)!=0).sum())
            record(f"BATCH:{name}:{sym}",asset=sym,sharpe=round(s,2),verdict="batch_screen",lane="batch_screen",maxyr=round(my),n=len(pnl))
            if s>0.5 and p>1.05 and my<50 and act>150:
                survivors.append(dict(key=f"{name}:{sym}",sym=sym,mech=name,sh=round(s,2),pf=round(p,2),maxyr=round(my),n=len(pnl),ret=pnl))
    # cross-sectional families (pooled groups — a different family)
    for gname,members in [("EQ",["MES","MNQ","MYM","M2K"]),("RATES",["ZN","ZF","ZB"]),("FX",["6E","6J","6B"])]:
        grp={s:dailies[s] for s in members if s in dailies}
        for name,pnl in cross_sectional(grp).items():
            n_screen+=1; fams.add("xsec")
            if len(pnl)<200: continue
            s=shp(pnl.values); yr=pnl.groupby(pnl.index.year).sum(); my=100*yr.max()/yr.sum() if yr.sum()>0 else 999; p=pf(pnl.values)
            record(f"BATCH:{name}:{gname}",asset=gname,sharpe=round(s,2),verdict="batch_screen",lane="batch_screen",maxyr=round(my),n=len(pnl))
            if s>0.5 and p>1.05 and my<50:
                survivors.append(dict(key=f"{name}:{gname}",sym=gname,mech=name,sh=round(s,2),pf=round(p,2),maxyr=round(my),n=len(pnl),ret=pnl))
    return survivors,n_screen,sorted(fams)
def dedup(survs,thresh=0.6):
    """keep only orthogonal return streams (corr<thresh to any kept)."""
    kept=[]
    for s in sorted(survs,key=lambda x:-x["sh"]):
        rk=s["ret"]; ok=True
        for k in kept:
            common=rk.index.intersection(k["ret"].index)
            if len(common)>50 and abs(rk.reindex(common).corr(k["ret"].reindex(common)))>thresh: ok=False; break
        if ok: kept.append(s)
    return kept
if __name__=="__main__":
    instr=sys.argv[1:] or INSTR
    survs,n,fams=run(instr)
    uniq=dedup(survs)
    print(f"=== BATCH SCREEN: {n} hypotheses, {len(fams)} families, {len(instr)} markets -> {len(survs)} cheap-gate ({100*len(survs)/max(1,n):.1f}%) -> {len(uniq)} orthogonal ===")
    for s in sorted(uniq,key=lambda x:-x["sh"])[:20]:
        print(f"    {s['key']:26s} Sh={s['sh']:>5.2f} PF={s['pf']:>4} maxyr={s['maxyr']:>3}% n={s['n']}")
    print(f"  families: {fams}")
    print(f"  global trial-N: {count()} (all recorded for honest N)")
    import json;from pathlib import Path
    Path(R/"research/data/factory_metrics.json").write_text(json.dumps({
        "batch_hypotheses":n,"families":len(fams),"markets":len(instr),"cheap_survivors":len(survs),
        "survivor_rate_pct":round(100*len(survs)/max(1,n),2),"orthogonal_streams":len(uniq),
        "family_list":fams,"note":"ONE generator's output — a null means THIS generator found nothing, not that the domain is dead"},indent=2))
    print(f"  FACTORY METRICS -> research/data/factory_metrics.json")
