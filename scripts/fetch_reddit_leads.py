#!/usr/bin/env python3
"""Reddit Source Lead Fetcher — finds strategy discussions for Claw to review.

Writes leads to ~/openclaw-intake/inbox/source_leads/reddit_leads.md
Uses Reddit's public JSON API (no auth needed for reading).
Claw reads this file during harvest tasks and synthesizes relevant
discussions into standard harvest notes.

This is a THIN FETCHER. It gathers URLs and titles.
Claw does the analysis, factor tagging, and note writing.

Usage:
    python3 scripts/fetch_reddit_leads.py
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote, unquote

LEADS_DIR = Path.home() / "openclaw-intake" / "inbox" / "source_leads"
OUTPUT = LEADS_DIR / "reddit_leads.md"
TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H:%M")

# Subreddits to search (futures/quant focused)
SUBREDDITS = ["algotrading", "quant", "FuturesTrading"]

# Search queries targeting portfolio gaps
QUERIES = [
    "futures strategy systematic",
    "volatility targeting futures",
    "carry trade futures",
    "value investing systematic",
    "crude oil futures strategy",
    "treasury futures",
    "session microstructure",
    "mean reversion futures",
]

MAX_PER_QUERY = 5
MAX_TOTAL = 15
MIN_UPVOTES = 5

USER_AGENT = "FQL-Harvest-Helper/1.0 (research tool)"


def fetch_reddit(subreddit, query, limit=5):
    """Fetch posts from Reddit's public JSON API."""
    url = (
        f"https://www.reddit.com/r/{subreddit}/search.json"
        f"?q={quote(query)}&sort=top&t=year&limit={limit}&restrict_sr=on"
    )
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        posts = []
        for child in data.get("data", {}).get("children", []):
            d = child.get("data", {})
            if d.get("ups", 0) < MIN_UPVOTES:
                continue
            # Skip crypto/forex spot
            title_lower = d.get("title", "").lower()
            if any(kw in title_lower for kw in ["crypto", "bitcoin", "ethereum", "nft", "defi"]):
                continue
            # Extract self-text excerpt if available
            selftext = d.get("selftext", "")[:500].strip()
            if selftext:
                selftext = selftext.replace("\n", " ").replace("|", " ")

            posts.append({
                "title": d.get("title", ""),
                "url": f"https://reddit.com{d.get('permalink', '')}",
                "subreddit": subreddit,
                "upvotes": d.get("ups", 0),
                "comments": d.get("num_comments", 0),
                "selftext": selftext,
                "created": datetime.fromtimestamp(d.get("created_utc", 0)).strftime("%Y-%m-%d") if d.get("created_utc") else "",
            })
        return posts
    except Exception as e:
        print(f"  Warning: failed to fetch r/{subreddit} for '{query}': {e}", file=sys.stderr)
        return []


def fetch_top_comments(permalink, max_comments=3):
    """Fetch top comments from a Reddit post."""
    url = f"https://www.reddit.com{permalink}.json?sort=top&limit={max_comments}"
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        if len(data) < 2:
            return []
        comments = []
        for child in data[1].get("data", {}).get("children", []):
            d = child.get("data", {})
            body = d.get("body", "").strip()
            if not body or body == "[deleted]" or body == "[removed]":
                continue
            score = d.get("ups", 0)
            if score < 3:
                continue
            body_clean = body[:300].replace("\n", " ").replace("|", " ")
            comments.append({"body": body_clean, "score": score})
            if len(comments) >= max_comments:
                break
        return comments
    except Exception:
        return []


def main():
    LEADS_DIR.mkdir(parents=True, exist_ok=True)

    seen_urls = set()
    all_leads = []

    for sub in SUBREDDITS:
        for query in QUERIES:
            if len(all_leads) >= MAX_TOTAL:
                break
            posts = fetch_reddit(sub, query, MAX_PER_QUERY)
            for p in posts:
                if p["url"] in seen_urls:
                    continue
                seen_urls.add(p["url"])

                # Fetch top comments for high-engagement posts
                if p["comments"] >= 5:
                    permalink = p["url"].replace("https://reddit.com", "")
                    top_comments = fetch_top_comments(permalink, max_comments=2)
                    p["top_comments"] = top_comments
                    time.sleep(1.0)
                else:
                    p["top_comments"] = []

                all_leads.append(p)
                if len(all_leads) >= MAX_TOTAL:
                    break
            time.sleep(1.5)

    # Write leads
    lines = [
        "# Reddit Source Leads (enriched)",
        f"# Generated: {TIMESTAMP}",
        "# Enriched with self-text excerpts and top comments.",
        "# Claw should read the discussion, extract any mechanical",
        "# futures strategy logic, and write a harvest note if testable.",
        "",
    ]

    for lead in all_leads:
        lines.append(f"- title: {lead['title']}")
        lines.append(f"  url: {lead['url']}")
        lines.append(f"  subreddit: r/{lead['subreddit']}")
        lines.append(f"  upvotes: {lead['upvotes']}")
        lines.append(f"  comments: {lead['comments']}")
        if lead.get("created"):
            lines.append(f"  date: {lead['created']}")
        if lead.get("selftext"):
            lines.append(f"  selftext: {lead['selftext'][:300]}")
        for i, c in enumerate(lead.get("top_comments", [])):
            lines.append(f"  top_comment_{i+1}: [{c['score']} pts] {c['body']}")
        lines.append("")

    lines.append(f"# Total leads: {len(all_leads)}")
    lines.append(f"# Fetched: {TIMESTAMP}")

    OUTPUT.write_text("\n".join(lines))
    print(f"Reddit leads: {len(all_leads)} posts written to {OUTPUT}")


if __name__ == "__main__":
    main()
