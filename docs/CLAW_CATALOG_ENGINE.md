# Claw Catalog Engine — Automated Weekly Discovery Schedule

*Claw operates as a scheduled catalog engine, not a prompt-dependent assistant.*
*Effective: 2026-03-17*

---

## Principle

Claw runs on a weekly rotating schedule. Each day has a defined task type.
Outputs land in structured subfolders. Claude picks them up, processes
them, and feeds them into the registry. You do not need to prompt Claw
for any of this — it runs via heartbeat/cron on its own cadence.

**Claw's boundary is absolute:** Claw discovers, catalogs, clusters, and
refines. Claw never converts to code, never tests, never backtests, never
promotes, never changes anything in the algo-lab repo. Claw's outputs are
markdown notes in its own workspace. Claude is the only bridge to the repo.

---

## 1. Weekly Rotating Schedule

### Day Assignments

| Day | Task Type | Category | Cap | Output Folder |
|-----|-----------|----------|-----|---------------|
| **Monday** | Gap-Targeted Harvest | HARVEST | 5-8 notes | `inbox/harvest/` |
| **Tuesday** | Academic / Literature Scan | HARVEST | 3-5 notes | `inbox/harvest/` |
| **Wednesday** | Family Refinement | REFINEMENT | 3-5 notes | `inbox/refinement/` |
| **Thursday** | TradingView / Practitioner Scan | HARVEST | 5-8 notes | `inbox/harvest/` |
| **Friday** | Cluster Review + Dedupe Sweep | CLUSTERING | 1 report | `inbox/clustering/` |
| **Saturday** | Off (no scheduled task) | — | — | — |
| **Sunday** | Blocker Mapping + Gap Refresh | ASSESSMENT | 1 report | `inbox/assessment/` |

### Task Descriptions

#### Monday: Gap-Targeted Harvest
Read the current gap priorities from `inbox/_priorities.md` (Claude updates
this weekly). Generate 5-8 new strategy ideas specifically targeting the
highest-priority gaps. Each note follows the standard intake format.

**Inputs:** `_priorities.md`, factor gaps, asset class gaps
**Focus:** CARRY, VOLATILITY, EVENT — whatever the current top gaps are
**Avoid:** Momentum variants (unless they pass the high-bar rule stated in
priorities), closed families (listed in priorities)

#### Tuesday: Academic / Literature Scan
Scan public academic sources (Quantpedia, SSRN abstracts, AlphaArchitect,
QuantifiedStrategies, Return Stacked) for documented futures edges. Extract
mechanical rules only. No discretionary methods.

**Inputs:** Public academic databases, source list in `_priorities.md`
**Focus:** Documented edges with futures applicability, emphasis on
underrepresented factors
**Output format:** Standard intake note with source URL, author, rule summary

#### Wednesday: Family Refinement
Pick 2-3 existing strategy families from the catalog (listed in
`_family_queue.md`) and generate improved variants, parameter alternatives,
or regime-conditioned versions. This is NOT new discovery — it's deepening
existing clusters.

**Inputs:** `_family_queue.md` (Claude updates with families that need depth)
**Focus:** Making existing clusters smarter, not wider
**Output format:** Refinement note with explicit parent family reference,
what's different, and why it might be better than the current best
representative

#### Thursday: TradingView / Practitioner Scan
Search TradingView public scripts, trading blogs, and practitioner content
for mechanical, testable strategies on futures. Extract entry/exit rules only.
Reject discretionary methods, ICT/SMC concepts, and crypto-only strategies.

**Inputs:** Search terms from `_priorities.md`, TradingView public library
**Focus:** Futures-only, factor-aware, gap-targeted
**Avoid:** Crypto, forex spot, equity single-stock, discretionary methods

#### Friday: Cluster Review + Dedupe Sweep
Review all notes generated this week (Mon-Thu). Group into concept clusters.
Flag duplicates, near-duplicates, and ideas that overlap with notes from
prior weeks. Produce a single cluster report.

**Inputs:** This week's `inbox/harvest/` + `inbox/refinement/` notes
**Output:** Single report in `inbox/clustering/` with:
- New clusters formed this week
- Existing clusters that grew
- Duplicates flagged for rejection
- Best representative per cluster (if changed)
- Any closed-family violations caught

