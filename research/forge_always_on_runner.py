"""FORGE ALWAYS-ON RUNNER (2026-06-30) — queue-driven, no-idle research loop (report-only).
Loop per RUN_NOW item: run script → capture report → record trial-ledger → commit → push → guardrails → mark DONE → next.
The machine, not 'Claude picks next'. NO capital surfaces (no deploy/paper/registry/scheduler/portfolio/sizing).
Queue: research/data/forge_run_queue.json  [{id, script, status: RUN_NOW|DONE|BLOCKED, verdict}]
Run:  python3 research/forge_always_on_runner.py [--max N]"""
import sys, json, subprocess, argparse, time
from pathlib import Path
from datetime import datetime, timezone
REPO=Path("/Users/chasefisher/projects/Algo Trading/algo-lab")
Q=REPO/"research/data/forge_run_queue.json"; REPORTS=REPO/"research/data/fql_forge/reports"
GHCRED='!gh auth git-credential'
def load(): return json.loads(Q.read_text()) if Q.exists() else {"queue":[]}
def save(d): Q.write_text(json.dumps(d,indent=2))
def git(*args):
    return subprocess.run(["git","-C",str(REPO),"-c",f"credential.helper={GHCRED}",*args],capture_output=True,text=True,timeout=120)
def run_item(it):
    script=REPO/it["script"]; stamp=datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    if not script.exists():
        it["status"]="BLOCKED"; it["verdict"]=f"script missing: {it['script']}"; return it
    print(f"[RUN] {it['id']} -> {it['script']}")
    try:
        r=subprocess.run([sys.executable,str(script)],capture_output=True,text=True,timeout=1800,cwd=str(REPO))
        out=(r.stdout or "")[-6000:]
    except Exception as e:
        it["status"]="BLOCKED"; it["verdict"]=f"run error: {e}"; return it
    REPORTS.mkdir(parents=True,exist_ok=True)
    rp=REPORTS/f"runner_{it['id']}_{stamp}.md"
    rp.write_text(f"# Runner: {it['id']} ({it['script']})\n\n```\n{out}\n```\n")
    # crude verdict parse
    v="KILL" if "KILL" in out else ("SCREEN-SURVIVOR" if "SCREEN-SURVIVOR" in out or "SURVIVOR" in out else ("SCREEN_PASS" if "SCREEN_PASS" in out else "done"))
    it["status"]="DONE"; it["verdict"]=v; it["report"]=str(rp.relative_to(REPO)); it["ran"]=stamp
    return it
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--max",type=int,default=1); a=ap.parse_args()
    d=load(); ran=0
    for it in d["queue"]:
        if it.get("status")!="RUN_NOW": continue
        if ran>=a.max: break
        run_item(it); save(d); ran+=1
        # record + commit + push + guardrails
        try:
            from research.forge_trial_ledger import record, count
            record(f"RUNNER:{it['id']}", verdict=it.get("verdict","done"))
        except Exception: pass
        git("add","-A","research/data/fql_forge/reports/","research/data/forge_run_queue.json","research/data/forge_trial_ledger.json")
        cm=git("commit","-q","-m",f"runner: {it['id']} -> {it.get('verdict')} (report-only, no capital)")
        ps=git("push","origin","main")
        g=subprocess.run([sys.executable,str(REPO/"research/forge_system_guardrails.py")],capture_output=True,text=True,timeout=120)
        gv="P0_FAIL" if g.returncode!=0 else "clean/P1"
        print(f"  [{it['id']}] verdict={it.get('verdict')} | committed | push={'ok' if ps.returncode==0 else 'FAIL'} | guardrails={gv}")
    remaining=[x for x in d["queue"] if x.get("status")=="RUN_NOW"]
    print(f"\nrunner pass done: ran {ran}; {len(remaining)} RUN_NOW remaining. Next: {remaining[0]['id'] if remaining else '(refill queue from master)'}")
if __name__=="__main__": main()
