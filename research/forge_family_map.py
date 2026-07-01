"""FAMILY MAP (computed, not static) — reads research/data/family_status.json + the live trial ledger, computes per-family
coverage and REAL family-N, and FLAGS drift: (a) status=CLEAN_KILL/EXHAUSTED but coverage<100% (over-claim), (b) status=
ACTIVE_EXPANSION/UNDERTESTED but 0 untested left (stale claim). Writes docs/fql_forge/EDGE_FAMILY_MAP_2026-06-30.md.
Because family-N comes from the ledger, the map cannot silently drift from what was actually run.
Run: python3 research/forge_family_map.py"""
import sys, json
from pathlib import Path
from datetime import datetime, timezone
REPO=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(REPO))
from research.forge_trial_ledger import count, lane_breakdown
REG=json.loads((REPO/"research/data/family_status.json").read_text())["families"]
lanes=lane_breakdown()
STRONG_KILL={"CLEAN_KILL","FAMILY_EXHAUSTED"}; PARKED={"SUBFAMILY_KILLED"}; KILLED=STRONG_KILL|PARKED
rows=[]; flags=[]
for fam,d in REG.items():
    tested=d.get("tested",[]); untested=d.get("untested",[])
    tot=len(tested)+len(untested); cov=round(100*len(tested)/tot) if tot else 0
    ln=count(lane=d["lane"])
    st=d["status"]
    if st in STRONG_KILL and untested: flags.append(f"OVER-CLAIM: {fam} is {st} but {len(untested)} untested expr remain: {untested}")
    if st in ("ACTIVE_EXPANSION","UNDERTESTED") and not untested: flags.append(f"STALE: {fam} is {st} but 0 untested expr — advance or re-status")
    tier=f"{d.get('data_tier','?')}→{d.get('richest_applicable_tier','?')}"+(" ⚠gap" if d.get("tier_gap") else "")
    rows.append((fam,st,tier,cov,len(tested),len(untested),ln,"; ".join(untested[:3]) or "—"))
rows.sort(key=lambda r:(r[1] in KILLED, -r[5]))   # active families with most untested first
stamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
n_active=sum(1 for _,st,*_ in rows if st not in KILLED)
lines=[f"# Edge-Family Map (computed {stamp}) — from family_status.json x trial ledger",
       f"> Regenerate: `python3 research/forge_family_map.py`. Coverage=tested/(tested+untested). family-N from ledger lane.",
       f"> **Families: {len(rows)} | active (not killed): {n_active} | global trial-N: {count()} | drift flags: {len(flags)}**","",
       "| family | status | tier(tested→applicable) | coverage | tested | untested | family-N | next untested expressions |",
       "|---|---|---|---|---|---|---|---|"]
for fam,st,data,cov,nt,nu,ln,nxt in rows:
    lines.append(f"| {fam} | {st} | {data} | {cov}% | {nt} | {nu} | {ln} | {nxt} |")
lines.append("\n## Drift flags (family-completion integrity)")
lines += [f"- ⚠️ {f}" for f in flags] or ["- none — no family over-claims exhaustion or falsely claims active"]
lines.append("\n## Family completion rule")
lines.append("A family is NOT FAMILY_EXHAUSTED until coverage=100% AND cost/roll/concentration/DSR checks done on survivors. "
             "Killing a whole family from one expression is over-claim (flagged above). Endless rescue-grind on a killed family is banned.")
(REPO/"docs/fql_forge/EDGE_FAMILY_MAP_2026-06-30.md").write_text("\n".join(lines))
print(f"family map computed: {len(rows)} families, {n_active} active, {len(flags)} drift flags")
for f in flags: print(f"  FLAG: {f}")
