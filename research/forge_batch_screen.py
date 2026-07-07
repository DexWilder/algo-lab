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
def mechanisms(g):
    """causal position generators -> dict name: position series (to be shift(1)'d)."""
    out={}; c=g["close"]; r=g["pret"]; gap=g["open"]-c.shift(1)
    hi=g["high"]; lo=g["low"]; vol=g["volume"]
    volz=(vol-vol.rolling(60,min_periods=20).mean())/vol.rolling(60,min_periods=20).std()
    for N in [1,2,3,5,10,20]:
        out[f"mom{N}"]=np.sign(c-c.shift(N))
        out[f"mr{N}"]=-np.sign(c-c.shift(N))
        rz=(r-r.rolling(60,min_periods=20).mean())/r.rolling(60,min_periods=20).std()
        out[f"mr{N}_extreme"]=(-np.sign(c-c.shift(N))).where(rz.abs()>1.5,0.0)
    for N in [5,10,20,40]:
        out[f"brk{N}"]=np.where(c>hi.rolling(N).max().shift(1),1,np.where(c<lo.rolling(N).min().shift(1),-1,0))
    out["gapfade"]=-np.sign(gap); out["gapfollow"]=np.sign(gap)
    for N in [3,5,10]:
        out[f"volmom{N}"]=(np.sign(c-c.shift(N))).where(volz>0.5,0.0)
        out[f"volmr{N}"]=(-np.sign(c-c.shift(N))).where(volz>0.5,0.0)
    dow=g.index.dayofweek
    for d in range(5): out[f"dow_long{d}"]=pd.Series(np.where(dow==d,1,0),index=g.index)
    return {k:(pd.Series(v,index=g.index) if not isinstance(v,pd.Series) else v) for k,v in out.items()}
def run(instr):
    survivors=[]; n_screen=0
    for sym in instr:
        try: g=daily(sym)
        except Exception: print(f"  {sym}: no data"); continue
        if len(g)<250: continue
        mechs=mechanisms(g); rng=g["ret"]
        for name,pos in mechs.items():
            pnl=(pos.shift(1)*rng).dropna(); n_screen+=1
            if len(pnl)<200: continue
            s=shp(pnl.values); yr=pnl.groupby(pnl.index.year).sum(); my=100*yr.max()/yr.sum() if yr.sum()>0 else 999
            p=pf(pnl.values); act=int((pos.shift(1).reindex(pnl.index).fillna(0)!=0).sum())
            record(f"BATCH:{name}:{sym}",asset=sym,sharpe=round(s,2),verdict="batch_screen",lane="batch_screen",maxyr=round(my),n=len(pnl))
            if s>0.5 and p>1.05 and my<50 and act>150:   # cheap-screen survivor gate
                survivors.append(dict(key=f"{name}:{sym}",sym=sym,mech=name,sh=round(s,2),pf=round(p,2),maxyr=round(my),n=len(pnl),ret=pnl))
    return survivors,n_screen
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
    survs,n=run(instr)
    print(f"=== BATCH SCREEN: {n} hypotheses tested across {len(instr)} markets, {len(survs)} passed cheap gate ({100*len(survs)//max(1,n)}%) ===")
    uniq=dedup(survs)
    print(f"  after correlation-dedup (orthogonal return streams): {len(uniq)} unique survivors")
    for s in sorted(uniq,key=lambda x:-x["sh"])[:20]:
        print(f"    {s['key']:24s} Sh={s['sh']:>5.2f} PF={s['pf']:>4} maxyr={s['maxyr']:>3}% n={s['n']}")
    print(f"  global trial-N now: {count()} (all batch screens recorded for honest multiple-testing)")
    print(f"  FACTORY METRIC: hypotheses={n} survivor-rate={100*len(survs)/max(1,n):.1f}% unique-streams={len(uniq)}")
