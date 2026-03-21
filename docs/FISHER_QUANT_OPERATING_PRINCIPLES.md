# Fisher Quant Lab Operating Principles

*The constitution of the FQL platform. These principles govern all design decisions, research priorities, and operational behavior.*
*Last updated: 2026-03-15*

---

## Mission

Build a self-improving systematic trading platform capable of compounding wealth generationally.

FQL is not a script collection. It is a platform with institutional memory, adaptive intelligence, and autonomous operation.

---

## Core Principles

### 1. Portfolio First

Strategies are evaluated based on portfolio contribution, not standalone metrics.

A mediocre standalone strategy that fills a portfolio gap is more valuable than a strong standalone strategy that overlaps with existing edges. Every decision -- discovery, promotion, allocation, retirement -- is made through a portfolio lens.

**In practice:**
- Marginal Sharpe contribution determines value, not absolute Sharpe
- Correlation and overlap analysis gate every promotion decision
- The counterfactual engine answers: "Did this strategy improve the portfolio or consume capital better used elsewhere?"
- Portfolio gap analysis drives discovery priorities

### 2. Continuous Adaptation

The platform must never become stale.

Markets evolve. Edges decay. Regimes shift. FQL must continuously adapt through:
- Strategy discovery (harvest, crossbreed, evolve)
- Edge lifecycle monitoring (half-life, drift, kill criteria)
- Portfolio diagnostics (contribution, overlap, counterfactual)
- Technology and methodology improvement

**In practice:**
- Half-life monitor tracks edge decay across all active strategies
- Kill criteria automatically flag strategies for review or removal
- Drift monitor compares forward-test behavior to backtest baselines
- The scheduler runs 19 automated jobs on daily/weekly/monthly/quarterly cadences

### 3. Massive Discovery, Brutal Filtering

The edge comes from volume of ideas combined with ruthless quality gates.

**The harvest layer and the validation layer have different jobs.**
The harvest layer optimizes for coverage, diversity, and novelty.
The validation layer optimizes for truth, robustness, and portfolio
usefulness. Do not confuse them. Narrowing intake too early is worse
than processing noise — you can always filter, but you cannot discover
what you never searched for.

**Intake discipline rules (added 2026-03-20):**
1. Intake should be broader than comfort. Collect more than seems useful.
2. No source monoculture. If most ideas come from one lane, diversify.
3. Portfolio gaps drive search bias. If a factor/asset/session is weak,
   search should tilt there via gap bonuses.
4. Closed families stay closed. Wide net does not mean revisiting dead ends.
5. Prefer under-covered assets/sessions when tie-breaking.
6. Human taste should not narrow intake too early. Elite outliers often
   look strange before validation.

**All major source classes must be open:**
Academic, TradingView, GitHub, YouTube, Reddit/forums, microstructure
specialists. Per-lane caps and noise penalties control volume; clustering
compresses duplicates; gap bonuses elevate undercovered areas.

```
Harvest ideas (ALL sources: academic, TradingView, GitHub, YouTube,
              Reddit/forums, microstructure specialists)
    |
Tag with source, factor, asset, session, direction, mechanism
    |
Deduplicate and cluster (compress variants into families)
    |
Cheap validation (baseline backtest, minimum thresholds)
    |
Full validation battery (10 criteria, walk-forward, bootstrap, Monte Carlo)
    |
Portfolio contribution analysis (marginal Sharpe, overlap, gap fit)
    |
Promotion or rejection (with full reason codes)
```

Every candidate gets a fair hearing. Most get rejected. Rejections are
recorded with reasons to prevent re-testing the same idea. The registry
is institutional memory.

**Full-spectrum discovery (added 2026-03-20):**

The lab should not only find complete strategies. It should also capture:
- Partial mechanisms (entry logic, exit logic, filters)
- Regime/vol/timing overlays
- Asset-specific structural behaviors
- Practitioner heuristics and session effects

These fragments are tagged by component type and stored as reusable
building blocks. Elite strategies are often assembled from validated
components, not merely found whole.

**Source convergence strengthens evidence.** When 3 independent sources
describe the same mechanism, that's stronger signal than 1 source
describing it once. Duplicates from different sources are convergent
evidence, not waste.

**Relationships and recombination.** The registry tracks parent/child
links, salvage origins, and component dependencies. When a strategy is
rejected, its salvageable components survive. When a falsification
control outperforms the hypothesis (as with ZN-Afternoon-Reversion),
the discovery is preserved and promoted.

### 4. Survivability First

Risk control and stability take precedence over aggressive growth.

- Drawdown control matters more than absolute return
- Prop firm compatibility is a design constraint, not an afterthought
- Kill switches and circuit breakers are non-negotiable
- Conservative position sizing until edges are proven in forward testing
- Safety systems must be tested before broker connection

