# Elite Operating Principles

**Filed:** 2026-04-29 as canonical operating reference. The last pre-runtime doc — the next layer is operating evidence.

**Companion to:** `hot_lane_architecture.md` (WHAT), `post_may1_build_sequence.md` (WHEN/HOW), `OUTSIDE_INTEL_AND_CONTINUOUS_IMPROVEMENT.md` (input lane). This doc aligns the weekly update, twice-monthly assessment, and post-May-1 execution around evidence-compounding behavior, not well-designed inertia.

**Authority:** T0 advisory. These are the operating disciplines for the operator + Claude as a working pair.

**Premise.** The design layer is sufficient. The next jump is making the machine learn faster than it drifts. The shift is from well-designed to evidence-compounding. The principles below are the operating disciplines that turn a strong design into an elite system.

---

## The Ten Operating Principles

### 1. One live portfolio score is the anchor

Every Friday update and every twice-monthly assessment opens with a single top-line answer:

> Did the live portfolio get better or worse this period?

Supported by ≤4 sub-metrics:
- Equity / drawdown change
- Contribution concentration (Top-3 / Top-5 share)
- Diversification (factor coverage / correlation profile)
- Active edge breadth (count of strategies producing forward evidence)

This prevents mistaking research productivity for portfolio improvement. Lane metrics report AFTER the live portfolio answer, never before.

### 2. Build the cheap-kill lane fast

The hot lane is the generation engine. Elite status requires the matching rejection engine. Push hard immediately after May 1 on:
- Cheap first-pass screen (≤30s/candidate)
- Automatic ranking
- Automatic rejection of obvious losers
- Minimal operator touch until a candidate is genuinely interesting

The faster weak hybrids die, the faster the lab becomes elite.

### 3. Donor scoring is the learning engine, not bookkeeping

Donor attribution must produce real learning, weekly:
- Which donor components create validation-worthy survivors
- Which donors poison hybrids
- Which templates produce useful children
- Which pairings should be cooled or retired

That is how recombination becomes smarter over time, not just busier.

### 4. Compress phases based on evidence, not dates

Calendar does not control progress. Operate explicitly on:
- **Gate-fired acceleration** — when binary gates are met early, move early
- **Tripwire-fired halt** — when a tripwire fires, halt regardless of schedule
- **No "stay on schedule" behavior** — if evidence is weak, extend; if strong, advance

Elite systems respond to evidence rate, not calendar comfort.

### 5. Automate all recurring operator-compression work

The operator's time goes to judgment, not compilation. Anything repeated and judgment-free is auto-drafted:
- Weekly elite-readout draft
- Recurring checkpoint / pre-flight packets
- Donor ranking draft (with operator surface only on disagreements / edge cases)
- Tripwire reports
- Stale-review draft packets
- Forward-testing summary draft

Operator edits and decides. Operator does not compile.

### 6. Twice-monthly assessment is the truth layer

This is where all delusion goes to die. Claude generates the evidence packet first; operator pressure-tests; both merge into one canonical assessment.

The packet must answer:
- What exists
- What actually works
- What is fake progress
- What improved the live portfolio
- What added noise
- What should be improved before anything new is built

### 7. Outside intel must force system change

Reading without operating-system change is theater. Outside-intel lane focuses on:
- AI/orchestration tooling that reduces operator time
- Books/research that change process, not just inspire
- External elite-shop methods translatable into FQL rules

Every outside-intel item answers: **What do we change in FQL because of this?** No passive learning.

### 8. Ruthlessly remove dead weight after May 1

Elite is not built by layering new systems on stale truth. After May 1, before any new lane work, prioritize:
- Stale / ghost / blocked strategy cleanup
- Registry / runner / scoreboard / doc authority alignment
- Cleaner active probation set
- Removal of references no longer reflecting live reality

Elite systems are clean systems.

### 9. The weekly update is a management report, not a recap

Strict ordering (already automated via ChatGPT Friday task — content order is what makes it elite, not the cadence):

