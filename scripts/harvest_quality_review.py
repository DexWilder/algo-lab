#!/usr/bin/env python3
"""Harvest Quality Review — measures whether the wide net is producing value.

Run after 1-2 weekly cycles to verify that broadened source lanes are
generating useful ideas, not just volume.

Usage:
    python3 scripts/harvest_quality_review.py              # Print
    python3 scripts/harvest_quality_review.py --save       # Print + save to inbox
    python3 scripts/harvest_quality_review.py --days 14    # Custom lookback
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

HARVEST_DIR = Path.home() / "openclaw-intake" / "inbox" / "harvest"
REVIEWED_DIR = Path.home() / "openclaw-intake" / "reviewed"
REJECTED_DIR = Path.home() / "openclaw-intake" / "rejected"
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
OUTPUT_PATH = Path.home() / "openclaw-intake" / "inbox" / "_harvest_quality_review.md"

NOW = datetime.now().strftime("%Y-%m-%d %H:%M")
ALL_FACTORS = ["MOMENTUM", "MEAN_REVERSION", "VOLATILITY", "CARRY", "EVENT", "STRUCTURAL", "VALUE"]


def _classify_source(text):
    """Classify a note's source from its content."""
    text_lower = text.lower()
    for line in text.split("\n"):
        if line.startswith("- source URL:") or line.startswith("- source url:"):
            url = line.split(":", 1)[-1].strip() if ":" in line else ""
            if "tradingview" in url:
                return "TradingView"
            if "ssrn" in url or "quantpedia" in url or "doi.org" in url or "arxiv" in url:
                return "Academic"
            if "youtube" in url:
                return "YouTube"
            if "github" in url:
                return "GitHub"
            if "reddit" in url or "elitetrader" in url:
                return "Reddit/Forum"
            if "internal" in url:
                return "Claw synthesis"
            return "Other"
    return "Unknown"


def _extract_factor(text):
    """Extract factor from a note's content."""
    for line in text.split("\n"):
        if line.startswith("- factor fit:"):
            factor = line.split(":")[-1].strip().upper()
            for f in ALL_FACTORS:
                if f in factor:
                    return f
    return "UNKNOWN"


def _extract_verdict(text):
    """Extract verdict from a note."""
    for line in text.split("\n"):
        if line.startswith("- verdict:"):
            v = line.split(":")[-1].strip().lower()
            if "reject" in v:
                return "REJECTED"
            if "blocked" in v:
                return "BLOCKED"
            if "review" in v:
                return "NEEDS_REVIEW"
            if "accept" in v:
                return "ACCEPTED"
    return "UNKNOWN"


def scan_notes(lookback_days):
    """Scan all harvest notes within the lookback window."""
    cutoff = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    notes = []

    for directory, status in [
        (HARVEST_DIR, "pending"),
        (REVIEWED_DIR, "accepted"),
        (REJECTED_DIR, "rejected"),
    ]:
        if not directory.exists():
            continue
        for f in directory.glob("*.md"):
            date_part = f.name[:10]
            if date_part < cutoff:
                continue
            try:
                text = f.read_text()
            except Exception:
                continue

            notes.append({
                "filename": f.name,
                "date": date_part,
                "source": _classify_source(text),
                "factor": _extract_factor(text),
                "verdict": _extract_verdict(text),
                "status": status,
            })

    return notes


def check_registry_conversions(lookback_days):
    """Check how many harvest notes made it to registry testing/probation."""
    if not REGISTRY_PATH.exists():
        return {}
    reg = json.load(open(REGISTRY_PATH))
    cutoff = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    conversions = Counter()
    for s in reg.get("strategies", []):
        if s.get("status") in ("testing", "probation"):
            # Check if entered recently
            for h in s.get("state_history", []):
                if h.get("date", "") >= cutoff:
                    source = s.get("source_category", "unknown")
                    conversions[source] += 1
    return dict(conversions)