**In practice:**
- Kill switch triggers: daily loss $800, trailing DD $4K, 8 consecutive losses, correlated loss
- Strategy state machine enforces lifecycle (VALIDATED -> PAPER -> ACTIVE -> ... -> DISABLED)
- Strategies must pass 10-criterion validation battery before promotion
- Forward testing minimum: 2 weeks or 100 trades before scaling

### 5. Platform-Agnostic Design

Strategies must remain pure trading logic. Everything else lives in separate controllers.

```
Strategy Engine  ->  pure signals (entry, exit, stop, target, filters)
       |
Risk Controller  ->  adapts signals to account environment
       |
Execution        ->  sends orders to broker/platform
```

- Swap environment by changing controller config, never by changing strategy code
- The same strategy runs identically on MES, MNQ, MGC, prop accounts, or cash accounts
- Prop firm rules, account constraints, and portfolio allocation are controller concerns

### 6. Explainability

Every decision must have a reason code.

- Controller actions include reason codes explaining why each strategy is ON, REDUCED, or OFF
- Kill criteria specify which dimension triggered the flag
- Drift alerts identify which metric diverged and by how much
- Promotion and rejection decisions are logged with full rationale
- The daily decision report is human-readable (Markdown) and machine-parseable (JSON)

### 7. Persistence

The repository is the memory of the lab.

- Save all meaningful work to the repo automatically
- Commit at meaningful milestones
- Log decisions in research logs
- Preserve learnings in research notes
- Never hold important state only in conversation

Every strategy ever evaluated is in the registry. Every experiment result is logged. Failures are data, not waste.

---

## Research Discipline

### Single-Variable Testing
Change one thing, measure impact. Never optimize multiple parameters simultaneously.

### Validation Before Promotion
No strategy reaches ACTIVE status without passing the validation battery. No exceptions.

### Forward Testing Before Scaling
Paper trading is mandatory. Minimum duration: 2 weeks or 100 trades.

### Failures Are Institutional Memory
Every rejected strategy is stored with metadata: source, family, validation results, rejection reason, similarity cluster. This prevents duplicate testing and enables salvage of useful components.

---

## Operational Discipline

### Automation Over Manual Intervention
Daily pipeline runs automatically via launchd. Manual intervention is the fallback, not the routine.

### Infrastructure Resilience

*Added 2026-03-20 after post-reboot dead zone incident.*

All critical services must satisfy three requirements:

1. **Health verification, not just auto-start.** `RunAtLoad` and
   `KeepAlive` are necessary but not sufficient. A service that starts
   but fails silently is worse than one that stays down — it looks
   healthy but isn't. Every critical service needs an active health
   check (process exists AND produces expected output).

2. **Catch-up behavior after downtime.** Scheduled jobs (daily research,
   twice-weekly batch, weekly scorecard) missed during sleep or reboot
   must be detected and re-fired. A missed job is not "skipped until
   tomorrow" — it's a gap in the evidence record.

3. **Visible recovery surface.** All recovery actions must be logged to
   a persistent audit trail and summarized in a status report readable
   at a glance. Self-healing that's invisible is indistinguishable from
   silent failure. The operator must be able to answer "is the system
   healthy?" in under 5 seconds.

Implementation: `scripts/fql_watchdog.sh` (5-minute health monitor),
`scripts/fql_recovery_status.sh` (compact status surface),
`docs/SELF_HEALING_RECOVERY.md` (full specification).

### Monitor, Don't Micromanage
The daily routine is checking results, not running the pipeline. Drift monitor, health check, and controller reports surface problems automatically.

### Separation of Concerns
- Strategies: pure signals
- Controllers: risk rules
- Execution: broker communication
- Monitoring: observability
- Research: discovery and validation

No layer reaches into another. Signals flow forward only.

---

## Long-Term Vision

FQL is designed to compound across three dimensions:

1. **Strategy capital** -- Growing through disciplined edge exploitation
2. **Strategy intelligence** -- Improving through continuous discovery, evolution, and retirement
3. **Platform capability** -- Expanding through better tooling, automation, and monitoring

The platform should become more valuable over time, independent of any single strategy's lifespan.

---

## Maintenance

These principles must be reviewed and updated as the platform evolves. They inform but do not replace the technical specifications in:
- `docs/FQL_ARCHITECTURE.md` -- System architecture reference
- `docs/BUILD_DOCTRINE.md` -- Strategy evaluation criteria
- `docs/OPERATING_RULES.md` -- Non-negotiable operating rules
- `docs/CANDIDATE_PROMOTION_STANDARD.md` -- Promotion criteria
