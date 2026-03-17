# FQL Probation-to-Core Promotion Checklist

*Exact operational steps when a strategy is promoted from probation to core.*
*Last updated: 2026-03-16*

---

## Pre-Promotion Verification

Before starting the promotion process, confirm:

- [ ] Forward trades meet or exceed the target threshold
- [ ] Forward PF meets the promote threshold for this strategy
- [ ] Probation decision journal has a formal Week 8 or Week 12 review entry with decision=promote
- [ ] No active ALARM drift alerts on this strategy
- [ ] Contribution report shows positive or neutral (not dilutive)
- [ ] No kill switch events caused by this strategy

---

## Step 1: Registry Update

```bash
python3 -c "
import json
from research.utils.atomic_io import atomic_write_json, backup_rotate
from pathlib import Path

reg_path = Path('research/data/strategy_registry.json')
reg = json.load(open(reg_path))

SID = 'STRATEGY_ID_HERE'

for s in reg['strategies']:
    if s['strategy_id'] == SID:
        s['prior_state'] = s.get('controller_state')
        s['status'] = 'core'
        s['controller_state'] = 'ACTIVE'
        s['controller_action'] = 'FULL_ON'
        s['last_review_date'] = '2026-XX-XX'
        s['review_priority'] = 'LOW'
        s['notes'] = s.get('notes', '') + ' PROMOTED to core on 2026-XX-XX. Forward PF=X.XX, N trades.'

        # Remove probation restrictions
        if 'deployment_restrictions' in s:
            s['promotion_history'] = s.pop('deployment_restrictions')

        # Add state history entry
        s.setdefault('state_history', []).append({
            'date': '2026-XX-XX',
            'from_state': 'PROBATION',
            'to_state': 'ACTIVE',
            'trigger': 'Promotion: forward PF=X.XX, N trades, Week 8 review'
        })
        break

backup_rotate(reg_path, keep=5)
atomic_write_json(reg_path, reg)
"
```

**Fields to change:**
| Field | From | To |
|-------|------|-----|
| status | probation | core |
| controller_state | PROBATION | ACTIVE |
| controller_action | PROBATION | FULL_ON |
| review_priority | HIGH | LOW |
| deployment_restrictions | (present) | moved to promotion_history |

---

## Step 2: Allocation Tier Upgrade

The allocation engine reads from the registry. After Step 1, the next daily
pipeline run will automatically pick up the new status. However, verify:

**Expected tier changes:**

| Strategy | Probation Tier | Core Tier |
|----------|---------------|-----------|
| DailyTrend-MGC-Long | REDUCED | BASE |
| MomPB-6J-Long-US | REDUCED | BASE |
| FXBreak-6J-Short-London | MICRO | REDUCED |

The allocation engine maps FULL_ON → BASE by default. Contribution and
counterfactual adjustments may boost to BOOST or cap at REDUCED.

**Manual override (if needed):**
Edit `execution_config.priority` in the registry entry to adjust relative
priority among core strategies.

---

## Step 3: Forward Runner Verification

The forward runner uses `build_portfolio_config(include_probation=True)`.
After promotion to core, the strategy will be included even without the
`include_probation` flag. Verify:

```bash
python3 -c "
from engine.strategy_universe import build_portfolio_config
config = build_portfolio_config()
for sid in sorted(config['strategies']):
    print(f'  {sid}')
"
```

Confirm the promoted strategy appears in the output.

---

## Step 4: Controller Integration

The Portfolio Regime Controller scores all strategies in `EVAL_STRATEGIES`
(derived from registry). After promotion:

- Strategy will receive a full 10-dimension activation score
- State machine transitions apply normally (ACTIVE can go to ACTIVE_REDUCED, PROBATION, etc.)
- No manual controller changes needed — the registry drives everything

Run the daily pipeline to verify:
```bash
python3 research/fql_research_scheduler.py --daily
```

Check that the promoted strategy appears in the activation matrix with
`recommended_action: FULL_ON` and appropriate allocation tier.

---

## Step 5: Logging and Audit Trail

Record the promotion in all relevant places:

- [ ] **Probation decision journal:**
  ```bash
  python3 research/probation_journal.py --review STRATEGY_ID --checkpoint week_8
  ```
  Decision: promote. Rationale: forward PF, trade count, contribution status.

- [ ] **CHANGELOG.md:** Add entry under current date:
  ```
  ### Strategy Promotion
  - STRATEGY_ID promoted from probation to core
  - Forward evidence: N trades, PF X.XX, Sharpe X.XX
  - Allocation tier: REDUCED → BASE
  ```

- [ ] **Git commit:** Commit registry changes with clear message.

---

## Step 6: Post-Promotion Monitoring (2 weeks)

After promotion, monitor closely for 2 weeks:

- [ ] Check weekly scorecard: is the strategy still performing?
- [ ] Check contribution report: is it adding value at the higher tier?
- [ ] Check drift monitor: any new DRIFT or ALARM alerts?
- [ ] Check allocation matrix: is the tier assignment correct?

If no issues after 2 weeks, the promotion is considered stable.

---

## Rollback Plan

If a newly promoted strategy degrades within 4 weeks of promotion:

### Trigger conditions for rollback:
- Forward PF drops below 0.8 after promotion
- Kill switch fires due to this strategy
- Contribution becomes dilutive AND redundant
- Drift ALARM appears on the strategy's primary session

### Rollback steps:

1. **Downgrade in registry:**
   - status: core → probation
   - controller_state: ACTIVE → PROBATION
   - controller_action: FULL_ON → PROBATION
   - Add deployment_restrictions back

2. **Log the rollback:**
   - Probation journal: decision=downgrade, rationale
   - CHANGELOG.md entry
   - state_history entry

3. **Allocation automatically adjusts** on next pipeline run (PROBATION action → MICRO/REDUCED tier)

4. **No need to remove from forward runner** — it stays in the pipeline at reduced tier, continuing to accumulate evidence

5. **Set next review:** 4 weeks from rollback date

---

## Special Handling

### Daily-bar strategies (DailyTrend-MGC-Long)

- Generates signals at daily close, not intraday
- Trade frequency is low (~3-4 per month)
- Contribution analysis should weight daily-bar trades differently (larger PnL per trade)
- Allocation tier should account for longer hold times (position may be open for days)
- No session-specific restrictions needed

### Session-specific strategies (MomPB-6J, FXBreak-6J)

- Execution config `preferred_window` and `allowed_window` remain in force after promotion
- Session restrictions are NOT removed at promotion — they are structural to the strategy
- If promoting FXBreak-6J: London session (03:00-08:00 ET) remains the trading window
- If promoting MomPB-6J: US session (08:00-17:00 ET) remains the trading window

### Asset-specific caps

- After promotion, check `max_positions_per_asset` in portfolio config
- MGC currently has 3 intraday core strategies + 1 daily probation
- Promoting DailyTrend-MGC-Long makes 4 MGC strategies — verify the asset cap is not exceeded
- 6J currently has 0 core strategies — promoting either 6J strategy is clean (no cap conflict)

---

## Quick Reference

```
Pre-check → Registry update → Verify allocation → Verify forward runner
→ Verify controller → Log everywhere → Monitor 2 weeks → Stable
```

Total time: ~15 minutes for the promotion itself, plus 2 weeks of monitoring.