def generate_report(lookback_days):
    notes = scan_notes(lookback_days)
    conversions = check_registry_conversions(lookback_days)

    lines = []
    lines.append("# Harvest Quality Review")
    lines.append(f"*Generated: {NOW} | Lookback: {lookback_days} days*")
    lines.append("")

    if not notes:
        lines.append("No harvest notes found in the review period.")
        return "\n".join(lines)

    total = len(notes)
    lines.append(f"**Total notes scanned: {total}**")

    # ── Notes by source ──
    lines.append("")
    lines.append("## Notes by Source Lane")
    lines.append("")

    source_counts = Counter(n["source"] for n in notes)
    source_factors = defaultdict(Counter)
    source_verdicts = defaultdict(Counter)
    for n in notes:
        source_factors[n["source"]][n["factor"]] += 1
        source_verdicts[n["source"]][n["verdict"]] += 1

    lines.append("| Source | Notes | % | Accepted | Blocked | Rejected | Top Factor |")
    lines.append("|--------|-------|---|----------|---------|----------|------------|")

    for source, count in source_counts.most_common():
        pct = count / total * 100
        verdicts = source_verdicts[source]
        accepted = verdicts.get("ACCEPTED", 0)
        blocked = verdicts.get("BLOCKED", 0)
        rejected = verdicts.get("REJECTED", 0)
        top_factor = source_factors[source].most_common(1)[0][0] if source_factors[source] else "—"
        lines.append(f"| {source:<16s} | {count:>5d} | {pct:>2.0f}% | {accepted:>8d} | {blocked:>7d} | {rejected:>8d} | {top_factor} |")

    # Source diversity check
    lines.append("")
    n_sources = len(source_counts)
    dominant = source_counts.most_common(1)[0] if source_counts else ("?", 0)
    dominant_pct = dominant[1] / total * 100 if total > 0 else 0

    if n_sources < 3:
        lines.append(f"**SOURCE DIVERSITY WARNING:** Only {n_sources} source type(s). Target: >= 3.")
    elif dominant_pct > 50:
        lines.append(f"**SOURCE CONCENTRATION:** {dominant[0]} at {dominant_pct:.0f}%. Target: no source > 50%.")
    else:
        lines.append(f"Source diversity: {n_sources} types, largest is {dominant[0]} at {dominant_pct:.0f}%. OK.")

    # ── Unique idea families by source ──
    lines.append("")
    lines.append("## Unique Idea Families by Source")
    lines.append("")

    # Approximate by factor × source
    unique_combos = set()
    source_unique = Counter()
    for n in notes:
        combo = (n["source"], n["factor"])
        if combo not in unique_combos:
            unique_combos.add(combo)
            source_unique[n["source"]] += 1

    lines.append("| Source | Unique Factor Families | Notes per Family |")
    lines.append("|--------|----------------------|------------------|")
    for source in sorted(source_unique.keys()):
        unique = source_unique[source]
        n_count = source_counts[source]
        ratio = n_count / unique if unique > 0 else 0
        dup_flag = " ◄ high duplication" if ratio > 4 else ""
        lines.append(f"| {source:<16s} | {unique:>22d} | {ratio:>16.1f}{dup_flag} |")

    # ── Gap fit ──
    lines.append("")
    lines.append("## Portfolio Gap Fit")
    lines.append("")

    factor_counts = Counter(n["factor"] for n in notes)
    gap_factors = {"VOLATILITY": "HIGH gap", "VALUE": "HIGH gap", "CARRY": "MEDIUM gap",
                   "STRUCTURAL": "MEDIUM gap", "EVENT": "MEDIUM gap"}

    lines.append("| Factor | Notes | Portfolio Gap | Targeting Effective? |")
    lines.append("|--------|-------|-------------|---------------------|")
    for f in ALL_FACTORS:
        count = factor_counts.get(f, 0)
        gap = gap_factors.get(f, "LOW/crowded")
        if gap.startswith("HIGH") and count == 0:
            effective = "**NO — gap not addressed**"
        elif gap.startswith("HIGH") and count > 0:
            effective = "YES"
        elif gap.startswith("MEDIUM") and count > 0:
            effective = "YES"
        elif f == "MOMENTUM" and count > 3:
            effective = "Over-harvesting crowded factor"
        else:
            effective = "OK"
        lines.append(f"| {f:<15s} | {count:>5d} | {gap:<13s} | {effective} |")

    # ── Noise / rejection rate ──
    lines.append("")
    lines.append("## Noise Rate by Source")
    lines.append("")

    lines.append("| Source | Accepted | Needs Review | Blocked | Rejected | Noise Rate |")
    lines.append("|--------|----------|-------------|---------|----------|------------|")
    for source, count in source_counts.most_common():
        v = source_verdicts[source]
        accepted = v.get("ACCEPTED", 0)
        review = v.get("NEEDS_REVIEW", 0) + v.get("UNKNOWN", 0)
        blocked = v.get("BLOCKED", 0)
        rejected = v.get("REJECTED", 0)
        noise = rejected / count * 100 if count > 0 else 0
        flag = " ◄ high noise" if noise > 40 else ""
        lines.append(f"| {source:<16s} | {accepted:>8d} | {review:>11d} | {blocked:>7d} | {rejected:>8d} | {noise:>9.0f}%{flag} |")

    # ── Conversion pipeline ──
    lines.append("")
    lines.append("## Conversion Pipeline")
    lines.append("")
    if conversions:
        lines.append("Notes that reached testing/probation in this period:")
        for source, count in sorted(conversions.items(), key=lambda x: -x[1]):
            lines.append(f"  - {source}: {count}")
    else:
        lines.append("No notes converted to testing/probation in this period.")
    lines.append("(Normal for early cycles — conversion is selective and gated.)")

    # ── Source helper metrics ──
    lines.append("")
    lines.append("## Source Helper Pipeline")
    lines.append("")

    manifest_path = Path.home() / "openclaw-intake" / "inbox" / "source_leads" / "_manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.load(open(manifest_path))
            runs = manifest.get("runs", [])
            lifecycle = manifest.get("lifecycle", {})

            if runs:
                last_run = runs[-1]
                lines.append(f"**Last fetch:** {last_run.get('timestamp', '?')}")
                lines.append(f"- GitHub: {last_run.get('github_leads', 0)} leads")
                lines.append(f"- Reddit: {last_run.get('reddit_leads', 0)} leads")
                lines.append(f"- YouTube: {last_run.get('youtube_leads', 0)} leads")
                lines.append(f"- Total: {last_run.get('total', 0)} leads")
                lines.append("")

            # Lifecycle summary
            fetched = sum(1 for v in lifecycle.values() if v.get("status") == "fetched")
            picked = sum(1 for v in lifecycle.values() if v.get("status") == "picked_up")
            stale = sum(1 for v in lifecycle.values() if v.get("status") == "stale")
            total_notes = sum(v.get("notes_produced", 0) for v in lifecycle.values())

            lines.append(f"**Lead lifecycle:** {fetched} fetched, {picked} picked up, {stale} stale")
            lines.append(f"**Notes produced from leads:** {total_notes}")

            if picked > 0 and total_notes == 0:
                lines.append("**NOTE:** Leads were picked up but produced 0 harvest notes.")
                lines.append("This may mean lead quality is low, or Claw filtered all of them.")
            elif total_notes > 0:
                conversion = total_notes / (fetched + picked + stale) * 100 if (fetched + picked + stale) > 0 else 0
                lines.append(f"**Conversion rate:** {conversion:.0f}% of lead batches produced notes")

            # Component yield by source
            attr = manifest.get("last_attribution", {})
            note_types = attr.get("note_types_by_source", {})
            comp_detail = attr.get("components_by_source", {})

            if note_types or comp_detail:
                lines.append("")
                lines.append("### Component Yield by Source")
                lines.append("")
                lines.append("| Source | Notes | Full Strategy | Fragments | Components Detected |")
                lines.append("|--------|-------|--------------|-----------|-------------------|")

                all_sources = set(list(note_types.keys()) + list(comp_detail.keys()))
                for src in sorted(all_sources):
                    nt = note_types.get(src, {})
                    full = nt.get("full_strategy", 0)
                    frag = nt.get("fragment", 0)
                    notes_n = full + frag
                    comps = comp_detail.get(src, {})
                    comp_str = ", ".join(f"{k}={v}" for k, v in comps.items()) if comps else "none"
                    lines.append(f"| {src:<8s} | {notes_n:>5d} | {full:>12d} | {frag:>9d} | {comp_str} |")

                # Best fragment source
                best_frag = max(note_types.items(), key=lambda x: x[1].get("fragment", 0), default=None)
                best_comp = max(comp_detail.items(), key=lambda x: sum(x[1].values()), default=None)
                if best_frag and best_frag[1].get("fragment", 0) > 0:
                    lines.append(f"\n**Best fragment source:** {best_frag[0]} ({best_frag[1]['fragment']} fragments)")
                if best_comp:
                    lines.append(f"**Best component source:** {best_comp[0]} ({sum(best_comp[1].values())} components detected)")

            # Source role classification
            lines.append("")
            lines.append("### Source Roles")
            lines.append("")
            lines.append("*Auto-classified from observed contribution. Activates after 2+ attributed notes per source.*")
            lines.append("")

            # Gather per-source metrics from lifecycle + attribution
            source_metrics = {}
            for key, entry in lifecycle.items():
                src = entry.get("source", "")
                if not src:
                    continue
                if src not in source_metrics:
                    source_metrics[src] = {"leads": 0, "notes": 0, "full": 0, "frag": 0, "comps": 0}
                source_metrics[src]["leads"] += entry.get("count", 0)
                source_metrics[src]["notes"] += entry.get("notes_produced", 0)

            # Add component detail from attribution
            for src, nt in note_types.items():
                if src not in source_metrics:
                    source_metrics[src] = {"leads": 0, "notes": 0, "full": 0, "frag": 0, "comps": 0}
                source_metrics[src]["full"] = nt.get("full_strategy", 0)
                source_metrics[src]["frag"] = nt.get("fragment", 0)
            for src, cd in comp_detail.items():
                if src in source_metrics:
                    source_metrics[src]["comps"] = sum(cd.values())

            # Classify roles
            lines.append("| Source | Leads | Notes | Fragments | Components | Role | Tuning |")
            lines.append("|--------|-------|-------|-----------|------------|------|--------|")

            for src in sorted(source_metrics.keys()):
                m = source_metrics[src]
                leads = m["leads"]
                notes = m["notes"]
                frags = m["frag"]
                comps = m["comps"]
                full = m["full"]

                # Classify
                if notes == 0 and leads > 0:
                    role = "Unproven"
                    tuning = "Wait for data"
                elif notes >= 3 and (frags >= 2 or comps >= 3):
                    role = "**Fragment source**"
                    tuning = "Raise cap — produces reusable components"
                elif notes >= 3 and full >= 2:
                    role = "**Primary idea source**"
                    tuning = "Raise cap — produces full strategies"
                elif notes >= 1 and notes <= 2:
                    role = "Support/convergence"
                    tuning = "Keep — may confirm ideas from other sources"
                elif leads > 20 and notes == 0:
                    role = "Low-yield"
                    tuning = "Lower cap or tighten queries"
                else:
                    role = "Emerging"
                    tuning = "Monitor — needs more cycles"

                lines.append(
                    f"| {src:<8s} | {leads:>5d} | {notes:>5d} | {frags:>9d} | "
                    f"{comps:>10d} | {role} | {tuning} |"
                )

            if not source_metrics:
                lines.append("No source data yet. Run helpers and wait for attribution.")

            lines.append("")

            # Run history
            if len(runs) > 1:
                lines.append("")
                lines.append("### Run History")
                lines.append("")
                lines.append("| Run Date | GitHub | Reddit | YouTube | Blog | Digest | Total |")
                lines.append("|----------|--------|--------|---------|------|--------|-------|")
                for r in runs[-4:]:
                    lines.append(
                        f"| {r.get('timestamp','?')[:10]} | {r.get('github_leads',0)} | "
                        f"{r.get('reddit_leads',0)} | {r.get('youtube_leads',0)} | "
                        f"{r.get('blog_leads',0)} | {r.get('digest_leads',0)} | {r.get('total',0)} |"
                    )
        except Exception as e:
            lines.append(f"Could not read manifest: {e}")
    else:
        lines.append("No source helper manifest found. Helpers may not have run yet.")

    # ── Top new fragments this week ──
    lines.append("## Top New Fragments This Week")
    lines.append("")

    harvest_dir = Path.home() / "openclaw-intake" / "inbox" / "harvest"
    reviewed_dir = Path.home() / "openclaw-intake" / "reviewed"
    cutoff = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    fragments_found = []
    for d in [harvest_dir, reviewed_dir]:
        if not d.exists():
            continue
        for f in d.glob("*.md"):
            if f.name[:10] < cutoff:
                continue
            try:
                text = f.read_text()
                comp_type = None
                title = ""
                summary = ""
                factor = ""
                for line in text.split("\n"):
                    if line.startswith("- component_type:"):
                        comp_type = line.split(":", 1)[-1].strip()
                    elif line.startswith("- title:"):
                        title = line.split(":", 1)[-1].strip()
                    elif line.startswith("- summary:"):
                        summary = line.split(":", 1)[-1].strip()[:120]
                    elif line.startswith("- factor fit:"):
                        factor = line.split(":", 1)[-1].strip()

                if comp_type and comp_type != "full_strategy" and title:
                    fragments_found.append({
                        "title": title,
                        "type": comp_type,
                        "factor": factor,
                        "summary": summary,
                        "file": f.name,
                    })
            except Exception:
                pass

    if fragments_found:
        lines.append(f"**{len(fragments_found)} fragments captured this period:**")
        lines.append("")
        for frag in fragments_found[:5]:
            lines.append(f"- **[{frag['type']}]** {frag['title']} ({frag['factor']})")
            if frag["summary"]:
                lines.append(f"  {frag['summary']}")
        if len(fragments_found) > 5:
            lines.append(f"  ... and {len(fragments_found) - 5} more")
    else:
        lines.append("No non-full_strategy fragments captured this period.")
        lines.append("Check that _note_template.md examples are guiding Claw toward component tagging.")

    lines.append("")

    # ── Salvage wins ──
    lines.append("## Salvage Wins")
    lines.append("")
    lines.append("*Rejected parents that produced useful children or salvageable components.*")
    lines.append("")

    reg_path = ROOT / "research" / "data" / "strategy_registry.json"
    if reg_path.exists():
        try:
            reg = json.load(open(reg_path))
            salvage_wins = []
            for s in reg.get("strategies", []):
                rels = s.get("relationships", {})
                if rels.get("parent"):
                    # Find the parent
                    parent_id = rels["parent"]
                    parent = next((p for p in reg["strategies"] if p["strategy_id"] == parent_id), None)
                    if parent and parent.get("status") == "rejected":
                        salvage_wins.append({
                            "child": s["strategy_id"],
                            "child_status": s.get("status", "?"),
                            "parent": parent_id,
                            "parent_status": "rejected",
                        })

                # Also check for strategies with salvageable components
                comps = s.get("components", {})
                if s.get("status") == "rejected" and comps.get("salvageable"):
                    salvage_wins.append({
                        "child": f"[component] {comps['salvageable'][:60]}",
                        "child_status": "salvageable",
                        "parent": s["strategy_id"],
                        "parent_status": "rejected",
                    })

            if salvage_wins:
                lines.append(f"**{len(salvage_wins)} salvage wins found:**")
                lines.append("")
                seen = set()
                for sw in salvage_wins:
                    key = f"{sw['parent']}→{sw['child']}"
                    if key in seen:
                        continue
                    seen.add(key)
                    lines.append(f"- **{sw['parent']}** (rejected) → **{sw['child']}** ({sw['child_status']})")
            else:
                lines.append("No salvage wins yet. These appear when rejected strategies produce useful children or fragments.")
        except Exception:
            lines.append("Could not read registry.")
    else:
        lines.append("Registry not found.")

    lines.append("")

    # ── Recommendations ──
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")

    # Underperforming lanes
    for source, count in source_counts.items():
        noise = source_verdicts[source].get("REJECTED", 0) / count * 100 if count > 0 else 0
        if noise > 50:
            lines.append(f"- **Lower cap for {source}**: {noise:.0f}% noise rate. Reduce per-run cap or tighten noise filters.")
        elif count > 15 and dominant_pct > 40:
            lines.append(f"- **{source} is dominant** ({count} notes, {count/total*100:.0f}%). Ensure other lanes get search time.")

    # Gap coverage
    for f in ["VOLATILITY", "VALUE"]:
        if factor_counts.get(f, 0) == 0:
            lines.append(f"- **{f} gap not addressed** — no notes targeting this HIGH-priority gap. Check that search terms and factor_targets include {f}.")

    # Lane expansion
    low_lanes = [s for s, c in source_counts.items() if c <= 2]
    if low_lanes:
        lines.append(f"- **Low-volume lanes** ({', '.join(low_lanes)}): producing very few notes. Consider raising caps if quality is good.")

    if not any(True for _ in lines if "**" in _):
        lines.append("- No urgent issues. Continue current configuration.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Harvest Quality Review")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--days", type=int, default=14, help="Lookback period in days")
    args = parser.parse_args()

    report = generate_report(args.days)
    print(report)

    if args.save:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w") as f:
            f.write(report)
        print(f"\n  Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
