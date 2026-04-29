# DRAFT — FQL Forge Hot Lane Architecture (Always-On Strategy Production Engine)

**Status:** Filed 2026-04-29 as canonical architecture reference. Hold-compliant. Execution begins 2026-05-04. Companion: `docs/fql_forge/post_may1_build_sequence.md` (canonical for WHEN/HOW).

**Authority for execution:** T2 for hybrid registry appends; T3 for any status transitions past `idea`; T0 for the lane itself (operator authority over scope).

**Premise.** Forge has graduated from disordered intake to disciplined sorter. The next graduation is from sorter to **always-on strategy production engine.** This doc specifies the concrete build, the existing-system insertion points, and the sequence — MVP first, throughput escalation after evidence, autonomous loop deferred until prerequisites earn it.

---

## 1. Diagnosis — where throughput chokes today

| Stage | Current rate | Bottleneck |
|---|---|---|
| Harvest (Claw) | 15-26 notes/cycle | Healthy — output abundant |
| Triage | 10-30% accept | Healthy — disciplined |
| **Hybrid generation** | **0/week** | **THE BOTTLENECK — does not exist as a process** |
| First-pass test (factory) | ~3-7/week | Capacity-constrained, but not the binding constraint |
| Validation battery | gated | Healthy by design |
| Promotion to probation | T3-gated | Healthy by design |

**Day-14 gate Item 2 verdict (yesterday) is the smoking gun:** 17 components catalogued, 25 rejected/archived strategies declare `extractable_components`, 3 components flagged `parent_failed_concept_potentially_reusable` — **and zero strategies have ever populated `relationships.components_used`.** The plumbing exists; no traffic flows through it.

**Implication:** even doubling first-pass test capacity wouldn't change throughput materially, because the input stream is harvest-only. Adding hybrid generation roughly doubles candidate volume without touching the test infrastructure.

**The fix is generation, not testing.** Then testing scales after.

---

## 2. Architecture — where the hot lane plugs in

```
[Harvest Engine]  ────┐
                       ├──► [Triage] ──► registry: status=idea ──┐
[Source Helpers] ─────┘                                            │
                                                                   ▼
[Component Catalog] ◄──── (extracted from validated + rejected) ──┤
        │                                                          │
        ▼                                                          │
[HYBRID GENERATOR] ────► hybrid specs ──► registry: status=idea  ──┤
   donor + parent +                       triage_route=             │
   gap-map +                              hybrid_generation_lane    │
   constraint gates                       components_used POPULATED │
                                                                    │
                                                                    ▼
                                                          [Candidate Pool]
                                                                    │
                                                                    ▼
                                                  [First-Pass Test (factory)]
                                                                    │
                                                              ─────┴─────
                                                              │         │
                                                          REJECT     SURVIVOR
                                                              │         │
                                                              ▼         ▼
                                                         registry:  [Validation
                                                         rejected,   Battery]
                                                         taxonomy        │
                                                                         ▼
                                                                    [Probation]
                                                                    (T3 gate)
```

**Hot lane = the new node in the middle.** Everything around it is existing infrastructure. The lane reads from registry components + donor catalog, writes hybrid specs back into the registry as new `idea` entries, and lets the existing factory + validation + governance stack handle the rest.

**The lane is internal, not parallel.** Hybrids share the registry, the authority ladder, the suppression layer, the dual-archetype factory, the elite promotion standards. Throughput goes up; standards do not.

---

## 3. Generator contract (operating spec — the lane's hard rules)

The contract is what makes the hot lane a machine instead of artisanal ideation. Every section below is binding from Phase 0 onward.

### 3.1 Generator inputs (required)

Every generator invocation must accept and respect these inputs:

