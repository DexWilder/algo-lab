# FQL Elite Review Rubric

*Practical scoring framework for every decision that costs attention, slots, or capital.*
*Effective: 2026-03-18*

---

## When to Use This Rubric

Apply this rubric before any of these decisions:
- Accepting an idea into the conversion queue
- Classifying a first-pass result (ADVANCE/SALVAGE/MONITOR/REJECT)
- Interpreting a validation battery outcome
- Making a probation checkpoint decision (continue/promote/downgrade/kill)
- Deciding whether to add or replace a portfolio slot
- Approving a blocked-unlock investment

The rubric produces a rating: **ELITE**, **STRONG**, **MARGINAL**, or
**WEAK**. Marginal is not good enough for deployment. It may be good
enough for continued research if the mechanism is real.

---

## The Six Questions

### Q1. Is the mechanism real or noise?

A real mechanism has a structural, behavioral, or informational reason
to persist. Noise looks like edge in a backtest but has no reason to
continue working.

| Rating | Criteria |
|--------|----------|
| **ELITE** | Published academic basis OR documented market microstructure reason. Edge survived a regime change (e.g., 2022 tightening) in backtest or forward. Multiple independent sources confirm the concept. |
| **STRONG** | Clear logical mechanism even without academic citation. Edge is consistent across walk-forward halves. Not dependent on a single parameter setting. |
| **MARGINAL** | Mechanism is plausible but unproven. Edge exists in backtest but hasn't been tested through a regime change. Parameter-sensitive — PF swings >30% with ±20% parameter change. |
| **WEAK** | No clear mechanism. Looks like curve-fitting. Edge concentrated in 1-2 outlier trades. Works on one asset/mode and fails everywhere else. Signal quality is PROXY or NOT_AVAILABLE with no path to REAL. |

### Q2. Is the edge durable or concentrated?

Durable edges produce returns across years, regimes, and market conditions.
Concentrated edges look good on aggregate but are driven by a few periods.

| Rating | Criteria |
|--------|----------|
| **ELITE** | Positive PF in 5+ of 7 years tested. No single year contributes >40% of total PnL. Works in both trending and ranging regimes. Walk-forward halves within 20% of each other. |
| **STRONG** | Positive PF in 4+ of 7 years. No single year >50% of total PnL. Walk-forward halves both positive. Some regime sensitivity is acceptable if the mechanism explains it. |
| **MARGINAL** | Positive PF in 3 of 7 years OR one year contributes >60% of total PnL. Edge may be regime-specific without a clear regime filter. Recent performance (last 12 months) is flat or negative. |
| **WEAK** | 2 or fewer positive years. One event or crisis period drives all the PnL. Recent performance is clearly degrading. Walk-forward halves disagree in sign. |

### Q3. Is this the best representative of its family?

Every strategy belongs to a concept family. FQL invests in the best
representative, not every variant.

| Rating | Criteria |
|--------|----------|
| **ELITE** | Clearly the strongest in its family by PF, Sharpe, trade count, and robustness. No other variant in the registry comes close. Would be the anchor if building a family sleeve. |
| **STRONG** | Among the top 2 in its family. May be slightly weaker than the best on one metric but stronger on another (e.g., lower PF but more trades, or same PF but different asset/session). |
| **MARGINAL** | Middle of the pack in its family. A better representative exists or could reasonably be built. Only worth testing if it fills a specific gap (different asset/session) that the best representative doesn't cover. |
| **WEAK** | Clearly inferior to an existing family member on every metric. Redundant. Would not be missed if the family were limited to its top 2. |

### Q4. Does it improve the portfolio meaningfully?

A strategy can be individually good but add nothing to the portfolio if
it's correlated with what already exists.

| Rating | Criteria |
|--------|----------|
| **ELITE** | Fills a factor GAP (0 active/probation in that factor). Correlation <0.15 with all existing strategies. Adds a new session, asset class, or horizon not currently covered. Marginal Sharpe contribution is strongly positive. |
| **STRONG** | Fills a stated gap (factor, asset, or session). Correlation <0.25 with existing strategies. Contribution simulation shows positive or neutral marginal Sharpe. Adds genuine diversification even if not a new factor. |
| **MARGINAL** | Doesn't fill a gap — adds depth to an already-covered area. Correlation 0.25-0.35 with an existing strategy. Contribution is neutral (doesn't hurt, doesn't clearly help). Would consume a slot without a clear portfolio reason. |
| **WEAK** | Adds to an overcrowded factor (MOMENTUM >40%), asset (at cap), or session (morning at cap). Correlation >0.35 with a better-performing existing strategy. Contribution is dilutive. Consumes a slot that could go to a gap-filler. |

### Q5. Does the evidence justify the cost?

Every decision costs something: a conversion slot, engineering time, a
probation slot, attention during weekly reviews, or capital margin.

