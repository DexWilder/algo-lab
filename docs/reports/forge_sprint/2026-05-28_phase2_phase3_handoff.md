# Forge Sprint — Phase 2 outcome + Phase 3 plan (2026-05-28)

This document is the durable hand-off between the Offensive Forge Sprint v1
(Phase 2) and the next scaled sprint (Phase 3). It records what we landed,
what's queued for controlled mutation, and what the next sprint must include.

---

## Phase 2 result (Offensive Forge Sprint v1)

**Screen used:** upgraded intake gate set (commits 55ef6d2 + e8dac9a).
Full metric set per candidate including top-3 / top-10 / max-year /
H1-H2 PF / archetype tag / verdict / blocker.

**Candidates tested:** 7

| Verdict | Count | Candidates |
|---|---|---|
| PASS_TO_FORWARD_CLOCK | 3 | XB-ORB-EMA-ATRTrail-MNQ, XB-ORB-EMA-TimeStop-MNQ, **XB-PB-EMA-Chandelier-MNQ** (wired) |
| MUTATE | 2 | XB-BB-EMA-Ladder-MES (PF too low), XB-ORB-Afternoon-Ladder-MNQ (PF too low) |
| DEFER | 1 | XB-PB-EMA-TimeStop-MNQ (max-year 41.5% just over 40% gate) |
| KILL | 1 | XB-VWAP-EMA-Ladder-MNQ (3/8 years positive) |

**Wired (commits 2fb2007 + db67310):** `XB-PB-EMA-Chandelier-MNQ` as Track 2
EXPERIMENTAL_FORWARD_CLOCK. Different entry family (pullback) than the first
Track 2 candidate (Chandelier-MNQ ORB) — tests payoff-ratio generalization.

**Not wired** (correlated-with-Chandelier-MNQ family — would dilute Track 2):
`XB-ORB-EMA-ATRTrail-MNQ`, `XB-ORB-EMA-TimeStop-MNQ`. Held until Chandelier
forward evidence specifically argues for an exit-mechanism comparison.

**Forward clocks active after Phase 2:**
- Track 1: `XB-ORB-EMA-Ladder-MNQ` (28/30, near packet)
- Track 2: `XB-ORB-EMA-Chandelier-MNQ` (0 forward, archetype review at 30)
- Track 2: `XB-PB-EMA-Chandelier-MNQ` (0 forward, archetype review at 30)

---

## Mutation queue (Phase 2 → Phase 3 carryover)

Each item is a single controlled mutation with one named hypothesis. To be
run through the upgraded cheap-screen at the start of Phase 3. **No wire
decision until screen produces a clean verdict.**

### M1 — XB-BB-EMA-Ladder-MGC (asset swap from MES)

- **Parent failure:** `XB-BB-EMA-Ladder-MES` → MUTATE on PF 1.14 (below 1.20),
  with extreme concentration (top-3 105%, top-10 202%, max-year 78%).
- **Hypothesis:** BB-reversion mean-reversion edge is stronger on gold (MGC)
  per CLAUDE.md portfolio observations and the family sweep's pattern that
  MGC favors counter-trend mechanisms.
- **Mutation type:** asset swap, mechanism unchanged
  (entry=bb_reversion, filter=ema_slope, exit=profit_ladder).
- **Portfolio role:** mean-reversion / non-index diversification.
- **Decision rule:** if PF ≥ 1.20 AND concentration clean → wire as Track 1
  workhorse candidate (or Track 2 if median negative).

### M2 — XB-ORB-Afternoon-Chandelier-MNQ (exit swap from Ladder)

- **Parent failure:** `XB-ORB-Afternoon-Ladder-MNQ` → MUTATE on PF 1.06
  (well below 1.20), concentration broken (top-3 59%, top-10 135%, max-year 58%).
- **Hypothesis:** afternoon ORB may have payoff-ratio shape rather than
  workhorse — every other ORB+EMA exit-variant produced PAYOFF_RATIO archetype
  in Phase 2. Chandelier exit may convert the failing-workhorse afternoon
  signal into a viable Track 2 candidate.
- **Mutation type:** exit swap (profit_ladder → chandelier), session filter
  unchanged.
