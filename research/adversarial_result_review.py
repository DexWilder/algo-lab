"""ADVERSARIAL RESULT REVIEW — red-team a result before its label hardens. Not Claude reviewing Claude only.
Usage: from research.adversarial_result_review import review; review(dict(label=..., sharpe=..., n=..., maxyr=..., long_share=..., cost_delta=..., global_n=..., family_n=..., data=..., richer_data_checked=bool, harness_checked=bool))"""
def review(r):
    fails=[]
    if r.get("label","").upper() in ("VALIDATED","PRIMARY","WORKHORSE","PAPER_READY"): fails.append("LABEL_TOO_STRONG (banned term)")
    if r.get("global_n") is None or r.get("family_n") is None: fails.append("N_NOT_REPORTED (need global+family N)")
    if r.get("maxyr",0)>60 and r.get("label","")!="CLEAN_KILL": fails.append(f"SINGLE_YEAR_DOMINATES maxyr={r.get('maxyr')}%")
    side=r.get("active_long_share", r.get("long_share",0.5))   # balance among NON-FLAT positions (sparse tail-engines are valid)
    if side>0.9 or side<0.1: fails.append(f"DEGENERATE_SIDE active_long_share={round(side,3)}")
    if r.get("flat_share",0)>0.9 and r.get("n_active",r.get("n",999))<60: fails.append(f"SPARSE_LOW_N n_active={r.get('n_active')} (<60 active days; tail-engine gates, not workhorse)")
    if r.get("cost_delta",1)==0 and r.get("n",0)>0: fails.append("COST_NOT_AFFECTING_PNL (turnover but cost inert)")
    if r.get("richer_data_checked") is False: fails.append("RICHER_DATA_NOT_CHECKED")
    if r.get("harness_checked") is False: fails.append("EXISTING_HARNESS_NOT_CHECKED (grep wp_/lever_/forge_cycle first)")
    if r.get("family_exhausted_claim") and r.get("expressions_tested",0)<3: fails.append("FAMILY_OVERKILL (<3 expressions before exhaustion claim)")
    if r.get("data_blocked_claim") and not r.get("certificate"): fails.append("DATA_BLOCKED_NO_CERT")
    # DATA-TIER sufficiency (doctrine A): a family-level kill/exhaustion below the richest applicable tier is false exhaustion
    _T={f"T{i}":i for i in range(8)}
    dt=r.get("data_tier"); rt=r.get("richest_applicable_tier")
    if dt and rt and _T.get(dt,9)<_T.get(rt,0) and any(k in r.get("label","").upper() for k in ("EXHAUST","FAMILY_KILL","CLEAN_KILL")):
        fails.append(f"DATA_TIER_INSUFFICIENT (killed at {dt}, richest applicable {rt} untested — expression-kill only)")
    ok=len(fails)==0
    print(f"  [adversarial-review {r.get('id','?')}] {'PASS' if ok else 'FAIL'}" + ("" if ok else " | "+"; ".join(fails)))
    return ok, fails
if __name__=="__main__":
    print("demo — overclaimed result:"); review(dict(id="demo",label="VALIDATED",sharpe=1.2,maxyr=80,long_share=0.95,global_n=None,family_n=None))
    print("demo — clean kill:"); review(dict(id="rates_carry",label="CLEAN_KILL",sharpe=-0.2,maxyr=999,long_share=0.5,global_n=1773,family_n=4,cost_delta=1,n=100,richer_data_checked=True,harness_checked=True))
