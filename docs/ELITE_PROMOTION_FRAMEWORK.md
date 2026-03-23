# Elite Strategy Promotion & Replacement Framework

*The standard for what earns a slot, what keeps a slot, and what loses a slot.*
*Effective: 2026-03-23*

---

## Core Principle

A strategy's value is determined by what it contributes to the portfolio,
not by its standalone metrics. A mediocre standalone strategy that fills
a genuine portfolio gap is more valuable than a strong standalone strategy
that overlaps with existing edges. Every promotion and replacement
decision is made through a portfolio lens.

**No strategy survives on tenure alone. Only current evidence and
portfolio contribution decide.**

---

## 1. What Qualifies as a Good Strategy

A good strategy clears the minimum bar for probation entry.

| Criterion | Threshold |
|-----------|-----------|
| Profit Factor | > 1.1 |
| Trade count | ≥ 30 (intraday), ≥ 8 (event/monthly) |
| Walk-forward | At least 1 OOS segment profitable |
| Mechanism | Identifiable, testable, not pattern-mined noise |
| Factor independence | Not a cosmetic variant of an existing strategy |

A good strategy earns a probation slot. It does not earn core deployment.

---

## 2. What Qualifies as an Elite Strategy

An elite strategy earns and defends a core portfolio slot. It must
demonstrate all of the following:

### Standalone Quality

| Criterion | Threshold |
|-----------|-----------|
| Forward PF | > 1.2 (30+ trades) |
| Forward Sharpe | > 0.5 (annualized) |
| Walk-forward stability | Both halves PF > 1.0 |
| Parameter stability | > 60% of parameter variants profitable |
| Bootstrap CI lower bound | > 1.0 |
| Max drawdown | Within 1.5x backtest worst |
| No catastrophic regime | No single regime where all trades lose |

### Portfolio Contribution

| Criterion | Threshold |
|-----------|-----------|
| Marginal Sharpe | ≥ 0 (does not dilute portfolio) |
| Correlation with portfolio | < 0.20 |
| Correlation with any individual strategy | < 0.35 |
| Factor contribution | Adds to an underrepresented factor, or strengthens a thin one |
| Fills a gap | Asset, session, direction, or horizon gap |

### Edge Durability

| Criterion | Threshold |
|-----------|-----------|
| Forward evidence duration | ≥ 8 weeks (intraday), ≥ 6 months (event/monthly) |
| Vitality score | STABLE or VITAL (not FADING or DEAD) |
| Half-life status | HEALTHY or MONITOR (not DECAYING or ARCHIVE_CANDIDATE) |
| Mechanism rationale | Structural or academic basis, not just empirical pattern |

**An elite strategy is not just profitable. It is profitable, durable,
independent, and portfolio-useful.**

---

## 3. When a Challenger Should Replace an Incumbent

Replacement happens when a challenger is more portfolio-useful than the
weakest incumbent in a capped bucket.

### The Displacement Test

1. **Identify the weakest incumbent.** Score all strategies in the bucket
   using the Elite Review Rubric (6 questions, 4 points each, 24 max).

2. **Score the challenger.** Same rubric.

3. **Apply gap bonus.** +2 to the challenger if it fills a factor, asset,
   or session gap that the incumbent does not.

4. **Compare.** Challenger must score strictly higher than the weakest
   incumbent. Ties go to the incumbent.

5. **Verify forward evidence.** The challenger must have forward evidence
   (not just backtest). A challenger with only backtest cannot displace
   an incumbent with forward evidence, regardless of rubric score.

### The Elite Review Rubric

| Question | 1 (WEAK) | 2 (MARGINAL) | 3 (STRONG) | 4 (ELITE) |
|----------|----------|-------------|-----------|----------|
| Q1: Mechanism clarity | Vague | Partial | Clear, documented | Academic basis, structurally motivated |
| Q2: Evidence durability | Single regime | Mixed, some decay | Stable across regimes | Multi-year, walk-forward perfect |
| Q3: Best in family | Inferior variants exist | Comparable to others | Best in cluster | Only viable representative |
| Q4: Portfolio fit | Overlaps heavily | Moderate overlap | Low overlap, fills a gap | Fills 2+ gaps simultaneously |
| Q5: Evidence quality | Backtest only | Thin forward evidence | Solid forward evidence | Forward confirms backtest thesis |
| Q6: Worth the attention | Marginal | Moderate | Clearly worth monitoring | Obvious portfolio improvement |

**Score ranges:**
- 20-24: Elite — promote or displace immediately
- 16-19: Strong — promote if slot available, challenge if necessary
- 12-15: Marginal — continue probation, do not promote
- < 12: Weak — downgrade or archive

### Displacement Scenarios

| Scenario | Decision |
|----------|----------|
| Challenger scores 20+, incumbent scores 16 | **Displace** — challenger is clearly superior |
| Challenger scores 18 with gap bonus, incumbent scores 17 | **Displace** — gap-fill value tips the balance |
| Challenger scores 17, incumbent scores 17 | **Keep incumbent** — ties go to the sitting strategy |
| Challenger has no forward evidence, incumbent has 3 months | **Keep incumbent** — forward evidence outranks backtest |
| Challenger fills 2 gaps (CARRY + Rates), incumbent fills 0 | **Displace** — even at equal score, gap-fill is decisive |

