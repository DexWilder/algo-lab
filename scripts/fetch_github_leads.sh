#!/bin/bash
# GitHub Source Lead Fetcher — finds quant strategy repos for Claw to review.
#
# Writes leads to ~/openclaw-intake/inbox/source_leads/github_leads.md
# Claw reads this file during gap_harvest and tradingview_scan tasks
# and synthesizes relevant repos into standard harvest notes.
#
# Requires: gh CLI (authenticated)
# Schedule: weekly (manual or via launchd)
#
# This is a THIN FETCHER. It gathers URLs and descriptions.
# Claw does the analysis, factor tagging, and note writing.

set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

LEADS_DIR="$HOME/openclaw-intake/inbox/source_leads"
OUTPUT="$LEADS_DIR/github_leads.md"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M')"

mkdir -p "$LEADS_DIR"

# ── Search queries targeting portfolio gaps ──
# Each query maps to a factor/asset gap from the portfolio dashboard.
QUERIES=(
    "quantitative trading strategy"
    "systematic trading backtest"
    "volatility managed portfolio"
    "algorithmic trading futures"
    "backtesting framework python trading"
    "carry trade systematic"
    "mean reversion trading strategy"
    "commodity trading systematic"
    "intraday trading strategy python"
    "trading strategy backtest python"
)

# ── Collect leads ──
TEMP=$(mktemp)

echo "# GitHub Source Leads" > "$TEMP"
echo "# Generated: $TIMESTAMP" >> "$TEMP"
echo "# For Claw to review during harvest tasks." >> "$TEMP"
echo "#" >> "$TEMP"
echo "# Format: one repo per block. Claw should read the repo," >> "$TEMP"
echo "# extract any mechanical futures strategy logic, and write" >> "$TEMP"
echo "# a standard harvest note if the content is testable." >> "$TEMP"
echo "" >> "$TEMP"

SEEN_REPOS=""
TOTAL=0
MAX_PER_QUERY=5
MAX_TOTAL=20

for query in "${QUERIES[@]}"; do
    if [ "$TOTAL" -ge "$MAX_TOTAL" ]; then
        break
    fi

    # Search for repos, sorted by stars, updated in last 2 years
    results=$(gh search repos "$query" \
        --limit "$MAX_PER_QUERY" \
        --sort stars \
        --order desc \
        --json fullName,description,url,stargazersCount,updatedAt \
        --jq '.[] | select(.stargazersCount >= 5) | "\(.url)|\(.stargazersCount)|\(.description // "no description")"' \
        2>/dev/null || true)

    while IFS='|' read -r url stars desc; do
        [ -z "$url" ] && continue

        # Skip if already seen
        if echo "$SEEN_REPOS" | grep -q "$url"; then
            continue
        fi
        SEEN_REPOS="$SEEN_REPOS $url"

        # Skip crypto/forex-spot repos
        desc_lower=$(echo "$desc" | tr '[:upper:]' '[:lower:]')
        if echo "$desc_lower" | grep -qE "crypto|bitcoin|ethereum|defi|nft|spot forex"; then
            continue
        fi

        echo "- url: $url" >> "$TEMP"
        echo "  stars: $stars" >> "$TEMP"
        echo "  description: $desc" >> "$TEMP"
        echo "  query: $query" >> "$TEMP"
        echo "" >> "$TEMP"

        TOTAL=$((TOTAL + 1))
        if [ "$TOTAL" -ge "$MAX_TOTAL" ]; then
            break
        fi
    done <<< "$results"
done

echo "# Total leads: $TOTAL" >> "$TEMP"
echo "# Fetched: $TIMESTAMP" >> "$TEMP"

mv "$TEMP" "$OUTPUT"
echo "GitHub leads: $TOTAL repos written to $OUTPUT"
