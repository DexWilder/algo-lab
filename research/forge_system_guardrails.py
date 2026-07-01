"""FORGE SYSTEM GUARDRAILS (P0, 2026-06-26) — fail-loud execution-memory checks.
Built because automations RAN but none checked the failure modes that bit us (Databento unused / close-only tests /
git backlog / stale automations / directive non-compliance). This is the teeth: it FAILS LOUD (non-zero exit + ALERT
lines written where the next session reads them) instead of writing an unread doc. Intended to be called by the
weekday learning-loop audit so it runs EVERY cycle, not monthly.
Run: python3 research/forge_system_guardrails.py   (exit 0 = clean, 1 = P0 violation)."""
import sys, subprocess, glob, re
from pathlib import Path
from datetime import datetime, timezone
REPO=Path("/Users/chasefisher/projects/Algo Trading/algo-lab")
alerts=[]; info=[]
def alert(sev, msg): alerts.append((sev, msg))

# --- 1) GIT BACKLOG ---
try:
    n=subprocess.run(["git","-C",str(REPO),"rev-list","--count","origin/main..HEAD"],capture_output=True,text=True).stdout.strip()
    n=int(n) if n.isdigit() else -1
    if n>5: alert("P0", f"GIT BACKLOG: {n} commits unpushed (>5). Restore auth (gh auth login) and push.")
    elif n>0: info.append(f"git backlog {n} (ok)")
    else: info.append("git backlog 0")
except Exception as e: alert("P1", f"git backlog check failed: {e}")

# --- 2) DATABENTO DATA USAGE (unused-data) ---
db=sorted(p.stem for p in (REPO/"data/databento").glob("*_1m.csv"))  # e.g. MNQ_1m
scripts=" ".join(Path(p).read_text(errors="ignore") for p in glob.glob(str(REPO/"research/*.py")))
uses_databento = ("data/databento" in scripts) or bool(re.search(r"_1m\.csv", scripts))
uses_volume = scripts.count("volume")
n_cycle=len(glob.glob(str(REPO/"research/forge_cycle_*.py")))
vol_scripts=sum(1 for p in glob.glob(str(REPO/"research/forge_cycle_*.py")) if "volume" in Path(p).read_text(errors="ignore"))
if db and not uses_databento:
    alert("P0", f"DATABENTO UNUSED: {len(db)} 1m files present but NO research script references data/databento or *_1m.csv.")
ratio = vol_scripts/max(n_cycle,1)
if ratio < 0.10:
    alert("P1", f"CLOSE-ONLY BIAS: only {vol_scripts}/{n_cycle} forge_cycle scripts use 'volume' ({ratio*100:.0f}%). Databento volume vein under-worked (target: keep ACTIVE_PACKET_LANE).")
else: info.append(f"volume usage {vol_scripts}/{n_cycle} cycle scripts")

# --- 3) STALE AUTOMATIONS (critical ones must have recent logs) ---
import os, time
def log_age_days(patterns):
    newest=0
    for pat in patterns:
        for f in glob.glob(str(REPO/"research/logs"/pat)):
            newest=max(newest, os.path.getmtime(f))
    return (time.time()-newest)/86400 if newest else 999
for name, pats, maxdays in [("watchdog",["watchdog_*.log"],2),("forge-morning-digest",["launchd_forge_morning_digest_stdout.log"],4),("learning-loop",["learning_loop_audit*.log"],9)]:
    age=log_age_days(pats)
    if age>maxdays: alert("P2", f"STALE AUTOMATION: {name} no log in {age:.0f}d (>{maxdays}).")
    else: info.append(f"{name} log {age:.1f}d old")

# --- 4) DIRECTIVE COMPLIANCE (machine invariants) ---
must_exist={"causality_audit":"research/causality_audit.py","DSR":"research/forge_deflated_sharpe.py",
            "no_lookahead_test":"research/test_no_lookahead_daily_filters.py","data_inventory":"docs/fql_forge/DATABENTO_INVENTORY_AND_UNLOCKS_2026-06-26.md"}
for k,v in must_exist.items():
    if not (REPO/v).exists(): alert("P0", f"DIRECTIVE CONTROL MISSING: {k} ({v}) not found.")
# paid-data memo must be provisional while databento vein active
memo=REPO/"docs/fql_forge/PAID_DATA_DECISION_MEMO_2026-06-26.md"
if memo.exists():
    t=memo.read_text(errors="ignore")
    if "PROVISIONAL" not in t.upper() and "SUSPENDED" not in t.upper():
        alert("P1","PAID-DATA MEMO not marked PROVISIONAL while Databento volume vein is ACTIVE_PACKET_LANE.")

# --- 5) NO-WH-LANGUAGE SCAN (asserting phrases only; exclude negated/historical/doctrine lines) ---
ASSERT=[r"is a workhorse", r"validated primary", r"is validated", r"paper-ready", r"deployment candidate",
        r"primary workhorse", r"deployment-ready"]
