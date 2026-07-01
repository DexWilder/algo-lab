"""CANDIDATE PROMOTION LADDER (enforced, not just labels in a doc). 10 rungs; a candidate can only advance one rung at a
time, and NOTHING can pass SCREEN_PASS(5) -> FAMILY_CONFIRMED(6)+ without a passing adversarial_result_review. Capital rungs
(PAPER_APPROVED/LIVE_APPROVED) are operator-gated and refuse to auto-set. Store: research/data/candidate_ladder.json.
Usage: from research.forge_candidate_ladder import promote, ladder_state
       promote('carry_commodity_CL', 'SCREEN_PASS', result_dict)   # result_dict fed to adversarial review at rung>=6"""
import json, sys
from pathlib import Path
from datetime import datetime, timezone
REPO=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(REPO))
from research.adversarial_result_review import review
STORE=REPO/"research/data/candidate_ladder.json"
RUNGS=["IDEA","PACKET","DATA_READY","CAUSAL_READY","SCREEN_PASS","FAMILY_CONFIRMED",
       "TRADEABLE_RESEARCH_CANDIDATE","PAPER_REVIEW_CANDIDATE","PAPER_APPROVED","LIVE_APPROVED"]
IDX={r:i for i,r in enumerate(RUNGS)}
ADVERSARIAL_GATE=IDX["FAMILY_CONFIRMED"]     # rung 6+ requires passing adversarial review
OPERATOR_GATE=IDX["PAPER_APPROVED"]          # rung 8+ refuses to auto-set (capital-facing)
def _load():
    try: return json.loads(STORE.read_text())
    except Exception: return {"candidates":{}}
def promote(cid, to_rung, result=None, operator_ok=False):
    if to_rung not in IDX: return False, f"unknown rung {to_rung}"
    d=_load(); cur=d["candidates"].get(cid,{}).get("rung","IDEA"); ti=IDX[to_rung]
    if ti>IDX[cur]+1: return False, f"cannot skip rungs {cur}->{to_rung} (advance one at a time)"
    if ti>=ADVERSARIAL_GATE:
        ok,fails=review(result or {});
        if not ok: return False, f"adversarial review FAIL, cannot reach {to_rung}: {fails}"
    if ti>=OPERATOR_GATE and not operator_ok:
        return False, f"{to_rung} is capital-facing — operator gate required (fail-closed)"
    d["candidates"][cid]={"rung":to_rung,"ts":datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                          "history":d["candidates"].get(cid,{}).get("history",[])+[cur]}
    STORE.write_text(json.dumps(d,indent=2)); return True, f"{cid}: {cur} -> {to_rung}"
def ladder_state():
    d=_load(); out={}
    for cid,c in d["candidates"].items(): out.setdefault(c["rung"],[]).append(cid)
    return out
def highest_rung():
    d=_load()
    if not d["candidates"]: return "IDEA(none)"
    return max((c["rung"] for c in d["candidates"].values()), key=lambda r:IDX[r])
if __name__=="__main__":
    st=ladder_state()
    print("CANDIDATE LADDER:", "nothing promoted yet" if not st else "")
    for r in RUNGS:
        if st.get(r): print(f"  {IDX[r]} {r}: {st[r]}")
    print(f"highest rung: {highest_rung()}  (capital gate: PAPER_APPROVED+ operator-only, fail-closed)")