#### Sunday: Blocker Mapping + Gap Refresh
Review all blocked ideas in the catalog. For each blocker type, assess
whether anything has changed (new data available, engineering capability
built, ambiguity resolved). Produce a gap refresh report that Claude uses
to update `_priorities.md` for the next week.

**Inputs:** Prior `_priorities.md`, blocked ideas from prior weeks
**Output:** Single report in `inbox/assessment/` with:
- Blockers that may have been resolved
- New gaps identified from this week's discovery
- Updated priority recommendations for next week
- Family queue recommendations for Wednesday refinement

---

## 2. Output Folder Structure

```
~/openclaw-intake/
├── inbox/
│   ├── harvest/         ← Mon, Tue, Thu: new strategy ideas
│   ├── refinement/      ← Wed: family deepening notes
│   ├── clustering/      ← Fri: weekly cluster report
│   ├── assessment/      ← Sun: blocker map + gap refresh
│   └── _priorities.md   ← Claude-maintained, Claw reads
│   └── _family_queue.md ← Claude-maintained, Claw reads
├── cleaned/             ← Notes processed by Claude (moved here)
├── rejected/            ← Notes rejected by Claude (moved here)
├── reviewed/            ← Notes accepted to registry (moved here)
└── logs/                ← Claw execution logs
```

### Note Naming Convention

```
harvest:     YYYY-MM-DD_NN_<short_name>.md
refinement:  YYYY-MM-DD_ref_<family>_<variant>.md
clustering:  YYYY-MM-DD_cluster_report.md
assessment:  YYYY-MM-DD_gap_refresh.md
```

Example: `2026-03-17_01_commodity_seasonal_carry.md`

### Standard Intake Note Format (Harvest + Refinement)

```markdown
- title: <strategy name>
- source URL: <url or "internal">
- author: <source author>
- target futures instruments: <specific contracts>
- summary: <2-3 sentences, mechanical rules only>
- factor fit: <which factor(s) this fills>
- distinctness from current portfolio: <why this is not redundant>
- testability: <High / Medium / Low + explanation>
- blocker: <what prevents immediate testing, or "none">
- parent family: <existing family name, or "new family">
- verdict: <ACCEPT as idea / ACCEPT but blocked / NEEDS REVIEW>
```

---

## 3. How Claude Picks Up and Processes Outputs

### Monday Session (or first session of the week)

Claude runs:
```bash
python3 research/harvest_engine.py --scan
```

Then for each note in `inbox/harvest/` and `inbox/refinement/`:
1. Read the note
2. Dedupe check against registry (hash + name + concept match)
3. Apply mandatory tags (factor, asset_class, horizon, session, etc.)
4. Assign to concept cluster
5. Present batch for your accept/reject decision
6. Accepted → registry with status=idea, move note to `reviewed/`
7. Rejected → log reason, move note to `rejected/`

### Friday Session

Claude reads `inbox/clustering/` report:
1. Verify cluster assignments match Claude's own clustering
2. Flag any disagreements for your review
3. Update best-representative rankings if needed
4. Check for closed-family violations

### Sunday/Monday Session

Claude reads `inbox/assessment/` gap refresh report:
1. Cross-reference against genome map and factor decomposition
2. Update `inbox/_priorities.md` with refreshed gap targets
3. Update `inbox/_family_queue.md` with families needing Wednesday depth
4. These files are ready for Claw's next Monday run

### Automated Flow

```
Claw (Mon):  Read _priorities.md → generate harvest notes → inbox/harvest/
Claw (Tue):  Academic scan → inbox/harvest/
Claw (Wed):  Read _family_queue.md → generate refinements → inbox/refinement/
Claw (Thu):  TradingView scan → inbox/harvest/
Claw (Fri):  Review week's notes → inbox/clustering/ report
Claw (Sun):  Blocker review → inbox/assessment/ gap refresh

Claude (Mon): Scan inbox → dedupe → tag → present for review
Claude (Fri): Read cluster report → verify → update rankings
Claude (Sun): Read gap refresh → update _priorities.md + _family_queue.md

You: Accept/reject on Monday. Review clusters on Friday. That's it.
```

---

## 4. Governance Boundaries

### Claw NEVER Does

- Write to any file in the algo-lab repo
- Run backtests, generate strategy.py files, or execute Python
- Decide whether an idea is accepted or rejected (Claw recommends, you decide)
- Promote, demote, or change the status of any strategy
- Modify the registry, genome map, manifest, or any FQL data file
- Access live trading logic, allocation tiers, or forward runner config
- Open conversion slots or queue ideas for testing

