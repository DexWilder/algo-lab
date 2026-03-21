#!/usr/bin/env python3
"""YouTube Source Lead Fetcher — finds practitioner strategy videos for Claw.

Searches YouTube for futures strategy content from known practitioner channels,
fetches transcripts where available, and writes leads with transcript excerpts.

Writes to ~/openclaw-intake/inbox/source_leads/youtube_leads.md
Claw reads this file during harvest tasks and synthesizes relevant
content into standard harvest notes.

This is a THIN FETCHER. It gathers video URLs and transcript excerpts.
Claw does the analysis, factor tagging, and note writing.

Requires: youtube-transcript-api (pip install)
Usage: python3 scripts/fetch_youtube_leads.py
"""

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote

LEADS_DIR = Path.home() / "openclaw-intake" / "inbox" / "source_leads"
OUTPUT = LEADS_DIR / "youtube_leads.md"
TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H:%M")

MAX_LEADS = 10

# Search queries — same gap-aware targeting as other helpers
QUERIES = [
    "futures trading strategy systematic",
    "volatility managed portfolio",
    "commodity futures carry trade",
    "mean reversion futures intraday",
    "algorithmic trading futures backtest",
    "treasury bond futures strategy",
    "crude oil futures systematic",
    "session microstructure trading",
]

# YouTube channel IDs known for mechanical/systematic content (optional filter)
# These are starting points — the search also finds other channels.
QUALITY_CHANNELS = [
    # Add channel handles or names here as they're discovered
]

USER_AGENT = "FQL-Harvest-Helper/1.0 (research tool)"


def search_youtube(query, max_results=3):
    """Search YouTube via the public search page (no API key needed).

    Returns list of {video_id, title, channel} dicts.
    This uses YouTube's public search — rate limited but functional.
    """
    url = f"https://www.youtube.com/results?search_query={quote(query)}&sp=EgIQAQ%253D%253D"
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  Warning: search failed for '{query}': {e}", file=sys.stderr)
        return []

    # Extract video IDs from the page
    video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
    # Dedupe while preserving order
    seen = set()
    unique_ids = []
    for vid in video_ids:
        if vid not in seen:
            seen.add(vid)
            unique_ids.append(vid)
        if len(unique_ids) >= max_results:
            break

    # Extract titles (rough — from the same page)
    titles = re.findall(r'"title":\{"runs":\[\{"text":"([^"]+)"\}', html)

    results = []
    for i, vid in enumerate(unique_ids):
        title = titles[i] if i < len(titles) else "Unknown title"
        results.append({
            "video_id": vid,
            "title": title,
            "url": f"https://www.youtube.com/watch?v={vid}",
        })

    return results


def get_transcript_excerpt(video_id, max_chars=500):
    """Fetch transcript and return first relevant excerpt."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        full_text = " ".join(entry["text"] for entry in transcript)

        # Find the most strategy-relevant section
        keywords = ["entry", "exit", "stop loss", "target", "backtest",
                     "strategy", "signal", "indicator", "buy", "sell",
                     "long", "short", "futures", "systematic"]

        # Score each 500-char window by keyword density
        best_start = 0
        best_score = 0
        for i in range(0, len(full_text) - max_chars, 100):
            window = full_text[i:i + max_chars].lower()
            score = sum(1 for kw in keywords if kw in window)
            if score > best_score:
                best_score = score
                best_start = i

        excerpt = full_text[best_start:best_start + max_chars]
        return excerpt.strip() if best_score >= 2 else None

    except Exception:
        return None


def main():
    LEADS_DIR.mkdir(parents=True, exist_ok=True)

    seen_ids = set()
    all_leads = []

    for query in QUERIES:
        if len(all_leads) >= MAX_LEADS:
            break

        results = search_youtube(query, max_results=3)
        for r in results:
            if r["video_id"] in seen_ids:
                continue
            seen_ids.add(r["video_id"])

            # Skip obvious non-strategy content
            title_lower = r["title"].lower()
            if any(kw in title_lower for kw in ["crypto", "bitcoin", "forex beginner", "scam", "motivation"]):
                continue

            # Try to get transcript excerpt
            excerpt = get_transcript_excerpt(r["video_id"])

            lead = {
                "title": r["title"],
                "url": r["url"],
                "query": query,
                "has_transcript": excerpt is not None,
            }
            if excerpt:
                lead["excerpt"] = excerpt[:300]

            all_leads.append(lead)
            if len(all_leads) >= MAX_LEADS:
                break

        time.sleep(2)  # Rate limit

    # Write leads
    lines = [
        "# YouTube Source Leads",
        f"# Generated: {TIMESTAMP}",
        "# For Claw to review during harvest tasks.",
        "#",
        "# Format: one video per block. Claw should watch/read the content,",
        "# extract any mechanical futures strategy logic, and write",
        "# a standard harvest note if the content is testable.",
        "# Reject discretionary/narrative-only content.",
        "",
    ]

    for lead in all_leads:
        lines.append(f"- title: {lead['title']}")
        lines.append(f"  url: {lead['url']}")
        lines.append(f"  query: {lead['query']}")
        lines.append(f"  has_transcript: {lead['has_transcript']}")
        if lead.get("excerpt"):
            # Clean excerpt for markdown
            excerpt = lead["excerpt"].replace("\n", " ").replace("|", " ")
            lines.append(f"  excerpt: {excerpt}")
        lines.append("")

    lines.append(f"# Total leads: {len(all_leads)}")
    lines.append(f"# Fetched: {TIMESTAMP}")

    OUTPUT.write_text("\n".join(lines))
    print(f"YouTube leads: {len(all_leads)} videos written to {OUTPUT}")


if __name__ == "__main__":
    main()
