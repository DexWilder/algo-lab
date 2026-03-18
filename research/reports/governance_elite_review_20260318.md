# Governance Elite Review — Cap and Restriction Audit
## 2026-03-18

*Core question: What governance structure gives us the highest chance of
ending up with a small, elite, high-conviction system instead of a
bloated mediocre one?*

---

## 1. Probation Slot Cap

**Current:** Soft 6, hard 8. Actual: 12 (4 over hard cap).

**Why it exists:** Attention budget. Each probation strategy needs weekly
monitoring during scorecard reviews. Too many dilutes review quality and
lets marginal strategies linger.

**Does it serve the elite standard?** The cap is right in spirit but
wrong in structure. The problem isn't the number — it's that the cap
treats all probation strategies equally. An ELITE-scored PreFOMC-Drift
(22/24) that trades 8 times a year costs almost zero monitoring attention.
A MARGINAL-scored VWAPMR-MCL (13/24) with zero forward trades costs the
same slot but produces no evidence and no value.

**Recommendation: RESTRUCTURE into tiered slots.**

| Tier | Max Slots | Who Qualifies | Monitoring Cost |
|------|-----------|---------------|----------------|
| **Conviction probation** | 5 | Rubric ≥ 18 (STRONG+), fills a gap | Weekly review, active |
| **Watch probation** | 3 | Rubric 15-17 (MARGINAL+), promising but unproven | Monthly review only |
| **Total** | **8** | Hard cap stays at 8 | Mixed |

Strategies scoring below 15 on the rubric should not occupy a probation
slot. They go to testing or archive. This prevents slot bloat from
controller-promoted strategies that haven't earned their place through
the lifecycle.

**Action:** The 4 strategies currently over cap (MomIgn 14, ORBEnh 13,
VWAPMR-MCL 13, GapMom 16) would be: GapMom → watch probation (16),
other three → back to testing pending extended-history validation.

---

## 2. Active Trading Slot Cap

**Current:** No explicit cap on core strategies. Implicit limit from
forward runner capacity (~25 strategies).

**Why it exists (implicitly):** Forward runner performance, margin
requirements, and review bandwidth.

**Does it serve the elite standard?** An uncapped core is dangerous.
It creates no pressure to replace weak core strategies with stronger
ones. If everything that passes probation stays in core forever, the
portfolio accumulates mediocrity over time.

**Recommendation: SET explicit core cap of 10.**