---

## 4. Portfolio Usefulness Over Standalone Attractiveness

### The Portfolio Usefulness Hierarchy

When evaluating a strategy, these dimensions are ranked in order of
portfolio value:

1. **Gap fill** — Does it cover a factor, asset, or session with 0 core
   coverage? (Highest value)
2. **Directional balance** — Does it add short exposure to a long-heavy
   portfolio?
3. **Correlation independence** — Is it genuinely uncorrelated with
   existing strategies?
4. **Regime diversification** — Does it perform well in a regime where
   the portfolio is weak?
5. **Standalone PF** — How profitable is it on its own? (Important but
   not decisive)

A strategy with PF 1.15 that fills the CARRY gap and adds rates
exposure is more portfolio-valuable than a strategy with PF 1.5 that
adds another morning equity momentum bet.

### When Standalone Attractiveness Can Override

Standalone metrics override portfolio usefulness only when:
- PF > 2.0 with 100+ trades and stable walk-forward (exceptional edge)
- Sharpe > 2.0 (extraordinary risk-adjusted return)
- The strategy is genuinely uncorrelated (< 0.10 with everything)

These are rare. For typical candidates, portfolio usefulness is
the primary decision criterion.

---

## 5. Minimum Evidence for Each Decision

### Promote to Core

| Criterion | Minimum |
|-----------|---------|
| Forward trades | ≥ 30 (intraday), ≥ 8 (event), ≥ 8 (monthly) |
| Forward PF | > threshold (strategy-specific, see probation criteria) |
| Forward Sharpe | > 0.5 |
| Forward duration | ≥ 8 weeks |
| Walk-forward confirmed | Forward behavior matches backtest thesis |
| Portfolio contribution | Marginal Sharpe ≥ 0 |
| Correlation check | < 0.20 with portfolio, < 0.35 with any strategy |
| Elite rubric score | ≥ 16 |

### Continue Probation

| Criterion | Condition |
|-----------|-----------|
| Evidence accumulating | Trade count progressing toward target |
| No kill triggers | PF not < 0.7, no catastrophic DD |
| Aging within window | < 75% of max probation weeks used |
| Edge direction | Forward PF ≥ 1.0 (at least not losing) |

### Downgrade to Watch

| Criterion | Condition |
|-----------|-----------|
| Forward PF < threshold | Below promote bar after sufficient trades |
| Evidence stale | > 75% of window used, insufficient evidence |
| Vitality declining | FADING or DECAYING with no reversal |
| Regime mismatch | Strategy's preferred regime hasn't appeared |

### Archive / Remove

| Criterion | Condition |
|-----------|-----------|
| Forward PF < 0.7 | Structural failure after ≥ 20 trades |
| Kill trigger fired | DD > 2x backtest worst |
| Max probation expired | All extension opportunities used |
| Mechanism invalidated | Market structure changed (session times, contract specs) |
| Redundancy confirmed | Correlation > 0.35 with a better strategy |

---

## Connection to FQL Systems

### Probation Scoreboard

The probation scoreboard (`fql review`) tracks every probation strategy
against these criteria automatically:
- Aging status (TOO_EARLY → ON_TRACK → GATE_REACHED → FAILING)
- Forward trades vs target
- Time used vs max window
- Edge health flags (vitality, half-life)

### Portfolio Gap Dashboard

The gap dashboard (`fql weekly`) identifies which gaps a challenger
fills. Gap-fill value is the primary input to displacement decisions.

### Challenger Stack Review

The challenger stack review (`fql review`) shows the three newest
challengers side-by-side with their portfolio usefulness assessment.

### Component Catalog

When a strategy is rejected, its salvageable components survive in the
component catalog (`fql components --salvageable`). These components
may be recombined into future children that are stronger than the parent.

### Registry Governance

All promotion, continuation, downgrade, and archive decisions are logged
in the registry `state_history` with date, reason, and evidence cited.
No decision is made without a written justification.

---

## Decision Flowchart

```
Strategy reaches review gate
    │
    ├─ Forward PF > threshold AND trades > target?
    │   ├─ YES → Check portfolio contribution
    │   │   ├─ Marginal Sharpe ≥ 0 AND correlation < 0.20?
    │   │   │   ├─ YES → Score on Elite Rubric
    │   │   │   │   ├─ Score ≥ 16 → PROMOTE (or displace if slot full)
    │   │   │   │   └─ Score < 16 → CONTINUE PROBATION
    │   │   │   └─ NO → CONTINUE PROBATION (portfolio not improved)
    │   │   └─ (insufficient data) → CONTINUE PROBATION
    │   └─ NO → Check severity
    │       ├─ PF < 0.7 → ARCHIVE
    │       ├─ PF < threshold but > 1.0 → DOWNGRADE to watch
    │       └─ PF < 1.0 → DOWNGRADE, consider archive at next review
    │
    └─ Not at gate yet
        ├─ Aging OK (< 75% window) → CONTINUE
        ├─ Aging warning (> 75%) → Flag for accelerated review
        └─ Max window expired → Force decision: promote, extend once, or archive
```