1. Live portfolio first
2. What improved vs worsened (sub-metrics)
3. Biggest current bottleneck
4. Biggest hidden risk
5. What changed this week (in the lane)
6. What next week is for
7. 1-2 outside-learning / tooling items worth testing

### 10. The May 8 review is the first real proof point

The Phase 0 Review Checkpoint asks the right questions, not procedural ones. Not "did we follow the architecture?" but:

- Did the hot lane produce validation-worthy survivors?
- Did portfolio utility improve?
- Did donor learning become real?
- Did backlog stay zero?
- Did operator time stay bounded?

If yes → accelerate. If no → revise generation logic, not the calendar.

---

## The Top Four (if only four can be enforced)

The four that produce the elite leap above all else:

1. **Anchor every report and every decision to live portfolio improvement** (Principle 1)
2. **Build the cheap-kill lane fast** (Principle 2)
3. **Automate recurring prep/reporting work — operator time goes to judgment, not compilation** (Principle 5)
4. **Force every review to separate real improvement from machine activity** (Principles 6 + 9)

If a tradeoff has to be made under operator-time pressure, these four come first.

---

## Operational forms (what each principle changes concretely)

| Principle | Lives in | Concrete change |
|---|---|---|
| 1. Live portfolio anchor | Weekly Friday update + twice-monthly assessment | Both open with the single live-portfolio answer; lane metrics come after |
| 2. Cheap-kill lane fast | post_may1_build_sequence Track B | MVP screen ships Week 2; portfolio-utility scoring gate before deeper validation |
| 3. Donor learning engine | post_may1_build_sequence Track C | Weekly donor ledger surfaces winners/losers; cooling rule active; tier transitions logged |
| 4. Evidence-paced phases | post_may1_build_sequence binary exit gates | Phase advance fires when gates are ☑, not on calendar |
| 5. Auto-prep | New (post-May-1 build target) | Auto-drafted readouts, packets, rankings, tripwire reports — operator edits, doesn't compile |
| 6. Twice-monthly truth layer | New cadence (Claude evidence + operator pressure-test) | Six-question packet → one canonical assessment |
| 7. Outside intel forces change | OUTSIDE_INTEL_AND_CONTINUOUS_IMPROVEMENT §6 | Quarterly intel-to-action rule already filed; sharpen "what do we change because of this?" enforcement |
| 8. Dead-weight cleanup | New post-May-1 priority | Pre-Phase-1 cleanup batch (stale strategies, doc/runner/registry alignment) |
| 9. Weekly update format | ChatGPT Friday task content | 7-step order: live → improved/worsened → bottleneck → hidden risk → changes → next week → outside learning |
| 10. May 8 proof questions | post_may1_build_sequence §3.2 Phase 0 Review | Five evidence questions render the Phase 1 advance decision |

---

## What this doc is NOT

- **Not more architecture.** The architecture and build sequence are filed and sufficient.
- **Not a substitute for live evidence.** Principles guide behavior; live results remain the ground truth.
- **Not permission to skip the existing rails.** The hot-lane contract, suppression, authority ladder, and tripwires all stand.
- **Not a license to accelerate without gates firing.** Evidence-paced means evidence in both directions: faster on green, slower on yellow, halted on red.
- **Not the start of a polish cycle.** This is the last pre-runtime doc. The next addition earns its place via observed-failure-mode evidence, not pre-emptive sophistication.

---

## Anti-drift rule for this doc itself

If a new operating principle surfaces during the post-May-1 run, it is added here only when:

1. There is observed evidence — a specific failure mode, not a hypothetical
2. The principle is testable — defines a behavior that can be enforced and audited
3. The principle is non-redundant — does not duplicate an existing principle in different language
4. The doc length stays ≤200 lines — when adding forces removing, retirement is mandatory

Without these, this doc becomes its own form of polish. The bar is high on purpose.

---

*Filed 2026-04-29 as the final pre-runtime alignment doc. From here, the operating system runs and produces evidence. The next tightening of the principles comes from real failure modes observed in operation, not from pre-runtime imagination.*
