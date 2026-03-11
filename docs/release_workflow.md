# Release Workflow — Milestone Snapshots

*Defines when and how to create permanent restore points beyond normal commits.*

---

## Two-Level Workflow

| Level | Trigger | Frequency |
|-------|---------|-----------|
| **Normal commits** | Every task / unit of work | Automatic (per CLAUDE.md) |
| **Milestone tags** | Major state changes (see triggers below) | Explicit |

Normal commits happen automatically after every phase or meaningful task.
Milestone tags are created explicitly at significant checkpoints.

---

## Tag Naming Format

```
v<major>.<minor>-phase<N>-<short-name>
```

Examples:
- `v0.13-phase13-range-discovery`
- `v0.14-phase14-gold-mr-refinement`
- `v0.15-phase15-gold-snapback-parent`
- `v0.16-phase16-strategy-controller`

**Rules:**
- Major version stays at `0` until live deployment
- Minor version increments with each milestone (tracks phase number when possible)
- Short name is lowercase, hyphenated, describes the milestone

---

## Milestone Trigger Rules

Create a milestone tag whenever one of these happens:

1. **Strategy promoted to parent** — a strategy passes validation and joins the portfolio
2. **Portfolio structure materially changes** — strategies added/removed, weighting scheme changed
3. **Phase completed** — a numbered research phase finishes with results
4. **Deployment infrastructure changes** — execution adapter, controller, risk logic
5. **Risk/weighting/prop simulation logic changes** — sizing, DD limits, account configs

---

## How to Create a Milestone

Use the milestone script:

```bash
./scripts/create_milestone.sh "v0.15-phase15-gold-snapback-parent" "BB Equilibrium promoted to 5th parent"
```

The script will:
1. Verify clean working tree (aborts if dirty)
2. Create an annotated git tag with the description
3. Push the tag to origin
4. Print a zip command for optional local backup

### Manual alternative

```bash
git tag -a v0.15-phase15-gold-snapback-parent -m "BB Equilibrium promoted to 5th parent"
git push origin v0.15-phase15-gold-snapback-parent
```

---

## GitHub Releases (Optional)

For major milestones (parent promotions, portfolio restructuring), consider creating a GitHub release:

```bash
gh release create v0.15-phase15-gold-snapback-parent \
  --title "Phase 15: Gold Snapback — 5th Parent Promoted" \
  --notes "BB Equilibrium refined (EMA-15, Trail-1.5, regime gate). 6-strategy portfolio: Sharpe 3.89, Calmar 11.65."
```

Good candidates for releases:
- Strategy promotions to parent
- Portfolio going from N to N+1 strategies
- First live deployment

---

## Zip Backups (Optional)

For critical milestones, create a cold backup:

```bash
zip -r ~/Desktop/algo-lab-v0.15-gold-snapback.zip . -x '.git/*' -x 'data/*' -x '__pycache__/*' -x '*.pyc'
```

Store in: iCloud / external drive / another folder outside the repo.

Good candidates for zip backups:
- Before deploying to live trading
- Before major architectural refactors
- When the portfolio reaches a new high-water mark

---

## Milestone Log

| Tag | Date | Description |
|-----|------|-------------|
| `v0.15-phase15-gold-snapback-parent` | 2026-03-10 | BB Equilibrium promoted to 5th parent. 6-strategy portfolio: Sharpe 3.89, Calmar 11.65. |

*Update this table when new milestones are created.*

---

*Last updated: 2026-03-10*
