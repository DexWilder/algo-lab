# Algo Lab Operating Rules

Non-negotiable rules for how the lab operates. Single source of truth.

## 1. Platform-Agnostic Strategy Design

Strategies output ONLY pure trading signals: entry, exit, stop, target, filters.

No prop rules, no account sizing, no drawdown limits inside strategy code. Ever.

Prop/account rules live in `controllers/` with swappable JSON configs.

## 2. Persistence Rule

The repository IS the memory of the Algo Lab.

- Save all meaningful work to the repo automatically
- Commit at meaningful milestones without being asked
- Log decisions in research logs automatically
- Preserve learnings in research notes automatically
- Never hold important state only in conversation — it must be in a file

## 3. Naming & Versioning

- Strategy IDs: `ALGO-CORE-{CLASS}-{NNN}` (e.g. `ALGO-CORE-ORB-001`)
- Portfolio targets: `PORT-{TYPE}-{NAME}-{NNN}` (e.g. `PORT-PROP-MASTER-001`)
- Pine files: `{name}_v{N}.pine`
- Python strategies: `strategy.py` inside `strategies/{name}/`
- Configs: descriptive JSON in `controllers/prop_configs/`
- Versions increment on any logic change, not cosmetic edits

## 4. Roster & Victory Definitions

Every roster target in `research/roster.json` must have:
- A named ID
- A clear mission statement
- A layer assignment (A/B/C)
- A product track
- A victory definition with specific, measurable conditions

No target gets promoted without meeting its victory conditions.

## 5. Controller Separation

```
strategy.generate_signals()  →  pure signals
controller.evaluate()        →  prop/account rules applied
execution.send_orders()      →  broker-specific
```

Swap environment by changing controller config. Never by changing strategy code.

## 6. Intake Quality

- Deduplicate by script ID and source URL
- Every harvested script gets: roster_target, portfolio_role, layer, strategy_class
- Status flow is enforced: raw → reviewed → cleaned → standardized → converted → backtested → validated → portfolio_tested → rejected/deployed
- Reject scripts with: no exits, obvious repainting, invite-only, martingale/grid, crypto-only

## 7. Testing Discipline

- Single-variable optimization only (change one thing, measure impact)
- Never skip the cleaning step before conversion
- Log every test result in research — wins AND losses
- Failures are data, not waste

## 8. Research Logging

- `research/review_logs/` — per-script review notes
- `research/portfolio_notes/` — cross-strategy learnings
- `research/standardized_notes/` — standardization decisions
- `strategies/{name}/research/` — per-strategy test results and logs