- **Portfolio role:** session diversification (afternoon).
- **Decision rule:** if PASS_TO_FORWARD_CLOCK as PAYOFF_RATIO → wire as Track 2.
  If still MUTATE/KILL, drop afternoon ORB family entirely.

### M3 (optional) — PB-TimeStop year-stratification analysis

- **Parent verdict:** `XB-PB-EMA-TimeStop-MNQ` → DEFER on max-year 41.5%
  (1.5pp over 40% gate). All other gates clean.
- **Hypothesis:** the 41.5% max-year is likely concentrated in one outlier
  year. If that year was a known regime (e.g. 2020 COVID, 2022 rate-hike),
  a regime-aware filter could exclude it without overfitting.
- **Action:** year-stratification table before any mutation. May not require
  a mutation at all if the concentration is structurally regime-driven.
- **Priority:** lower than M1/M2; only run if Phase 3 capacity allows.

---

## Phase 3 plan (required mix, not yet authorized to run)

**Goal:** 15–20 candidate offensive sprint with broader diversity than Phase 2.

**Sourcing rule (lightweight correlation guard):**

> Do not promote multiple candidates that share the same asset + entry + filter
> unless the purpose is explicitly an exit-mechanism comparison.

**Diversity requirements for Phase 3 sprint:**

| Requirement | Target |
|---|---|
| Non-MNQ candidates | ≥ 4 |
| Non-ORB candidates | ≥ 3 |
| Afternoon / session-diversification candidates | ≥ 3 |
| Mean-reversion / stabilizer candidates | ≥ 3 |
| Tail / payoff-ratio candidates | ≥ 2 |
| Non-index candidates (FX / rates / commodities ex-MGC) | ≥ 2 if primitives/data allow |

**Screen unchanged from Phase 2** (full intake gate set; archetype + verdict).
**Promotion cap unchanged:** up to 3 to Track 1 or Track 2 from a single sprint.

**Pre-run gate (do not run Phase 3 until):**
1. ✓ PB-Chandelier wire verified (done 2026-05-28).
2. ✓ Mutation queue recorded (this document).
3. Phase 3 sprint candidate list drafted with the diversity check applied at
   sourcing time (not just at promotion time).

---

## Living state at end of Phase 2 (2026-05-28)

```
Track 1 — Paper Packet Track
  XB-ORB-EMA-Ladder-MNQ          28/30 forward trades  (anchor, near packet)

Track 2 — Experimental Forward Clock
  XB-ORB-EMA-Chandelier-MNQ      0 forward trades  (wired 2026-05-27)
  XB-PB-EMA-Chandelier-MNQ       0 forward trades  (wired 2026-05-28)

Mutation queue (Phase 3 entry)
  M1: XB-BB-EMA-Ladder-MGC
  M2: XB-ORB-Afternoon-Chandelier-MNQ
  M3 (optional): PB-TimeStop year-stratification

Deferred (out of immediate sprint scope)
  XB-ORB-EMA-Ladder-MYM          concentration re-check pending
  XB-ORB-EMA-Ladder-MCL          fragility / broker-rate / half-life
  XB-PB-EMA-Ladder-MNQ           PENDING_EXECUTABLE_MODULE
  XB-PB-EMA-TimeStop-MNQ         max-year 1.5pp over 40% gate
  XB-ORB-EMA-ATRTrail-MNQ        correlated with ORB-EMA-Chandelier
  XB-ORB-EMA-TimeStop-MNQ        correlated with ORB-EMA-Chandelier

Killed
  XB-VWAP-EMA-Ladder-MNQ         3/8 years positive (structural)
```

---

## Pointers

- Phase 2 sprint result: `docs/reports/2026-05-28_offensive_sprint_v1.json` / `.log`
- Phase 2 measurement evidence for wired candidates: registry rule_summary + notes
- Upgraded screen helper: `research/forge_screen_metrics.py`
- Upgraded screen integration: `research/fql_forge_batch_runner.py:_metrics`
- Three-track candidate model: `feedback_three_track_candidate_model.md` (memory)
- Candidate readiness ladder: `project_candidate_readiness_ladder.md` (memory)
