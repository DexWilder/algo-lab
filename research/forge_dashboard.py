"""ALPHA RESEARCH DASHBOARD generator — one command answers 'where are we?'. Reads live state (trial ledger, queue,
guardrails, git, families) and writes docs/fql_forge/ALPHA_RESEARCH_DASHBOARD.md. Run: python3 research/forge_dashboard.py"""
import sys, json, subprocess, glob
from pathlib import Path
from datetime import datetime, timezone
REPO=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(REPO))
def sh(*a):
    try: return subprocess.run(["git","-C",str(REPO),*a],capture_output=True,text=True,timeout=30).stdout.strip()
    except Exception: return "?"
from research.forge_trial_ledger import count, lane_breakdown
q=json.loads((REPO/"research/data/forge_run_queue.json").read_text()) if (REPO/"research/data/forge_run_queue.json").exists() else {"queue":[]}
runnow=[x for x in q["queue"] if x.get("status")=="RUN_NOW"]
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
- **Validated primaries: 0** (nothing above SCREEN_PASS). Capital gate: FAIL-CLOSED.
- Guardrails: **{gv}** | Git backlog: **{backlog}** | Test scripts run: {ncycle} | Global trial-N: **{count()}**

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
