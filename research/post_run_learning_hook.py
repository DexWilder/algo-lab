"""POST-RUN LEARNING HOOK — "no test is complete until the machine learns from it." Run after every packet/test/deepening.
Orchestrates the compounding update: learning_state -> family_tier_matrix -> family_map -> dashboard -> guardrails ->
self-audit, and prints a "what changed because of this run" diff (trial-N delta, new kills, novelty-weight shifts, next-action
head). This is the enforcement that generation reads outcomes. Run: python3 research/post_run_learning_hook.py"""
import sys, json, subprocess
from pathlib import Path
REPO=Path("/Users/chasefisher/projects/Algo Trading/algo-lab"); sys.path.insert(0,str(REPO))
from research.forge_trial_ledger import count, failure_taxonomy
def _snap():
    ls=REPO/"research/data/learning_state.json"
    prev=json.loads(ls.read_text()) if ls.exists() else {}
    return dict(N=prev.get("global_trial_N",count()), weights=prev.get("novelty_weights",{}), killed=len(prev.get("killed_expressions",[])))
def run(step, *args):
    r=subprocess.run([sys.executable,str(REPO/step)]+list(args),capture_output=True,text=True,timeout=180)
    return r.returncode, (r.stdout.strip().splitlines() or [""])[-1]
if __name__=="__main__":
    before=_snap()
    print("=== POST-RUN LEARNING HOOK ===")
    for step in ["research/update_learning_state.py","research/forge_family_map.py","research/forge_dashboard.py"]:
        rc,last=run(step); print(f"  {step.split('/')[-1]:28} -> {last[:80]}")
    # guardrails + self-audit (both must be visible every report)
    grc,_=run("research/forge_system_guardrails.py"); src,_=run("research/forge_self_audit.py")
    after=_snap()
    ls=json.loads((REPO/"research/data/learning_state.json").read_text())
    print("\n  WHAT CHANGED BECAUSE OF THIS RUN:")
    print(f"    trial-N: {before['N']} -> {after['N']} (+{after['N']-before['N']})")
    print(f"    killed expressions: {before['killed']} -> {after['killed']}")
    shifts={k:(before['weights'].get(k),after['weights'].get(k)) for k in after['weights'] if before['weights'].get(k)!=after['weights'].get(k)}
    print(f"    novelty-weight shifts: {shifts or 'none'}")
    print(f"    failure taxonomy: {failure_taxonomy()}")
    print(f"    next action: {ls.get('next_25_actions',['-'])[0]}")
    print(f"    guardrails exit={grc} | self-audit exit={src}")
    print("  (commit/push is the caller's final step — hook does not mutate git)")
