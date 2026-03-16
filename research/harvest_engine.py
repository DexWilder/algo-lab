#!/usr/bin/env python3
"""FQL Strategic Harvest Engine — Gap-aware idea sourcing framework.

Dormant by default. Reads harvest_config.yaml to determine which source
lanes are active and what genome-map gaps to target. Manages the intake
manifest, deduplication, and staging of new ideas.

This does NOT generate strategies or run backtests. It manages the intake
funnel: discover -> dedupe -> stage -> log to registry.

Usage:
    python3 research/harvest_engine.py --status        # Show lane status
    python3 research/harvest_engine.py --gaps           # Show current gap targets
    python3 research/harvest_engine.py --scan           # Scan intake folder for new notes
    python3 research/harvest_engine.py --run            # Run active harvest lanes
    python3 research/harvest_engine.py --run --dry-run  # Preview without writing
"""

import argparse
import json
import sys
import hashlib
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.utils.atomic_io import atomic_write_json

CONFIG_PATH = ROOT / "research" / "harvest_config.yaml"
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
MANIFEST_PATH = ROOT / "research" / "data" / "harvest_manifest.json"
GENOME_MAP_PATH = ROOT / "research" / "data" / "strategy_genome_map.json"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def load_manifest():
    if MANIFEST_PATH.exists():
        return json.load(open(MANIFEST_PATH))
    return {"items": [], "last_scan": None, "stats": {"total": 0, "staged": 0, "logged": 0, "rejected": 0}}


def save_manifest(manifest):
    atomic_write_json(MANIFEST_PATH, manifest)


def load_registry_ids():
    """Load all strategy IDs and names for dedup checking."""
    if not REGISTRY_PATH.exists():
        return set(), set()
    reg = json.load(open(REGISTRY_PATH))
    ids = {s["strategy_id"] for s in reg.get("strategies", [])}
    names = {s.get("strategy_name", "") for s in reg.get("strategies", []) if s.get("strategy_name")}
    return ids, names


def content_hash(text):
    """Generate a short hash for dedup."""
    return hashlib.md5(text.encode()).hexdigest()[:12]


# ── Gap-Aware Targeting ──────────────────────────────────────────────────────

def get_current_gaps(config):
    """Load gap priorities from config + genome map."""
    gaps = config.get("targeting", {}).get("priority_gaps", [])
    avoids = config.get("targeting", {}).get("avoid", [])

    # Enrich with genome map if available
    if GENOME_MAP_PATH.exists():
        try:
            gmap = json.load(open(GENOME_MAP_PATH))
            analysis = gmap.get("analysis", {})
            # Add any new gaps from genome map not already in config
            for gap in analysis.get("gaps", []):
                dim = gap.get("dimension", "")
                if not any(g.get("dimension") == dim.split(":")[0].strip() and
                           g.get("target") == dim.split(":")[-1].strip()
                           for g in gaps):
                    gaps.append({
                        "dimension": dim.split(":")[0].strip() if ":" in dim else dim,
                        "target": dim.split(":")[-1].strip() if ":" in dim else "",
                        "note": gap.get("note", ""),
                        "priority": "MEDIUM",
                        "source": "genome_map_auto",
                    })
        except Exception:
            pass

    return gaps, avoids


# ── Intake Scanner ───────────────────────────────────────────────────────────

def scan_intake_folder(config):
    """Scan OpenClaw intake folder for new harvest notes."""
    results = []

    for lane_name, lane in config.get("source_lanes", {}).items():
        intake_path = lane.get("intake_path", "")
        if not intake_path:
            continue

        intake_dir = Path(intake_path).expanduser()
        if not intake_dir.exists():
            continue

        for f in sorted(intake_dir.glob("*.md")):
            text = f.read_text()
            h = content_hash(text)
            results.append({
                "file": str(f),
                "filename": f.name,
                "lane": lane_name,
                "content_hash": h,
                "size": len(text),
                "title": _extract_title(text),
            })

    return results


def _extract_title(text):
    """Extract title from harvest note."""
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("- title:"):
            return line.replace("- title:", "").strip()
        if line.startswith("# "):
            return line.replace("# ", "").strip()
    return "untitled"


def dedupe_check(item, manifest, registry_ids, registry_names):
    """Check if an item is a duplicate."""
    # Check manifest hashes
    existing_hashes = {i.get("content_hash") for i in manifest.get("items", [])}
    if item["content_hash"] in existing_hashes:
        return True, "duplicate_hash_in_manifest"

    # Check registry by title similarity (basic)
    title_lower = item.get("title", "").lower()
    for name in registry_names:
        if name and name.lower() in title_lower:
            return True, f"similar_to_registry:{name}"

    return False, None


# ── Run Engine ───────────────────────────────────────────────────────────────