### Claw ALWAYS Does

- Generate ideas in standard intake format with all required fields
- Tag every note with factor, asset class, testability, and blocker
- Reference the priority gaps when generating new ideas
- Flag when a note falls in a closed or high-bar family
- Flag when a note is potentially redundant with an existing idea
- Produce the Friday cluster report and Sunday gap refresh

### Claude Is the Bridge

Claude is the only entity that:
- Writes to the algo-lab repo
- Updates the registry
- Runs backtests and batch_first_pass
- Moves notes between inbox folders (harvest → reviewed/rejected)
- Updates `_priorities.md` and `_family_queue.md`
- Presents ideas for your accept/reject decision

---

## 5. Scheduling and Verification

### Claw Heartbeat: OpenClaw Native Cron

Claw runs via OpenClaw's built-in cron scheduler, firing every 30 minutes.

```
Job:      fql-catalog-heartbeat
ID:       85c3eb78-b228-4106-a71e-ff6011e5ac1d
Schedule: every 30m
Agent:    main
Target:   isolated session
Timeout:  300s
Thinking: medium
```

### Verification Commands

```bash
# Check job is registered and next fire time
openclaw cron list

# Check scheduler status (enabled, next wake time)
openclaw cron status

# View recent execution history
openclaw cron runs --id 85c3eb78-b228-4106-a71e-ff6011e5ac1d --limit 10

# Manual test fire (does not affect schedule)
openclaw cron run 85c3eb78-b228-4106-a71e-ff6011e5ac1d

# Disable temporarily (e.g., during maintenance)
openclaw cron disable 85c3eb78-b228-4106-a71e-ff6011e5ac1d

# Re-enable
openclaw cron enable 85c3eb78-b228-4106-a71e-ff6011e5ac1d
```

### Stall Detection

Check these if you suspect the loop has stalled:

```bash
# 1. Is the cron job still enabled and scheduled?
openclaw cron status

# 2. When did it last fire?
openclaw cron runs --id 85c3eb78-b228-4106-a71e-ff6011e5ac1d --limit 3

# 3. Did Claw actually write a log today?
ls -la ~/openclaw-intake/logs/$(date +%Y-%m-%d)*.log

# 4. Is the Gateway running? (cron requires it)
openclaw gateway status 2>/dev/null || echo "Gateway may not be running"

# 5. Check Claude's side — did the control loop run?
ls -la ~/projects/Algo\ Trading/algo-lab/research/logs/claw_loop_$(date +%Y%m%d)*.log
```

### Log Locations

| Component | Where to Look |
|-----------|---------------|
| Claw task logs | `~/openclaw-intake/logs/YYYY-MM-DD_task*.log` |
| Claw cron run history | `openclaw cron runs --limit 10` |
| Claude control loop logs | `research/logs/claw_loop_YYYYMMDD_HHMM.log` |
| Claude launchd stdout | `research/logs/launchd_claw_loop_stdout.log` |
| EOD audit archive | `research/data/claw_audits/audit_YYYY-MM-DD.md` |
| Directive freshness | Check timestamp in `inbox/_directives_today.md` header |

### Full Cadence Summary

| Component | Frequency | Mechanism |
|-----------|-----------|-----------|
| Claw heartbeat | Every 30 min | OpenClaw cron (`fql-catalog-heartbeat`) |
| Claude directive refresh | Every 4 hours | launchd (`com.fql.claw-control-loop`) |
| Claude EOD audit | 22:00 ET | Same launchd (last run of day) |
| Max idle between work | ~30 min | Claw heartbeat interval |
| Daily note budget | 15 notes + 2 reports | Enforced in directives + HEARTBEAT.md |

---

## 6. Bootstrap Files

Claude should create these two files in the Claw inbox to seed the system:

### `inbox/_priorities.md`
Updated weekly by Claude based on genome map + factor decomposition.
Contains current gap targets, closed families, momentum high-bar rule,
and search term suggestions.

### `inbox/_family_queue.md`
Updated weekly by Claude. Lists 3-5 families that need Wednesday
refinement depth, with the current best representative and what kind
of variant would be most useful.

### `inbox/_note_template.md`
The standard intake note format, so Claw can reference it without
needing to remember the schema.