- **donor component** — the seed component being recombined
- **donor confidence tier** — `proven` / `candidate` / `salvage` (per donor catalog)
- **source parent(s)** — one or two existing strategies whose structure scaffolds the hybrid
- **allowed family targets** — which families this hybrid is permitted to seed
- **blocked family targets** — closed families + currently-suppressed clusters (read from `inbox/_family_queue.md`)
- **regime/session compatibility** — donor's validated regime/session must match target context
- **factor tags** — VALUE / CARRY / EVENT / STRUCTURAL / VOLATILITY
- **asset scope** — specific tickers or asset class
- **required supporting filters** — e.g., a regime filter mandatory when donor was validated only in specific regimes
- **forbidden pairings** — e.g., no pairing with components from a parent in the same closed-family lineage

Without this contract Phase 0 drifts into ad hoc recombination and the lane loses repeatability.

### 3.2 Hybrid spec — minimum required fields (intake-boundary check)

Every hybrid spec emitted by the generator must populate ALL of these. Specs missing any field are rejected at the intake boundary; they do not reach registry append:

- `strategy_id` (proposed canonical name)
- `parent_family` (which existing family this hybrid extends or recombines)
- `factor` (one of the 5 factor tags)
- `entry_logic` (named component or rule reference)
- `exit_logic` (named component or rule reference)
- `filters_gates` (list of regime / session / quality filters)
- `target_asset` and `target_session`
- `relationships.components_used` (donor IDs from donor catalog — non-empty)
- `relationships.parent` (scaffolding parent)
- `relationships.salvaged_from` (donor source — when any donor came from a failed parent)
- `rationale_for_combination` (one sentence — why this specific combination)
- `expected_portfolio_role` (gap targeted, role within portfolio)
- `cheap_test_path` (which first-pass profile applies — workhorse vs tail-engine)

This is the floor. The generator outputs testable candidates, not pretty prose.

### 3.3 Bounded recombination — combinatorial restraint

Hybrids are built from **bounded combinations only.** Unrestricted N-way recombination is forbidden at every phase.

- **Phase 0:** 2-component and 3-component combinations only
- **Phase 1:** still bounded; only the approved pairing templates from §3.4 are eligible
- **Phase 2:** broader templates may be admitted, but only after donor attribution from Phase 1 has produced clean signal on which combinations actually survive

"Aggressive recombination" does not mean unbounded; it means high-volume within a tight contract. This rule is what prevents the lane from degenerating into combinatorial explosion the moment volume goes up.

### 3.4 Phase 0 pairing templates (the initial 6)

The first wave of hybrids comes from one of these patterns only. Generator must tag each spec with the template it came from.

1. **Entry donor + regime filter donor** — proven entry combined with a separately-validated regime gate
2. **Entry donor + exit donor** — proven entry combined with a separately-validated exit
3. **Carry/value donor + volatility gate donor** — factor-driven entry combined with a vol-state filter
4. **Structural/event donor + session filter donor** — event-or-structure entry combined with a session-window component
5. **Parent strategy + salvaged failed-parent component** — existing intact parent extended by a single component from a rejected parent. This is the path that populates `relationships.salvaged_from` for the first time in registry history.
6. **Sizing-overlay donor + workhorse parent** — a validated sizing component added to a workhorse-archetype existing strategy

Templates that produce zero survivors after N hybrids get retired before Phase 2; templates with a positive survival rate get promoted to Phase 1's approved list. Phase 1 may not introduce new templates without operator approval.

### 3.5 Donor attribution — first-class output

Every hybrid first-pass outcome MUST update donor-level attribution. The donor catalog tracks per-donor:

- `contributed_to_pass` (count)
- `contributed_to_fail` (count)
- `uncertain` (count — when first-pass result is inconclusive)

When a hybrid passes / fails / inconclusive, every donor in its `components_used` is credited / debited. After ≥10 hybrids per donor, donors with `pass_rate < threshold` auto-demote one tier; donors with `pass_rate > threshold` and `attempts ≥ M` auto-promote.

Attribution is the long-term asset. The lane's value accrues not just from more children but from **learning which donors actually survive recombination** — that is what a real component economy looks like, distinct from a static donor catalog.

---

## 4. Phase sequence

### Phase 0 — Proof of pipeline (Week 1: May 4-8)

Single manual cycle, end-to-end, to flush out assumptions before automating.

