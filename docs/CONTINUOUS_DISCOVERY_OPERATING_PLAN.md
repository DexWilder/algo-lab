# Continuous Discovery, Selective Deployment — Operating Plan

*How FQL runs the discovery machine continuously while keeping deployment gates tight.*
*Effective: 2026-03-17*

---

## Standing Principles

> **Discover continuously. Deploy selectively. Accept nothing mediocre.**

### Continuous Catalog Growth

Continuous catalog growth is a standing FQL principle. The research engine
never idles. Discovery, harvesting, cataloging, tagging, clustering, blocker
mapping, and assessment run at all times. Source lanes may follow a cadence,
but **discovery itself never pauses.** The catalog engine is always on.

Conversion, testing, probation, and live portfolio changes remain selective
and gated. These two clocks — discovery and deployment — run at different
speeds, on purpose.

### Elite Standard

Elite standard is a standing FQL principle. FQL does not optimize for
quantity, activity, or mediocre passable results. It optimizes for
elite-quality edges, elite portfolio construction, elite robustness,
and elite decision discipline.

- Every strategy must earn its place with forward evidence, not backtest hope
- Every family must demonstrate a real mechanism, not pattern-mined noise
- Every unlock must prove its leverage within 2 weeks, or be logged as a miss
- Every automation must make the system stronger, not just busier
- Weak or mediocre ideas are pruned quickly — a fast REJECT is more
  valuable than a slow MONITOR that wastes attention
- Strong ideas are refined ruthlessly — the best representative in a
  cluster gets investment, the rest get archived
- Discovery is relentless, but standards are uncompromising — volume
  without quality is catalog bloat, not competitive advantage

### Why This Is Policy

1. **Hedge-fund-level discovery depth.** Institutional quant shops maintain
   catalogs of 500-2,000+ ideas. Every idea is a future option. A thin
   catalog means thin options when the market regime shifts and you need
   a new strategy family. A deep catalog means you can immediately pull
   the best candidate for any gap.

2. **No idle time in the research engine.** Time spent not discovering is
   time wasted. Even when the deployment pipeline is bottlenecked — all
   probation slots full, conversion queue paused, no strong candidates —
   the discovery side should still be accumulating ideas, mapping blockers,
   forming new clusters, and refining family knowledge.

3. **Continuous accumulation of ideas, families, and variants.** Each new
   idea makes the catalog smarter: it sharpens cluster boundaries, reveals
   family patterns, identifies which blockers are worth unblocking, and
   surfaces convergent evidence across independent sources. A strategy
   confirmed by three independent sources is stronger than one found once.

### What "Always On" Means Concretely

- Harvest lanes run on their defined cadences without waiting for
  conversion slots to open
- Every session is an opportunity to scan, stage, tag, or assess
- Registry entries accumulate even when no conversion is planned
- Blocker mapping continues so that when a data pipeline or engineering
  capability is built, the ideas that were blocked by it are immediately
  actionable
- Genome map and factor decomposition refresh regularly to keep gap
  targeting current
- The only reason to pause a harvest lane is a quality problem (>50%
  reject rate), not a deployment bottleneck

---

## 1. What Runs Continuously on Claude's Side

Claude handles everything that requires code execution, data access, and
system-level automation inside the algo-lab repo.

### 1a. Fully Automated (launchd, no human action)

| Job | Schedule | Script/Module | What It Does |
|-----|----------|---------------|--------------|
| Daily health check | Weekdays 17:30 ET | `run_fql_daily.sh` | 60-pt health, half-life, contribution, controller, drift |
| Twice-weekly batch testing | Tue/Thu 18:00 ET | `run_fql_twice_weekly.sh` | `batch_first_pass` on status=testing strategies |
| Weekly integrity + kill criteria | Fri 18:30 ET | `run_fql_weekly.sh` | System integrity monitor, kill criteria review, auto-report |
| Log rotation | Built into daily script | `find ... -mtime +30 -delete` | Clean old per-run logs |

### 1b. Session-Triggered (Claude runs when you open a session)

| Task | Trigger | What Claude Does |
|------|---------|------------------|
| **Forward day run** | You request it on a market day | Run `./scripts/start_forward_day.sh`, verify trade log output. **Not scheduled** — the forward runner plist exists but is disabled (`FORWARD_ENABLED=false`). This is a manual start with automated downstream reporting. |
| **Harvest intake scan** | Monday or any session with new Claw notes | `python3 research/harvest_engine.py --scan` then `--run` |
| **Friday scorecard** | Friday session | Run scorecard + intake digest + dashboard, flag actions |
| **Probation checkpoint** | Week 2/4/8/12 of probation cycle | Gather evidence, run `probation_journal.py --snapshot`, present decision |
| **Genome map refresh** | Monthly or after 20+ new registry entries | `python3 research/strategy_genome_classifier.py --save` |
| **Factor decomposition** | Monthly or after portfolio change | `python3 research/factor_decomposition.py` |

### 1c. On-Demand (Claude runs when you ask or when scorecard flags it)