At the prop-first scale (1 micro contract per strategy), 10 core
strategies is the right number:
- Provides enough diversification across factors/assets/sessions
- Creates replacement pressure (to add #11, you must archive the weakest)
- Keeps the weekly scorecard review manageable
- Matches the ~10-15 independent bets a prop portfolio should have

The cap is not a target. Having 4 elite core strategies is better than
having 10 mediocre ones. The cap is a ceiling, not a goal.

---

## 3. Research / Watch Slot Treatment

**Current:** No formal distinction between actively-monitored probation
and passively-watched strategies. All 12 probation strategies get the
same status.

**Does it serve the elite standard?** No. Treating everything the same
means the ELITE candidates (PreFOMC, DailyTrend) compete for attention
with MARGINAL candidates (ORBEnh, VWAPMR-MCL) that may never promote.

**Recommendation: CREATE a formal "watch" status.**

```
IDEA → TESTED → WATCH → PROBATION → CORE
                  ↓         ↓          ↓
              ARCHIVED   DOWNGRADE    KILL
```

**Watch:** Strategy has code, has backtest results, may be in the forward
runner, but is NOT actively monitored weekly. It accumulates evidence
passively. Review quarterly or when evidence threshold is hit. Does not
count against the probation cap.

**Probation (conviction):** Strategy is actively monitored weekly, has
rubric ≥ 18, fills a stated gap, and is on a defined promotion timeline.
Counts against the probation cap.

This separates "we're watching this" from "we believe in this and are
investing attention in it."

---

## 4. Micro / Event / Low-Frequency Sleeve Treatment

**Current:** Event sleeves (PreFOMC at 8 trades/year, NFP at 12/year)
count the same as workhorses (NoiseBoundary at 612 trades/6yr). Same
slot cost, same review cadence.

**Does it serve the elite standard?** Partially. Event sleeves are
high-value diversifiers (zero correlation, fill factor gaps) but their
low frequency means they accumulate evidence very slowly. Giving them
the same slot as a workhorse overcharges them for attention they don't
need.

**Recommendation: Event sleeves count at 0.5 slots against the
probation cap.**

Rationale: An event strategy that trades 8-12 times per year needs
almost no weekly monitoring — you check it at checkpoint weeks, not
every Friday. It fills a critical factor gap (EVENT) at minimal
attention cost.

Practically: with an 8-slot cap and 2 event sleeves at 0.5 each,
you effectively have 7 full slots + 2 event slots = 9 strategies
but only 8 slots of monitoring load.

---

## 5. Family Closure Rules

**Current:** 3+ rejections in same family → family closed. Reopening
requires explicit thesis addressing prior failure mode.

**Does it serve the elite standard?** Yes. This is one of the strongest
rules in the system. It prevents repeated investment in dead families
and forces intellectual honesty about what doesn't work.

**Recommendation: KEEP UNCHANGED.** This rule is already elite.

One refinement: add a **time-based reopening clause.** If a family has
been closed for 12+ months AND market structure has materially changed
(documented, not speculative), a single controlled re-test is allowed.
This prevents permanently closing a family that might work under
different conditions (e.g., mean-reversion on equity index could work
if vol regime shifts permanently).

---

## 6. Salvage / Retry Limits

**Current:** Exactly 1 salvage attempt per strategy. Fix must be
pre-declared, singular, and executed within 30 days. Failed salvage →
permanent rejection.

**Does it serve the elite standard?** Yes. The one-retry rule prevents
sunk-cost escalation (repeatedly fixing a broken strategy instead of
finding a better one). The 30-day expiry prevents salvage items from
lingering indefinitely.

**Recommendation: KEEP UNCHANGED** but add one clarification:

A salvage attempt that changes the strategy's rubric score by ≥ 3
points (e.g., from 14 to 17) justifies the retry even if the absolute
PF improvement is modest. The rubric delta matters, not just the PF
delta.

---

## 7. Factor Concentration Caps

**Current:** Soft 40%, hard 50%. MOMENTUM is at 61% (over hard cap).

**Does it serve the elite standard?** The thresholds are right but
enforcement has been weak. MOMENTUM has been over the hard cap since
the system was built, and strategies keep being added to it because
they're the easiest to find and test.

**Recommendation: TIGHTEN enforcement, keep thresholds.**

- **At 40% (soft):** New entrants in that factor must score ELITE (22+)
  on the rubric to be accepted. STRONG is not enough when the factor
  is already crowded.
- **At 50% (hard):** No new entrants regardless of score. Period. The
  only action is to grow other factors or archive existing strategies
  in the overcrowded factor.
- **Active reduction plan:** When a factor exceeds 50%, the weakest
  strategy in that factor is reviewed for archive at every monthly
  review until the factor is below 50%.

This creates real pressure to diversify, not just talk about it.

---

## 8. Session Concentration Caps

**Current:** Soft 5, hard 6 per session. Morning is at ~8 (over hard cap).

**Does it serve the elite standard?** Same problem as factor caps —
right thresholds, weak enforcement. Morning session concentration is
the portfolio's biggest structural risk. If morning equity/gold
patterns decorrelate or regime-shift, 8+ strategies take the hit
simultaneously.

**Recommendation: TIGHTEN to soft 4, hard 5.**

The current 5/6 cap was set when the system had fewer strategies.
With 16 active strategies, allowing 6 in one session means 37% of
the portfolio is concentrated in one 2-hour window. At soft 4 / hard 5:

- Morning is forced to 5 max (currently ~8, needs pruning)
- Afternoon, close, London, overnight all have room to grow
- The cap creates real pressure to find non-morning edges

Combined with the probation rubric: if a new morning strategy scores
below 22 (ELITE), it doesn't enter probation because the session is
at cap. Only ELITE candidates can displace weaker morning incumbents.

---

## 9. Other Governance Rules

### Asset Concentration (single asset: soft 4, hard 5)

**Recommendation: KEEP UNCHANGED.** Already serving well. MGC at 4 is
at soft cap, which correctly blocks new MGC strategies unless they fill
a gap (DailyTrend-MGC was accepted because daily horizon is genuinely
different from intraday).

### Direction Ratio (soft 2:1, hard 3:1)

**Recommendation: TIGHTEN soft to 1.5:1.** The current portfolio is
long-biased. A 2:1 ratio means longs can outnumber shorts 2-to-1 before
even triggering a soft warning. At 1.5:1, the system pushes harder for
short-side strategies, which are structurally harder to find but more
valuable for portfolio balance.

### Horizon Concentration (soft 70%, hard 80% on single bar freq)

**Recommendation: TIGHTEN soft to 60%.** Currently ~80% of strategies
are intraday 5-minute. This is a single-horizon risk — if 5-minute
alpha decays (crowding, latency competition), the entire portfolio is
exposed. At 60% soft cap, the system creates stronger pressure for
daily, swing, and monthly strategies.

### Probation Maximum Time (16 weeks)

**Recommendation: KEEP at 16 weeks for full-frequency strategies.
EXTEND to 24 weeks for event sleeves** (which trade 8-12 times per
year and need longer to accumulate 8 forward trades). Forcing a
promotion decision on 3-4 trades after 16 weeks is not evidence-based.

### Rubric Minimum for Probation Entry

**Current:** STRONG (18+) required. MARGINAL strategies should not enter.

**Recommendation: ENFORCE strictly.** The current probation bloat (12
strategies, 4 over cap) happened because the controller promoted
strategies without rubric review. Going forward: no strategy enters
probation without an explicit rubric score ≥ 18. Controller promotions
are advisory — human approval with rubric score is required.

---

## Summary: Elite Governance Structure

### What Changes

| Rule | Current | Proposed | Why |
|------|---------|----------|-----|
| Probation cap | Flat 8 | **5 conviction + 3 watch = 8** | Separate active monitoring from passive watching |
| Core cap | None | **10 max** | Create replacement pressure |
| Event sleeve counting | 1 slot each | **0.5 slots** | Low monitoring cost, high diversification value |
| Factor cap enforcement | Thresholds exist, weakly enforced | **Hard enforcement: no new entrants above 50%, ELITE-only above 40%** | Force real diversification |
| Session cap | Soft 5, hard 6 | **Soft 4, hard 5** | Morning concentration is the #1 structural risk |
| Direction ratio | Soft 2:1 | **Soft 1.5:1** | Push harder for short-side strategies |
| Horizon cap | Soft 70% | **Soft 60%** | Push for non-5m strategies |
| Probation time (events) | 16 weeks | **24 weeks** | Low-frequency strategies need longer |
| Probation entry | STRONG (18+) | **STRONG (18+) strictly enforced + rubric required** | No controller-promoted strategies without rubric |
| Watch status | Doesn't exist | **New status: between tested and probation** | Stops marginal strategies from occupying conviction slots |

### What Stays Unchanged

| Rule | Why It's Already Elite |
|------|----------------------|
| Family closure (3+ rejects) | Prevents repeated dead-family investment |
| Salvage one-retry rule | Prevents sunk-cost escalation |
| 30-day salvage expiry | Prevents salvage queue lingering |
| Asset cap (soft 4, hard 5) | Working correctly |
| Pairwise correlation trigger (0.35) | Correctly flags redundancy |
| Blocked-unlock max 1 at a time | Prevents attention fragmentation |
| Forward evidence > backtest | Core principle, never weaken |

### The Target Portfolio Shape

If all proposed rules were in effect, the elite portfolio would look like:

```
CORE (6-10):
  3-4 workhorses (high frequency, moderate PF, different assets/sessions)
  1-2 tail engines (low frequency, high PF)
  1-2 stabilizers (low correlation, smooths equity curve)
  1-2 event sleeves (calendar-driven, zero overlap)
  0-1 diversifiers (fills the most critical gap)

PROBATION — CONVICTION (5):
  5 strategies with rubric ≥ 18, each filling a stated gap
  Actively monitored weekly
  On a defined promotion timeline

PROBATION — WATCH (3):
  3 strategies with rubric 15-17, promising but unproven
  Quarterly review only
  Running in forward runner but not consuming weekly attention

TESTING (unlimited):
  Factory pipeline, batch_first_pass, first-pass results
  No monitoring cost until promoted to watch/probation

IDEAS (unlimited):
  Catalog — discovery engine feeds this continuously
  Zero monitoring cost
```

This structure keeps the active system small (max 18 strategies consuming
any attention at all: 10 core + 5 conviction + 3 watch) while the
catalog grows without bound. Elite standard applied at every gate.
