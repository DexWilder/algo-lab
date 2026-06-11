# Packet Standard V1 — Change Control

> **Status:** Locked 2026-06-11.
> **Governs:** Changes to [[packet_standard_v1]] for the remainder of the Paper-Readiness Sprint.

## Default: V1 is frozen for the sprint

After ratification, Packet Standard V1 governs candidate classification through end of sprint (2026-07-02).

**The classification rules do not change in response to candidate results.** This is the entire point — eliminate ad-hoc rule churn that reverses verdicts.

## Allowed V1 changes (non-emergency)

Trivial, non-substantive:
- Typo fixes
- Formatting cleanup
- Clarifying examples that do not change verdicts
- Documentation of already-defined rules

Anything that could change a candidate's verdict is NOT allowed under "allowed V1 changes." It must go through V1.1 emergency (if integrity) or V2 backlog (if improvement).

## NOT allowed during V1

- Changing PF thresholds after seeing candidate results
- Changing concentration gates to save a candidate
- Changing archetype assignment after seeing outcome without written cause
- Adding filters because a near-miss almost passed
- Selectively applying new rules to one candidate
- Repeated ad-hoc reclassification
- Lowering stress requirements to rescue knife-edge results

## V1.1 emergency integrity amendment

V1.1 is for INTEGRITY DEFECTS only. The trigger list is exhaustive:

1. Data corruption
2. Lookahead in the strategy or test harness
3. Materially wrong cost model
4. False calendar source (event date doesn't match official record)
5. Engine execution / fill error
6. Invalid session / rollover handling
7. Reproducibility failure (signal hash differs across runs)

Anything else goes to V2 backlog.

### V1.1 enforcement clause (per operator addition)

> **Every V1.1 emergency integrity amendment MUST:**
> 1. List every prior candidate affected by the integrity defect.
> 2. Apply the new rule retroactively to ALL affected candidates in a single audit pass.
> 3. Never apply selectively to one candidate.
> 4. State whether each prior verdict changes (yes/no) under the amendment.
> 5. Update the inventory rescore table once with all changes.

A V1.1 amendment that affects only one candidate is forbidden — if a rule is general enough to be doctrine, it applies to all candidates the rule could touch.

A V1.1 amendment that excuses some candidates from the new rule via discretion is forbidden.

V1.1 amendments are versioned (V1.1, V1.2, ...) and dated. Each version's first commit pushes the retroactive rescore update simultaneously.

## V2 backlog

Non-integrity improvements (better gate ergonomics, additional archetype refinements, audit-quality enhancements) accumulate in a V2 backlog. They do NOT churn V1 verdicts mid-sprint.

V2 ratification happens at end of sprint or operator-triggered review. V2 may revise V1.x verdicts as part of its launch, but only as a complete reset of inventory, not selective.

## What change control protects

The discipline this enforces: **a candidate ratified under correct rules is worth more than a candidate "accepted" under rules that flexed to fit it.**

If a near-miss is genuinely close to packet under V1 + an arguable refinement, that's a V2 backlog candidate, not a V1 verdict reversal.

## Examples (concrete)

| Scenario | Allowed? | Where it goes |
|---|---|---|
| Typo in PF threshold formula | ✅ | V1 typo fix |
| "FOMC-MGC almost passed, let's lower PF threshold from 1.30 to 1.20" | ❌ | V2 backlog (not allowed in V1) |
| Discovered data corruption affecting 5 candidates | ✅ | V1.1 emergency, applied to all 5 |
| "Era 3 median rule too harsh for FOMC, exempt FOMC candidates" | ❌ | V2 backlog |
| Strategy uses lookahead | ✅ | V1.1 emergency, applied to all affected candidates |
| "Better instance-CV formula" proposal | Backlog | V2 backlog |
| Calendar source was wrong | ✅ | V1.1 emergency, re-audit affected candidates |

## Cross-references

- [[packet_standard_v1]] — the standard itself
- `docs/fql_forge/PACKET_STANDARD_V1_2026-06-11.md` — frozen spec
- [[feedback_evidence_integrity_failsafe]] — fail-closed rule
- [[feedback_proactive_plumbing_inspection]] — inspect-don't-infer
