#!/usr/bin/env python3
"""GitHub Source Lead Fetcher v2 — enriched with README excerpts.

Searches GitHub for quant strategy repos, fetches README content,
scores by quality and relevance, writes enriched leads.

Replaces the v1 shell script with richer metadata:
  - README excerpt (strategy-relevant section)
  - Language, topics, last updated
  - Quality score based on stars, README depth, topic relevance

Usage: python3 scripts/fetch_github_leads.py
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

LEADS_DIR = Path.home() / "openclaw-intake" / "inbox" / "source_leads"
OUTPUT = LEADS_DIR / "github_leads.md"
TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H:%M")

MAX_LEADS = 15
MAX_PER_QUERY = 5

QUERIES = [
    # Broad quant/systematic
    "quantitative trading strategy",
    "systematic trading backtest",
    "algorithmic trading futures",
    "backtesting framework python trading",
    "trading strategy backtest python",
    # Factor-specific (portfolio gaps)
    "volatility managed portfolio",
    "carry trade systematic",
    "mean reversion trading strategy",
    "value factor investing quantitative",
    "momentum trading systematic python",
    # Asset-specific (portfolio gaps)
    "commodity trading systematic",
    "commodity futures python",
    "treasury bond trading strategy",
    "crude oil trading algorithm",
    "gold futures strategy",
    "forex carry trade python",
    # Mechanism-specific
    "intraday trading strategy python",
    "pairs trading cointegration",
    "statistical arbitrage futures",
    "risk parity portfolio python",
    "trend following backtest",
    "market microstructure trading",
    "session trading strategy",
    "overnight gap strategy",
]

JUNK_KEYWORDS = ["crypto", "bitcoin", "ethereum", "defi", "nft", "spot forex",
                  "web3", "solana", "binance", "uniswap"]

QUALITY_KEYWORDS = ["backtest", "futures", "systematic", "strategy", "signal",
                     "entry", "exit", "sharpe", "pnl", "portfolio", "momentum",
                     "mean reversion", "carry", "volatility", "risk"]


def _gh_search(query, limit=5):
    """Search repos via gh CLI."""
    try:
        result = subprocess.run(
            ["gh", "search", "repos", query,
             "--limit", str(limit), "--sort", "stars", "--order", "desc",
             "--json", "fullName,description,url,stargazersCount,updatedAt"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return []
        return json.loads(result.stdout)
    except Exception:
        return []


def _gh_readme(full_name, max_chars=800):
    """Fetch README content via gh API."""
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{full_name}/readme",
             "--jq", ".content"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return None
        import base64
        content = base64.b64decode(result.stdout.strip()).decode("utf-8", errors="ignore")

        # Find the most strategy-relevant section
        lines = content.split("\n")
        best_window = ""
        best_score = 0
        window_size = 15  # lines

        for i in range(0, max(1, len(lines) - window_size)):
            window = "\n".join(lines[i:i + window_size]).lower()
            score = sum(1 for kw in QUALITY_KEYWORDS if kw in window)
            if score > best_score:
                best_score = score
                best_window = "\n".join(lines[i:i + window_size])

        if best_score >= 2:
            # Clean and truncate
            excerpt = best_window.replace("\n", " ").replace("|", " ")
            excerpt = " ".join(excerpt.split())  # collapse whitespace
            return excerpt[:max_chars]
        return None
    except Exception:
        return None


def score_repo(repo, readme_excerpt):
    """Score a repo by quality and strategy relevance."""
    score = 0
    stars = repo.get("stargazersCount", 0)
    desc = (repo.get("description") or "").lower()
    full_text = f"{desc} {readme_excerpt or ''}".lower()

    # Stars
    if stars >= 500:
        score += 3
    elif stars >= 100:
        score += 2
    elif stars >= 20:
        score += 1

    # README quality
    if readme_excerpt and len(readme_excerpt) > 200:
        score += 2
    elif readme_excerpt:
        score += 1

    # Strategy keywords
    score += sum(1 for kw in QUALITY_KEYWORDS if kw in full_text)

    return score


def main():
    LEADS_DIR.mkdir(parents=True, exist_ok=True)

    seen = set()
    all_leads = []

    for query in QUERIES:
        if len(all_leads) >= MAX_LEADS * 2:  # Fetch extra, score later
            break
        repos = _gh_search(query, MAX_PER_QUERY)
        for repo in repos:
            url = repo.get("url", "")
            if not url or url in seen:
                continue
            seen.add(url)

            desc = (repo.get("description") or "").lower()
            if any(junk in desc for junk in JUNK_KEYWORDS):
                continue

            full_name = repo.get("fullName", "")
            readme = _gh_readme(full_name) if full_name else None
            time.sleep(0.3)  # Rate limit

            stars = repo.get("stargazersCount", 0)
            if stars < 5:
                continue

            quality = score_repo(repo, readme)
            updated = (repo.get("updatedAt") or "")[:10]

            all_leads.append({
                "url": url,
                "name": full_name,
                "description": repo.get("description") or "no description",
                "stars": stars,
                "updated": updated,
                "quality_score": quality,
                "readme_excerpt": readme,
                "query": query,
            })

    # Score with shared scorer
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from lead_scorer import score_lead, tier_lead, format_score_line

    for lead in all_leads:
        full_text = f"{lead['description']} {lead.get('readme_excerpt', '')}"
        result = score_lead(full_text, lead["name"])
        tier = tier_lead(result)
        lead["_score"] = result
        lead["_tier"] = tier
        lead["_score_line"] = format_score_line(result, tier)
        # Combine repo quality + mechanism score
        lead["combined_score"] = lead["quality_score"] + result["net_score"]

    # Filter out rejects, sort by combined score
    all_leads = [l for l in all_leads if l["_tier"] != "R"]
    all_leads.sort(key=lambda x: x["combined_score"], reverse=True)
    all_leads = all_leads[:MAX_LEADS]

    # Write
    lines = [
        "# GitHub Source Leads (scored)",
        f"# Generated: {TIMESTAMP}",
        "# Scored by mechanism density + repo quality. Tiers: A/B/C/R.",
        "",
    ]

    for lead in all_leads:
        lines.append(f"- url: {lead['url']}")
        lines.append(f"  name: {lead['name']}")
        lines.append(f"  stars: {lead['stars']}")
        lines.append(f"  updated: {lead['updated']}")
        lines.append(f"  quality_score: {lead['quality_score']}")
        lines.append(f"  score: {lead['_score_line']}")
        lines.append(f"  description: {lead['description']}")
        if lead.get("readme_excerpt"):
            excerpt = lead["readme_excerpt"][:400]
            lines.append(f"  readme_excerpt: {excerpt}")
        lines.append("")

    lines.append(f"# Total leads: {len(all_leads)}")
    lines.append(f"# Fetched: {TIMESTAMP}")

    OUTPUT.write_text("\n".join(lines))
    print(f"GitHub leads: {len(all_leads)} repos written to {OUTPUT}")


if __name__ == "__main__":
    main()
