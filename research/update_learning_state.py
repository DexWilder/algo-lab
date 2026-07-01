"""LEARNING-STATE UPDATER — closes the learning loop. Reads every outcome surface (trial ledger, family_status, candidate
ladder, inbound, queue) and writes ONE aggregated brain research/data/learning_state.json that GENERATION reads: the novelty
engine consumes novelty_weights (down-weight dead families / up-weight survivor neighborhoods); the dashboard shows gaps and
next-25. A test is NOT complete until this runs. Run: python3 research/update_learning_state.py"""
import sys, json
from pathlib import Path
from datetime import datetime, timezone
REPO=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(REPO))
from research.forge_trial_ledger import lane_breakdown, count, _load as _led
from research.forge_candidate_ladder import ladder_state
from research.capture_inbound import stats as inb_stats
OUT=REPO/"research/data/learning_state.json"
reg=json.loads((REPO/"research/data/family_status.json").read_text())["families"]
try: queue=json.loads((REPO/"research/data/forge_run_queue.json").read_text())["queue"]
except Exception: queue=[]
trials=_led()["trials"]; ib=inb_stats(); lad=ladder_state()

DEAD={"CLEAN_KILL","FAMILY_EXHAUSTED","SUBFAMILY_KILLED"}
killed_expressions=[]; survivor_neighborhoods=[]; tested_tiers={}
for fam,f in reg.items():
    tested_tiers[fam]=f.get("tested_tiers",[])
    if f["status"] in DEAD:
        for e in f.get("tested",[]): killed_expressions.append(f"{fam}:{e}")
# survivors = ladder SCREEN_PASS+ and their neighborhood (family, tier, mechanism dims)
NEIGH_DIMS={"carry_commodity":["roll/settlement","carry"], "carry_rates":["carry"], "curve_rv":["curve RV"]}
for rung,cids in lad.items():
    if rung in ("SCREEN_PASS","FAMILY_CONFIRMED","TRADEABLE_RESEARCH_CANDIDATE"):
        for cid in cids: survivor_neighborhoods.append({"candidate":cid,"rung":rung,"neighbor_dims":NEIGH_DIMS.get("carry_commodity",[])})
# data utilization gaps: families with tier_gap (richer validated tier unused)
util_gaps=[{"family":k,"data_tier":f.get("data_tier"),"richest":f.get("richest_applicable_tier"),"reason":f.get("tier_gap_reason","")}
           for k,f in reg.items() if f.get("tier_gap")]
# NOVELTY WEIGHTS — the loop closure: dims tied to dead families down, survivor dims up, tier_gap (rich untested) up
DIM_FAMILY={"roll/settlement":"carry_commodity","carry":"carry_commodity","curve RV":"curve_rv",
 "hedging reflexivity":"gamma_dealer","microstructure":"intraday_micro","execution window":"fx_fixing_ratediv",
 "month-end/rebalance":"monthend_settlement","event uncertainty":"macro_event_drift","inventory pressure":"inventory_eia",
 "crowding":"positioning_cot","cross-asset":"xasset_leadlag"}
weights={}
for dim,fam in DIM_FAMILY.items():
    f=reg.get(fam,{}); w=1.0
    if f.get("status") in DEAD and not f.get("tier_gap"): w=0.4          # truly dead -> down-weight
    if f.get("tier_gap"): w=1.5                                          # richer tier unused -> UP (the frontier)
    if any(fam=="carry_commodity" for s in survivor_neighborhoods): w=max(w,1.6) if fam=="carry_commodity" else w
    weights[dim]=round(w,2)
# next 25 actions: TIER_INCOMPLETE reopenings + RUN_NOW queue + deepening + tier_gap frontier
next25=[]
for k,f in reg.items():
    if f.get("status")=="TIER_INCOMPLETE": next25.append(f"RETEST {k} at {f.get('richest_applicable_tier')} (reopened false-exhaustion)")
for k,f in reg.items():
    if f.get("tier_gap") and f.get("status") not in DEAD and k!="carry_legacy_fx_rates": next25.append(f"TEST {k} at richer tier {f.get('richest_applicable_tier')} ({f.get('data_tier')} done)")
for x in queue:
    if x.get("status")=="RUN_NOW": next25.append(f"QUEUE {x['id']}: {(x.get('note') or '')[:60]}")
next25=next25[:25]
stale_labels=[k for k,f in reg.items() if not f.get("data_tier")]
unresolved=ib["mistakes_no_control"]+ib["untriaged_directives"]
state=dict(timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    global_trial_N=count(), lane_breakdown=lane_breakdown(),
    families={k:{"status":f["status"],"data_tier":f.get("data_tier"),"richest_applicable_tier":f.get("richest_applicable_tier"),"tier_gap":f.get("tier_gap",False)} for k,f in reg.items()},
    tested_tiers_by_family=tested_tiers, killed_expressions=killed_expressions, survivor_neighborhoods=survivor_neighborhoods,
    candidate_rungs={cid:rung for rung,cids in lad.items() for cid in cids}, data_utilization_gaps=util_gaps,
    novelty_weights=weights, next_25_actions=next25, stale_labels=stale_labels, unresolved_learning_gaps=unresolved)
OUT.write_text(json.dumps(state,indent=2))
print(f"learning_state updated: {len(reg)} families, {len(killed_expressions)} killed exprs, {len(survivor_neighborhoods)} survivors,")
print(f"  {len(util_gaps)} data-util gaps, novelty weights up>1: {[d for d,w in weights.items() if w>1]}")
print(f"  next-25 head: {next25[0] if next25 else '-'} | unresolved learning gaps: {len(unresolved)}")
