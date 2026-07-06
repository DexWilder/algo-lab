"""WH1 MISSION CLASSIFIER — core mission is an MNQ/MES/MYM index workhorse. Every packet/family classified so the runner
stays WH1-weighted and diversifiers don't dominate. Classes: INDEX_DIRECT (trades MES/MNQ/MYM) > INDEX_REGIME_INPUT
(conditions index behavior) > DIVERSIFIER (separate return stream) > LOW_PRIORITY_ARCHIVE (killed/parked)."""
INDEX={"MES","MNQ","MYM","M2K","ES","NQ"}
FAMILY_CLASS={
 "intraday_micro":"INDEX_DIRECT","open_close_liquidity":"INDEX_DIRECT","mean_reversion":"INDEX_DIRECT",
 "trend_momentum":"INDEX_DIRECT","monthend_settlement":"INDEX_DIRECT","xasset_leadlag":"INDEX_DIRECT",
 "gamma_dealer":"INDEX_REGIME_INPUT","vol_risk_premium":"INDEX_REGIME_INPUT","macro_event_drift":"INDEX_REGIME_INPUT",
 "regime_filters":"INDEX_REGIME_INPUT","expiry_opex":"INDEX_REGIME_INPUT",
 "carry_commodity":"DIVERSIFIER","carry_rates":"DIVERSIFIER","curve_rv":"DIVERSIFIER","carry_legacy_fx_rates":"DIVERSIFIER",
 "positioning_cot":"DIVERSIFIER","auction_issuance":"DIVERSIFIER","inventory_eia":"DIVERSIFIER",
 "fx_fixing_ratediv":"DIVERSIFIER","crypto_funding":"LOW_PRIORITY_ARCHIVE","execution_cost":"INDEX_REGIME_INPUT"}
def classify(*, family=None, instrument=None, note="", surface=""):
    t=f"{note} {surface}".lower()
    if instrument in INDEX or any(x in t for x in ("mes","mnq","mym","index","orb","opening range","closing")):
        # index-traded microstructure = direct; unless it's clearly a regime input
        if any(x in t for x in ("gex","gamma","vix","dvol","regime","event surprise","cpi","fomc","nfp")): return "INDEX_REGIME_INPUT"
        return "INDEX_DIRECT"
    if any(x in t for x in ("gex","gamma","vix","dvol","event","surprise","cpi","fomc","nfp","regime","opex")): return "INDEX_REGIME_INPUT"
    if family in FAMILY_CLASS: return FAMILY_CLASS[family]
    if any(x in t for x in ("spreadmr","gc ","gold","cl ","crude","carry","curve","crypto","funding","6e","6j","fx","auction","cot","rates","zn","zb","zf")): return "DIVERSIFIER"
    return "INDEX_REGIME_INPUT"
if __name__=="__main__":
    import json;from pathlib import Path
    R=Path("/Users/chasefisher/projects/Algo Trading/algo-lab")
    # tag families
    fs=json.loads((R/"research/data/family_status.json").read_text())
    for k,f in fs["families"].items(): f["mission_class"]=FAMILY_CLASS.get(k,classify(family=k,note=k))
    (R/"research/data/family_status.json").write_text(json.dumps(fs,indent=2))
    # tag queue
    q=json.loads((R/"research/data/forge_run_queue.json").read_text())
    for x in q["queue"]:
        x["mission_class"]=classify(family=x.get("lane"),instrument=None,note=x.get("note",""),surface=x.get("surface",""))
    (R/"research/data/forge_run_queue.json").write_text(json.dumps(q,indent=2))
    from collections import Counter
    rn=[x for x in q["queue"] if x.get("status")=="RUN_NOW"]
    print("families by mission:",dict(Counter(f["mission_class"] for f in fs["families"].values())))
    print("RUN_NOW by mission:",dict(Counter(x["mission_class"] for x in rn)))
    wh1=sum(1 for x in rn if x["mission_class"] in ("INDEX_DIRECT","INDEX_REGIME_INPUT"))
    print(f"WH1-weighted RUN_NOW: {wh1}/{len(rn)} ({100*wh1//max(1,len(rn))}%) — target majority INDEX_DIRECT/REGIME_INPUT")