| Rating | Criteria |
|--------|----------|
| **ELITE** | Forward evidence confirms backtest (forward PF within 80% of backtest PF). Trade count exceeds target threshold. Evidence is unambiguous — anyone reviewing the data would reach the same conclusion. |
| **STRONG** | Forward evidence is directionally consistent with backtest. Trade count is adequate but not excessive. Evidence supports the decision with reasonable confidence, though reasonable people might weigh it differently. |
| **MARGINAL** | Evidence is mixed or thin. Forward trades exist but count is below target. PF is near the threshold boundary (e.g., 1.05 when threshold is 1.0). Decision depends on which metric you emphasize. A "maybe" that consumes a slot. |
| **WEAK** | Evidence is insufficient (too few trades), contradictory (backtest strong, forward weak), or absent (no forward data yet). Decision would be based on hope, not evidence. Backtest PF alone does not justify slot cost. |

### Q6. Is this worth the attention?

FQL has finite review bandwidth. Every strategy in probation needs weekly
monitoring. Every idea in the conversion queue needs spec + code + testing.
Attention is the scarcest resource.

| Rating | Criteria |
|--------|----------|
| **ELITE** | High confidence this will promote. Low monitoring burden (high trade count = fast evidence, clear mechanism = few surprises). Fills a critical gap. Opportunity cost of NOT doing this is high. |
| **STRONG** | Good chance of promotion. Moderate monitoring burden. Fills a real gap. Opportunity cost is moderate — other candidates exist but this one is clearly top-2. |
| **MARGINAL** | Uncertain outcome. Monitoring burden is high (low trade count = slow evidence, noisy signal = frequent false alarms). Doesn't fill a critical gap. Other candidates might be better uses of the same attention. |
| **WEAK** | Low chance of promotion based on current evidence. High monitoring burden. Doesn't fill a gap. Attention would be better spent on discovery, existing probation strategies, or a stronger candidate. |

---

## Scoring and Decision Rules

### How to Score

Rate each question ELITE (4), STRONG (3), MARGINAL (2), or WEAK (1).
Sum the six scores.

| Total Score | Rating | Decision Guidance |
|-------------|--------|-------------------|
| **22-24** | **ELITE** | Proceed without hesitation. This is what the system is built for. |
| **18-21** | **STRONG** | Proceed. Minor concerns are acceptable if the mechanism and evidence are sound. |
| **13-17** | **MARGINAL** | Pause. Do not deploy. May be worth continued research if Q1 (mechanism) scored STRONG+. Otherwise, archive or deprioritize. |
| **6-12** | **WEAK** | Reject or archive. Attention is better spent elsewhere. A fast REJECT here is a gift to future research capacity. |

### Decision-Specific Thresholds

| Decision | Minimum Rating | Minimum Q1 (Mechanism) | Notes |
|----------|---------------|----------------------|-------|
| **Accept idea to conversion queue** | MARGINAL (13+) | STRONG (3+) | Mechanism must be real even if evidence is thin |
| **Classify as ADVANCE (first-pass)** | STRONG (18+) | STRONG (3+) | Skip Q5 (no forward evidence yet) — score on 5 questions |
| **Enter probation** | STRONG (18+) | STRONG (3+) | All six questions must be answerable |
| **Promote to core** | STRONG (18+) | STRONG (3+) | Q5 (evidence) must score STRONG or ELITE |
| **Approve blocked unlock** | STRONG (18+) on ideas it unblocks | — | Score the best unblocked idea, not the unlock itself |
| **Replace existing strategy** | New scores higher than existing on Q1-Q4 | — | Must beat existing on at least 4 of 6 questions |

### Automatic REJECT Triggers

Regardless of total score, REJECT if any of these are true:
- Q1 (mechanism) = WEAK — no mechanism means no edge, regardless of backtest
- Q2 (durability) = WEAK AND Q1 = MARGINAL — noise compounded by fragility
- Q4 (portfolio fit) = WEAK — adding to overcrowded area with correlation >0.35
- Q5 (evidence) = WEAK AND decision requires forward evidence (probation/promotion)

---

## Application Templates

### Template: New Strategy Candidate Review

```
Strategy: ___________________
Family: ___________________
Factor: ___________________
Stage: IDEA / TESTED / VALIDATION

Q1. Mechanism:    [ ] ELITE  [ ] STRONG  [ ] MARGINAL  [ ] WEAK
    Basis: ___________________

Q2. Durability:   [ ] ELITE  [ ] STRONG  [ ] MARGINAL  [ ] WEAK
    Year spread: ___________________

Q3. Best in family: [ ] ELITE  [ ] STRONG  [ ] MARGINAL  [ ] WEAK
    vs: ___________________

Q4. Portfolio fit: [ ] ELITE  [ ] STRONG  [ ] MARGINAL  [ ] WEAK
    Gap filled: ___________________

Q5. Evidence:     [ ] ELITE  [ ] STRONG  [ ] MARGINAL  [ ] WEAK
    Forward PF/trades: ___________________

Q6. Worth attention: [ ] ELITE  [ ] STRONG  [ ] MARGINAL  [ ] WEAK
    Opportunity cost: ___________________

Total: ___/24   Rating: ___________
Decision: ___________________
```

### Template: Probation Checkpoint Review

