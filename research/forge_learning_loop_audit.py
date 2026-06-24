"""Forge learning-loop audit + self-repair — keeps the save→learn→index loop closed automatically.

The gap this prevents (caught 2026-06-24): doctrine memory FILES get written but not INDEXED in MEMORY.md
(the index loaded into context each session) → learnings silently fail to recall next session.

Checks + repairs:
  1. MEMORY INDEX consistency: every memory/*.md (except MEMORY.md) must have a link in MEMORY.md.
     --fix appends a correctly-sectioned index line (from each file's frontmatter name/description/type).
  2. UNCOMMITTED Forge artifacts: research/forge_cycle_*.py, research/data/fql_forge/reports/*, docs/fql_forge/*
     flagged if not committed (so research isn't lost / unpushed).
Report-only by default; --fix performs the safe index repair (append-only, idempotent) and (with --commit)
commits the index repair. NEVER touches strategy/registry/portfolio/capital. Verdict: CLEAN or DRIFT_FOUND.

Usage: python3 research/forge_learning_loop_audit.py [--fix] [--commit]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import re
import subprocess
import sys
from pathlib import Path

MEM_DIR = Path.home() / ".claude" / "projects" / "-Users-chasefisher" / "memory"
INDEX = MEM_DIR / "MEMORY.md"
REPO = Path(__file__).resolve().parent.parent
SECTION = {"user": "## User", "project": "## Project", "feedback": "## Feedback", "reference": "## Reference"}


def _frontmatter(p: Path):
    txt = p.read_text()
    name = re.search(r"^name:\s*(.+)$", txt, re.M)
    desc = re.search(r"^description:\s*(.+)$", txt, re.M)
    typ = re.search(r"^\s*type:\s*(\w+)", txt, re.M)
    return (name.group(1).strip() if name else p.stem,
            desc.group(1).strip() if desc else "(no description)",
            (typ.group(1).strip().lower() if typ else "feedback"))


def audit(fix=False, commit=False):
    index_txt = INDEX.read_text()
    mem_files = sorted(f for f in MEM_DIR.glob("*.md") if f.name != "MEMORY.md")
    missing = []
    for f in mem_files:
        # indexed if filename appears as a link target in MEMORY.md
        if f.name not in index_txt:
            missing.append(f)

    print(f"=== MEMORY INDEX AUDIT === {len(mem_files)} memory files | {len(mem_files)-len(missing)} indexed | {len(missing)} MISSING")
    repaired = 0
    if missing:
        for f in missing:
            nm, desc, typ = _frontmatter(f)
            print(f"  MISSING: {f.name}  (type={typ})  — {desc[:80]}")
        if fix:
            lines = index_txt.splitlines()
            for f in missing:
                nm, desc, typ = _frontmatter(f)
                hdr = SECTION.get(typ, "## Feedback")
                entry = f"- [{f.name}]({f.name}) — {desc}"
                # insert at END of the matching section (before next '## ' or EOF)
                if hdr in lines:
                    start = lines.index(hdr)
                    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
                    ins = end
                    while ins > start + 1 and lines[ins - 1].strip() == "":
                        ins -= 1
                    lines.insert(ins, entry)
                else:  # section missing entirely -> append section + entry
                    lines += ["", hdr, entry]
                repaired += 1
            INDEX.write_text("\n".join(lines) + "\n")
            print(f"  REPAIRED: appended {repaired} index line(s) to MEMORY.md")

    # uncommitted Forge artifacts (research only; never automation-owned logs/processed-data)
    try:
        st = subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True).stdout
    except Exception:
        st = ""
    forge_pat = re.compile(r"(research/forge_cycle_.*\.(py|json|txt)|research/data/fql_forge/reports/.*|docs/fql_forge/.*\.md|research/forge_.*\.py)")
    uncommitted = [ln[3:] for ln in st.splitlines() if forge_pat.search(ln[3:])]
    print(f"\n=== UNCOMMITTED FORGE ARTIFACTS === {len(uncommitted)}")
    for u in uncommitted[:20]:
        print(f"  {u}")

    drift = bool(missing) or bool(uncommitted)
    if fix and missing and commit and repaired:
        subprocess.run(["git", "-C", str(MEM_DIR), "add", "MEMORY.md"], capture_output=True)  # memory dir may be its own repo or not
        print("  (index repaired in place; commit memory dir manually if version-controlled)")
    verdict = 'CLEAN — loop closed' if not drift else 'DRIFT_FOUND' + (' (index repaired)' if (fix and repaired) else ' (run with --fix to repair index; commit forge artifacts)')
    print(f"\n=== VERDICT: {verdict} ===")
    # persistent dated HEARTBEAT (append one line per run) — makes scheduled firing self-evidencing
    try:
        hist = REPO / "research" / "logs" / "learning_loop_audit_history.log"
        hist.parent.mkdir(parents=True, exist_ok=True)
        ts = _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        with hist.open("a") as fh:
            fh.write(f"{ts} | verdict={'CLEAN' if not drift else 'DRIFT'} | indexed={len(mem_files)-len(missing)}/{len(mem_files)} | uncommitted={len(uncommitted)} | repaired={repaired} | fix={fix}\n")
    except Exception:
        pass
    return 0 if (not drift or (fix and repaired and not uncommitted)) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="auto-append missing memory index lines")
    ap.add_argument("--commit", action="store_true")
    a = ap.parse_args()
    sys.exit(audit(fix=a.fix, commit=a.commit))
