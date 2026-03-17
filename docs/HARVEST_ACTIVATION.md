# FQL Harvest Activation Plan

*Exact criteria for activating dormant harvest lanes.*
*Last updated: 2026-03-16*

---

## Current State: ALL LANES DISABLED

The harvest infrastructure is built and dormant. This document defines
when and how to activate the first lane.

---

## First Lane: `openclaw_tactical`

**Why first:** Lowest risk. Targeted prompts based on genome map gaps.
Manual review of every note. Capped volume.

### Activation Criteria (ALL must be true)

- [ ] Week 4 probation checkpoint passed with no critical issues
- [ ] Forward runner has executed on at least 10 market days
- [ ] Factory pipeline (batch_first_pass) has run at least 4 times automatically
- [ ] No active system integrity FAIL status
- [ ] You have time capacity for 15 min/week of harvest review

### Configuration When Activated

```yaml
harvest:
  enabled: true
  max_ideas_per_run: 3
  mode: tactical

source_lanes:
  openclaw_tactical:
    enabled: true
    max_per_run: 3
    targeting_mode: gap_aware
```

### Weekly Cap: 3 notes maximum

### Quality Threshold

A harvested note must have:
- Specific entry/exit rules (not just a concept)
- Target asset that FQL has data for
- Strategy family that is NOT in the genome map AVOID list
- Different from any existing registry entry (dedupe check passes)

Reject immediately if:
- No testable rules
- Crypto-only
- Equity single-stock
- Family is in AVOID list (M2K mean-reversion, morning equity breakout, ICT)

### Review Process

1. Harvest engine scans intake folder (automatic or manual)
2. Notes staged to manifest with status=staged
3. **You review each note manually** (15 min/week)
4. Accept → log to registry as status=idea
5. Reject → log reason in manifest, discard
6. Tuesday conversion rhythm picks up accepted ideas

### Pause Conditions

Pause the lane immediately if:
- More than 50% of harvested notes are irrelevant/rejected
- Factory pipeline is backed up (> 5 strategies in testing without batch results)
- Forward runner is broken or not executing
- You don't have time to review (quality drops without review)

### Rollback

To disable:
```yaml
source_lanes:
  openclaw_tactical:
    enabled: false
```

No data is lost. Manifest preserves everything. Registry entries remain.

---

## Second Lane: `tradingview_scan` (after tactical proves quality)

### Activation Criteria

- [ ] openclaw_tactical has run for 4+ weeks
- [ ] At least 50% of tactical notes were useful (led to specs or ideas)
- [ ] No quality issues in the factory pipeline
- [ ] Genome map still shows unfilled gaps

### Configuration

```yaml
source_lanes:
  tradingview_scan:
    enabled: true
    max_per_run: 5
    targeting_mode: gap_aware
```

---

## Third Lane: `openclaw_strategic` (broad discovery)

### Activation Criteria

- [ ] Both tactical lanes running cleanly for 4+ weeks
- [ ] Week 8 probation review is complete
- [ ] Factory pipeline can handle the volume (batch_first_pass not backed up)
- [ ] Specific research sprint is planned (e.g., rates second attempt with deeper data)

### Configuration

```yaml
source_lanes:
  openclaw_strategic:
    enabled: true
    max_per_run: 10
    targeting_mode: broad
```

---

## Lane Activation Timeline

| Week | Lane | Status |
|------|------|--------|
| 1-4 | All disabled | Operate-and-observe mode |
| 5+ | openclaw_tactical | First activation (if criteria met) |
| 9+ | tradingview_scan | Second activation (if tactical quality proven) |
| 12+ | openclaw_strategic | Broad discovery (if research sprint planned) |

**Never activate all lanes simultaneously.** One at a time, prove quality, then expand.

---

## What NOT to Do

- Don't activate strategic harvesting before tactical is proven
- Don't skip the manual review step (quality gate)
- Don't harvest into families on the AVOID list
- Don't let the factory pipeline back up with untested ideas
- Don't harvest just to feel productive — only harvest to fill real gaps
