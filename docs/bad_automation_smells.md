# Bad Automation Smells

**One-page reference. Standing governance note.**

Patterns that make FQL's automation look healthy while quietly failing.
Each smell: what it is, why it's dangerous, concrete FQL instance (where
we have one), early warning sign, and what to do when detected.

This list grows. New smells get added as they're observed, not
hypothesized. Initial seed drawn from week of 2026-04-14 operational
findings.

---

## 1. Advisory-only component treated as decision authority

**What:** A component was demoted to advisory only, but its outputs are
still consumed as if actionable. Operator mentally flags them, then
forgets the flag.

**Why dangerous:** The system looks automated. The operator is silently
doing the real classification in their head. Nobody notices until the
operator changes or gets distracted.

**Concrete FQL instance:** `scripts/fql_alerts.py` closed-family
detector after 2026-04-17 (8/8 FP). Demotion is explicit in
`improvement_log.md` — but if a future reader misses that note, they
might wire the same detector into auto-action.

**Early warning:** Outputs from a component are cited in operator
decisions without anyone re-checking trust level. Reference predates
any trust-level validation.

**What to do:** Tag the component's output file or doc explicitly
(`STATUS: ADVISORY ONLY — do not drive auto-action`). Enumerate
advisory-only components in weekly rollup. Auto-action authority must
be *earned* by validation, not *assumed from existence*.

---

## 2. Detector precision unknown but outputs operationalized

**What:** A detector fires. Downstream consumers read its output.
Nobody has measured false-positive or false-negative rate.

**Why dangerous:** "Signal from a detector" is not the same as "trusted
signal." Consuming unmeasured outputs is gambling. Worst case: bad
outputs get auto-actioned before the quality check ever happens.

**Concrete FQL instance:** closed-family detector was consumed by the
operator digest as escalating ALERTs for weeks before today's batch
spot-check revealed 100% FP rate. Nobody had measured precision.

**Early warning:** A detector exists, fires regularly, is cited in
downstream docs or alerts, but no file or log records its measured
precision on actual data.

**What to do:** Before consuming detector output downstream, run a
batch spot-check with labeled ground truth. Record FP/TP count in a
dedicated doc. Re-check quarterly or when the underlying distribution
might have shifted.

---

## 3. Fallback path becoming the default path

**What:** A workflow has a primary path and a fallback. Operator
gradually prefers the fallback because it's easier, faster, or more
predictable. Eventually fallback is the path, primary is the exception.

**Why dangerous:** The system was designed with the primary path as
the trusted mechanism. Drift into fallback-by-default means the system
is no longer being run as designed — but documentation still describes
the original design.

**Concrete FQL instance:** not yet observed in Forge (first week had
0% fallback usage), but `cadence.md` 40% fallback threshold exists
because the designer anticipated this smell.

**Early warning:** Fallback usage rate creeping above 25% sustained;
operator narrates fallback work in ways that sound like normal work
("today I cleaned up some memory payloads") without acknowledging it
was fallback.

**What to do:** Track fallback usage rate as an integrity metric. Flag
sustained >40%. When flagged, do not raise the threshold — investigate
why the primary path stopped working.

---

## 4. Queue growth masking lack of closure

**What:** Queue depth increases. Looks like "we're doing more work."
Actually closure rate is flat; intake grew.

**Why dangerous:** Throughput measured by queue activity looks
productive. Throughput measured by closure/resolution is flat. Gap
between the two is the smell.

**Concrete FQL instance:** harvest backlog 183 → 217 (+34) over 3
days. Closure on those items is much slower. If we measured "Forge is
busy" by queue activity alone, we'd be misled.

**Early warning:** Queue count in digest increases week over week;
closure count in scorecard doesn't. Operator reports feel productive;
closure ratio (resolved/opened) drops below 1.0.

**What to do:** Always report closure ratio alongside queue depth.
Anti-drift metrics exist for this — enforce them. Sustained closure
ratio < 1.0 is a harvest-to-closure imbalance requiring either more
closure capacity or less intake.

---

## 5. Apparent automation that still requires hidden manual judgment

**What (the worst one):** A pipeline looks automated end-to-end. In
practice, at least one step requires a human to check something, make
a call, or apply context the code can't. The human workload is
invisible because nobody logged it.

**Why dangerous:** System appears scalable; isn't. As volume grows,
the hidden manual step becomes the binding constraint. Nobody sees it
until the operator is drowning.

**Concrete FQL instance:** today's closed-family alerts. "Automated
detector → automated alert → operator dismisses after mental check"
*looks* like 2-step automation. Is 2-step automation + 1 hidden manual
classification per alert per day. At 8 alerts/day × 30 days = 240
hidden classifications before anyone measured the precision.

**Early warning:** Operator habitually reviews outputs of an
"automated" component before acting on them. That review time is real
work but isn't tracked anywhere. When asked "is this automated?" the
operator says "yes, mostly."

**What to do:** If a step requires human judgment, make it explicit —
tag the component as human-in-loop, not automated. Track the human
time. Human-in-loop is a legitimate design; pretending it's automated
is the smell.

