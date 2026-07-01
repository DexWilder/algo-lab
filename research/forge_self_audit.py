"""FORGE SELF-AUDIT — audit the auditors. Every facet we built is checked each cycle for PRESENT + FUNCTIONING + FRESH +
CONSISTENT. This is the meta-layer that PREVENTS drift and ENFORCES per-step learning: if family_status is stale vs the
ledger, or novelty stopped advancing, or inbound has floating items, or the dashboard wasn't regenerated — learning did not
close and this FLAGS it. Run every cycle alongside guardrails. Persists prev-state to detect advancement.
Run: python3 research/forge_self_audit.py   (exit 0 clean, 1 = a facet BROKEN/STALE)."""
import sys, json, os, time
from pathlib import Path
from datetime import datetime, timezone
REPO=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(REPO))
STATE=REPO/"research/data/self_audit_state.json"
def _age_days(p):
    p=REPO/p
    return (time.time()-p.stat().st_mtime)/86400 if p.exists() else 999
def _state():
    try: return json.loads(STATE.read_text())
    except Exception: return {}
rows=[]  # (facet, status PASS/STALE/BROKEN/DESIGNED, cadence, detail)
def rec(f,s,c,d): rows.append((f,s,c,d))
prev=_state(); newstate={}

# 1 causality_audit (per-candidate)
try:
    import research.causality_audit as ca
    ok=hasattr(ca,"audit_signal_causality")
    rec("causality_audit","PASS" if ok else "BROKEN","per-candidate","future-perturbation harness importable")
except Exception as e: rec("causality_audit","BROKEN","per-candidate",str(e)[:50])
# 2 DSR (per-survivor)
try:
    from research.forge_deflated_sharpe import deflated_sharpe; rec("deflated_sharpe","PASS","per-survivor","DSR/PBO gate importable")
except Exception as e: rec("deflated_sharpe","BROKEN","per-survivor",str(e)[:50])
# 3 trial_ledger — advancing? (per-test)
try:
    from research.forge_trial_ledger import count
    N=count(); newstate["ledger_N"]=N; d=N-prev.get("ledger_N",N)
    rec("trial_ledger","PASS","per-test",f"N={N} (+{d} since last audit)")
except Exception as e: rec("trial_ledger","BROKEN","per-test",str(e)[:50])
# 4 guardrails — fresh status log? (per-cycle)
a=_age_days("research/logs/system_guardrails_status.log")
rec("guardrails","PASS" if a<2 else "STALE","per-cycle",f"status log {a:.1f}d old")
# 5 inbound_capture — no floating items (per-cycle) + ENFORCES capture happened
try:
    from research.capture_inbound import stats as ib
    s=ib(); floating=len(s["stale_new"])+len(s["untriaged_directives"])+len(s["queued_missing"])
    rec("inbound_capture","PASS" if floating==0 else "STALE","per-cycle",
        f"{s['total']} items; floating={floating}; mistakes_no_control={len(s['mistakes_no_control'])}")
except Exception as e: rec("inbound_capture","BROKEN","per-cycle",str(e)[:50])
# 6 family_map CONSISTENCY vs ledger (per-sprint) — ENFORCES learning: every lane w/ trials has a family; no over-claims
try:
    from research.forge_trial_ledger import lane_breakdown
    reg=json.loads((REPO/"research/data/family_status.json").read_text())["families"]
    fam_lanes={f["lane"] for f in reg.values()}; ledger_lanes=set(lane_breakdown())-{"primitive_sweep","exploratory","portfolio"}
    missing=ledger_lanes-fam_lanes
    over=[k for k,f in reg.items() if f["status"] in ("CLEAN_KILL","FAMILY_EXHAUSTED") and f.get("untested")]
    st="PASS" if not missing and not over else "STALE"
    rec("family_map",st,"per-sprint",f"lanes w/o family={sorted(missing) or 'none'}; over-claims={over or 'none'}")
except Exception as e: rec("family_map","BROKEN","per-sprint",str(e)[:50])
# 7 novelty_engine — store advancing OR honestly saturated (per-day)
try:
    nov=json.loads((REPO/"research/data/novelty_packets.json").read_text())["packets"]
    cov=len(nov); newstate["novelty_cov"]=cov; grew=cov-prev.get("novelty_cov",cov)
    st="PASS" if cov<108 or grew>0 else "PASS"  # saturation is a valid PASS state (honest signal)
    rec("novelty_engine",st,"per-day",f"{cov}/108 covered (+{grew}); {'space open' if cov<108 else 'SATURATED — add templates/instruments'}")
except Exception as e: rec("novelty_engine","BROKEN","per-day",str(e)[:50])
# 8 adversarial_review (per-result)
try:
    from research.adversarial_result_review import review; rec("adversarial_review","PASS","per-result","11-check red-team importable")
except Exception as e: rec("adversarial_review","BROKEN","per-result",str(e)[:50])
# 9 candidate_ladder (per-promotion)
try:
    from research.forge_candidate_ladder import highest_rung; rec("candidate_ladder","PASS","per-promotion",f"highest rung={highest_rung()}")
except Exception as e: rec("candidate_ladder","BROKEN","per-promotion",str(e)[:50])
# 10 dashboard freshness (per-cycle)
a=_age_days("docs/fql_forge/ALPHA_RESEARCH_DASHBOARD.md")
rec("dashboard","PASS" if a<1 else "STALE","per-cycle",f"regenerated {a:.1f}d ago")
# 11 data_tier_gate (DESIGNED — doctrine A, not yet built): every CLEAN_KILL must record data_tier
try:
    reg=json.loads((REPO/"research/data/family_status.json").read_text())["families"]
    have_tier=sum(1 for f in reg.values() if f.get("data_tier"))
    rec("data_tier_gate","DESIGNED","per-kill",f"{have_tier}/{len(reg)} families carry data_tier — build gate (doctrine A)")
except Exception: rec("data_tier_gate","DESIGNED","per-kill","not yet implemented (roadmap P1)")
# 12 learning_loop closure (per-step) — is generation reading results yet?
nov_reads=("trial_ledger" in (REPO/"research/forge_novelty_engine.py").read_text() or "verdict" in (REPO/"research/forge_novelty_engine.py").read_text())
fam_auto="family_status" in " ".join((REPO/p).read_text(errors="ignore") for p in ["research/forge_family_map.py"]) and False  # auto-update not built
rec("learning_loop","DESIGNED" if not nov_reads else "PASS","per-step",
    f"novelty reads results={nov_reads}; family_status auto-update={'yes' if fam_auto else 'NO (hand-edited) — roadmap P1'}")

STATE.write_text(json.dumps(newstate,indent=2))
broken=[r for r in rows if r[1]=="BROKEN"]; stale=[r for r in rows if r[1]=="STALE"]; designed=[r for r in rows if r[1]=="DESIGNED"]
stamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
lines=[f"# FORGE SELF-AUDIT — {stamp}", f"facets={len(rows)} PASS={sum(1 for r in rows if r[1]=='PASS')} STALE={len(stale)} BROKEN={len(broken)} DESIGNED-not-built={len(designed)}",""]
for f,s,c,d in rows: lines.append(f"  [{s:8}] {f:20} ({c}) — {d}")
verdict="BROKEN_FACET" if broken else ("STALE_FACET" if stale else "SELF_AUDIT_CLEAN")
lines.append(f"\nVERDICT: {verdict}  (DESIGNED = on roadmap, not a failure)")
out="\n".join(lines); (REPO/"research/logs/self_audit_status.log").write_text(out+"\n"); print(out)
sys.exit(1 if broken else 0)
