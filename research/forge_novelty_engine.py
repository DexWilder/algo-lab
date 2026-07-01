"""NOVELTY ENGINE (generative, not a static list) — grows the opportunity surface each run.
Cross-products FORCED-FLOW TEMPLATES x our INSTRUMENT holdings, resolves data availability per combo, dedups against a
persistent store, scores by feasibility x mechanism-prior, emits only NEW packets, and reports an honest SATURATION signal
when the current templates x instruments are covered (=> add templates or instruments, don't loop).
Run: python3 research/forge_novelty_engine.py [--emit N]   (default emit top 12 new, queue LOCAL-feasible high-score)"""
import json, sys
from pathlib import Path
from datetime import datetime, timezone
REPO=Path("/Users/chasefisher/projects/Algo Trading/algo-lab")
STORE=REPO/"research/data/novelty_packets.json"
QUEUE=REPO/"research/data/forge_run_queue.json"

# --- forced-flow archetypes: the generative dimensions the operator specified ---
# data_req types: PERCONTRACT (term structure), OPTIONS_OI (gamma), M1 (1m intraday path), CALENDAR, FEED_EXT (external feed)
# prior: mechanism strength 1-3 (mechanical/regulatory forced flow > behavioral crowding)
TEMPLATES=[
 dict(id="roll_pressure",     dim="roll/settlement",  mech="longs must roll front->deferred over the roll window",           who="index/ETF/CTA roll schedules (calendar-driven, price-insensitive)", horizon="roll window", data="PERCONTRACT", harness="term-structure", prior=3),
 dict(id="contango_bleed",    dim="roll/settlement",  mech="long-ETF holders bleed roll return in steep contango",           who="commodity-ETF holders (must hold front, can't avoid decay)",        horizon="daily",       data="PERCONTRACT", harness="term-structure-carry", prior=2),
 dict(id="detrended_carry",   dim="carry",            mech="carry vs own rolling term-structure baseline (not raw sign)",    who="carry harvesters; level is beta, deviation is signal",              horizon="daily",       data="PERCONTRACT", harness="term-structure-carry", prior=2),
 dict(id="curve_slope_mom",   dim="curve RV",         mech="curve slope momentum (2s10s / front-deferred spread)",           who="macro funds reprice curve slowly",                                  horizon="daily",       data="PERCONTRACT", harness="curve-RV", prior=2),
 dict(id="opex_gamma_pin",    dim="hedging reflexivity", mech="dealers hedge short-gamma into expiry, pin to max-OI strike",  who="option dealers (delta-hedge obligation, mechanical)",               horizon="OPEX week",   data="OPTIONS_OI", harness="gamma-regime", prior=3),
 dict(id="gamma_flip_accel",  dim="hedging reflexivity", mech="below gamma-flip dealers sell weakness (accel); above they dampen", who="option dealers (hedge sign flips at flip level)",                horizon="daily",       data="OPTIONS_OI", harness="gamma-regime", prior=3),
 dict(id="settlement_revert", dim="microstructure",   mech="marks pinned to cash/settlement close, revert after",            who="funds marking books on official close (price-insensitive at mark)",  horizon="15:00-16:00", data="M1", harness="event-path-1m", prior=2),
 dict(id="opening_imbalance", dim="microstructure",   mech="overnight order imbalance resolves in the opening auction",      who="MOC/opening-auction participants (must fill at open)",              horizon="first 30m",   data="M1", harness="intraday-path", prior=2),
 dict(id="benchmark_fix",     dim="execution window", mech="benchmark-tracking funds transact at a known fix (16:00 WMR)",    who="index/benchmark FX funds (must trade at the fix)",                  horizon="fix window",  data="M1", harness="event-path-1m", prior=3),
 dict(id="month_end_extend",  dim="month-end/rebalance", mech="duration/equity index funds rebalance in the last session(s)", who="index funds (mechanical month-end rebalance)",                    horizon="last 1-3 sess", data="CALENDAR", harness="calendar-adapter", prior=2),
 dict(id="post_event_vol_crush", dim="event uncertainty", mech="hedges unwind and IV collapses after a scheduled decision",   who="event hedgers (unwind once uncertainty resolves)",                  horizon="event+1",     data="OPTIONS_OI", harness="event-adapter", prior=2),
 dict(id="inventory_surprise",dim="inventory pressure",mech="producers/refiners hedge after an inventory-report surprise",    who="physical hedgers (must hedge post-surprise)",                       horizon="event day",   data="FEED_EXT", harness="event-adapter", prior=2),
 dict(id="crowd_unwind",      dim="crowding",         mech="trapped specs cut on an adverse break (COT extreme + break)",    who="crowded specs (margin-forced, not naive fade-the-crowd)",           horizon="weekly",      data="FEED_EXT", harness="cot-conditional", prior=1),
 dict(id="auction_concession",dim="roll/settlement",  mech="dealers demand concession pre-auction, unwind post-auction",     who="primary dealers (must absorb issuance)",                            horizon="T-2..T+2",    data="CALENDAR", harness="event-adapter", prior=2),
 dict(id="xasset_leadlag",    dim="cross-asset",      mech="lead instrument moves, laggard reprices with delay",             who="slow cross-asset arbitrageurs / latency",                           horizon="intraday",    data="M1", harness="cross-asset-latency", prior=1),
]
# --- our instrument holdings (what data we actually possess) ---
INSTR={
 "MES":dict(cls="equity",m1=1,pc=1,opt=1),"MNQ":dict(cls="equity",m1=1,pc=1,opt=0),"MYM":dict(cls="equity",m1=1,pc=0,opt=0),"M2K":dict(cls="equity",m1=1,pc=0,opt=0),
 "MGC":dict(cls="metal",m1=1,pc=0,opt=0),"GC":dict(cls="metal",m1=0,pc=1,opt=0),"MCL":dict(cls="energy",m1=1,pc=0,opt=0),"CL":dict(cls="energy",m1=0,pc=1,opt=0),
 "ZT":dict(cls="rates",m1=0,pc=1,opt=0),"ZF":dict(cls="rates",m1=0,pc=1,opt=0),"ZN":dict(cls="rates",m1=1,pc=1,opt=0),"ZB":dict(cls="rates",m1=0,pc=1,opt=0),
 "6E":dict(cls="fx",m1=1,pc=0,opt=0),"6J":dict(cls="fx",m1=1,pc=0,opt=0),"6B":dict(cls="fx",m1=1,pc=0,opt=0),
}
def applies(t,sym,a):
    d=t["data"]; cls=a["cls"]
    if d=="PERCONTRACT": return bool(a["pc"])
    if d=="OPTIONS_OI":  return bool(a["opt"])
    if d=="M1":          return bool(a["m1"])
    if d=="CALENDAR":    return (cls in ("rates","equity")) if t["id"] in ("auction_concession","month_end_extend") else True
    if d=="FEED_EXT":    return (cls=="energy" and t["id"]=="inventory_surprise") or (t["id"]=="crowd_unwind")
    return True
