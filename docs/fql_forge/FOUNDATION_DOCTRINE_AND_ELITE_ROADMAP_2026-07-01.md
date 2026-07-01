# FQL Forge — Foundation Doctrine & Elite Roadmap (2026-07-01)

> **Goal:** the most novel and elite alpha-discovery machine possible — one that learns and improves automatically on every
> step, audits every facet of itself on a regular cadence, and never takes a backstep. This document is the canonical
> operating contract. It is written to be reviewed by a second Claude instance for adversarial feedback. Report-only;
> capital gate fail-closed. Nothing above SCREEN_PASS exists today.

---

## 0. Grounded truth (inspected 2026-07-01, not inferred)

| Layer | Hold | Use | Gap |
|---|---|---|---|
| **Data** | 11 instruments × ~7.9M **1-minute bars w/ volume** (441MB) + 6 per-contract curves + 19 external feeds | **3 scripts** touch 1m+volume; **69** run on 5m-close | richest asset ~97% idle; 1m span ~2y (2024–26) → intraday/microstructure, not multi-year-daily |
| **Organization** | 359 research scripts (~250 infra), 138 forge docs, 90 memory files | trial-N **94% one primitive sweep**; ~100 real ex-sweep trials | scaffolding:edges inverted; newest 6 files all tooling |
| **Learning** | ledger + memory + inbound + `forge_source_feedback.py` | novelty engine **blind to the 1,679 kills**; `family_status` hand-edited | loop saves but generation doesn't read outcomes |

**One-line diagnosis:** we build faster than we use what we own. The frontier (1m/volume/microstructure) is already paid for and on disk.

---

## 1. The three backstep risks (what makes a system regress)

1. **False exhaustion (most dangerous).** Every family "killed" was killed on close-only/daily data. That is not exhaustion — it is "the close-only expression failed." Those kills float as permanently-dead doors. A false-negative that closes an unexplored frontier is the worst backstep because it is silent and permanent.
2. **Infrastructure drift.** ~250 infra scripts + 138 docs + 90 memory files → 1 DSR-borderline candidate. The last three build-turns produced ~10 org artifacts and 1 candidate. More scaffolding hides the absence of edges.
3. **Half-open learning loop.** We never forget (inbound/ledger/memory), but generation (novelty, family_status) doesn't read results, so we can re-derive dead facts and mis-prioritize.

---

## 2. The no-backstep doctrine

- **A. DATA-TIER ESCALATION GATE.** Tiers: `close → 1m → 1m+volume → microstructure → paid`. No family may be labeled `CLEAN_KILL`/`FAMILY_EXHAUSTED` until tested at the richest *applicable* tier. Every kill records its `data_tier`. Enforced in `family_status.json` + `forge_family_map.py` + `adversarial_result_review.py` + guardrail + self-audit. **Re-opens every close-only kill as incompletely tested.**
- **B. INFRA FREEZE + consolidation.** Organization layer is declared complete. No new infra script/doc without retiring one. Prune dormant one-off sprints (guardrail already flags unrun harnesses). **Scoreboard = candidates, not tools.**
- **C. CLOSE THE LEARNING LOOP.** `forge_novelty_engine` reads the ledger (down-weight dead families, up-weight the survivor neighborhood); `family_status` auto-updates from sprint verdicts. Generation becomes informed, not blind.
- **D. MINE THE 1m/VOLUME WE OWN.** One clean minute-bar/volume/microstructure harness, then re-run close-only kills at the tier they deserve — starting where microstructure *is* the thesis (opening imbalance, settlement revert, volume-conditioned continuation, lead-lag).

---

## 3. Automatic learning — the "close-the-step" protocol (mandatory after every test)

Every test/sprint MUST end by closing the loop — no terminal-only results:
1. `forge_trial_ledger.record(...)` — trial-N (multiple-testing) updates automatically.
2. `family_status` updates from the verdict (tested/untested/status) — **auto (roadmap C), enforced by self-audit consistency check.**
3. `forge_novelty_engine` priors update from the verdict (kill → down-weight; survive → up-weight neighborhood) — **auto (roadmap C).**
4. `capture_inbound` — any discovery/mistake/idea captured with a control if it's a mistake.
5. `adversarial_result_review` — result cannot harden if it fails.
6. `forge_candidate_ladder.promote` — rung advances only through the enforced gate.
7. `forge_dashboard` regenerated; `forge_system_guardrails` + `forge_self_audit` run; commit + push; backlog 0.
8. Durable learning saved to memory + `MEMORY.md` index (via `forge_learning_loop_audit`).

**Enforcement:** `forge_self_audit.py` flags if any of these went stale (e.g., family_status inconsistent with ledger, dashboard not regenerated, inbound floating) — i.e. it detects when a step failed to *learn*.

---

## 4. Continuous self-audit — audit the auditors (`research/forge_self_audit.py`, BUILT)

Each facet checked every cycle for **PRESENT + FUNCTIONING + FRESH + CONSISTENT**, on its cadence:

