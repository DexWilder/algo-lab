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
from collections import Counter as _MC
_mc=_MC(x.get("mission_class","?") for x in runnow); _wh1=sum(v for k,v in _mc.items() if k in ("INDEX_DIRECT","INDEX_REGIME_INPUT"))
mission_wt=f"{_wh1}/{len(runnow)} WH1-aligned ({dict(_mc)})"
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
from research.capture_inbound import stats as inb_stats
ib=inb_stats()
# FACTORY METRICS (measure the factory, not the strategy)
_bt=[t for t in _ledload()["trials"] if t.get("lane")=="batch_screen"]
factory=dict(batch_hypotheses=len(_bt), markets_screened=len(set(t.get("asset") for t in _bt)),
             dsr_credible=sum(1 for t in _ledload()["trials"] if isinstance(t.get("dsr"),(int,float)) and t.get("dsr",0)>=0.95),
             validated_assets=2)
ds=json.loads((REPO/"research/data/data_sources.json").read_text())["sources"] if (REPO/"research/data/data_sources.json").exists() else []
from collections import Counter as _C
ds_stat=dict(_C(s["status"] for s in ds)); ds_active=sum(1 for s in ds if s["status"]=="ACTIVE_IN_TESTS")
ls=json.loads((REPO/"research/data/learning_state.json").read_text()) if (REPO/"research/data/learning_state.json").exists() else {}
next25=ls.get("next_25_actions",[]); gaps=ls.get("data_utilization_gaps",[])
g=subprocess.run([sys.executable,str(REPO/"research/forge_system_guardrails.py")],capture_output=True,text=True,timeout=120)
gv="P0_FAIL" if g.returncode!=0 else "clean/P1"
p0=[l.strip() for l in g.stdout.splitlines() if "[P0]" in l]; p1=[l.strip() for l in g.stdout.splitlines() if "[P1]" in l]
backlog=sh("rev-list","--count","origin/main..HEAD") or "0"
sa=subprocess.run([sys.executable,str(REPO/"research/forge_self_audit.py")],capture_output=True,text=True,timeout=120)
sav=next((l.split("VERDICT:")[1].split("(")[0].strip() for l in sa.stdout.splitlines() if "VERDICT:" in l),"?")
sa_line=next((l.strip() for l in sa.stdout.splitlines() if l.startswith("facets=")),"")
ncycle=len(glob.glob(str(REPO/"research/forge_cycle_*.py")))+len(glob.glob(str(REPO/"research/forge_sprint_*.py")))+len(glob.glob(str(REPO/"research/forge_family_*.py")))
lanes=lane_breakdown()
stamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
out=f"""# ALPHA RESEARCH DASHBOARD (auto-generated {stamp})
> `python3 research/forge_dashboard.py` regenerates this. Single canonical state view.

## HEADLINE
- **Validated primaries: 0** (highest ladder rung: **{hi}**; capital gate FAIL-CLOSED, PAPER_APPROVED+ operator-only).
- Guardrails: **{gv}** | Self-audit: **{sav}** ({sa_line}) | Git backlog: **{backlog}** | Global trial-N: **{count()}**
- **Mission:** MNQ/MES/MYM index workhorse (WH1). RUN_NOW mission-weighting: {mission_wt}
- **Search posture:** the NAIVE direct-index price/volume surface (gap/fade/trend/MR/OR) is picked-over UNDER TESTED EXPRESSIONS. WH1 direct-index remains LIVE via GEX/event/regime/source-CONDITIONED mechanisms + MYM (1m now pulled). Structural surfaces (GEX/dealer-flow, event-surprise, forced-flow) are EARLY — prove over 20–50 cycles, not solved.

## Throughput (computed live)
- Tests logged today: **{tested_today}** | total kills: {kills} | screen-passes: {screenpass}
- Novelty packets: **{nov_total}** stored ({nov_today} today) of {108} template×instrument space
- Families: **{fam_active} active** / {len(reg)} | coverage {fam_cov}% (tested exprs / total exprs)
- Candidate ladder: {', '.join(f'{k}={len(v)}' for k,v in lstate.items()) or 'empty (nothing promoted)'}

## Factory metrics (product = validated DISCOVERIES; measure the factory)
- Batch hypotheses run: **{factory['batch_hypotheses']}** across {factory['markets_screened']} markets | DSR-credible ever: {factory['dsr_credible']} | validated assets: {factory['validated_assets']} (spreadMR_GC diversifier + GEX regime ingredient)
- **Evidence-matched claim (NOT overclaimed):** the batch generator's templates produced 0 DSR-credible daily price/volume survivors at honest N — *this generator's output, not "the whole daily price/volume space is dead."* Untested families: vol-state, cross-sectional RV, dispersion, breadth, term-structure, cross-asset conditioning, adaptive exits, calendar, execution-timing, hybrid. Redirect = richer generators + flow data, not "domain solved."

## Inbound capture (organizational memory — nothing floats)
- Items: **{ib['total']}** | NEW: {ib['new']} | P0/P1: {ib['p0']}/{ib['p1']} | source packets today: {ib['source_packets_today']}
- Untriaged directives: {len(ib['untriaged_directives'])} | mistakes w/o control: **{len(ib['mistakes_no_control'])}** {ib['mistakes_no_control'][:4]} | unused feeds: {len(ib['feeds_no_lane'])}
- QUEUED-missing-from-queue: {len(ib['queued_missing'])} | source notes unresolved: {len(ib['source_unresolved'])} | oldest untriaged: {ib['oldest_untriaged']}d
- Ledger: `docs/fql_forge/INBOUND_RESEARCH_LEDGER.md` (capture: `python3 research/capture_inbound.py`)

## Trial-N by lane (family diagnostics)
{chr(10).join(f'- {k}: {v}' for k,v in sorted(lanes.items(), key=lambda x:-x[1]))}

## Queue depth
- RUN_NOW: {len(runnow)} | total queue items: {len(q['queue'])}
{chr(10).join(f"- [{x.get('status')}] {x['id']}: {x.get('verdict') or x.get('note','')[:70]}" for x in q['queue'][:12])}

## Data-utilization map ({ds_active}/{len(ds)} ACTIVE_IN_TESTS — no asset floats)
{chr(10).join(f"- [{s['tier']}] {s['source']} — {s['status']} ({s.get('lane','')})" for s in ds)}
- status mix: {ds_stat}

## Roadmap (operational) — Phase 1: foundation hardening
- **Exit criteria:** data-tier gate live ✅ · learning-state updater live ✅ · close-only kills rescoped ✅ · 1m+volume harness running ✅ (OR batch=kill) · data-util dashboard ✅ · self-audit artifact ✅ | REMAINING: ≥1 close-only family re-scoped edge found OR cleanly killed at T3 (in progress); self-audit clean streak ≥5
- **Blockers:** gamma T6 needs chunked-OI loader (+$11.54 gate); intraday 1m-path MR + settlement/lead-lag T3 packets not yet run
- **Data-util gaps (richer tier unused):** {len(gaps)} families — {[g['family'] for g in gaps][:8]}
- **Next-25 (from learning_state):**
{chr(10).join(f"  {i+1}. {a}" for i,a in enumerate(next25[:12]))}

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
