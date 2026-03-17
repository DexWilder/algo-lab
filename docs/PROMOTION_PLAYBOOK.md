# FQL Promotion / Downgrade Playbook

*How to make consistent probation decisions at each review checkpoint.*
*Effective: 2026-03-16*

---

## Review Schedule

| Checkpoint | When | Purpose |
|------------|------|---------|
| Week 2 | 2 weeks after deployment | Sanity check: are trades happening? Any obvious problems? |
| Week 4 | 4 weeks after deployment | Early signal: is the direction right? Any red flags? |
| Week 8 | 8 weeks after deployment | **Formal review**: apply promotion/downgrade criteria |
| Week 12 | 12 weeks after deployment | **Final decision**: promote, extend, or remove |

---

## What to Check at Each Stage

### Week 2 — Sanity Check (10 min)

Run:
```bash
python3 research/weekly_scorecard.py
```

Questions:
- [ ] Are probation strategies generating trades? (Any > 0?)
- [ ] Is the forward runner executing daily?
- [ ] Any kill switch events?
- [ ] Any data feed issues?

**Action if 0 trades after 2 weeks:**
Investigate. Check:
1. Is the strategy generating signals? (Run backtest on recent data)
2. Is the controller blocking it? (Check activation matrix)
3. Is the data feed updating for that asset? (Check data freshness)

**No promotion or downgrade decisions at Week 2.** Observe only.

### Week 4 — Early Signal (15 min)

Run:
```bash
python3 research/weekly_scorecard.py
python3 research/portfolio_contribution_report.py
```

Questions:
- [ ] How many forward trades per strategy?
- [ ] Is PnL directionally correct (not catastrophic)?
- [ ] Any drift alerts on probation strategies?
- [ ] Is the contribution analysis showing overlap concerns?

**Warning signs that matter at Week 4:**
- 0 trades on any probation strategy → INVESTIGATE
- PnL drawdown > $2K on a single probation strategy → FLAG
- Drift ALARM on a probation strategy → REVIEW session restrictions
- Two probation strategies losing on the same days → CHECK correlation

**No promotion decisions at Week 4.** But downgrade IS possible if:
- Strategy shows catastrophic loss pattern (PF < 0.5 after 10+ trades)
- Kill switch fires due to a probation strategy

### Week 8 — Formal Review (30 min)

Run:
```bash
python3 research/weekly_scorecard.py
python3 research/portfolio_contribution_report.py
python3 research/system_integrity_monitor.py
```

**Apply these criteria per strategy:**

#### DailyTrend-MGC-Long

| Metric | Promote | Continue | Downgrade | Remove |
|--------|---------|----------|-----------|--------|
| Forward trades | >= 15 | < 15 | any | any |
| Forward PF | > 1.2 | 1.0 - 1.2 | < 1.0 | < 0.7 after 20 |
| Forward Sharpe | > 0.5 | > 0 | < 0 | < -1.0 |
| Max single DD | < $3K | < $4K | > $4K | > $5K |
| Contribution | positive or neutral | any | dilutive + redundant | — |

#### MomPB-6J-Long-US

| Metric | Promote | Continue | Downgrade | Remove |
|--------|---------|----------|-----------|--------|
| Forward trades | >= 30 | < 30 | any | any |
| Forward PF | > 1.2 | 1.0 - 1.2 | < 1.0 | < 0.8 after 40 |
| Forward Sharpe | > 0.8 | > 0 | < 0 | < -1.0 |
| US session edge | confirmed | unclear | disappeared | — |
| Contribution | positive | neutral | dilutive | — |

#### FXBreak-6J-Short-London

| Metric | Promote | Continue | Downgrade | Remove |
|--------|---------|----------|-----------|--------|
| Forward trades | >= 50 | < 50 | any | any |
| Forward PF | > 1.1 | 1.0 - 1.1 | < 0.95 | < 0.85 after 60 |
| Short bias | confirmed | unclear | disappeared | — |
| London session | generating signals | quiet but OK | dead | — |
| Complementary to MomPB | yes | neutral | conflicting | — |

### Week 12 — Final Decision (30 min)

Same tools as Week 8. If a strategy hasn't accumulated enough trades
by Week 12, decide:

- **Low-frequency strategy (daily bars):** Extend probation 4 more weeks
- **Intraday strategy with < 50% of target:** Likely a signal generation issue. Investigate or downgrade.
- **Intraday strategy at target with borderline metrics:** One more 4-week extension maximum, then promote or remove.

**No strategy stays in probation indefinitely.** Maximum probation: 16 weeks.

---

## Evidence Hierarchy

What matters most, in order:

1. **Forward PF** — the single most important number
2. **Forward trade count** — enough evidence to trust the PF?
3. **Drawdown behavior** — is it within expected range?
4. **Walk-forward consistency** — does forward match backtest character?
5. **Contribution** — is it adding value or just taking space?
6. **Drift alerts** — has the edge structurally changed?
7. **Overlap / redundancy** — is it duplicating another strategy's returns?

---

## Decision Actions

### PROMOTE to ACTIVE

When criteria are met:
1. Update registry: `status: core`, `controller_state: ACTIVE`
2. Update allocation tier: REDUCED → BASE (or as appropriate)
3. Remove deployment restrictions
4. Log decision in `docs/CHANGELOG.md`
5. Run contribution report to verify no new overlap issues

### CONTINUE PROBATION

When evidence is accumulating but not yet decisive:
1. Keep current tier and restrictions
2. Note in registry: extend review date
3. No action needed — system continues automatically

### DOWNGRADE to MONITOR

When evidence is negative but not catastrophic:
1. Update registry: `status: testing`, `controller_action: OFF`
2. Remove from forward runner active set
3. Log reason in registry notes
4. Strategy stops accumulating forward evidence
5. Can be revisited if market conditions change

### REMOVE

When evidence is clearly negative:
1. Update registry: `status: rejected`, add `rejection_reason`
2. Remove from forward runner
3. Log in `docs/CHANGELOG.md`
4. Add to genome map as rejected pattern
5. Never re-test the same strategy without material changes

---

## What Gets Logged

For every promotion decision, record:

```json
{
  "strategy_id": "...",
  "decision": "PROMOTE | CONTINUE | DOWNGRADE | REMOVE",
  "date": "2026-XX-XX",
  "review_stage": "week_8",
  "forward_trades": N,
  "forward_pf": X.XX,
  "forward_pnl": $X,XXX,
  "forward_max_dd": $X,XXX,
  "contribution_status": "positive | neutral | dilutive",
  "drift_status": "clean | drift | alarm",
  "rationale": "one sentence explaining the decision",
  "next_review": "2026-XX-XX or N/A"
}
```

This goes into the strategy's `state_history` array in the registry.

---

## How This Connects

| Tool | Feeds Into |
|------|-----------|
| Weekly scorecard | Probation progress bars, trade counts, anomalies |
| Contribution report | Overlap, complementarity, forward PnL per strategy |
| Integrity monitor | System health, scheduler, data freshness |
| Drift monitor | Session-specific edge degradation |
| Allocation matrix | Current tier assignments |
| Registry | Decision history, state transitions |

The playbook uses all of these. No single tool gives the full picture.
