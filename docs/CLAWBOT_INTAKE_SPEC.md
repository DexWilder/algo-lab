# Clawbot Intake Spec

Defines exactly how Clawbot/OpenClaw should deliver harvested TradingView scripts into the Algo Lab pipeline.

## Output Destination

All harvested artifacts go into:

```
algo-lab/intake/tradingview/<family>/
```

Where `<family>` is one of: `ict`, `orb`, `vwap`, `trend`, `mean_reversion`, `breakout`, `opening_drive`, `session`

## File Naming Convention

Pine files: `<author_slug>--<title_slug>.pine`

- Lowercase, alphanumeric + hyphens only
- Author and title separated by `--`
- Max 80 characters total
- Example: `icttrader99--silver-bullet-fvg-strategy.pine`

## Required Output Per Script

### 1. Pine Source File

Save the full Pine source code to:

```
intake/tradingview/<family>/<author>--<title>.pine
```

If source is not publicly visible, save an empty file and set `source_status: "metadata_only"` in the manifest entry.

### 2. Manifest Entry

Either call the CLI:

```bash
python3 intake/manage.py add \
  --title "Script Title" \
  --url "https://tradingview.com/script/XXXXX/" \
  --author "AuthorName" \
  --family ict \
  --type strategy \
  --description "Brief description" \
  --pine-version 5 \
  --tags "tag1,tag2,tag3" \
  --notes "Any observations"
```

Or append directly to `intake/manifest.json` following the schema in `intake/script_template.json`.

## Required Fields

Every manifest entry MUST have:

| Field | Required | Source |
|-------|----------|--------|
| `title` | YES | TradingView script title |
| `url` | YES | Full TradingView URL |
| `author` | YES | TradingView username |
| `type` | YES | `strategy` or `indicator` or `library` |
| `family` | YES | Strategy family classification |
| `pine_version` | YES | Pine version (4 or 5 or 6) |
| `description` | YES | From TradingView description or first 200 chars |
| `tags` | YES | Comma-separated from TradingView tags + Clawbot classification |

## Optional Fields (populate if available)

| Field | Notes |
|-------|-------|
| `asset_candidates` | What instruments the script targets |
| `preferred_timeframes` | What timeframes the author recommends |
| `session_window` | If the script uses session filters |
| `strategy_class` | `trend`, `breakout`, `mean_reversion`, `liquidity`, `continuation` |
| `entry_style` | `market`, `limit_retrace`, `stop_breakout` |
| `notes` | Anything notable from the description |

## Deduplication Rules

Before adding any script, check for duplicates:

1. **By URL** — exact match on TradingView URL (reject if exists)
2. **By ID** — generated from `<author>--<title>` slug (reject if exists)
3. **By content** — if two scripts from the same author have >90% code similarity, keep only the newer version

## Source Status Categories

| Status | Meaning | Action |
|--------|---------|--------|
| `full_source` | Complete Pine code is publicly visible and saved | Proceed normally |
| `partial_source` | Some code visible but sections hidden/obfuscated | Save what's visible, note gaps |
| `metadata_only` | Script exists but code is invite-only or hidden | Save metadata, skip code |
| `rejected` | Script doesn't meet intake criteria | Log reason, don't save |

Add a `source_status` field to the notes when not `full_source`.

## Intake Acceptance Criteria

### ACCEPT — pull and register:

- Strategy scripts with visible source code
- Has explicit entry AND exit logic
- Intraday / session-based logic
- Futures-compatible (or easily adaptable)
- Pine v4, v5, or v6

### REJECT — log reason and skip:

| Reason | Example |
|--------|---------|
| `no_exits` | Indicator-only, no strategy entries/exits |
| `invite_only` | Source code not publicly visible |
| `repainting` | Uses `security()` with lookahead, `request.security` without barmerge |
| `martingale` | Grid trading, martingale position sizing |
| `crypto_only` | Built exclusively for crypto with no futures applicability |
| `duplicate` | Already exists in manifest by URL or ID |
| `low_quality` | Less than 20 lines of logic, no meaningful edge |
| `not_strategy` | Library, utility, or pure visual indicator |

## Roster Target Mapping

When possible, map each accepted script to a roster target:

| Family | Default Roster Target |
|--------|----------------------|
| `ict` | `ALGO-CORE-ICT-001` |
| `orb` | `ALGO-CORE-ORB-001` |
| `vwap` | `ALGO-CORE-VWAP-001` |
| `trend` | `ALGO-CORE-TREND-001` |
| `mean_reversion` | `ALGO-CORE-VWAP-001` |
| `breakout` | `ALGO-CORE-ORB-001` |
| `opening_drive` | `ALGO-CORE-ORB-001` |
| `session` | `ALGO-CORE-ORB-001` |

Set `portfolio_role: "core"` and `layer: "A"` for initial harvest.

## Batch Size Rules

- Harvest Batch 1 target: 20 ICT + 20 ORB + 20 VWAP = 60 scripts
- Do not exceed 100 scripts per batch without review
- Quality over quantity — skip marginal scripts

## Error Handling

- If TradingView rate-limits: back off and retry with exponential delay
- If a script page is unavailable: log as `metadata_only`, continue
- If Pine version can't be determined: default to `5`, note uncertainty
- If family classification is ambiguous: use best guess, add `needs_review` tag

## Post-Harvest Deliverable

After each batch, produce a harvest report with:

1. Total scripts pulled
2. Total accepted vs rejected
3. Count by family
4. Count by roster target
5. Rejection reasons summary
6. Asset/timeframe distribution
7. Duplicate count
8. Scripts flagged for manual review
9. Any patterns or observations

Save the report to: `research/harvest_reports/batch_N_report.md`

## Directory Structure Reference

```
intake/
  manifest.json                              ← master tracking file
  manage.py                                  ← CLI tool
  script_template.json                       ← field reference
  tradingview/
    ict/
      <author>--<title>.pine                 ← raw Pine source
    orb/
      <author>--<title>.pine
    vwap/
      <author>--<title>.pine
    trend/
    mean_reversion/
    breakout/
    opening_drive/
    session/
```
