"""INBOUND CAPTURE — the organizational memory layer. Operating law: if something is not in the inbound ledger, queue,
dashboard, control map, or archived status, the SYSTEM DOES NOT KNOW IT. Every operator directive, Claude discovery, source
note, data feed, harness, strategy idea, validation failure, bug, guardrail finding, paid-data idea, or old ledger item is
captured here with a stable ID, triaged status, and links to packet/queue/control. JSON is source-of-truth; MD is a rendered
view; stats() is imported by guardrails + dashboard so nothing floats.
  python3 research/capture_inbound.py --type "operator directive" --note "..." --family "..." --priority P0 [--status QUEUED --queue]
  python3 research/capture_inbound.py --backfill      # idempotent seed of known inbound history
  python3 research/capture_inbound.py --render        # regenerate the markdown view
  python3 research/capture_inbound.py --stats         # print triage stats (also importable)"""
import json, sys, argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
REPO=Path("/Users/chasefisher/projects/Algo Trading/algo-lab")
LJSON=REPO/"research/data/inbound_research_ledger.json"
LMD=REPO/"docs/fql_forge/INBOUND_RESEARCH_LEDGER.md"
QUEUE=REPO/"research/data/forge_run_queue.json"
STATUSES=["NEW","TRIAGED","QUEUED","ACTIVE_PACKET_LANE","DATA_STATUS_UNPROVEN","CERTIFIED_BLOCKED","NEEDS_BESPOKE_HARNESS",
          "RETEST_REQUIRED","CLEAN_KILL","ARCHIVED_LOW_PRIORITY","PROMOTED_TO_PACKET","INVENTORIED_UNUSED","CONTROL_REQUIRED","PACKET_REQUIRED"]
TYPES=["operator directive","claude discovery","source","data feed","harness","strategy idea","validation failure","bug",
       "guardrail finding","paid-data idea","old report"]
FIELDS=["inbound_id","date","source_type","source_ref","raw_note","mechanism","family","required_data","available_data",
        "required_harness","status","priority","next_action","linked_packet","linked_queue","linked_control"]
def _today(): return datetime.now(timezone.utc).strftime("%Y-%m-%d")
def load():
    try: return json.loads(LJSON.read_text())
    except Exception: return {"note":"inbound research ledger — source of truth (MD is a view)","items":[]}
def save(d):
    LJSON.parent.mkdir(parents=True,exist_ok=True); LJSON.write_text(json.dumps(d,indent=2))
def _natural_key(it): return (it.get("source_type",""), (it.get("raw_note") or "")[:70].lower().strip())
def next_id(d, date):
    n=sum(1 for it in d["items"] if it.get("date")==date)+1
    return f"INB-{date.replace('-','')}-{n:03d}"
def add_item(d=None, save_after=True, queue=False, **kw):
    d=d or load()
    kw.setdefault("date",_today()); kw.setdefault("status","NEW"); kw.setdefault("priority","P2")
    key=_natural_key(kw)
    for it in d["items"]:
        if _natural_key(it)==key:   # idempotent update-in-place
            it.update({k:v for k,v in kw.items() if v is not None});
            if save_after: save(d); render(d)
            return it["inbound_id"], False
    iid=next_id(d,kw["date"]); item={f:kw.get(f) for f in FIELDS}; item["inbound_id"]=iid
    d["items"].append(item)
    if queue or kw.get("status") in ("QUEUED","ACTIVE_PACKET_LANE"):
        _ensure_queue(iid, kw.get("raw_note") or kw.get("mechanism") or "", kw.get("family",""))
        item["linked_queue"]=item.get("linked_queue") or f"queue:{iid}"
    if save_after: save(d); render(d)
    return iid, True
def _ensure_queue(iid, note, fam):
    try: q=json.loads(QUEUE.read_text())
    except Exception: q={"queue":[]}
    if not any(x.get("id")==iid for x in q["queue"]):
        q["queue"].append({"id":iid,"status":"BACKLOG","lane":"inbound","note":f"[{fam}] {note[:90]}"})
        QUEUE.write_text(json.dumps(q,indent=2))