def availability(t,sym,a):
    d=t["data"]
    if d=="PERCONTRACT": return ("LOCAL",3) if sym in ("ZT","ZF","ZN","ZB","CL","GC") else ("REPULL",2)
    if d=="M1":          return ("LOCAL",3) if a["m1"] else ("REPULL",2)
    if d=="OPTIONS_OI":  return ("REPULL_PAID",1)          # ES.OPT OI pullable (chunked loader) — >$5 => approval
    if d=="CALENDAR":    return ("LOCAL",3)                # treasury_auctions.csv / holiday calendars local
    if d=="FEED_EXT":    return ("CERT",1)                 # EIA/COT external feed (free API but not yet wired => certificate)
    return ("REPULL",2)
def key(tid,sym): return f"{tid}::{sym}"
def _load(p,default):
    try: return json.loads(p.read_text())
    except Exception: return default

def generate(emit=12):
    store=_load(STORE,{"packets":{}}); seen=set(store["packets"].keys())
    cand=[]
    for t in TEMPLATES:
        for sym,a in INSTR.items():
            if not applies(t,sym,a): continue
            k=key(t["id"],sym)
            if k in seen: continue
            avail,fw=availability(t,sym,a)
            cand.append(dict(key=k,tid=t["id"],dim=t["dim"],sym=sym,mech=t["mech"],who=t["who"],
                             horizon=t["horizon"],harness=t["harness"],data=t["data"],avail=avail,score=fw*t["prior"]))
    cand.sort(key=lambda c:(-c["score"],c["key"]))
    total_space=sum(1 for t in TEMPLATES for sym,a in INSTR.items() if applies(t,sym,a))
    new=cand[:emit]; stamp=datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for c in new: store["packets"][c["key"]]=dict(**{x:c[x] for x in ("tid","sym","dim","avail","score","harness")},created=stamp)
    STORE.parent.mkdir(parents=True,exist_ok=True); STORE.write_text(json.dumps(store,indent=2))
    q=_load(QUEUE,{"queue":[]}); qids={x.get("id") for x in q["queue"]}; queued=0
    for c in new:
        if c["avail"]=="LOCAL" and c["score"]>=4:
            qid=f"nov_{c['tid']}_{c['sym']}"
            if qid not in qids:
                q["queue"].append(dict(id=qid,status="BACKLOG",lane="novelty",
                    note=f"{c['dim']}: {c['mech']} [{c['sym']}] harness={c['harness']} (validators first, predeclared)"))
                qids.add(qid); queued+=1
    QUEUE.write_text(json.dumps(q,indent=2))
    return new,total_space,len(seen),queued

if __name__=="__main__":
    emit=12
    if "--emit" in sys.argv: emit=int(sys.argv[sys.argv.index("--emit")+1])
    new,total,covered,queued=generate(emit); stamp=datetime.now(timezone.utc).strftime("%Y-%m-%d")
    saturated=(len(new)==0)
    lines=[f"# Novelty Packets — generated {stamp}",
           f"> generative engine (templates x instruments, dedup, feasibility-scored). Space={total} combos, covered={covered+len(new)}/{total}, emitted-this-run={len(new)}, queued-LOCAL={queued}.",
           "","| score | dim | mechanism | instr | horizon | data | availability | harness |","|---|---|---|---|---|---|---|---|"]
    for c in new: lines.append(f"| {c['score']} | {c['dim']} | {c['mech']} | {c['sym']} | {c['horizon']} | {c['data']} | {c['avail']} | {c['harness']} |")
    if saturated: lines.append("\n**SATURATION: no new template x instrument combos. Add TEMPLATES or INSTRUMENTS to grow the surface (do not re-loop).**")
    (REPO/f"docs/fql_forge/NOVELTY_PACKETS_{stamp}.md").write_text("\n".join(lines))
    print(f"emitted {len(new)} NEW packets (space={total}, now covered {covered+len(new)}/{total}), queued {queued} LOCAL-feasible")
    for c in new[:8]: print(f"  +{c['score']} {c['tid']}/{c['sym']} [{c['avail']}] {c['dim']}")
    if saturated: print("  SATURATION — add templates/instruments")
