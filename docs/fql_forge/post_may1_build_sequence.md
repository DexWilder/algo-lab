# DRAFT — Post-May-1 Build Sequence (Always-On Production Engine)

**Status:** Filed 2026-04-29 as canonical post-May-1 operating reference. Hold-compliant. Execution begins 2026-05-04 (Monday after May 1 checkpoint). Phase 0 Review Checkpoint: 2026-05-08 EOD.

**Companion to:** `docs/fql_forge/hot_lane_architecture.md` (canonical for WHAT). This doc is canonical for WHEN, IN WHAT ORDER, WITH WHICH TRIPWIRES, AND AT WHAT COST.

**Authority for execution:** T2 for hybrid registry appends; T3 for any status transition past `idea`; T0 for the lane and the build sequence itself.

**Premise.** Architecture is approved. Execution sequencing brings cheap first-pass forward as a mandatory partner, wires donor attribution from day 1, operationalizes anti-backlog as enforced behavior, and constrains the lane on five additional surfaces that separate "high-throughput smart machine" from "elite production engine": **cost efficiency, portfolio utility, exploration, toxic-donor suppression, multi-stage survivor quality.** Core instruction: **find and test ideas faster, recombine aggressively, reject fast, learn from donor survival, stay governed by the same rails — and constrain on cost, novelty, utility, and quality so throughput cannot disguise drift.**

---

## 1. The four parallel tracks (NOT a sequential phase ladder)

Architecture's Phase 0 → 1 → 2 ladder is correct. Within each phase, four tracks run **in parallel**, not in series:

| Track | What it does | First-week deliverable |
|---|---|---|
| **A — Hot lane Phase 0** | Generator skeleton + donor catalog + manual run pattern | First 3-5 hybrid specs generated under §3.1-3.2 contract |
| **B — Cheap first-pass kill lane** | Lightweight test path that rejects weak hybrids fast + portfolio-utility scoring | MVP screen + ranking + utility score running on hybrid output |
| **C — Donor attribution/scoring** | Counters wired from day 1; every outcome credits/debits donors; cooling rule for toxic donors | Counters in `donor_catalog.json`; first attribution event logged |
| **D — Anti-backlog closure rule** | Hard constraint: no approved hybrid sits unregistered; survivor-inflation tripwire | Tripwire script + same-day registration discipline |

Track A produces output. Track B receives, screens, and scores it. Track C learns from results and suppresses toxic donors. Track D enforces traceability and detects metric gaming. Skipping any one creates a hidden failure mode the others cannot recover from.

---

## 2. Time-budget contract per track (hard resource ceilings)

Elite systems constrain cost, not just output. Each track has a hard ceiling. Exceeding it is a tripwire event, not a budget overrun to be amortized.

| Track | Resource | Hard ceiling | Tripwire response |
|---|---|---|---|
| **A — manual generation (Phase 0)** | Operator time | **≤4 hours/week** for review + triage + manual append | If >4h required, generator output is too noisy; tighten §3.2 enforcement before next run |
| **A — automated generation (Phase 1+)** | Operator time | **≤30 minutes/week** for review + override | If >30m required, automation isn't holding the contract; halt and diagnose |
| **B — cheap screen** | Compute | **≤30 seconds/candidate** end-to-end | If a candidate runs longer, the screen is not cheap; redesign before adding throughput |
| **B — portfolio-utility scoring** | Compute | **≤10 seconds/candidate** | Same response as cheap screen |
| **C — attribution maintenance** | Operator time | **≤30 minutes/week** for tier-transition review + override window | If >30m, tier logic needs tightening or transitions need batching |
| **D — tripwire handling** | Operator time | **Same-day only — no spillover** | Tripwire fires Wednesday → cleared by EOD Wednesday OR generation halts Thursday automatically |

**The cost-efficiency principle:** if the lane requires more operator time than the harvest-only intake it replaces, the lane has not made the system elite — it has made it expensive. Costs cap before throughput targets do.

---

## 3. Track A — Hot lane Phase 0 activation

**Reference:** `_DRAFT_hot_lane_architecture.md` §3 (contract) + §4 Phase 0.

### 3.1 MVP build (Week 1: May 4-8)