def render(d=None):
    d=d or load(); items=d["items"]
    order={s:i for i,s in enumerate(["NEW","CONTROL_REQUIRED","PACKET_REQUIRED","DATA_STATUS_UNPROVEN","RETEST_REQUIRED",
        "NEEDS_BESPOKE_HARNESS","QUEUED","ACTIVE_PACKET_LANE","INVENTORIED_UNUSED","TRIAGED","PROMOTED_TO_PACKET","CERTIFIED_BLOCKED","CLEAN_KILL","ARCHIVED_LOW_PRIORITY"])}
    pr={"P0":0,"P1":1,"P2":2,"P3":3}
    items=sorted(items,key=lambda it:(pr.get(it.get("priority"),9),order.get(it.get("status"),99),it.get("inbound_id","")))
    st=stats(d)
    lines=[f"# Inbound Research Ledger (rendered {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')})",
      "> **Operating law:** if it is not in this ledger, the queue, the dashboard, or the control map — the system does not know it.",
      f"> Source of truth: `research/data/inbound_research_ledger.json`. Capture: `python3 research/capture_inbound.py`. Items: **{len(d['items'])}**.",
      f"> NEW:{st['new']} | P0/P1:{st['p0']}/{st['p1']} | untriaged directives:{len(st['untriaged_directives'])} | mistakes w/o control:{len(st['mistakes_no_control'])} | unused feeds:{len(st['feeds_no_lane'])} | source notes unresolved:{len(st['source_unresolved'])}","",
      "| id | date | type | status | P | family | mechanism / issue | next action | linked (packet/queue/control) |",
      "|---|---|---|---|---|---|---|---|---|"]
    for it in items:
        link=" ".join(x for x in [it.get("linked_packet"),it.get("linked_queue"),it.get("linked_control")] if x) or "—"
        lines.append(f"| {it['inbound_id']} | {it.get('date','')} | {it.get('source_type','')} | {it.get('status','')} | {it.get('priority','')} | {it.get('family') or '—'} | {(it.get('mechanism') or it.get('raw_note') or '')[:70]} | {(it.get('next_action') or '—')[:50]} | {link[:60]} |")
    LMD.parent.mkdir(parents=True,exist_ok=True); LMD.write_text("\n".join(lines))
def stats(d=None, new_age_days=4):
    d=d or load(); items=d["items"]; today=datetime.now(timezone.utc).date()
    def age(it):
        try: return (today-datetime.strptime(it["date"],"%Y-%m-%d").date()).days
        except Exception: return 0
    try: qids={x.get("id") for x in json.loads(QUEUE.read_text())["queue"]}
    except Exception: qids=set()
    new=[it for it in items if it.get("status")=="NEW"]
    stale_new=[it["inbound_id"] for it in new if age(it)>new_age_days]
    untriaged_directives=[it["inbound_id"] for it in items if it.get("source_type")=="operator directive"
        and (it.get("status")=="NEW" or not (it.get("linked_control") or it.get("linked_queue") or it.get("linked_packet")))]
    mistakes_no_control=[it["inbound_id"] for it in items if it.get("source_type") in ("bug","validation failure","guardrail finding")
        and not it.get("linked_control") and it.get("status") not in ("CLEAN_KILL","ARCHIVED_LOW_PRIORITY","RETEST_REQUIRED")]
    feeds_no_lane=[it["inbound_id"] for it in items if it.get("source_type")=="data feed" and it.get("status")=="INVENTORIED_UNUSED"]
    ideas_unmapped=[it["inbound_id"] for it in items if it.get("source_type")=="strategy idea"
        and not (it.get("family") and it.get("required_harness") and it.get("required_data"))]
    queued_missing=[it["inbound_id"] for it in items if it.get("status") in ("QUEUED","ACTIVE_PACKET_LANE")
        and not (it.get("linked_queue") or it["inbound_id"] in qids)]
    source_unresolved=[it["inbound_id"] for it in items if it.get("source_type")=="source"
        and it.get("status") not in ("PROMOTED_TO_PACKET","ARCHIVED_LOW_PRIORITY","CLEAN_KILL")]
    from collections import Counter
    return dict(total=len(items), new=len(new), stale_new=stale_new,
        p0=sum(1 for it in items if it.get("priority")=="P0"), p1=sum(1 for it in items if it.get("priority")=="P1"),
        by_status=dict(Counter(it.get("status") for it in items)),
        untriaged_directives=untriaged_directives, mistakes_no_control=mistakes_no_control,
        feeds_no_lane=feeds_no_lane, ideas_unmapped=ideas_unmapped, queued_missing=queued_missing,
        source_unresolved=source_unresolved, oldest_untriaged=max([age(it) for it in new],default=0),
        source_packets_today=sum(1 for it in items if it.get("source_type")=="source" and it.get("date")==_today()))