| Facet | Cadence | Health check |
|---|---|---|
| causality_audit | per-candidate | future-perturbation harness importable |
| deflated_sharpe | per-survivor | DSR/PBO gate importable |
| trial_ledger | per-test | count() works; **advancing** (Δ since last audit) |
| guardrails | per-cycle | status log fresh (<2d) |
| inbound_capture | per-cycle | 0 floating; mistakes-without-control tracked |
| family_map | per-sprint | **every ledger lane has a family**; 0 over-claims |
| novelty_engine | per-day | store advancing OR honestly saturated |
| adversarial_review | per-result | 11-check red-team importable |
| candidate_ladder | per-promotion | highest rung sane |
| dashboard | per-cycle | regenerated <1d |
| **data_tier_gate** | per-kill | DESIGNED (roadmap P1) — every kill records data_tier |
| **learning_loop** | per-step | DESIGNED (roadmap P1) — novelty reads results; family_status auto-updates |

Verdict states: `SELF_AUDIT_CLEAN` / `STALE_FACET` / `BROKEN_FACET`. `DESIGNED` = on roadmap, not a failure. Current: **CLEAN** (2 DESIGNED).

---

## 5. What "novel" and "elite" mean here (so we can measure them)

- **NOVEL** = mechanism-first (forced participant, price-insensitive flow, hedging reflexivity, roll/settlement, microstructure bottleneck), on **data others under-use** (our 7.9M idle 1m+volume bars; term-structure; feeds), multiple-testing-honest. NOT another close-only MR sweep. The novelty engine's job is to grow this surface faster than we exhaust it, and now to learn from what dies.
- **ELITE** = hostile validation at *every* step (causality → cost → concentration → layered-N DSR → cross-asset → adversarial red-team), **candidates not tools** as the scoreboard, fail-closed capital, and a machine that audits and improves itself without prompting. Elite is not "less broken" — it is throughput × ruthlessness × self-correction.

---

## 6. Roadmap — phases, current position, exit criteria

- **Phase 0 — Truth-reset & foundation (DONE).** Causality harness; DSR gate; layered trial ledger; guardrails (fail-loud); inbound capture (organizational memory); expression/data validators; novelty engine (generative); computed family map; enforced candidate ladder; adversarial review; self-audit watchdog; **first SCREEN_PASS candidate (spreadMR_GC, DSR-borderline).**
- **Phase 1 — Foundation hardening (NOW).** (a) Build data-tier gate (doctrine A); (b) close learning loop (doctrine C); (c) infra freeze + prune dormant scripts (doctrine B); (d) first clean 1m+volume microstructure harness (doctrine D). **Exit:** data-tier gate enforced across families; novelty reads ledger + family_status auto-updates; ≥1 close-only kill re-scoped at 1m+volume; self-audit clean streak ≥5 cycles.
- **Phase 2 — Microstructure / 1m alpha sweep.** Systematically re-test close-only-killed families at 1m+volume + run the microstructure-native forced-flow packets (opening imbalance, settlement revert, WMR fix, lead-lag). Each through the full hostile stack. **Exit:** ≥N families re-scoped with recorded data_tier; ≥1 **DSR-credible** candidate (not just borderline).
- **Phase 3 — Deepening & paper-readiness.** Take DSR-credible candidates through execution realism (real 2-leg/liquidity models), capacity/sizing, robustness → paper-readiness packet. **Exit:** 1–3 paper-readiness packets (every capital step operator-gated).
- **Phase 4 — Portfolio & continuous compounding.** Diversified sleeve construction; allocation curves; the closed loop (results → novelty priors → source helpers) running unattended with self-audit as the immune system.

**Current position:** end of Phase 0, entering Phase 1. Highest rung: SCREEN_PASS (spreadMR_GC). Validated primaries: 0.

---

## 7. Scoreboard (candidates, not tools) — tracked on the dashboard

candidates by rung · DSR-credible count · families re-scoped at richer tier · **data-tier coverage** · self-audit clean streak · kills · screen-passes · inbound floating count · **infra-freeze adherence (new-infra vs retired)** · tests/day. Explicitly NOT: script count, doc count.

---

## 8. Governance

Capital gate fail-closed (ladder rung ≥ PAPER_APPROVED operator-only). No WH/primary/validated/paper-ready language unless the ladder supports it. Report-only lanes self-run; only money (>$5 Databento) and capital surfaces require an operator ask. Every cycle: guardrails + self-audit + commit + push + backlog 0.

---

## 9. Build state (honest, for the reviewer)

**BUILT & functioning:** causality_audit, deflated_sharpe, forge_trial_ledger (layered), forge_system_guardrails (11 checks), capture_inbound + triage rules, validate_strategy_expression, validate_data_file, forge_novelty_engine (generative), forge_family_map (computed), forge_candidate_ladder (enforced), adversarial_result_review, forge_dashboard, **forge_self_audit (watchdog)**, term_structure loader, per-contract data.
**DESIGNED — Phase 1 immediate builds:** (P1a) data-tier escalation gate; (P1b) novelty engine reads ledger; (P1c) family_status auto-update from verdicts; (P1d) 1m+volume microstructure harness.
**Open honest gaps flagged by our own tooling:** inbound `mistakes_no_control=3` (data gap, infra drift, half-open loop — the 3 foundation findings, each awaiting its control = the Phase 1 builds); forge-daily-loop stale-tripwire (`INB-20260625-002`, CONTROL_REQUIRED).

> **Request to reviewing Claude:** attack this. Where is the false confidence? Which doctrine rule is unenforceable or gameable? Is the data-tier gate the right anti-false-exhaustion mechanism, or is there a better one? Is the infra freeze real or will it be quietly violated? What would a genuinely elite quant shop do here that this plan misses?