---

## 6. Auto-action with no disagreement gate

**What:** Auto-action fires purely on detector output, without
cross-checking against an independent authority (peer component, human
review, second detector using different logic).

**Why dangerous:** A single-source detector has no backstop. One bad
detection becomes one bad action. At scale, one bad detection pattern
becomes many bad actions.

**Concrete FQL instance:** exception pipeline design Phase C was
*originally* designed as pure auto-reject on closed-family detector
match. Today's 8/8 FP finding would have meant 100% of auto-rejects
were wrong. Added detector-replacement prerequisite to avoid this.

**Early warning:** An auto-action's inputs trace to exactly one
detector with no quality check or agreement requirement.

**What to do:** Never wire auto-action against a single unvalidated
source. Require either (a) measured precision ≥ threshold, (b) agreement
with a second independent authority, or (c) operator confirmation.
Pipeline design §3 HARVEST_NOISE pattern is the template.

---

## 7. Classification without closure tracking

**What:** An item gets classified (alert, warning, status change) but
there's no mechanism to track it to resolution. The classification
reappears daily, each time treated as "new," each time dismissed
manually.

**Why dangerous:** Same cognitive load repeatedly. Operator burnout.
The system has no memory of "we already decided this doesn't matter."

**Concrete FQL instance:** the 8 closed-family alerts escalating
x8/x16/x23 days. Each day they re-fire, each day operator re-sees
them. No mechanism for "dismiss and suppress."

**Early warning:** Same alert text appearing in digest N days in a
row. Escalation counts climb without the item changing.

**What to do:** Exception pipeline closure tracker (design §1,
`closure_tracker.py`) is the answer. Until it's built: operator can
manually add a "dismissed-until" field to the alert source data.

---

## 8. Silent state divergence between monitoring surfaces

**What:** Two components both claim to monitor the same thing. Their
outputs quietly drift apart. Neither checks the other.

**Why dangerous:** The operator reads whichever surface is
convenient. Might be the wrong one. The *right* one might be broken.

**Concrete FQL instance:** 2026-04-16 — `watchdog_state.json`
timestamp was 23h old while `fql_doctor.py` reported watchdog ran 4min
ago. Two sources disagreed; nothing caught it. Caught only because
human noticed mtime.

**Early warning:** When two sources report on the same subsystem, no
code compares them. "Trust whichever is fresher" is not a policy.

**What to do:** Meta-monitoring (exception pipeline design §5). Any
monitoring file expected fresh must have a freshness SLO enforced.
Cross-check across surfaces where they exist.

---

## 9. Phantom automation — scheduled job runs but doesn't change state

**What:** A job fires on schedule. Logs show it ran. But its output
state doesn't update because the job only writes on state-change, or
only writes on failure, or some other conditional. Looks healthy; is
dead.

**Why dangerous:** Job appears to be working. It isn't producing the
output the system relies on. Downstream consumers read stale state and
assume it's current.

**Concrete FQL instance:** `fql_watchdog.sh save_state()` only writes
on state change. If no state changes for 23h, file is 23h stale but
job is running fine. Fixed in pipeline design Phase A (heartbeat every
run).

**Early warning:** A scheduled job's log shows regular runs, but its
output state file's mtime is much older than the log's mtime.

**What to do:** Jobs should write a heartbeat every run, independent
of whether they detected something. "No detection" is information and
should be recorded.

---

## 10. Self-referential validation loop

**What:** A component's outputs are validated only by another
component that reads the same component's outputs. No external ground
truth ever enters the loop.

**Why dangerous:** Internally consistent does not mean correct.
Two components can reinforce each other's errors indefinitely.

**Concrete FQL instance:** not yet directly observed, but risk exists
once Forge kernel + exception pipeline are both running. Kernel
generates candidates; pipeline classifies them. If both rely on
genome-map definitions without external validation, blind spots
compound.

**Early warning:** Component A's output is validated by component B;
component B's validation logic references the same rules/configs that
generated A's output. No user feedback, no live PnL, no independent
data source enters the loop.

**What to do:** Ensure at least one external ground truth touches the
loop — live trade results, human review sample, out-of-sample
backtest, or reference dataset. If none exists, flag the loop as
self-referential in its doc header.

---

## How to use this list

- **Weekly rollup:** skim the 10 smells. Ask: has any appeared this
  week that wasn't here before?
- **New component design:** before shipping, check the smells that apply
  to the component's category. Pre-empt them.
- **Debugging surprise behavior:** one of these is usually the cause.
  Start here before deeper investigation.
- **Before granting auto-action authority:** every applicable smell
  must be absent. No exceptions.

## Adding to this list

A new smell earns a slot when:
1. It's been observed in FQL (or in a very similar system with clear
   transfer) — not hypothetical
2. Its failure mode is distinct from existing entries
3. It has a concrete early-warning sign that can actually be monitored

Hypothetical smells that haven't been observed go in `docs/roadmap_queue.md`
with "smell candidate" tag, not here.
