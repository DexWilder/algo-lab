# FQL Weekly Operating Rhythm

*Steady-state operating cadence during observe-and-accumulate phase.*
*Effective: 2026-03-17 onward*

---

## Daily (automated, no manual action)

**17:30 ET** — launchd triggers `run_fql_daily.sh`:
- Health check (60 points)
- Half-life monitor
- Contribution analysis
- Portfolio Regime Controller + Allocation tiers
- Daily decision report
- Drift monitor

**Morning (when trading)** — `./scripts/start_forward_day.sh`:
- Forward runner processes new bars across all 10 strategies
- Logs trades with probation/core status, asset, tier, horizon

---

## Weekly Manual Rhythm

### Monday — Review and log (15 min)
- Check weekend OpenClaw harvest inbox for new notes
- Log any new ideas to registry with status=idea
- Quick scan of launchd_stdout.log for scheduler errors
- Run watchdog: `python3 research/system_watchdog.py`

### Tuesday — Convert and queue (30-60 min)
- Pick 1-2 highest-priority ideas from registry (status=idea)
- Write spec if needed, convert to strategy.py
- Set status=testing in registry
- batch_first_pass will auto-test on Wednesday

### Wednesday — Automatic batch testing (0 min manual)
- Scheduler runs biweekly_batch_first_pass automatically
- Tests any strategies with status=testing that haven't been evaluated

### Thursday — Review and classify (15-30 min)
- Check `research/data/first_pass/` for new reports
- Review any ADVANCE or SALVAGE results
- If ADVANCE: trigger validation battery manually
- If SALVAGE: decide on one follow-up or archive
- Update registry statuses

### Friday — Weekly scorecard (15 min)
- Run: `python3 research/fql_research_scheduler.py --status`
- Check forward runner trade log: `tail -20 logs/trade_log.csv`
- Count: probation strategy forward trades this week
- Note: any drift alerts, kill switch events, or anomalies
- Quick journal entry: what worked, what didn't, what to adjust

### Saturday — Automatic batch testing (0 min manual)
- Second biweekly_batch_first_pass run

### Sunday — Targeted harvest (15 min, optional)
- If Friday scorecard identified gaps, send targeted OpenClaw prompts
- Otherwise: rest

---

## Total weekly time commitment: ~75-120 minutes

This is intentionally low. The system should run itself.
Manual effort is review, classification, and occasional conversion — not building.