def backfill():
    d=load()
    B=[
     dict(source_type="operator directive",date="2026-06-26",priority="P0",status="TRIAGED",family="data governance",
       raw_note="Use ALL Databento feeds + local data before any paid-data conclusion",mechanism="inventory-before-exhausted-claim",
       linked_control="forge_system_guardrails.py (unused-databento) + memory inventory_before_exhausted_claim",next_action="keep databento/1m lane active"),
     dict(source_type="bug",date="2026-06-30",priority="P0",status="TRIAGED",family="data governance",
       raw_note="False DATA_BLOCKED labels asserted without lineage proof",mechanism="unproven blocker claim",
       linked_control="DATA_BLOCKER_CERTIFICATES + guardrail P1 (cert required)",next_action="none — control locked"),
     dict(source_type="data feed",date="2026-06-30",priority="P1",status="ACTIVE_PACKET_LANE",family="term structure",
       raw_note="Per-contract Databento re-pull (ZT/ZF/ZN/ZB/CL/GC ohlcv-1d)",mechanism="term-structure curve data",
       available_data="LOCAL",required_harness="term_structure.py",linked_packet="term_structure.py"),
     dict(source_type="bug",date="2026-06-30",priority="P2",status="TRIAGED",family="data integrity",
       raw_note="CL/GC date-column dropped on save (ts_event was index)",mechanism="save-time column loss",
       linked_control="validate_data_file.py",next_action="none — validator guards"),
     dict(source_type="bug",date="2026-06-25",priority="P0",status="TRIAGED",family="causality",
       raw_note="ORB ema_slope filter uses same-day session close (lookahead)",mechanism="same-day-close lookahead",
       linked_control="causality_audit.py + memory project_orb_ema_slope_lookahead",next_action="ORB family INVALIDATED"),
     dict(source_type="validation failure",date="2026-06-13",priority="P1",status="RETEST_REQUIRED",family="port fidelity",
       raw_note="stop_run_reversal port contamination risk (research->runner fidelity)",mechanism="port byte-fidelity",
       linked_control="feedback_port_fidelity_discipline",next_action="prove signal-hash on audit window before wiring"),
     dict(source_type="bug",date="2026-06-26",priority="P2",status="TRIAGED",family="harness hygiene",
       raw_note="Old harness bypass / P03 auction duplicate trial",mechanism="duplicate/bypassed harness",
       linked_control="guardrail unrun-harnesses + forge_trial_ledger dedup",next_action="none"),
     dict(source_type="guardrail finding",date="2026-06-26",priority="P1",status="TRIAGED",family="governance",
       raw_note="Monthly audit blind spot — checks were unread docs not machine checks",mechanism="non-fail-loud enforcement",
       linked_control="forge_system_guardrails.py (every-cycle) + memory system_guardrails_fail_loud",next_action="run guardrails each cycle"),
     dict(source_type="bug",date="2026-06-25",priority="P2",status="CONTROL_REQUIRED",family="automation",
       raw_note="forge-daily-loop stale-tripwire bug",mechanism="stale tripwire not firing",next_action="add freshness check to loop"),
     dict(source_type="bug",date="2026-06-25",priority="P1",status="TRIAGED",family="causality",
       raw_note="Feature-cache hash ignores close content (perturbation cache leak)",mechanism="cache key ignores close",
       linked_control="causality_audit.py _clear_cache()",next_action="none — audit clears cache"),
     dict(source_type="guardrail finding",date="2026-06-29",priority="P1",status="TRIAGED",family="multiple-testing",
       raw_note="Trial-N was manual/memory-based, could drift",mechanism="uncounted multiple-testing N",
       linked_control="forge_trial_ledger.py (automatic count)",next_action="DSR reads count()"),
     dict(source_type="guardrail finding",date="2026-06-26",priority="P1",status="TRIAGED",family="labeling",
       raw_note="WH/validated/paper-ready language drift risk",mechanism="overclaim language",
       linked_control="forge_system_guardrails.py WH-scan + candidate ladder",next_action="scan recent docs each cycle"),
     dict(source_type="old report",date="2026-06-16",priority="P2",status="RETEST_REQUIRED",family="rescue (Lane F)",
       raw_note="83 idea-ledger + 10 watch registry items parked",mechanism="dormant inventory",
       linked_control="Lane F rescue",next_action="retest under truth-gated harness, ranked"),
     dict(source_type="data feed",date="2026-06-26",priority="P1",status="ACTIVE_PACKET_LANE",family="macro/carry",
       raw_note="Local data/feeds library (yield curve, policy rates, vix, cot) under-used",mechanism="unused feeds",
       available_data="LOCAL",linked_control="guardrail unused-feeds",next_action="attach each feed to a packet lane"),
     dict(source_type="paid-data idea",date="2026-07-01",priority="P1",status="NEEDS_BESPOKE_HARNESS",family="gamma/dealer",
       raw_note="Gamma/options OI pull (ES.OPT) for GEX",mechanism="dealer gamma / OPEX pin",required_data="ES.OPT statistics OI",
       available_data="pullable (cost ~$11.54 >$5 => operator $ gate; 'pull gamma' approved in principle)",
       required_harness="chunked-OI loader (5-mo pull 504-timed-out)",next_action="build chunked loader then approx-GEX"),
     dict(source_type="claude discovery",date="2026-07-01",priority="P1",status="ACTIVE_PACKET_LANE",family="carry_commodity",
       raw_note="Commodity term-structure sprint (CL/GC carry)",mechanism="roll-yield carry + spread",
       linked_packet="SPRINT_COMMODITY_CARRY_VERDICT_2026-07-01.md",next_action="naive carry KILLed; refined -> spreadMR_GC"),
     dict(source_type="claude discovery",date="2026-07-01",priority="P1",status="PROMOTED_TO_PACKET",family="carry_commodity",
       raw_note="spreadMR_GC gold calendar-spread MR = first SCREEN_PASS candidate",mechanism="gold calendar-spread mean-reversion",
       required_data="GC per-contract (LOCAL)",required_harness="term-structure MR",
       linked_packet="SCREEN_PASS_CANDIDATE_spreadMR_GC_2026-07-01.md",linked_queue="deepen_spreadMR_GC_*",next_action="Lane G deepening (operator-gated for capital)"),
     dict(source_type="bug",date="2026-07-01",priority="P2",status="TRIAGED",family="review calibration",
       raw_note="Adversarial reviewer false-flagged sparse tail strategies as DEGENERATE_SIDE",mechanism="side-share over all days not active",
       linked_control="adversarial_result_review.py (active-side + SPARSE_LOW_N)",next_action="none — fixed"),
     dict(source_type="validation failure",date="2026-07-01",priority="P1",status="NEEDS_BESPOKE_HARNESS",family="multiple-testing",
       raw_note="spreadMR_GC DSR cliff — credible N<=20, fails N>=30; search-N ambiguous",mechanism="layered-N ambiguity",
       linked_queue="deepen_spreadMR_GC_searchN",next_action="pin honest search-N; blocks advancement past SCREEN_PASS"),
     dict(source_type="validation failure",date="2026-07-01",priority="P1",status="RETEST_REQUIRED",family="execution realism",
       raw_note="spreadMR_GC 63% PnL near F2 rolls (stale deferred price risk)",mechanism="roll-adjacent concentration",
       linked_queue="deepen_spreadMR_GC_execution",next_action="2-leg calendar-spread exec model + tick/1m near roll"),
     dict(source_type="validation failure",date="2026-07-01",priority="P2",status="CLEAN_KILL",family="carry_commodity",
       raw_note="CL calendar-spread MR Sh -0.01 (cross-asset FAIL)",mechanism="cross-asset generalization",
       next_action="gold-specific noted; not a family win"),
     dict(source_type="operator directive",date="2026-06-30",priority="P1",status="TRIAGED",family="sourcing",
       raw_note="Source-intake quotas + novelty generation engine required",mechanism="grow opportunity surface",
       linked_control="forge_novelty_engine.py (generative) + ALPHA_RESEARCH_OS_ELITE_MODE",next_action="run novelty engine, keep BACKLOG full"),
     dict(source_type="operator directive",date="2026-06-30",priority="P1",status="TRIAGED",family="validation",
       raw_note="Adversarial review layer required (not Claude reviewing Claude only)",mechanism="hostile second-pass",
       linked_control="adversarial_result_review.py",next_action="review every hardening result; later OpenClaw red-team"),
     dict(source_type="operator directive",date="2026-07-01",priority="P0",status="ACTIVE_PACKET_LANE",family="organizational memory",
       raw_note="Build the inbound capture system (no terminal-only discoveries)",mechanism="inbound ledger->triage->queue->control->dashboard",
       linked_control="capture_inbound.py + INBOUND_TRIAGE_RULES + guardrail inbound checks",next_action="operationalize + backfill (this build)"),
    ]
    added=0
    for b in B:
        _,new=add_item(d, save_after=False, **b); added+=1 if new else 0
    save(d); render(d)
    return added, len(d["items"])

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--type",dest="source_type"); ap.add_argument("--note",dest="raw_note"); ap.add_argument("--mechanism")
    ap.add_argument("--family"); ap.add_argument("--priority",default="P2"); ap.add_argument("--status",default="NEW")
    ap.add_argument("--ref",dest="source_ref"); ap.add_argument("--data",dest="required_data"); ap.add_argument("--available",dest="available_data")
    ap.add_argument("--harness",dest="required_harness"); ap.add_argument("--next",dest="next_action"); ap.add_argument("--date")
    ap.add_argument("--linked-packet",dest="linked_packet"); ap.add_argument("--linked-queue",dest="linked_queue"); ap.add_argument("--linked-control",dest="linked_control")
    ap.add_argument("--queue",action="store_true"); ap.add_argument("--backfill",action="store_true")
    ap.add_argument("--render",action="store_true"); ap.add_argument("--stats",action="store_true")
    a=ap.parse_args()
    if a.backfill:
        n,tot=backfill(); print(f"backfill: {n} new inbound items, ledger total={tot}")
    elif a.render:
        render(); print("rendered INBOUND_RESEARCH_LEDGER.md")
    elif a.stats:
        import pprint; pprint.pprint(stats())
    elif a.raw_note:
        kw={k:getattr(a,k) for k in FIELDS if hasattr(a,k) and getattr(a,k) is not None}
        iid,new=add_item(queue=a.queue,**kw); print(f"{'added' if new else 'updated'} {iid} [{a.status}]")
    else:
        ap.print_help()