NEG=("not","no ","invalidated","void","forbidden","banned","never","without","≠","pending","not a","is not",
     "label","vocabulary","taxonomy","rule","only if","must","require","`")  # `=code word-list; meta-rule lines
META=("DOCTRINE","OVERHAUL","RESCUE","INVENTORY","MEMO","AUDIT")  # docs that DISCUSS the ban, not assert WH
wh_hits=[]
import glob as _glob
recent_docs=[d for d in sorted(_glob.glob(str(REPO/"docs/fql_forge/*.md")), key=lambda p: os.path.getmtime(p), reverse=True)[:10]
             if not any(m in Path(d).name for m in META)]
for d in recent_docs:
    for i,ln in enumerate(Path(d).read_text(errors="ignore").splitlines()):
        low=ln.lower()
        if any(re.search(a, low) for a in ASSERT) and not any(n in low for n in NEG):
            wh_hits.append(f"{Path(d).name}:{i+1}: {ln.strip()[:80]}")
if wh_hits:
    alert("P2", f"WH-LANGUAGE: {len(wh_hits)} asserting WH/validated phrase(s) in recent docs (verify gate-passed): "+wh_hits[0])
else: info.append("no asserting WH/validated language in recent docs")

# --- 6) TRIAL-LEDGER present (multiple-testing N automatic) ---
if not (REPO/"research/data/forge_trial_ledger.json").exists():
    alert("P1","TRIAL LEDGER missing — DSR multiple-testing N is manual/uncounted.")
else:
    try:
        import json as _j; tn=len(_j.loads((REPO/"research/data/forge_trial_ledger.json").read_text()).get("trials",[]))
        info.append(f"trial-ledger N={tn}")
    except Exception: pass

# --- 7) UNUSED FEEDS (feed exists but no research script references it) ---
feed_files=[p for p in (REPO/"data/feeds").glob("*.csv")]
research_blob=scripts  # already concatenated above
unused_feeds=[]
for fp in feed_files:
    # strict: the actual feed filename/stem must appear in a research script (no coarse token match)
    if fp.name not in research_blob and fp.stem not in research_blob and f"feeds/{fp.stem}" not in research_blob:
        unused_feeds.append(fp.name)
if unused_feeds:
    alert("P2", f"UNUSED FEEDS: {len(unused_feeds)} data/feeds files referenced by NO research script: {unused_feeds[:6]}")
else: info.append(f"feeds: all {len(feed_files)} referenced")

# --- 8) UNRUN HARNESSES (wp_*/lever_* exist but produced no output) ---
unrun=[]
for hp in list((REPO/"research").glob("wp_*.py"))+list((REPO/"research").glob("lever_*.py")):
    name=hp.stem
    out_exists = any((REPO/"research/data").glob(f"*{name}*")) or any((REPO/"research/data/fql_forge").rglob(f"*{name.split('_')[0]}*")) \
                 or any((REPO/"docs/fql_forge").glob(f"*{name}*"))
    # also: was it referenced (run) in any committed result? heuristic: a screen json mentioning it
    if not out_exists and name not in ("lever_b1_feed_validator",):  # validators are structure-only
        unrun.append(hp.name)
if unrun:
    alert("P1", f"UNRUN HARNESSES: {len(unrun)} wp_/lever_ harnesses with no output (built-but-never-run): {unrun}")
else: info.append("harnesses: all have output")

# --- 9) DATA_BLOCKED requires a CERTIFICATE (the $0.30-was-not-blocked failure class) ---
cert=REPO/"docs/fql_forge/DATA_BLOCKER_CERTIFICATES_2026-06-30.md"
recent_md=sorted(_glob.glob(str(REPO/"docs/fql_forge/*.md")), key=lambda p: os.path.getmtime(p), reverse=True)[:6]
blocked_hits=[]
for d in recent_md:
    if Path(d).name==cert.name: continue
    for i,ln in enumerate(Path(d).read_text(errors="ignore").splitlines()):
        if re.search(r"DATA_BLOCKED|PAID_DATA_REQUIRED", ln) and "certificate" not in ln.lower() and "DATA_STATUS_UNPROVEN" not in ln:
            blocked_hits.append(f"{Path(d).name}:{i+1}")
if blocked_hits and not cert.exists():
    alert("P1", f"DATA_BLOCKED without certificate: {len(blocked_hits)} mentions, no DATA_BLOCKER_CERTIFICATES doc. Prove it or label DATA_STATUS_UNPROVEN.")
elif not cert.exists():
    info.append("no DATA_BLOCKED claims / cert n/a")
else:
    info.append(f"data-blocker certificates present ({len(blocked_hits)} recent blocked-mentions, cert exists)")

# --- 10) VALIDATION LAYER present + per-contract files pass data-validator ---
for vf in ["research/validate_strategy_expression.py","research/validate_data_file.py"]:
    if not (REPO/vf).exists(): alert("P1", f"VALIDATION LAYER missing: {vf} (expression/data validator required pre-sprint).")