**Build:**
- `research/hybrid_generator.py` — minimal version implementing the §3.1 input contract and §3.2 output spec. Inputs: donor catalog + parent registry + suppression list + active templates from §3.4. Outputs: 3-5 hybrid specs printed to stdout (not yet writing to registry).
- `research/data/donor_catalog.json` — canonical donor surface. Resolves yesterday's Item 2 implication 2 (proven_donors vs CVH overlap). Contains: every component from `proven_donors` + every `result=validated` entry from `component_validation_history` + every `result=parent_failed_concept_potentially_reusable` or `salvaged` entry. Three tiers: `proven` (validated in ≥2 strategies), `candidate` (validated once), `salvage` (from a failed parent, reusable claimed). Schema must support §3.5 attribution counters from day 1.

**Run manually:**
1. Generate 3-5 hybrid specs via §3.4 templates only (2-3 component combinations).
2. Operator reviews specs — does each pass the §3.2 minimum-fields check? Does each make sense as a strategy?
3. Manually triage: keep, edit, reject.
4. Manually append survivors to registry via `_DRAFT_hybrid_batch_register_<date>.md` pre-flight pattern (same as Tuesday's batch register).
5. **Critically: every appended entry populates `relationships.components_used` and (where relevant) `relationships.salvaged_from`.** This is the first traffic through Item 2's empty plumbing.
6. Twice-weekly research factory picks up the new hybrids in its next run automatically.
7. Observe: do hybrids pass first-pass at a different rate than harvest-derived ideas?

**Phase 0 exit (binary — all five must be ☑ to advance):**
- ☐ Donor catalog consolidated (`proven_donors` + CVH merged into single canonical surface; tier field present; §3.5 attribution counters initialized)
- ☐ First `components_used` entries written successfully to registry
- ☐ 3-5 hybrid specs generated under §3.1-3.2 contract
- ☐ At least 1 hybrid survives manual triage and reaches registry as `idea`
- ☐ No schema drift; no governance exceptions required

**Hold-compliance:** Phase 0 starts May 4 (post-hold). All operations are existing authority levels (T2 for registry append, T1 for triage). No launchd changes. No new dependencies.

### Phase 1 — MVP recurring (Weeks 2-4: May 11-29)

Once Phase 0 has produced clean hybrid specs and operator confidence is there, automate the generation step inside the existing twice-weekly cadence.

**Build:**
- Promote `hybrid_generator.py` from manual to scheduled. Invoked by the existing `com.fql.twice-weekly-research` agent BEFORE the factory's first-pass sweep.
- `research/hybrid_intake.py` (or extend `research/batch_first_pass.py`) — accepts the generator's output, applies the §3.2 minimum-fields check, applies **suppression layer** (closed families + the 8 deprioritized clusters from `inbox/_family_queue.md`), appends survivors to registry as `status=idea`, `triage_route=hybrid_generation_lane`.
- `docs/HYBRID_GENERATION_DOCTRINE.md` — short governance doc (target ≤80 lines): generation constraints, donor-eligibility rules, anti-pile-on logic, schema-field-population requirements. Reuses authority ladder, does NOT introduce new T-class.
- §3.5 donor attribution wired: every hybrid first-pass outcome updates `donor_catalog.json`.
- Generator produces 5-10 hybrids per twice-weekly run, all from §3.4 templates only.

**Throughput target Phase 1:** 10-20 hybrids/week (2× → ~5× current candidate flow when combined with harvest stream).

**Phase 1 exit (binary — all five must be ☑ to advance):**
- ☐ ≥30 hybrids cycled through first-pass
- ☐ ≥2 true cross-pollination cases (Item 2 cross-pollination criterion measurable)
- ☐ Donor attribution running on every hybrid outcome (zero gap rows)
- ☐ Cheap-test path stable across ≥4 weekly runs
- ☐ Suppression catches generator junk without manual override

### Phase 2 — Throughput escalation (Month 2+: June-July)

Conditions: Phase 1 exit criteria all green, ≥1 hybrid has reached probation, no governance drift observed.

**Build:**
- `com.fql.hybrid-generation.plist` — daily launchd job (or every 6h), independent of twice-weekly. Generates ~5/day.
- `research/continuous_first_pass.py` — lighter-weight than the full factory battery. Cheap subset of tests sufficient to reject most candidates fast. Survivors graduate to the full twice-weekly factory.
- `research/data/candidate_queue.json` — explicit priority queue, populated by:
  - Harvest accepts (existing)
  - Hybrid generator output (Phase 1)
  - Gap-map directed proposals (depends on roadmap Item 1 activation)
  - Component memory queries (depends on Item 2 activation)
  - Source-expansion lanes (existing source helpers)
- Donor economy with explicit tier transitions: `proven` ↔ `candidate` ↔ `salvage` ↔ `retired`. §3.5 attribution drives auto-tier-changes per defined thresholds.
- Broader pairing templates (§3.3 Phase 2 expansion), admitted one at a time after Phase 1 survival data justifies each.

**Throughput target Phase 2:** 35-50 candidates/week through first-pass; rejection rate ~85-90%; survivors ~5-7/week graduate to full validation.

**New launchd jobs (count: 2):** `com.fql.hybrid-generation` and `com.fql.continuous-first-pass`. Both subject to existing watchdog. Both T2-authority on registry mutations.

**Phase 2 exit (binary — all four must be ☑ before Phase 3 design opens):**
- ☐ Sustained weekly throughput (≥30/wk for ≥4 consecutive weeks)
- ☐ Survival rate not collapsing below usefulness (≥1 survivor/week sustained)
- ☐ Donor economy ranking is informative (tier transitions occurring AND tier predicts survival)
- ☐ Candidate queue not creating registry drift (queue depth bounded, not monotonic-up)

### Phase 3 — Autonomous loop (Q3+ 2026, out of scope here)

The full closed-loop research factory from `roadmap_queue.md` Item 7. Depends on roadmap Items 1, 2, 3, 5 all reaching their own activation. Not designed in this doc — the path opens once Phases 0-2 produce the substrate.

---

## 5. What can start May 4 vs. what waits

| Component | Earliest start | Depends on |
|---|---|---|
| Donor catalog consolidation | May 4 | None — reads existing registry |
| `hybrid_generator.py` skeleton (§3.1-3.2 contract) | May 4 | Donor catalog |
| Phase 0 manual run (§3.4 templates only) | May 4-8 | Generator skeleton |
| Hybrid intake into registry (`triage_route=hybrid_generation_lane`) | May 4 | None — uses existing T2 path |
| `components_used` / `salvaged_from` population convention | May 4 | None — fields already exist |
| Donor attribution scaffolding (§3.5 counters initialized) | May 4 | Donor catalog |
| `HYBRID_GENERATION_DOCTRINE.md` | May 11 | Phase 0 evidence |
| Twice-weekly automated invocation | May 11 | Phase 0 stable |
| Donor pass/fail attribution wired | May 11 | Generator running automated |
| Suppression layer integration | May 11 | Generator automated |
| Continuous first-pass | June+ | Phase 1 exit criteria |
| Daily hybrid generation launchd | June+ | Phase 1 exit criteria |
| Persistent candidate queue | June+ | Continuous first-pass + queue sources defined |
| Donor tier transitions automated | June+ | ≥10 hybrids per donor of survival data |
| Broader pairing templates (Phase 2 expansion) | June+ | Phase 1 attribution data |
| Gap-map directed generation | TBD | roadmap Item 1 activation |
| Memory-driven candidate seeding | TBD | roadmap Item 2 activation |
| Autonomous loop | TBD | roadmap Item 7 prerequisites |

**Day-1 ship list (May 4):** donor catalog, generator skeleton implementing §3.1-3.2, manual run pattern using §3.4 templates, schema-field-population convention, §3.5 counter scaffolding. Five artifacts. The cross-pollination criterion can start moving from 0 toward 2 within the first week.

---

## 6. Governance rails preserved (explicit, not aspirational)

Every hybrid candidate, regardless of phase:

| Surface | Rule |
|---|---|
| Registry entry | Enters as `status: idea` only |
| Triage route | `triage_route: hybrid_generation_lane` (new value, existing field) |
| Provenance | `relationships.parent` and `relationships.components_used` MUST be populated (§3.2) |
| Suppression | Suppression layer applies BEFORE generator output enters intake — no override |
| Factory | Existing dual-archetype classification; routes through workhorse OR tail-engine paths per `trades < 500` rule |
| Promotion standards | `ELITE_PROMOTION_STANDARDS.md` framework; same shape-to-framework matching |
| First-pass gates | Existing `batch_first_pass.py` thresholds — no relaxation |
| Authority | T2 for append; T3 for any status transition past `idea`; T0 for the lane itself |
| Closed families | Closed-family list (mean_reversion×equity_index, ict×any, gap_fade, overnight equity premium) is hard-block at generation time |
| Stale-probation review | Hybrids that reach probation enter normal probation review cadence |
| Hold compliance | All Phase 0 / Phase 1 work is documentation + script-build (allowed during hold); Phase 2 launchd additions wait for post-checkpoint authority |

**The rail-preservation principle:** the hot lane is a faster way to fill the candidate pool. It is not a faster way to bypass any gate. If a candidate would have been blocked under the current rules, the hot-lane version is also blocked.

---

## 7. Anti-patterns (per `bad_automation_smells.md` + observed failure modes)

What this design **does not** do:

1. **No parallel registry.** Hybrids enter the same `strategy_registry.json` as harvest-derived ideas. One source of truth.
2. **No new authority class.** T0-T3 ladder is sufficient. The hot lane uses T2 for append, T3 for promotion, T0 for lane scope. No T4.
3. **No schema additions.** Every new piece of metadata uses existing fields (`relationships.components_used`, `relationships.salvaged_from`, `triage_route`). Donor catalog is a separate file, not a registry-schema mutation.
4. **No auto-promotion past `idea`.** The hot lane only writes `idea`-status entries. Probation, core, archive transitions remain T3-gated and operator-rendered.
5. **No suppression bypass.** Generator output passes through the same suppression that filters harvest notes. A hybrid that matches a closed family or deprioritized cluster gets blocked at the generator → intake boundary.
6. **No "infinite generation."** §3.3 bounded recombination + §3.4 template limits + donor exhaustion + cluster suppression jointly prevent combinatorial explosion. Aggressive ≠ unbounded.
7. **No new governance docs for surfaces existing docs already cover.** `PROBATION_REVIEW_CRITERIA.md`, `ELITE_PROMOTION_STANDARDS.md`, `LANE_A_B_OPERATING_DOCTRINE.md`, `authority_ladder.md` all stay authoritative. `HYBRID_GENERATION_DOCTRINE.md` is the only new doc, and it's small (target ≤80 lines).
8. **No coordination drift.** The lane plugs into existing scheduler agents (`com.fql.twice-weekly-research`, later `com.fql.hybrid-generation`). Watchdog covers them. Recovery script (`fql_recover.sh`) extends naturally.
9. **No backlog recreation.** Hot-lane output must not recreate the harvest→registry drift pattern that took explicit pre-flight discipline to address. **Hybrid generation rate is capped by the system's ability to register, trace, and first-pass candidates cleanly** — if the test funnel saturates, the generator throttles before the registry develops a hidden backlog.

---

## 8. Throughput math (concrete, not aspirational)

**Throughput is a means, not the goal.** The lane succeeds only if higher generation rate produces a non-trivial increase in **validation-worthy survivors.** If volume goes up but survival rate collapses to noise, the lane is failing even at "high throughput." Track survivors-per-week, not candidates-per-week, as the success metric.

| Stage | Current | Phase 1 target | Phase 2 target |
|---|---|---|---|
| Harvest accepts/week | ~3-7 | ~3-7 (unchanged) | ~3-7 (unchanged) |
| Hybrids generated/week | 0 | 10-20 | 35-50 |
| Total candidates/week into first-pass | ~3-7 | ~13-27 (3-4×) | ~40-57 (8-10×) |
| First-pass survival rate | ~30-40% | ~30-40% (unchanged — same gates) | ~10-15% (lower because hybrids skew weaker) |
| Survivors/week to validation | ~1-3 | ~4-8 | ~5-7 |
| Validations/week | gated by capacity | gated by capacity | gated by capacity |
| Probation entries/quarter | 1-3 | 3-5 | 5-10 |

**Why Phase 2 survival rate drops:** hybrids generated combinatorially have lower prior than human-curated harvest accepts. That's the *point* — fast rejection of weak hybrids is how the lane stays elite. Rejection discipline matters more than acceptance rate.

---

## 9. Concrete build sequence (week-by-week)

### Week of May 4 (post-checkpoint — Phase 0)
- **Mon May 4:** Build `donor_catalog.json` from existing registry data; resolve `proven_donors` vs CVH canonicalization; initialize §3.5 attribution counters.
- **Tue May 5:** Build `hybrid_generator.py` skeleton implementing §3.1 inputs and §3.2 output spec. Templates from §3.4 only.
- **Wed May 6:** Manual run #1. Operator reviews 3-5 specs against §3.2 minimum-fields check, picks 1-2, drafts `_DRAFT_2026-05-07_hybrid_batch_register.md` pre-flight.
- **Thu May 7:** Append manual hybrids to registry. **First `components_used` populations in registry history.**
- **Fri May 8:** Phase 0 retro. Which §3.4 templates worked? Which donors looked productive in early specs? Adjust skeleton — but only within contract; do not relax §3.2 or §3.3 to accommodate weak specs.

### Weeks of May 11 / May 18 / May 25 (Phase 1)
- **May 11-15:** Wire generator into `com.fql.twice-weekly-research`. First automated run Tue May 12. Draft `HYBRID_GENERATION_DOCTRINE.md` (≤80 lines).
- **May 18-22:** §3.5 donor attribution telemetry live. First donor stats accumulating.
- **May 25-29:** Phase 1 exit-criteria check (binary list in §4 Phase 1 exit). If all five ☑ → Phase 2 plan opens. If any ☐ → Phase 1 extends one more week; do not advance with partial criteria.

### June+ (Phase 2 — gated by Phase 1 evidence)
Build sequence parallel to Phase 1 structure. New launchd jobs come last, after script-level continuous first-pass is stable. Broader §3.4 templates admitted one at a time, each with explicit attribution-data justification.

---

## 10. What this graduation looks like in one paragraph

Today: harvest in, factory tests at twice-weekly cadence, governance solid, recombination plumbing empty. By end of May: harvest in + hybrids in (10-20/wk under §3.1-3.4 contract), same factory tests + same governance, donor attribution accumulating per §3.5, cross-pollination criterion measurable for the first time, ≥2-3 hybrids in first-pass survival data. By end of Q2: continuous first-pass running daily, ~50 candidates/wk through the funnel, donor economy producing tiered behavior driven by attribution evidence, a sustained survivor-rate that lets us decide whether the recombination economy works as a long-term lever or needs a different generation strategy. The throughput escalates; the standards do not move; the contract holds.

---

## What this draft is NOT

- **Not committed code.** Skeletons are sketched in Section 9 prose; the actual scripts are written during Phase 0.
- **Not a registry-schema migration.** Uses existing fields exclusively.
- **Not a launch authorization.** Phase 2 launchd additions need a separate operator approval after Phase 1 evidence.
- **Not autonomy.** Operator remains in the loop at every status transition past `idea` and at every Phase exit-criteria check.
- **Not unbounded.** §3.3 + §3.4 + Anti-pattern #6 + Anti-pattern #9 jointly cap the generator. Aggressive within a tight contract is the design; aggressive without a contract is what this doc explicitly forbids.

---

*Filed 2026-04-29 as `docs/fql_forge/hot_lane_architecture.md` — the canonical reference for Phase 0-2 build work starting May 4. Companion build sequence: `docs/fql_forge/post_may1_build_sequence.md`.*
