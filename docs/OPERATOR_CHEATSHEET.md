# FQL Operator Cheat Sheet

*One page. Everything you need to operate the platform.*

---

## Daily Rhythm

```bash
fql morning          # Start of day: health + brief + notifications
fql summary          # Quick check anytime (3 seconds)
fql daily            # Read operator brief
```

## Weekly Rhythm

```bash
fql friday           # End of week: weekly reports + review
fql sunday           # Pre-week prep: run source helpers + doctor
```

## When Something Feels Off

```bash
fql doctor           # Full system audit
fql repair           # Audit + auto-fix common issues
fql last             # When did each component last run?
fql alerts           # What needs attention?
fql restart          # Nuclear option: restart all services
```

## Strategy Review

```bash
fql review           # Probation scoreboard + challenger stack
fql components       # Search strategy building blocks
fql components --type filter --asset ZN    # Targeted search
fql components --salvageable               # From rejected strategies
```

## Harvest & Discovery

```bash
fql harvest          # Run source helpers + show lead counts
fql funnel           # Debug helper pipeline (where are leads lost?)
fql weekly           # Gap dashboard + coverage + quality review
```

## Checkpoints

```bash
fql checkpoint       # Full evaluation (shows all reports)
fql checkpoint --auto  # Automated pass/fail verdict
fql notify-test      # Confirm notifications work
```

---

## What Runs Automatically

| Schedule | What | Service |
|----------|------|---------|
| Every 5 min | Watchdog + recovery status | com.fql.watchdog |
| Every 30 min | Claw control loop + EOD audit | com.fql.claw-control-loop |
| Sunday 20:00 | Source helpers (GitHub, Reddit, YouTube, blog, digest) | com.fql.source-helpers |
| Weekdays 17:30 | Daily pipeline (alerts, scoreboard, challengers, brief) | com.fql.daily-research |
| Tue/Thu 18:00 | Batch first-pass factory testing | com.fql.twice-weekly-research |
| Friday 18:30 | Weekly reports (gaps, coverage, quality) | com.fql.weekly-research |

## Key Files

| File | What |
|------|------|
| `_operator_brief.md` | Daily front page — read this |
| `_system_health.md` | System health verdict |
| `_alerts.md` | Active alerts |
| `_probation_scoreboard.md` | All probation strategies |
| `_challenger_stack_review.md` | Newest challengers |
| `_portfolio_gap_dashboard.md` | Factor/asset/session gaps |
| `_harvest_quality_review.md` | Source quality metrics |
| `_recovery_status.md` | Infrastructure health |

All in `~/openclaw-intake/inbox/`.

## North-Star Metrics

- **Usable components created** — fragments + validated entries/exits/filters
- **Forward trades accumulated** — probation evidence
- **Portfolio gap coverage** — VOL, VALUE, Energy, short-bias
- **Source diversity** — ≥ 3 types, no source > 50%
- **Lead → note conversion** — are helpers producing material Claw uses?

## Emergency

```bash
fql repair           # Auto-fix most issues
fql restart          # Restart everything
fql doctor           # Verify recovery
```

If `fql` itself doesn't work: `python3 scripts/fql_doctor.py --repair`