| Task | Trigger | What Claude Does |
|------|---------|------------------|
| Spec-to-code conversion | You approve a conversion slot | Write strategy.py, set status=testing, batch_first_pass auto-tests |
| Validation battery | batch_first_pass returns ADVANCE | Walk-forward, param stability, cross-asset, contribution sim |
| Promotion execution | You approve promotion decision | Update registry, adjust tiers, update forward runner config |
| Kill/downgrade execution | Kill criteria triggered | Present evidence, execute if approved |
| Data backfill | Blocked unlock identified | Execute download, verify, update data depth roadmap |

---

## 2. What Runs Continuously on Claw's (OpenClaw) Side

Claw operates as a **scheduled catalog engine**, not a prompt-dependent
assistant. It runs on a weekly rotating schedule via heartbeat/cron.
You do not need to prompt Claw — it runs on its own cadence.

See `docs/CLAW_CATALOG_ENGINE.md` for the full specification.

### 2a. Weekly Rotating Schedule

| Day | Task | Category | Cap | Output |
|-----|------|----------|-----|--------|
| **Mon** | Gap-targeted harvest | HARVEST | 5-8 | `inbox/harvest/` |
| **Tue** | Academic / literature scan | HARVEST | 3-5 | `inbox/harvest/` |
| **Wed** | Family refinement | REFINEMENT | 3-5 | `inbox/refinement/` |
| **Thu** | TradingView / practitioner scan | HARVEST | 5-8 | `inbox/harvest/` |
| **Fri** | Cluster review + dedupe sweep | CLUSTERING | 1 report | `inbox/clustering/` |
| **Sat** | Off | — | — | — |
| **Sun** | Blocker mapping + gap refresh | ASSESSMENT | 1 report | `inbox/assessment/` |

### 2b. Claw Reads, Claude Writes

Claw reads two files that Claude maintains:
- `inbox/_priorities.md` — current factor/asset/horizon gaps, closed families,
  momentum high-bar rule, search suggestions
- `inbox/_family_queue.md` — families needing Wednesday refinement depth

Claude updates these weekly based on genome map and factor decomposition.
This is the feedback loop that keeps Claw targeted without manual prompting.

### 2c. Governance Boundary (Absolute)

- Claw NEVER modifies any file in the algo-lab repo
- Claw NEVER converts, tests, backtests, promotes, or changes live logic
- Claw NEVER decides accept/reject — it recommends, you decide
- Claw only writes markdown notes inside `~/openclaw-intake/`
- Claude is the only bridge between Claw's output and the repo

---

## 3. What Remains Manual / Gated

These are the decisions that require human judgment. No automation should
bypass them.

### 3a. Hard Gates (Never Automate)

| Gate | Who Decides | Why It's Manual |
|------|-------------|-----------------|
| **Idea acceptance** (staged → registry) | You | Quality control — reject momentum clones, closed-family rehashes |
| **Conversion slot opening** | You | Resource allocation — only 1-2 per week, must fill a real gap |
| **Promotion decision** (probation → core) | You | Irreversible portfolio change with capital implications |
| **Kill/downgrade execution** | You approve, Claude executes | Irreversible — removing a strategy needs human sign-off |
| **New probation entry** | You | Requires validation battery pass + review of portfolio impact |
| **Tier changes** (MICRO → REDUCED, etc.) | You | Capital allocation change |
| **Harvest lane activation/deactivation** | You | Volume/quality tradeoff |
| **Closed family reopening** | You | Must present thesis addressing prior failure mode |

### 3b. Soft Gates (Claude Proposes, You Approve)

| Gate | What Claude Does | What You Do |
|------|------------------|-------------|
| Registry tagging | Claude applies mandatory tags to accepted ideas | You verify tags are correct |
| Cluster assignment | Claude assigns to concept cluster | You confirm or reassign |
| Conversion priority ranking | Claude ranks by factor gap + quality | You pick which to convert |
| Probation checkpoint report | Claude gathers evidence + presents | You decide continue/promote/kill |
| Genome map gap update | Claude runs classifier, updates priorities | You review before Claw prompts change |

---

## 4. Recurring Reports and Checks

### 4a. Reports Claude Generates

| Report | Cadence | Module | Content |
|--------|---------|--------|---------|
| **Weekly Scorecard** | Friday | `weekly_scorecard.py` | Forward runner, probation progress, drift, regime, factory, actions |
| **Intake Digest** | Friday | `weekly_intake_digest.py` | Pipeline summary, family reps, conversion queue, overlaps, blocked ideas |
| **Operating Dashboard** | Friday | `operating_dashboard.py` | Single-pane: probation bars, factor coverage, watch items, queue |
| **Integrity Monitor** | Friday (automated) | `system_integrity_monitor.py` | 7-check diagnostic across all subsystems |
| **Probation Snapshot** | At checkpoint weeks | `probation_journal.py --snapshot` | Forward trade count, PnL, win rate, per-strategy evidence |
| **Genome Map** | Monthly | `strategy_genome_classifier.py` | 9-dimension classification, overcrowding/gaps |
| **Factor Decomposition** | Monthly | `factor_decomposition.py` | Factor concentration, complementarity, portfolio risk |