| Day | Build | Output |
|---|---|---|
| Mon May 4 | `research/data/donor_catalog.json` — consolidate `proven_donors` + CVH `result=validated` + CVH `salvaged` / `parent_failed_concept_potentially_reusable`. Three tiers: `proven` / `candidate` / `salvage`. Include §3.5 attribution counter scaffolding (zeros) and cooling-state field. | Donor catalog file, ≥17 entries (matches yesterday's gate count) |
| Tue May 5 | `research/hybrid_generator.py` skeleton implementing §3.1 inputs + §3.2 output spec. Templates from §3.4 only. Bounded recombination per §3.3. **Novelty quota enforcement** (§3.3 below). | Script that emits 3-5 hybrid spec dicts to stdout |
| Wed May 6 | Manual run #1. Operator reviews specs against §3.2 minimum-fields check + novelty quota. Picks 1-2 keepers. Stages `_DRAFT_2026-05-07_hybrid_batch_register.md` pre-flight. | Pre-flight draft with 1-2 hybrids ready for next-day append |
| Thu May 7 | Append manual hybrids to registry as `status=idea`, `triage_route=hybrid_generation_lane`, full traceability fields populated. | **First `components_used` populations in registry history.** Item 2 cross-pollination criterion moves from 0 toward 2. |
| Fri May 8 | Phase 0 retro. Which §3.4 templates worked? Which donors looked productive? What did §3.2 catch? Adjust skeleton — within contract only; do not relax §3.2/§3.3 to accommodate weak specs. | Retro notes; generator adjustments; Phase 1 readiness assessment |

### 3.2 Phase 0 exit gate (binary — all five must be ☑ to advance)

**Phase 0 Review Checkpoint: Friday 2026-05-08, EOD.** Not "end of week sometime" — a literal scheduled review session where the five gates below are evaluated and the Phase 1 advance decision is rendered. Same surgical pattern as the May 1 checkpoint: dated, scoped, decision-ready.

- ☐ Donor catalog consolidated (proven_donors + CVH merged; tiers assigned; §3.5 counters present; cooling-state field present)
- ☐ First `components_used` entries written successfully to registry
- ☐ 3-5 hybrid specs generated under §3.1-3.2 contract
- ☐ At least 1 hybrid survives manual triage and reaches registry as `idea`
- ☐ No schema drift; no governance exceptions required

### 3.3 Novelty quota (anti-drift control)

A hot lane that always recombines the same proven donors becomes locally optimized. Two quotas, enforced at generator output time:

- **Exploration quota:** ≥30% of weekly hybrids must use a donor pairing or template combination **not used in the prior 2 weeks**. Measured per twice-weekly run.
- **Gap-direction quota:** ≥25% of weekly hybrids must explicitly target a portfolio gap from `docs/PORTFOLIO_TRUTH_TABLE.md` open-gaps section, not just recombine known good families.

Generator must self-report quota compliance per run. If either quota falls below threshold, the run flags `EXPLORATION_DEFICIT` and operator decides whether to accept the run (one-time exception, logged) or regenerate.

**The exploitation/exploration split:** ≤70% of hybrids may exploit known-good pairings; ≥30% must explore novel combinations. Without this rule, donor attribution becomes circular — the system rewards the donors it already over-uses.

### 3.4 Template lifecycle — retirement AND resurrection

Templates from §3.4 (architecture doc) are not permanent.

**Retirement (existing rule, sharpened):**
- Template produces 10 hybrids with **zero cheap-screen survivors** → retired automatically
- Template produces 20 hybrids with **zero validation-worthy survivors** (per §6 split metric) → retired automatically even if cheap-screen survival > 0
- Retired templates are flagged in `donor_catalog.json` with `template_status: retired` and the retirement reason

**Resurrection (NEW):**
A retired template can come back, but only under a defined evidence path:
- **Time floor:** retired template is ineligible for resurrection for ≥90 days
- **Context-shift trigger:** if ≥2 of the original donors used in the retired template have moved tiers (e.g., proven → retired, or salvage → candidate) since retirement, the template can be flagged `RESURRECTION_ELIGIBLE`
- **Operator approval required:** resurrection is never automatic. Operator must explicitly mark `template_status: resurrected` with a reason citing what changed
- **Probation period:** resurrected template re-enters with a 5-hybrid probation. If it produces zero survivors in probation, it's permanently retired (no further resurrection).

**The principle:** elite recombination is ruthless on dead templates but not amnesiac. Resurrection exists because donor tier shifts can change a template's expected value — but resurrection requires evidence of context change, not nostalgia.

---

## 4. Track B — Cheap first-pass kill lane + portfolio-utility scoring

This is the hot lane's mandatory partner. Two stages: cheap screen (rejects garbage) → portfolio-utility score (rejects standalone-good-but-portfolio-irrelevant hybrids before deeper validation).

### 4.1 MVP build — cheap screen (Week 2: May 11-15)

`research/hybrid_first_pass_screen.py`:
- Inputs: hybrid `strategy_id`s with `triage_route=hybrid_generation_lane` and `lifecycle_stage=discovery`
- Runs lightweight subset of factory tests: dual-archetype router + cheapest gates (PF, top-3/top-10 concentration, sample size adequacy). Skips deep walk-forward, regime decomposition, cross-asset extension at this stage.
- Outputs: ranked list with verdict per hybrid (`SCREEN_PASS` / `REJECT_FAST` / `INCONCLUSIVE`), written to `research/data/hybrid_first_pass_log.csv`.
- Triggers donor attribution updates per §3.5 (Track C).
- Time budget: ≤30s/candidate (§2 ceiling).
- Auto-updates registry: `REJECT_FAST` → `lifecycle_stage=first_pass_rejected`; `SCREEN_PASS` → routes to portfolio-utility scoring (§4.2).

### 4.2 Portfolio-utility score (gate before deeper validation)

A hybrid that passes cheap screen has shown standalone test viability. Before consuming full-factory capacity, score its portfolio fit:

| Dimension | Score | Definition |
|---|---|---|
| **Factor gap fill** | 0 / 1 / 2 | 0 = no gap targeted; 1 = partial gap (partially-served factor); 2 = direct gap (per `PORTFOLIO_TRUTH_TABLE.md` open-gaps) |
| **Session gap fill** | 0 / 1 / 2 | 0 = no session diversification; 1 = secondary session; 2 = unfilled session window |
| **Workhorse decorrelation** | 0 / 1 | 1 if behavior orthogonal to XB-ORB family (different signal source / regime / session) |
| **Cross-asset diversification** | 0 / 1 | 1 if asset is not currently over-represented in active portfolio |
| **Mechanism novelty** | 0 / 1 | 1 if the hybrid's mechanism is not a duplicate of an existing core/probation strategy |

Sum: 0-7. **Threshold: ≥3 to advance to full factory.** Hybrids scoring <3 are routed to `lifecycle_stage=screen_passed_low_utility` — they remain in registry as research memory, but consume no further test capacity.

**The portfolio-shape principle:** elite is not "many good strategies." Elite is a better portfolio. A hybrid with strong standalone stats but redundant role does not improve the portfolio; it only inflates the inventory.

### 4.3 Recurring cadence (Week 3+)

- `hybrid_first_pass_screen.py` invoked by `com.fql.twice-weekly-research` immediately AFTER `hybrid_generator.py`. Same cadence; back-to-back execution.
- Portfolio-utility scoring runs on every `SCREEN_PASS` candidate before full-factory queue.
- Survivors of BOTH gates accumulate as `lifecycle_stage=validation_worthy`; full factory picks them up.
- Rejections at either stage stay in registry with rejection taxonomy.

### 4.4 Throughput target — Track B

| Week | Hybrids screened | Cheap-screen survivors | Validation-worthy (utility ≥3) |
|---|---|---|---|
| Week 2 | 1-2 (Phase 0 manual) | 100% within 24h | 0-1 |
| Week 3 | 5-10 (first Phase 1 run) | 100% within 24h | 1-3 |
| Week 4+ | 10-20/wk (steady Phase 1) | 100% within 24h | 2-4/wk |

### 4.5 Failure conditions — Track B

- **Screen runs > 5 minutes per hybrid:** kill lane is not cheap; redesign before adding throughput
- **0 candidates pass to full factory after first 20 screened:** generator output is junk OR screen thresholds wrong; halt generation
- **REJECT_FAST rate < 60%:** screen too lax; tighten before scaling
- **REJECT_FAST rate > 95%:** screen too strict OR generator weak; investigate generator first
- **Utility-score reject rate > 80%:** generator is producing standalone-viable but portfolio-irrelevant hybrids; gap-direction quota (§3.3) is failing
- **Utility-score reject rate < 10%:** scoring may be too lenient; review thresholds

---

## 5. Track C — Donor attribution/scoring + cooling rule

### 5.1 MVP build (parallel with Track A, Week 1)

`research/data/donor_catalog.json` schema includes per-donor:
```json
{
  "donor_id": "profit_ladder",
  "tier": "proven",
  "contributed_to_pass": 0,
  "contributed_to_fail": 0,
  "uncertain": 0,
  "attempts": 0,
  "last_used": null,
  "templates_used_in": [],
  "validated_in": ["XB-ORB-EMA-Ladder-MNQ", "XB-ORB-EMA-Ladder-MCL", "XB-ORB-EMA-Ladder-MYM"],
  "cooling_state": null,
  "cooling_until": null,
  "cooling_reason": null
}
```

### 5.2 Wiring

- Generator (Track A): on every spec emitted, increments `attempts`, appends to `templates_used_in`, sets `last_used`.
- Cheap screen (Track B): on every PASS / REJECT / INCONCLUSIVE, increments the appropriate counter for every donor in the hybrid's `components_used`.
- Portfolio-utility score (Track B): contributes to the donor's `validation_worthy_count` (separate from cheap-screen `pass`).
- All writes use atomic_io.

### 5.3 Donor tier transitions (Phase 1+)

Floor: `attempts ≥ 10` before any tier transition fires.

- `proven → candidate` if `pass_rate < 0.30` after ≥10 attempts
- `candidate → proven` if `pass_rate > 0.50` after ≥10 attempts
- `salvage → candidate` if `pass_rate > 0.40` after ≥10 attempts
- `any → retired` if `pass_rate < 0.10` after ≥20 attempts

Tier transitions happen at weekly scorecard, **logged before becoming effective the following week.** Operator override window is one week.

### 5.4 Donor cooling rule (toxic-donor suppression — NEW)

Tier transitions are the long-term mechanism. Cooling is the fast suppression for donors that are actively producing failures:

- **Cooling trigger:** any donor with `contributed_to_fail` > 8 in the **last 14 days** OR `pass_rate < 0.10` over its last 10 attempts (rolling)
- **Cooling action:** donor flagged `cooling_state: cooling`, `cooling_until: <date+14 days>`. Generator excludes donors in cooling state from new hybrid specs.
- **Cooling exit:** automatic 14 days after `cooling_until`. Donor returns to its current tier; counters reset is NOT done — historical attribution preserved.
- **Repeat cooling:** if the same donor enters cooling twice in any 90-day window, it auto-demotes one tier on the second cooling event.
- **Cooling override:** operator may manually clear cooling early if there's evidence the failures were upstream (e.g., a bug in screening that has since been fixed). Override is logged.

**The toxic-donor principle:** elite recombination is not just promoting good donors — it's quickly suppressing bad ones. A donor producing 8+ failures in 2 weeks is corrupting current generation runs while waiting for the slower tier-transition mechanism to act.

### 5.5 Failure conditions — Track C

- **No attribution event logged after 5 hybrids screened:** wiring broken; halt generation
- **Single donor attempts > 50 with `pass_rate` indistinguishable from random (0.45-0.55):** signal noise; review source data
- **All donors converge to similar `pass_rate`:** attribution not informative; donor catalog may not be the right unit (could be template-driven)
- **Cooling fires on >30% of active donors simultaneously:** generator-wide quality issue, not donor-specific; halt generation and audit

---

## 6. Track D — Anti-backlog closure rule + survivor-inflation tripwire

### 6.1 The hard rule

1. **Every approved hybrid appends to registry within 24h of approval.** No exceptions.
2. **Every registry append carries full traceability.** All §3.2 fields at append time.
3. **No "approved but unregistered" entries in any draft, triage file, or scratch log.** Pre-append draft window: ≤24h.
4. **Generator throttles when downstream is saturated.** Hybrid candidates accumulating without screening (Track B) → generator pauses next scheduled run until queue clears.

### 6.2 The tripwires

`scripts/hot_lane_backlog_check.sh` (build alongside Track A in Week 1):

```
Tripwire A — Approved-not-registered:
  Find any draft/triage doc with "ACCEPT" / "approved" markers
  whose target strategy_id is NOT in registry after 48h.
  If found: HALT generation. Block next twice-weekly run.

Tripwire B — Unscreened pile-up:
  Find any registry entry with triage_route=hybrid_generation_lane
  and lifecycle_stage=discovery for >7 days (not screened).
  If found: HALT generation until kill lane drains queue.

Tripwire C — Traceability gap:
  Find any registry entry with triage_route=hybrid_generation_lane
  whose relationships.components_used is empty or relationships.parent is null.
  If found: HALT generation; investigate generator output gap.

Tripwire D — Time-budget overrun:
  Any track exceeds its §2 hard ceiling for two consecutive weeks.
  If found: HALT generation in that track until cost is recalibrated.

Tripwire E — Survivor inflation (NEW):
  Compare 4-week rolling: cheap-screen survivors trend vs.
  validation-worthy survivors trend.
  If cheap-screen survivors rise while validation-worthy survivors
  do not (or fall), filters are softening.
  If found: HALT generation; review §4.1 and §4.2 thresholds for drift.
```

Watchdog invokes this script daily — not a new launchd job, just a check the watchdog already runs adjacent to integrity monitoring.

### 6.3 Failure conditions — Track D

- **Tripwire A fires once:** investigate, document, fix; resume
- **Tripwire A fires twice in a month:** Track A faster than registration discipline can sustain; throttle Track A
- **Tripwire B fires once:** Track B undersized; expand screen capacity OR throttle Track A
- **Tripwire C fires once:** generator contract violated; pause generation, fix §3.2 enforcement, resume
- **Tripwire D fires:** cost recalibration required; the lane is more expensive than budgeted
- **Tripwire E fires:** screen is gaming the survivor metric; tighten cheap-screen gates or utility-score thresholds before the metric becomes vanity

---

## 7. Sequenced calendar (May 4 → end of May)

```
            Track A (gen)      Track B (kill+util)  Track C (donors)    Track D (closure)
Week 1     ━━━━━━━━━━━         ░ pre-build           ━━ counters         ━━ tripwires
May 4-8    Phase 0 manual                            scaffolded          live in dry-run

Week 2     ━━━━━━━━━━━         ━━━━━━━━━━━           ━━━━━━━━━━━         ━━━━━━━━━━━
May 11-15  Phase 1 auto        MVP screen +          First attribution   Tripwires A-E
           (twice-weekly)      utility score         events              enforced
                               back-to-back gen

Week 3-4   ━━━━━━━━━━━         ━━━━━━━━━━━           ━━━━━━━━━━━         ━━━━━━━━━━━
May 18-29  Phase 1 steady      Recurring screen      Tier transitions    All tripwires
           10-20/wk            + utility on every    + cooling rule      green required
           novelty quota       batch                 active              for advance
           enforced
```

---

## 8. Throughput + survivor targets per phase (split metric)

Survivor metric is **two-stage** — the headline number is validation-worthy survivors, not cheap-screen survivors.

| Metric | Phase 0 (Wk 1) | Phase 1 (Wk 2-4) | Phase 1 exit (Wk 4) | Phase 2 (Mo 2+) |
|---|---|---|---|---|
| Hybrids generated/wk | 3-5 (manual) | 10-20 | sustained 10-20 | 35-50 |
| % screened within 24h | 100% | 100% | 100% | 100% |
| **Cheap-screen survival rate** | n/a | 30-40% expected | actual measured | 10-15% |
| **Cheap-screen survivors/wk** | 0-1 | 3-7 | sustained ≥4 | 5-7 |
| **Utility-score pass rate** (of cheap-screen survivors) | n/a | 40-60% expected | actual measured | 40-60% |
| **VALIDATION-WORTHY SURVIVORS/wk (HEADLINE)** | 0 | 1-4 | **sustained ≥2** | 2-4 |
| Cross-pollination cases | 1-2 (manual) | growing | ≥2 (Item 2 measurable) | 5-10+ |
| Donor attribution events | first events | growing | every donor ≥3 attempts | every donor ≥10 attempts |
| Novelty quota compliance | n/a (manual) | ≥30% / ≥25% | ≥30% / ≥25% sustained | same |
| Tripwires fired/month | 0 | ≤1 | 0 | ≤1 |
| Operator hours/wk on lane | ≤4 | ≤30min (+screen review) | ≤30min sustained | ≤30min |

**Headline success metric: validation-worthy survivors-per-week, not candidates-per-week and not cheap-screen survivors.** A week with 50 generated, 10 cheap-screen-passing, and 0 validation-worthy is failure even at "high screen survival." A week with 10 generated, 4 cheap-screen-passing, and 3 validation-worthy is elite.

---

## 9. Failure conditions (system-level — when to halt and reassess)

| Condition | Tripwire | Response |
|---|---|---|
| Phase 0 produces zero specs that pass §3.2 check | Generator contract wrong | Redesign §3.1-3.2; do not relax check |
| Phase 1 produces ≥30 hybrids with zero validation-worthy survivors | Lane is not producing portfolio value | Halt generation; diagnose generator + utility scoring jointly |
| Donor attribution shows no signal after ≥30 hybrids | Catalog uncorrelated with survival | Halt; reassess donor unit |
| Any §3.4 template produces zero validation-worthy survivors after 20 hybrids | Template is dead | Retire template; resurrection per §3.4 protocol |
| Tripwire A or B fires repeatedly | Backlog regenerating | Throttle Track A until discipline holds |
| Tripwire D fires | Cost overrun | Recalibrate budget OR cut throughput |
| Tripwire E fires | Survivor metric being gamed | Tighten screens before resuming |
| Suppression layer bypassed once | Generator escaped governance | Halt; restore suppression precedence |
| Cross-pollination criterion still 0 after 30 hybrids | Item 2 plumbing not flowing | Halt; investigate `components_used` write path |
| Validation-worthy survivors/wk drops below 1 sustained for 2 weeks | Lane failing at portfolio value | Halt scaling; revisit generator strategy |
| Novelty quota fails for 2 consecutive weeks | Lane converging to local optimum | Halt; force exploration before resuming exploitation |
| >30% of active donors in cooling simultaneously | Generator-wide quality issue | Halt; audit generator output |

**No failure condition is "embarrassing to surface."** Each represents diagnostic information; halting on a tripwire and diagnosing is the elite move.

**The "speed is not the problem" principle.** If the hot lane increases candidate flow but does not improve validation-worthy survivors or portfolio utility within the first review window (Phase 0 Review Checkpoint, Friday 2026-05-08), speed is not the problem and the generation logic must be revised. Adding throughput on top of weak generation logic compounds the failure; "run it longer" is the wrong diagnosis when the bottleneck is upstream of throughput.

---

## 10. Dependencies (what starts May 4 vs what waits)

### Day-1 ship list (Mon May 4):
- Track A: donor catalog file (with cooling field), generator skeleton with §3.1-3.2 contract + novelty quota + template-status field
- Track C: §3.5 counters initialized; cooling-state schema present
- Track D: tripwire script with all 5 tripwires + watchdog hook (dry-run mode Week 1, enforce mode Week 2)

### Week 1 deliverable list (Fri May 8):
- Track A: 3-5 hybrid specs + 1-2 in registry with `components_used` populated + novelty quota self-reported
- Track B: MVP screen + utility-score scripts designed (built Week 2)
- Track C: first attribution events logged; cooling-state schema populated
- Track D: tripwires A-E running in dry-run mode (alerting but not yet halting)

### Week 2 deliverable list (Fri May 15):
- Track A: first automated twice-weekly run; 5-10 new hybrids; quota enforced
- Track B: cheap screen + utility scoring run back-to-back with generator; first PASS/REJECT and utility verdicts; first validation-worthy survivors identified
- Track C: tier-transition logic active (logged for visibility); cooling rule active
- Track D: tripwires in enforcement mode

### Waits (post-Phase-1, June+):
- Daily generator launchd job (`com.fql.hybrid-generation`)
- Continuous first-pass as separate daily launchd job (`com.fql.continuous-first-pass`)
- Persistent candidate queue (`research/data/candidate_queue.json`)
- Broader §3.4 templates (Phase 2 expansion, only after attribution data)
- Gap-map directed generation (depends on roadmap Item 1 activation)
- Memory-driven candidate seeding (depends on roadmap Item 2 activation)

### Hard waits (out of scope here):
- Phase 3 autonomous loop (depends on roadmap Items 1, 2, 3, 5 activating)
- Authority-class additions (none planned)

---

## 11. Weekly elite-readout (recurring report — strict ordering)

The weekly scorecard for the lane reports in this exact order. Throughput is last on purpose.

```
1. LIVE SYSTEM
   - Forward equity / drawdown / trades-this-week (the headline)
   - Any probation review thresholds hit

2. SURVIVORS-PER-WEEK
   - Cheap-screen survivors (count + rate)
   - Validation-worthy survivors (count + rate) ← HEADLINE for the lane

3. DONOR LEDGER (top movers)
   - Donor winners: top 3 promotions / pass-rate climbers
   - Donor losers: top 3 demotions / cooling events / retirements

4. PORTFOLIO-GAP COVERAGE
   - Which open gaps moved closer to filled
   - Which gaps still have zero candidates after N weeks

5. TRIPWIRE STATE
   - Which tripwires fired this week
   - Which cleared, which still active
   - Time-budget compliance per track

6. NOVELTY QUOTA COMPLIANCE
   - Exploration % (target ≥30)
   - Gap-direction % (target ≥25)
   - Templates retired this week / templates resurrected this week

7. THROUGHPUT (LAST)
   - Raw candidates generated this week
   - Tracked but explicitly not the success measure
```

**The ordering principle:** what gets reported first becomes what gets optimized for. Putting throughput last forces the question "did this generation produce portfolio value?" before the question "did we generate enough?" Vanity metrics cannot dominate the readout if they're at the bottom.

The readout is published every Friday alongside the existing weekly scorecard, in `docs/fql_forge/scorecard.md`.

---

## 12. What this build sequence is NOT

- **Not a parallel registry build.** Same registry, same authority ladder, same suppression. Track A appends use existing T2 path.
- **Not a "more candidates = better" optimization.** Validation-worthy survivors-per-week is the metric. Volume that doesn't translate is failure.
- **Not deferred first-pass.** Cheap kill lane (Track B) ships Week 2 with utility scoring, not June+.
- **Not unsupervised.** Operator stays in the loop at Phase 0 manual triage, every Phase exit gate, every tier-transition override window, every cooling override.
- **Not silent on failure.** Every tripwire halts and surfaces; nothing degrades quietly.
- **Not unbounded.** §3.3 + §3.4 + Anti-pattern #6 + Anti-pattern #9 + Track D tripwires + Track A novelty quota + Track C cooling rule + §2 time-budget contracts jointly cap the lane on output, exploration, donor health, and cost.
- **Not throughput-optimized at the expense of utility.** Portfolio-utility scoring (§4.2) is a hard gate before deeper validation; standalone-good-but-portfolio-irrelevant hybrids do not consume full-factory capacity.
- **Not amnesiac about retired templates.** Resurrection protocol (§3.4) exists; nostalgia does not.

---

## Closing rule (operator weekly check, in this exact order)

Every week, in this order:

1. **Live evidence first.** Forward results stay the headline; the lane comes after.
2. **Validation-worthy survivors before cheap-screen survivors before candidates.** Volume is means, not goal; quality is the test.
3. **Tripwires reviewed before throughput targets.** Halt-conditions outrank growth conditions.
4. **Time-budget compliance before scaling.** If §2 ceilings exceeded, scaling adds cost without justification.
5. **Track D backlog count == 0 is the precondition for any Track A acceleration.** No new throughput on top of hidden drift.
6. **Novelty quota compliance before reading donor performance.** If exploration deficit, donor attribution is suspect.
7. **Cooling-state donors excluded from new generation runs.** Toxic-donor suppression is enforced, not advisory.

If those seven orderings stay intact, the lane is governed even as it accelerates. If any of them slip, the rails are gone — fix that before adding speed.

---

*Filed 2026-04-29 alongside `hot_lane_architecture.md`. Together they form the canonical post-May-1 build reference. Operational May 4. The next tightening pass comes from real operating evidence, not pre-runtime polish.*
