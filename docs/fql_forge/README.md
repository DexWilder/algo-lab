# FQL Forge

**FQL Forge v1 — 2026-04-14**

The adaptive strategy discovery, refinement, and memory machine running
inside Lane B.

```
Lane A  = protected live system
Lane B  = research/build lane
FQL Forge = the machine inside Lane B
```

## Core doctrine

**Search relentlessly. Validate brutally. Build continuously. Preserve everything useful.**

Full doctrine in [`../LANE_A_B_OPERATING_DOCTRINE.md`](../LANE_A_B_OPERATING_DOCTRINE.md).
FQL Forge is the operational implementation of Lane B under that doctrine.

## v1 status

- **Version:** 1 (operational kernel + cadence layer + minimal source architecture)
- **Shipped:** 2026-04-14
- **Exit gate:** day 14 (2026-04-28) expanded integrity review decides refine-v1 vs advance-to-v2

**v1 deliberately excludes (v2+ deferrals):**
- Automated source-lane ranking from accumulated yield data
- Search-pattern learning (queries → outcomes)
- Refinement-playbook auto-generation from memory payloads
- Automated stale detection (currently manual checklist)
- Dashboard/scorecard automation

These are earned upgrades — each requires observed data FQL Forge v1 will
produce. Building them before the data exists would be premature.

## Standing question

**What source surfaces are we not harvesting yet that may contain differentiated strategy ideas or components?**

This question is reviewed every biweekly source-expansion cadence and
answered with at least one concrete proposal. The source map is never
closed.

## File layout

| File | Role |
|---|---|
| `README.md` (this file) | Index + status + standing question |
| [`queues.md`](./queues.md) | 5 states, transition rules, current items |
| [`active_packet.md`](./active_packet.md) | Today's bounded work packet |
| [`scorecard.md`](./scorecard.md) | Daily append-only + weekly rollup |
| [`stale_checks.md`](./stale_checks.md) | Stale rules + thresholds + observable signals |
| [`anti_drift_checks.md`](./anti_drift_checks.md) | 4 anti-drift metrics |
| [`improvement_log.md`](./improvement_log.md) | Process improvement entries |
| [`memory_index.md`](./memory_index.md) | Strategy memory payload schema |
| [`cadence.md`](./cadence.md) | 4 cadence layers + 6 fallback modes + 2-week gate |
| [`source_map.md`](./source_map.md) | Source lanes + expansion protocol |

## Relationship to authorities

FQL Forge references but does not modify:
- `CLAUDE.md` — operating authority
- `docs/LANE_A_B_OPERATING_DOCTRINE.md` — standing doctrine
- `docs/ELITE_PROMOTION_STANDARDS.md` — framework-by-shape
- `docs/PROBATION_REVIEW_CRITERIA.md` — non-XB-ORB thresholds
- `docs/XB_ORB_PROBATION_FRAMEWORK.md` — XB-ORB thresholds
- `docs/PORTFOLIO_TRUTH_TABLE.md` — current portfolio state
- `docs/HOLD_STATE_CHECKLIST.md` — hold governance

FQL Forge's outputs feed into these authorities via the Lane B → Lane A
promotion protocol (see doctrine). FQL Forge does not edit them directly.

## How to use this v1

- **Daily:** open `active_packet.md`, run the daily cadence from `cadence.md`, append to `scorecard.md`.
- **Weekly Friday:** run the weekly cadence (scorecard rollup, stale review, integrity checks, improvement log entry, source yield + gap review).
- **Biweekly Friday:** run source expansion cadence.
- **Day 14:** run the expanded v1 exit-gate review.

If this is your first time opening the forge, read the files in this
order: doctrine → this README → cadence → queues → active_packet →
scorecard → the rest as needed.