### 4b. Checks Built Into Automation

| Check | Frequency | What It Does | Alert Condition |
|-------|-----------|--------------|-----------------|
| Scheduler error detection | Daily | Count ERROR jobs in scheduler log | Any error → log ALERT |
| Data freshness | Daily | Check processed CSV modification times | Any file >7 days stale |
| Drift monitor | Daily | Compare forward behavior to backtest baseline | ALARM severity |
| Kill criteria | Weekly | Evaluate all active strategies against kill thresholds | Any strategy triggers kill |
| Forward runner staleness | Weekly (scorecard) | Check last_run timestamp | >3 trading days since last run |
| Harvest quality | Friday (intake digest) | Reject rate, cluster diversity | >50% reject rate |
| Registry consistency | Weekly (integrity) | Schema validation, orphan detection | Any FAIL |

### 4c. Friday Review Sequence (Claude Runs All Three)

```bash
# Claude runs these in sequence during Friday session:
python3 research/weekly_scorecard.py --save
python3 research/weekly_intake_digest.py --save
python3 research/operating_dashboard.py
```

Claude presents a consolidated summary with:
1. System health: PASS/WARN/FAIL
2. Probation progress: bars + any review-ready strategies
3. Harvest quality: accept rate, new clusters formed
4. Recommended actions: promote, investigate, convert, or continue

---

## 5. How This Changes the Weekly Operating Cadence

### Before (Old Rhythm)

```
Mon: Manual check inbox + log ideas (15 min)
Tue: Manual pick + convert 1-2 ideas (30-60 min)
Wed: Auto batch test (0 min)
Thu: Manual review results (15-30 min)
Fri: Manual scorecard (15 min)
Sat: Auto batch test (0 min)
Sun: Optional targeted harvest (15 min)
────────────────────────────────────────
Total: 75-120 min/week, mostly manual review
Discovery: reactive, 1-2 ideas/week
```

### After (Continuous Discovery Rhythm)

```
Mon: Claude scans inbox, stages notes, presents for review (10 min you)
     Claw: tactical gap prompts generated (async, your time with Claw)
Tue: Claude presents ranked conversion candidates (5 min you)
     You approve 0-1 conversion slots (5 min you)
     Auto batch test runs overnight
Wed: Auto batch test results available (0 min)
     Claude auto-tags and clusters any new registry entries
Thu: Claude presents batch results if any (5 min you)
     Claw: biweekly academic/practitioner review (every other week)
Fri: Claude runs full Friday review sequence (10 min you)
     Consolidated report: health + probation + harvest + actions
     You make decisions on flagged items (5-10 min you)
Sat: Auto batch test (0 min)
Sun: Rest (0 min)
────────────────────────────────────────
Total you: 40-50 min/week (down from 75-120)
Total Claude: ~20 min automated + session work
Discovery: continuous, 30-50 ideas staged/week, 10-20 accepted
Deployment: unchanged — same gates, same evidence bar
```

### Key Differences

| Dimension | Before | After |
|-----------|--------|-------|
| Discovery volume | 3-5 ideas/week | 30-50 staged, 10-20 accepted |
| Your review time | 75-120 min | 40-50 min |
| Claude's role | Run scripts when asked | Proactive scan, stage, tag, report |
| Claw's role | Ad-hoc prompts | Structured weekly/biweekly cadence |
| Conversion rate | 1-2/week (when ideas exist) | 0-1/week (unchanged — bottleneck is intentional) |
| Deployment gates | Manual | Manual (unchanged) |
| Report cadence | Friday only | Friday consolidated + daily automated |
| Catalog growth | ~5/week | ~15/week accepted |

---

## 6. Governance Unchanged

The following are NOT changed by this plan:

- Probation review criteria (`docs/PROBATION_REVIEW_CRITERIA.md`)
- Promotion playbook (`docs/PROMOTION_PLAYBOOK.md`)
- Kill criteria thresholds
- Momentum high-bar rule
- Closed family policy (high-bar-only, not absolute ban)
- Forward runner logic
- Allocation tier definitions
- Factor decomposition methodology
- Security policy (GREEN/YELLOW/RED)
- Conversion bottleneck (1-2/week max, intentional)

---

## 7. Activation Checklist

- [x] Harvest Phase 1 active (5/6 lanes running)
- [x] harvest_config.yaml has gap-aware targeting
- [x] Mandatory tagging schema defined
- [x] Dedupe + clustering rules defined
- [x] Weekly intake digest built
- [x] Operating dashboard built
- [x] Genome classifier operational
- [ ] Claude proactively scans inbox on Monday sessions
- [ ] Claude proactively runs Friday review sequence
- [ ] Monthly genome map refresh scheduled
- [ ] Claw prompt templates aligned to harvest_config priority_gaps

The unchecked items are behavioral — Claude should start doing them now.
