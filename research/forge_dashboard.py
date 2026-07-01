"""ALPHA RESEARCH DASHBOARD generator — one command answers 'where are we?'. Reads live state (trial ledger, queue,
guardrails, git, families) and writes docs/fql_forge/ALPHA_RESEARCH_DASHBOARD.md. Run: python3 research/forge_dashboard.py"""
import sys, json, subprocess, glob
from pathlib import Path
from datetime import datetime, timezone
REPO=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(REPO))
def sh(*a):
    try: return subprocess.run(["git","-C",str(REPO),*a],capture_output=True,text=True,timeout=30).stdout.strip()
    except Exception: return "?"
from research.forge_trial_ledger import count, lane_breakdown, _load as _ledload
from research.forge_candidate_ladder import highest_rung, ladder_state
q=json.loads((REPO/"research/data/forge_run_queue.json").read_text()) if (REPO/"research/data/forge_run_queue.json").exists() else {"queue":[]}
runnow=[x for x in q["queue"] if x.get("status")=="RUN_NOW"]
# --- throughput (computed from live state) ---
today=datetime.now(timezone.utc).strftime("%Y-%m-%d")
trials=_ledload()["trials"]
tested_today=sum(1 for t in trials if t.get("ts")==today)
kills=sum(1 for t in trials if "KILL" in str(t.get("verdict","")).upper())
screenpass=sum(1 for t in trials if "SCREEN_PASS" in str(t.get("verdict","")).upper())
nov=json.loads((REPO/"research/data/novelty_packets.json").read_text()) if (REPO/"research/data/novelty_packets.json").exists() else {"packets":{}}
nov_total=len(nov["packets"]); nov_today=sum(1 for p in nov["packets"].values() if p.get("created")==today)
reg=json.loads((REPO/"research/data/family_status.json").read_text())["families"]
fam_active=sum(1 for f in reg.values() if f["status"] not in ("CLEAN_KILL","FAMILY_EXHAUSTED","SUBFAMILY_KILLED"))
fam_cov=round(100*sum(len(f["tested"]) for f in reg.values())/max(1,sum(len(f["tested"])+len(f["untested"]) for f in reg.values())))
lstate=ladder_state(); hi=highest_rung()
g=subprocess.run([sys.executable,str(REPO/"research/forge_system_guardrails.py")],capture_output=True,text=True,timeout=120)
gv="P0_FAIL" if g.returncode!=0 else "clean/P1"
p0=[l.strip() for l in g.stdout.splitlines() if "[P0]" in l]; p1=[l.strip() for l in g.stdout.splitlines() if "[P1]" in l]
backlog=sh("rev-list","--count","origin/main..HEAD") or "0"
ncycle=len(glob.glob(str(REPO/"research/forge_cycle_*.py")))+len(glob.glob(str(REPO/"research/forge_sprint_*.py")))+len(glob.glob(str(REPO/"research/forge_family_*.py")))
lanes=lane_breakdown()
stamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
out=f"""# ALPHA RESEARCH DASHBOARD (auto-generated {stamp})
> `python3 research/forge_dashboard.py` regenerates this. Single canonical state view.

## HEADLINE
- **Validated primaries: 0** (highest ladder rung: **{hi}**; capital gate FAIL-CLOSED, PAPER_APPROVED+ operator-only).
- Guardrails: **{gv}** | Git backlog: **{backlog}** | Test scripts run: {ncycle} | Global trial-N: **{count()}**

## Throughput (computed live)
- Tests logged today: **{tested_today}** | total kills: {kills} | screen-passes: {screenpass}
- Novelty packets: **{nov_total}** stored ({nov_today} today) of {108} template×instrument space
- Families: **{fam_active} active** / {len(reg)} | coverage {fam_cov}% (tested exprs / total exprs)
- Candidate ladder: {', '.join(f'{k}={len(v)}' for k,v in lstate.items()) or 'empty (nothing promoted)'}

## Trial-N by lane (family diagnostics)
{chr(10).join(f'- {k}: {v}' for k,v in sorted(lanes.items(), key=lambda x:-x[1]))}

## Queue depth
- RUN_NOW: {len(runnow)} | total queue items: {len(q['queue'])}
{chr(10).join(f"- [{x.get('status')}] {x['id']}: {x.get('verdict') or x.get('note','')[:70]}" for x in q['queue'][:12])}

## Guardrail alerts
{chr(10).join(p0+p1) or '- none (P0 clear)'}

## Highest-EV lanes NOW (family map)
1. Gamma/dealer-flow (feasible, chunked-loader pending) 2. Commodity term-structure carry (RUN_NOW) 3. Databento event-path/liquidity
4. Rates event-path/FOMC/auction (untested) 5. Source/novelty intake

## Latest verdicts (recent families)
- rates carry (daily per-contract) = CLEAN_KILL (scoped) | gamma = FEASIBLE | commodity carry = RUN_NOW | primitive sweep = exhausted (1680)

## Operator actions required
- gamma full pull \$11.54 (>threshold; approved 'pull gamma' — needs chunked loader first)
- (else: none — report-only lanes self-run)
"""
(REPO/"docs/fql_forge/ALPHA_RESEARCH_DASHBOARD.md").write_text(out)
print(out)
