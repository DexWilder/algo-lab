"""FORGE TRIAL LEDGER (P1, 2026-06-29) — automatic multiple-testing N counter.
Every packet/test/basket attempt appends here; DSR-at-N reads count() so the multiple-testing correction is
AUTOMATIC, not memory-based (root cause: trial-N was manual in ALPHA_INTAKE_FACTORY §8 and could drift).
Usage:  from research.forge_trial_ledger import record, count
        record("P16_volume_climax", asset="MES", sharpe=0.3, verdict="KILL")
        N = count()   # -> pass to deflated_sharpe(returns, N, ...)"""
import json, sys
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path("/Users/chasefisher/projects/Algo Trading/algo-lab")
LEDGER=ROOT/"research/data/forge_trial_ledger.json"
def _load():
    if LEDGER.exists():
        try: return json.loads(LEDGER.read_text())
        except Exception: pass
    return {"trials": [], "note": "auto multiple-testing N; every test appends"}
def record(packet, asset="", sharpe=None, verdict="", horizon="", stamp=None):
    d=_load()
    d["trials"].append({"packet":packet,"asset":asset,"sharpe":sharpe,"verdict":verdict,"horizon":horizon,
                        "ts":stamp or datetime.now(timezone.utc).strftime("%Y-%m-%d")})
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(d, indent=2))
    return len(d["trials"])
def count(): return len(_load()["trials"])
def seed(entries):
    """One-time backfill of trials already run this session (so N reflects history)."""
    d=_load(); existing={(t["packet"],t.get("asset",""),t.get("horizon","")) for t in d["trials"]}
    added=0
    for e in entries:
        k=(e["packet"],e.get("asset",""),e.get("horizon",""))
        if k not in existing: d["trials"].append({**e,"ts":e.get("ts","2026-06-26")}); added+=1
    LEDGER.write_text(json.dumps(d, indent=2)); return added, len(d["trials"])
if __name__=="__main__":
    # backfill the session's trials so the multiple-testing N is honest going forward
    flat=[
        {"packet":"P02_equity_monthend","asset":"MES","verdict":"KILL"},
        {"packet":"P02_equity_monthend","asset":"MNQ","verdict":"KILL"},
        {"packet":"P04_zn_monthend","asset":"ZN","verdict":"SCREEN_PASS_RETAINED"},
        {"packet":"P04_crosstenor","asset":"ZF"},{"packet":"P04_crosstenor","asset":"ZB"},
        {"packet":"basket_B1","verdict":"FAIL"},{"packet":"basket_B2","verdict":"FAIL"},
        {"packet":"P03_auction","asset":"ZN","verdict":"KILL"},
        {"packet":"P14_vwap_reversion","verdict":"KILL"},{"packet":"P15_volume_momentum","verdict":"KILL"},
    ]
    for n in (1,2,4,5): flat.append({"packet":"P04_zn_window","asset":"ZN","horizon":str(n)})
    for a in ("MES","MNQ","MGC"): flat.append({"packet":"P13_overnight","asset":a})
    for a in ("Gold","ZN","6E","6J","6B","SP500","Nasdaq","Crude"):
        for h in ("L1w","L2w","L4w","S1w","S2w","S4w"): flat.append({"packet":"COT","asset":a,"horizon":h})
    n_add,total=seed(flat)
    print(f"seeded {n_add} trials; trial ledger N={total}")
    print(f"-> future DSR calls should use forge_trial_ledger.count() = {total}")
    sys.exit(0)
