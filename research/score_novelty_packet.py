"""NOVELTY PACKET SCORER — grades each generated packet so generic indicator-mashups get rejected/deprioritized and only
mechanism-driven, data-rich, forced-flow packets reach the queue. Elite novelty != technical variations of old kills.
Usage: from research.score_novelty_packet import score ; score(packet_dict) -> {scores..., total, priority, verdict}"""
GENERIC=("breakout","mean reversion","moving average","rsi","macd","crossover","indicator")
def _has_mechanism(p):   # forced/constrained participant + economic reason + timing
    return bool(p.get("who")) and bool(p.get("mech")) and bool(p.get("horizon"))
def score(p):
    txt=f"{p.get('mech','')} {p.get('tid','')}".lower()
    mech_clarity = 5 if _has_mechanism(p) else 1
    forced = 5 if any(w in p.get("who","").lower() for w in ("must","forced","obligation","mechanical","price-insensitive","index","dealer")) else 2
    non_generic = 1 if any(g in txt for g in GENERIC) and forced<4 else (5 if forced>=4 else 3)
    data_avail = {"LOCAL":5,"REPULL":3,"REPULL_PAID":2,"CERT":2,"PAID":1}.get(p.get("avail","REPULL"),3)
    tier = {"T6":5,"T5":4,"T4":4,"T3":5,"T2":2,"T1":1}.get(p.get("data_tier","T2"),3)   # richer/underused tiers score higher
    testability = 5 if p.get("harness") and p.get("data") else 2
    persistence = forced  # forced flow is the main reason an edge persists
    total = mech_clarity+forced+non_generic+data_avail+tier+testability+persistence
    verdict = "NOVELTY_QUALITY_WEAK (archive/rewrite)" if (non_generic<=2 or mech_clarity<=2 or total<20) else ("HIGH" if total>=28 else "OK")
    prio = "P1" if total>=28 else ("P2" if total>=22 else "P3")
    return dict(mech_clarity=mech_clarity,forced_flow=forced,non_generic=non_generic,data_availability=data_avail,
                tier=tier,testability=testability,persistence=persistence,total=total,priority=prio,verdict=verdict)
if __name__=="__main__":
    import json;from pathlib import Path
    REPO=Path("/Users/chasefisher/projects/Algo Trading/algo-lab")
    nov=json.loads((REPO/"research/data/novelty_packets.json").read_text())["packets"]
    # score stored packets (they carry tid/dim/avail; enrich with template mech/who via novelty engine templates)
    import sys;sys.path.insert(0,str(REPO));from research.forge_novelty_engine import TEMPLATES
    T={t["id"]:t for t in TEMPLATES}
    weak=hi=0
    for k,v in nov.items():
        t=T.get(v["tid"],{}); s=score({**v,**{x:t.get(x) for x in ("who","mech","horizon","harness","data")}})
        if "WEAK" in s["verdict"]: weak+=1
        if s["verdict"]=="HIGH": hi+=1
    print(f"scored {len(nov)} stored packets: HIGH={hi} WEAK={weak} | scorer rejects generic mashups (non_generic<=2 or total<20)")
    print("  demo generic 'RSI crossover breakout':", score({"who":"traders","mech":"rsi macd crossover breakout","horizon":"intraday","harness":"x","data":"M1","avail":"LOCAL","data_tier":"T2"})["verdict"])