```
Strategy: ___________________
Checkpoint: Week ___
Forward trades: ___ / ___ target
Forward PF: ___

Q1. Mechanism still intact?     [ ] YES  [ ] DEGRADED  [ ] BROKEN
Q2. Edge durable in forward?    [ ] YES  [ ] MIXED     [ ] NO
Q3. Still best in family?       [ ] YES  [ ] TIED      [ ] SUPERSEDED
Q4. Portfolio contribution?     [ ] POSITIVE [ ] NEUTRAL [ ] DILUTIVE
Q5. Evidence sufficient?        [ ] YES  [ ] THIN      [ ] INSUFFICIENT
Q6. Worth continued attention?  [ ] YES  [ ] UNCERTAIN [ ] NO

Decision: [ ] CONTINUE  [ ] PROMOTE  [ ] DOWNGRADE  [ ] KILL
Reasoning: ___________________
```

### Template: Displacement Check (MANDATORY for every tested/validation candidate)

Every candidate that reaches TESTED or VALIDATION_PASS must include this
displacement analysis. This is a standing review rule, not optional.

```
Candidate: ___________________
Rubric Score: ___/24
Factor: ___________  Session: ___________  Asset: ___________

DISPLACEMENT CHECK 1: Core Vulnerability
  Weakest core incumbent: PB-MGC-Short (16/24 MARGINAL)
  Does this candidate beat it?  [ ] YES (score ___) [ ] NO
  Same asset/session overlap?   [ ] YES → direct replacement candidate
                                [ ] NO → additive if core has room
  If YES: what does the portfolio gain by swapping?
  ___________________

DISPLACEMENT CHECK 2: Watch Slot
  Weakest watch name: MomIgn-M2K-Short (14/24)
  Does this candidate beat it?  [ ] YES (score ___) [ ] NO
  If YES and watch is full: which watch name does it displace?
  ___________________

DISPLACEMENT CHECK 3: Gap Value
  Fills a factor gap (CARRY/STRUCTURAL/VOL with 0 active)?  [ ] YES [ ] NO
  Fills an asset gap (MCL/Rates with 0 active)?              [ ] YES [ ] NO
  Fills a session gap (afternoon/Tokyo/overnight)?            [ ] YES [ ] NO
  Number of gaps filled: ___
  Gap-filling bonus: +2 if any gap filled

DISPLACEMENT VERDICT:
  [ ] DISPLACE core incumbent (score > 16 + fills gap PB-MGC doesn't)
  [ ] DISPLACE watch name (score > weakest watch)
  [ ] ADD to open slot (conviction/watch has room)
  [ ] QUEUE — strong candidate but no slot available, wait for expiry
  [ ] REJECT — does not beat any incumbent and fills no gap
```

### Template: Blocked Unlock Proposal

```
Unlock: ___________________
Cost: $_____ / _____ days engineering
Ideas unblocked: ___________________

Score the BEST idea this unlock enables:
Q1. Mechanism:    ___/4
Q2. Durability:   ___/4 (estimated from backtest/academic evidence)
Q3. Best in family: ___/4
Q4. Portfolio fit: ___/4
Q5. Evidence:     N/A (not yet testable — that's the point)
Q6. Worth attention: ___/4

Best-idea score: ___/20 (5 questions)
Unlock justified if best-idea score ≥ 15/20 (STRONG)
Decision: ___________________
```

---

## Calibration Examples

### ELITE Example: PreFOMC-Drift-Equity
- Q1 ELITE: Academic basis (Lucca & Moench 2015), documented Fed premium
- Q2 STRONG: Consistent across decades, survived multiple rate regimes
- Q3 ELITE: Only FOMC drift strategy in the catalog
- Q4 ELITE: Fills EVENT factor gap, zero session overlap with any strategy
- Q5 MARGINAL: Forward trade count still low (event frequency ~8/year)
- Q6 STRONG: Low monitoring burden, fills critical gap
- **Total: 22/24 = ELITE** — correctly in probation

### MARGINAL Example: Commodity-TermStructure-Carry (current proxy test)
- Q1 MARGINAL: Mechanism is real (academic), but signal is PROXY (conflated)
- Q2 MARGINAL: MGC dominates PnL, 2025 gold rally is 70% of returns
- Q3 STRONG: Best commodity carry candidate (only one with code + data)
- Q4 STRONG: Fills CARRY gap, different asset class
- Q5 MARGINAL: batch_first_pass = SALVAGE (PF 3.23 but MGC-only)
- Q6 MARGINAL: Needs v2 data (front/back) to be conclusive
- **Total: 15/24 = MARGINAL** — correctly in testing, not promoted

### WEAK Example: Overnight-Equity-Premium (rejected)
- Q1 MARGINAL: Academic basis exists but effect may have decayed
- Q2 WEAK: PF 1.03-1.09 across variants, barely above 1.0
- Q3 WEAK: Both tested variants showed the same weak result
- Q4 MARGINAL: Would fill overnight session gap
- Q5 WEAK: Two tests, both near-zero edge
- Q6 WEAK: Further attention unlikely to find a different answer
- **Total: 9/24 = WEAK** — correctly rejected, family closed