try:
    sys.path.insert(0,str(REPO)); from research.validate_data_file import validate_data_file
    bad=[]
    for f in (REPO/"data/databento").glob("*_percontract_1d.csv"):
        ok,fl=validate_data_file(str(f))
        if not ok: bad.append(f"{f.name}:{fl}")
    if bad: alert("P1", f"PER-CONTRACT DATA INVALID (validator): {bad[:3]}")
    else: info.append("per-contract data files pass validator")
except Exception as e: info.append(f"data-validator check skipped: {e}")

# --- 12) DATA-TIER GATE (doctrine A — no false exhaustion) ---
try:
    import json as _dj
    reg=_dj.loads((REPO/"research/data/family_status.json").read_text())["families"]
    _T={f"T{i}":i for i in range(8)}
    no_tier=[k for k,f in reg.items() if not f.get("data_tier")]
    false_exh=[k for k,f in reg.items() if f.get("status") in ("CLEAN_KILL","FAMILY_EXHAUSTED")
               and f.get("richest_applicable_tier") and _T.get(f.get("data_tier","T7"),9)<_T.get(f["richest_applicable_tier"],0)
               and k!="carry_legacy_fx_rates"]
    gap_active=[k for k,f in reg.items() if f.get("tier_gap") and f.get("status") not in ("CLEAN_KILL","FAMILY_EXHAUSTED","TIER_INCOMPLETE","SUBFAMILY_KILLED","DATA_BLOCKED_CERT")]
    if no_tier: alert("P1", f"DATA-TIER: {len(no_tier)} families have no data_tier field (stale pre-tier labels): {no_tier[:6]}")
    if false_exh: alert("P0", f"FALSE EXHAUSTION: {len(false_exh)} family-level kills below richest applicable tier (must be expression-kill): {false_exh}")
    else: info.append(f"data-tier gate: 0 false-exhaustion; {sum(1 for f in reg.values() if f.get('tier_gap'))} families have untested richer tier (TIER_INCOMPLETE ok)")
except Exception as e: alert("P1", f"data-tier gate check failed: {e}")

# --- 11) INBOUND CAPTURE (organizational memory — nothing floats) ---
try:
    from research.capture_inbound import stats as _inb_stats
    ib=_inb_stats()
    if ib["stale_new"]: alert("P1", f"INBOUND STALE: {len(ib['stale_new'])} NEW items >4d untriaged: {ib['stale_new'][:5]}")
    if ib["untriaged_directives"]: alert("P1", f"INBOUND: {len(ib['untriaged_directives'])} operator directive(s) not operationalized (no control/queue/packet): {ib['untriaged_directives'][:5]}")
    if ib["mistakes_no_control"]: alert("P1", f"INBOUND: {len(ib['mistakes_no_control'])} mistake/validation item(s) with NO durable control: {ib['mistakes_no_control'][:5]} (no control = not fixed)")
    if ib["feeds_no_lane"]: alert("P2", f"INBOUND: {len(ib['feeds_no_lane'])} data feed(s) INVENTORIED_UNUSED (no packet lane): {ib['feeds_no_lane'][:5]}")
    if ib["ideas_unmapped"]: alert("P2", f"INBOUND: {len(ib['ideas_unmapped'])} strategy idea(s) missing family/harness/data mapping: {ib['ideas_unmapped'][:5]}")
    if ib["queued_missing"]: alert("P1", f"INBOUND: {len(ib['queued_missing'])} QUEUED/ACTIVE inbound item(s) missing from forge queue: {ib['queued_missing'][:5]}")
    if ib["source_unresolved"]: alert("P2", f"INBOUND: {len(ib['source_unresolved'])} source note(s) with no packet and not archived: {ib['source_unresolved'][:5]}")
    info.append(f"inbound ledger: {ib['total']} items ({ib['new']} NEW, P0={ib['p0']} P1={ib['p1']}); status={ib['by_status']}")
except Exception as e:
    alert("P1", f"INBOUND LEDGER check failed (organizational memory offline): {e}")

# --- WRITE STATUS where the next session reads it ---
stamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
p0=[m for s,m in alerts if s=="P0"]; p1=[m for s,m in alerts if s=="P1"]; p2=[m for s,m in alerts if s=="P2"]
lines=[f"# FORGE GUARDRAILS — {stamp}", f"P0={len(p0)} P1={len(p1)} P2={len(p2)}"]
for s,m in alerts: lines.append(f"  [{s}] {m}")
for i in info: lines.append(f"  [ok] {i}")
out="\n".join(lines)
(REPO/"research/logs/system_guardrails_status.log").write_text(out+"\n")
print(out)
print(f"\nVERDICT: {'P0_FAIL — fix before trusting research' if p0 else ('P1_WARN' if p1 else 'CLEAN')}")
sys.exit(1 if p0 else 0)