def run_harvest(config, dry_run=False):
    """Run active harvest lanes."""
    harvest_cfg = config.get("harvest", {})

    if not harvest_cfg.get("enabled", False):
        print("  Harvest engine is DISABLED (harvest.enabled = false)")
        print("  To enable, set harvest.enabled: true in harvest_config.yaml")
        return

    manifest = load_manifest()
    registry_ids, registry_names = load_registry_ids()
    max_ideas = harvest_cfg.get("max_ideas_per_run", 5)
    added = 0

    for lane_name, lane in config.get("source_lanes", {}).items():
        if not lane.get("enabled", False):
            continue

        print(f"\n  Running lane: {lane_name}")
        print(f"    Type: {lane.get('type', '?')}")
        print(f"    Targeting: {lane.get('targeting_mode', '?')}")

        # For intake-folder lanes, scan for new notes
        intake_path = lane.get("intake_path", "")
        if intake_path:
            items = scan_intake_folder(config)
            lane_items = [i for i in items if i["lane"] == lane_name]
            print(f"    Found {len(lane_items)} notes in intake folder")

            for item in lane_items:
                if added >= max_ideas:
                    print(f"    Max ideas per run reached ({max_ideas})")
                    break

                is_dupe, reason = dedupe_check(item, manifest, registry_ids, registry_names)
                if is_dupe:
                    print(f"    SKIP (dupe): {item['filename']} — {reason}")
                    continue

                manifest_entry = {
                    "filename": item["filename"],
                    "title": item["title"],
                    "lane": lane_name,
                    "content_hash": item["content_hash"],
                    "status": "staged",
                    "scanned_date": datetime.now().isoformat(),
                    "targeting_gap": None,
                }

                if not dry_run:
                    manifest["items"].append(manifest_entry)
                    manifest["stats"]["total"] += 1
                    manifest["stats"]["staged"] += 1

                added += 1
                print(f"    STAGED: {item['filename']} — {item['title']}")

    if not dry_run and added > 0:
        manifest["last_scan"] = datetime.now().isoformat()
        save_manifest(manifest)
        print(f"\n  Manifest updated: {added} new items staged")
    elif dry_run:
        print(f"\n  DRY RUN: {added} items would be staged")
    else:
        print(f"\n  No new items found")


# ── Status / Reporting ───────────────────────────────────────────────────────

def print_status(config):
    """Print harvest engine status."""
    W = 70
    harvest_cfg = config.get("harvest", {})
    enabled = harvest_cfg.get("enabled", False)

    print()
    print("=" * W)
    print("  FQL HARVEST ENGINE STATUS")
    print(f"  Master switch: {'ENABLED' if enabled else 'DISABLED'}")
    print(f"  Mode: {config.get('mode', '?')}")
    print("=" * W)

    print(f"\n  SOURCE LANES")
    print(f"  {'-' * (W - 4)}")
    for name, lane in config.get("source_lanes", {}).items():
        status = "ON" if lane.get("enabled") else "OFF"
        icon = "[+]" if lane.get("enabled") else "[-]"
        print(f"  {icon} {name:<30s} {status:<4s} {lane.get('type', '?'):<12s} {lane.get('cadence', '?')}")

    manifest = load_manifest()
    print(f"\n  MANIFEST")
    print(f"  {'-' * (W - 4)}")
    print(f"  Total items: {manifest['stats']['total']}")
    print(f"  Staged: {manifest['stats']['staged']}")
    print(f"  Logged to registry: {manifest['stats']['logged']}")
    print(f"  Last scan: {manifest.get('last_scan', 'never')}")

    print(f"\n{'=' * W}")


def print_gaps(config):
    """Print current gap-aware targeting priorities."""
    gaps, avoids = get_current_gaps(config)

    W = 70
    print()
    print("=" * W)
    print("  HARVEST GAP TARGETING")
    print("=" * W)

    print(f"\n  PRIORITY GAPS (harvest these)")
    print(f"  {'-' * (W - 4)}")
    for gap in gaps:
        prio = gap.get("priority", "?")
        dim = gap.get("dimension", "?")
        target = gap.get("target", "?")
        print(f"  [{prio:>6s}] {dim}: {target}")
        if gap.get("note"):
            print(f"          {gap['note']}")

    print(f"\n  AVOID (overcrowded, don't harvest)")
    print(f"  {'-' * (W - 4)}")
    for avoid in avoids:
        print(f"  [AVOID] {avoid}")

    print(f"\n{'=' * W}")


def main():
    parser = argparse.ArgumentParser(description="FQL Strategic Harvest Engine")
    parser.add_argument("--status", action="store_true", help="Show engine status")
    parser.add_argument("--gaps", action="store_true", help="Show gap targeting")
    parser.add_argument("--scan", action="store_true", help="Scan intake for new notes")
    parser.add_argument("--run", action="store_true", help="Run active harvest lanes")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    config = load_config()

    if args.status:
        print_status(config)
    elif args.gaps:
        print_gaps(config)
    elif args.scan:
        items = scan_intake_folder(config)
        print(f"Found {len(items)} notes in intake folders:")
        for item in items:
            print(f"  {item['filename']}: {item['title']}")
    elif args.run:
        run_harvest(config, dry_run=args.dry_run)
    else:
        print_status(config)


if __name__ == "__main__":
    main()
