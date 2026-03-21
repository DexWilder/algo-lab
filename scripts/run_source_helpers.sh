#!/bin/bash
# FQL Source Helper Runner — fetches leads from GitHub + Reddit + YouTube
# Triggered by launchd: com.fql.source-helpers
# Schedule: Sunday 20:00 ET (before Monday gap harvest)
#
# Writes leads to ~/openclaw-intake/inbox/source_leads/
# Tracks lead lifecycle in source_leads/_manifest.json
# Claw reads leads during Monday gap_harvest and Thursday tradingview_scan

set -euo pipefail
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PYTHONUNBUFFERED=1
export HOME="/Users/chasefisher"

ALGO_LAB="/Users/chasefisher/projects/Algo Trading/algo-lab"
LEADS_DIR="$HOME/openclaw-intake/inbox/source_leads"
LOG_DIR="$ALGO_LAB/research/logs"
TIMESTAMP="$(date +%Y%m%d_%H%M)"
LOG_FILE="$LOG_DIR/source_helpers_${TIMESTAMP}.log"

mkdir -p "$LEADS_DIR" "$LOG_DIR"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG_FILE"
    echo "$*"
}

log "=== Source Helper Run ==="

# ── Archive previous leads (mark as stale) ──
if [ -f "$LEADS_DIR/github_leads.md" ]; then
    mv "$LEADS_DIR/github_leads.md" "$LEADS_DIR/github_leads_prev.md" 2>/dev/null || true
fi
if [ -f "$LEADS_DIR/reddit_leads.md" ]; then
    mv "$LEADS_DIR/reddit_leads.md" "$LEADS_DIR/reddit_leads_prev.md" 2>/dev/null || true
fi

# ── Fetch GitHub leads (v2 — enriched with READMEs) ──
log "--- Fetching GitHub leads ---"
GH_OUTPUT=$(python3 "$ALGO_LAB/scripts/fetch_github_leads.py" 2>&1) || true
GH_COUNT=$(echo "$GH_OUTPUT" | grep -o '[0-9]* repos' | grep -o '[0-9]*' || echo 0)
log "GitHub: $GH_COUNT leads fetched"

# ── Fetch Reddit leads ──
log "--- Fetching Reddit leads ---"
RD_OUTPUT=$(python3 "$ALGO_LAB/scripts/fetch_reddit_leads.py" 2>&1) || true
RD_COUNT=$(echo "$RD_OUTPUT" | grep -o '[0-9]* posts' | grep -o '[0-9]*' || echo 0)
log "Reddit: $RD_COUNT leads fetched"

# ── Fetch YouTube leads ──
YT_COUNT=0
if [ -f "$ALGO_LAB/scripts/fetch_youtube_leads.py" ]; then
    log "--- Fetching YouTube leads ---"
    YT_OUTPUT=$(python3 "$ALGO_LAB/scripts/fetch_youtube_leads.py" 2>&1) || true
    YT_COUNT=$(echo "$YT_OUTPUT" | grep -o '[0-9]* videos' | grep -o '[0-9]*' || echo 0)
    log "YouTube: $YT_COUNT leads fetched"
fi

# ── Fetch blog/Substack leads ──
BL_COUNT=0
if [ -f "$ALGO_LAB/scripts/fetch_blog_leads.py" ]; then
    log "--- Fetching blog leads ---"
    BL_OUTPUT=$(python3 "$ALGO_LAB/scripts/fetch_blog_leads.py" 2>&1) || true
    BL_COUNT=$(echo "$BL_OUTPUT" | grep -o '[0-9]* posts' | grep -o '[0-9]*' || echo 0)
    log "Blog: $BL_COUNT leads fetched"
fi

# ── Fetch strategy digest leads ──
DG_COUNT=0
if [ -f "$ALGO_LAB/scripts/fetch_digest_leads.py" ]; then
    log "--- Fetching strategy digest leads ---"
    DG_OUTPUT=$(python3 "$ALGO_LAB/scripts/fetch_digest_leads.py" 2>&1) || true
    DG_COUNT=$(echo "$DG_OUTPUT" | grep -o '[0-9]* strategies' | grep -o '[0-9]*' || echo 0)
    log "Digest: $DG_COUNT leads fetched"
fi

# ── Update manifest ──
log "--- Updating lead manifest ---"
python3 -c "
import json
from datetime import datetime
from pathlib import Path

manifest_path = Path('$LEADS_DIR/_manifest.json')
manifest = json.load(open(manifest_path)) if manifest_path.exists() else {'runs': [], 'lifecycle': {}}

# Record this run
run = {
    'timestamp': '$(date -u +%Y-%m-%dT%H:%M:%SZ)',
    'github_leads': int('$GH_COUNT' or 0),
    'reddit_leads': int('$RD_COUNT' or 0),
    'youtube_leads': int('$YT_COUNT' or 0),
    'blog_leads': int('$BL_COUNT' or 0),
    'digest_leads': int('$DG_COUNT' or 0),
    'total': int('$GH_COUNT' or 0) + int('$RD_COUNT' or 0) + int('$YT_COUNT' or 0) + int('$BL_COUNT' or 0) + int('$DG_COUNT' or 0),
}
manifest['runs'].append(run)

# Keep last 12 runs (3 months)
manifest['runs'] = manifest['runs'][-12:]

# Mark previous leads as stale
for key in list(manifest.get('lifecycle', {}).keys()):
    entry = manifest['lifecycle'][key]
    if entry.get('status') == 'fetched':
        entry['status'] = 'stale'
        entry['stale_date'] = datetime.now().strftime('%Y-%m-%d')

# Register new leads
for source, count_str in [('github', '$GH_COUNT'), ('reddit', '$RD_COUNT'), ('youtube', '$YT_COUNT'), ('blog', '$BL_COUNT'), ('digest', '$DG_COUNT')]:
    count = int(count_str or 0)
    if count > 0:
        lead_key = f'{source}_{datetime.now().strftime(\"%Y%m%d\")}'
        manifest['lifecycle'][lead_key] = {
            'source': source,
            'fetched_date': datetime.now().strftime('%Y-%m-%d'),
            'count': count,
            'status': 'fetched',
            'picked_up': False,
            'notes_produced': 0,
        }

# Clean old lifecycle entries (keep 30 days)
cutoff = (datetime.now() - __import__('datetime').timedelta(days=30)).strftime('%Y-%m-%d')
manifest['lifecycle'] = {
    k: v for k, v in manifest['lifecycle'].items()
    if v.get('fetched_date', '9999') >= cutoff
}

json.dump(manifest, open(manifest_path, 'w'), indent=2)
print(f'Manifest updated: {len(manifest[\"lifecycle\"])} active lead batches')
" >> "$LOG_FILE" 2>&1

log "=== Source helpers complete: GH=$GH_COUNT RD=$RD_COUNT YT=$YT_COUNT BL=$BL_COUNT DG=$DG_COUNT ==="

# Clean old logs
find "$LOG_DIR" -name "source_helpers_*.log" -mtime +30 -delete 2>/dev/null || true
