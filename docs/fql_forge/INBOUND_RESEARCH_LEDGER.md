# Inbound Research Ledger (rendered 2026-07-02 17:33 UTC)
> **Operating law:** if it is not in this ledger, the queue, the dashboard, or the control map — the system does not know it.
> Source of truth: `research/data/inbound_research_ledger.json`. Capture: `python3 research/capture_inbound.py`. Items: **41**.
> NEW:0 | P0/P1:10/22 | untriaged directives:0 | mistakes w/o control:2 | unused feeds:0 | source notes unresolved:0

| id | date | type | status | P | family | mechanism / issue | next action | linked (packet/queue/control) |
|---|---|---|---|---|---|---|---|---|
| INB-20260701-010 | 2026-07-01 | guardrail finding | CONTROL_REQUIRED | P0 | governance | INFRA DRIFT: 250 infra scripts + 138 forge docs + 90 memory files; new | declare INFRA FREEZE; retire dormant one-off scrip | — |
| INB-20260701-009 | 2026-07-01 | claude discovery | RETEST_REQUIRED | P0 | data governance | DATA GAP: hold 11 instruments x ~7.9M 1m bars+volume (441MB) + 6 per-c | build ONE clean 1m/volume/microstructure harness;  | — |
| INB-20260701-008 | 2026-07-01 | operator directive | ACTIVE_PACKET_LANE | P0 | organizational memory | inbound ledger->triage->queue->control->dashboard | operationalize + backfill (this build) | queue:INB-20260701-008 capture_inbound.py + INBOUND_TRIAGE_R |
| INB-20260701-012 | 2026-07-01 | operator directive | ACTIVE_PACKET_LANE | P0 | governance | Make learning+improvement automatic each step; regular self-audit of e | Phase 1: data-tier gate + learning-loop closure +  | queue:INB-20260701-012 forge_self_audit.py + FOUNDATION_DOCT |
| INB-20260702-001 | 2026-07-02 | operator directive | ACTIVE_PACKET_LANE | P0 | governance | Full-spectrum Elite Novelty System Assessment: grade every layer, buil | P1: failure_class backfill, source->packet x3, exe | queue:INB-20260702-001 ELITE_NOVELTY_SYSTEM_ASSESSMENT_2026- |
| INB-20260702-008 | 2026-07-02 | claude discovery | ACTIVE_PACKET_LANE | P0 | governance | SEARCH-SURFACE AUDIT: GEX kill was WRONG DATA (ES.OPT=monthly only, 0  | weekly-OI pull -> real 0DTE GEX; integrate bbo-1m  | queue:INB-20260702-008 SEARCH_SURFACE_AND_DATA_FIT_AUDIT_202 |
| INB-20260625-001 | 2026-06-25 | bug | TRIAGED | P0 | causality | same-day-close lookahead | ORB family INVALIDATED | causality_audit.py + memory project_orb_ema_slope_lookahead |
| INB-20260626-001 | 2026-06-26 | operator directive | TRIAGED | P0 | data governance | inventory-before-exhausted-claim | keep databento/1m lane active | forge_system_guardrails.py (unused-databento) + memory inven |
| INB-20260630-001 | 2026-06-30 | bug | TRIAGED | P0 | data governance | unproven blocker claim | none — control locked | DATA_BLOCKER_CERTIFICATES + guardrail P1 (cert required) |
| INB-20260702-002 | 2026-07-02 | operator directive | TRIAGED | P0 | governance | Data budget: auto-approve report-only pulls <=/pull, /day cap, ~weekly | gamma OI sample pull -> GEX feasibility memo | research/data/data_budget.json |
| INB-20260701-011 | 2026-07-01 | guardrail finding | CONTROL_REQUIRED | P1 | learning | LEARNING LOOP HALF-OPEN: novelty engine is template-only (blind to the | novelty reads ledger (down-weight dead families/up | — |
| INB-20260613-001 | 2026-06-13 | validation failure | RETEST_REQUIRED | P1 | port fidelity | port byte-fidelity | prove signal-hash on audit window before wiring | feedback_port_fidelity_discipline |
| INB-20260701-006 | 2026-07-01 | validation failure | RETEST_REQUIRED | P1 | execution realism | roll-adjacent concentration | 2-leg calendar-spread exec model + tick/1m near ro | deepen_spreadMR_GC_execution |
| INB-20260701-014 | 2026-07-01 | claude discovery | RETEST_REQUIRED | P1 | intraday_micro | 1m+volume T3 microstructure harness built+run (tz-agnostic session det | next T3 packets: intraday 1m-path MR, settlement-w | — |
| INB-20260701-001 | 2026-07-01 | paid-data idea | NEEDS_BESPOKE_HARNESS | P1 | gamma/dealer | dealer gamma / OPEX pin | build chunked loader then approx-GEX | — |
| INB-20260701-005 | 2026-07-01 | validation failure | NEEDS_BESPOKE_HARNESS | P1 | multiple-testing | layered-N ambiguity | pin honest search-N; blocks advancement past SCREE | deepen_spreadMR_GC_searchN practice: report costed-DSR acros |
| INB-20260626-005 | 2026-06-26 | data feed | ACTIVE_PACKET_LANE | P1 | macro/carry | unused feeds | attach each feed to a packet lane | queue:INB-20260626-005 guardrail unused-feeds |
| INB-20260630-002 | 2026-06-30 | data feed | ACTIVE_PACKET_LANE | P1 | term structure | term-structure curve data | — | term_structure.py queue:INB-20260630-002 |
| INB-20260701-002 | 2026-07-01 | claude discovery | ACTIVE_PACKET_LANE | P1 | carry_commodity | roll-yield carry + spread | naive carry KILLed; refined -> spreadMR_GC | SPRINT_COMMODITY_CARRY_VERDICT_2026-07-01.md queue:INB-20260 |
| INB-20260702-009 | 2026-07-02 | data feed | ACTIVE_PACKET_LANE | P1 | execution_cost | bbo-1m quotes/spread unlocked (ES median spread 0.25pt=1tick, /bin/zsh | real spread cost in harnesses; spread-conditioned  | queue:INB-20260702-009 |
| INB-20260625-003 | 2026-06-25 | bug | TRIAGED | P1 | causality | cache key ignores close | none — audit clears cache | causality_audit.py _clear_cache() |
| INB-20260626-003 | 2026-06-26 | guardrail finding | TRIAGED | P1 | governance | non-fail-loud enforcement | run guardrails each cycle | forge_system_guardrails.py (every-cycle) + memory system_gua |
| INB-20260626-004 | 2026-06-26 | guardrail finding | TRIAGED | P1 | labeling | overclaim language | scan recent docs each cycle | forge_system_guardrails.py WH-scan + candidate ladder |
| INB-20260629-001 | 2026-06-29 | guardrail finding | TRIAGED | P1 | multiple-testing | uncounted multiple-testing N | DSR reads count() | forge_trial_ledger.py (automatic count) |
| INB-20260630-004 | 2026-06-30 | operator directive | TRIAGED | P1 | sourcing | grow opportunity surface | run novelty engine, keep BACKLOG full | forge_novelty_engine.py (generative) + ALPHA_RESEARCH_OS_ELI |
| INB-20260630-005 | 2026-06-30 | operator directive | TRIAGED | P1 | validation | hostile second-pass | review every hardening result; later OpenClaw red- | adversarial_result_review.py |
| INB-20260701-013 | 2026-07-01 | guardrail finding | TRIAGED | P1 | governance | Self-audit watchdog built: audits 12 facets/cycle (present+functioning | wire into every-cycle runner | forge_self_audit.py |
| INB-20260702-011 | 2026-07-02 | data feed | TRIAGED | P1 | data governance | Databento 504/connection-reset on ES weekly-OI pull: parents EW1-4/E1A | run EW GEX expiry test now; retry E1A/E3C 0DTE nex | DATABENTO_TRANSIENT_FAILURE_RETRY_POLICY.md + provider_retry |
| INB-20260702-012 | 2026-07-02 | bug | TRIAGED | P1 | data governance | DATA-PROVENANCE RACE: ran GEX test on weekly-OI file while background  | append 'no mid-pull analysis' rule to retry policy | retry-policy: analyze ONLY after task completion + validate_ |
| INB-20260701-003 | 2026-07-01 | claude discovery | PROMOTED_TO_PACKET | P1 | carry_commodity | gold calendar-spread mean-reversion | Lane G deepening (operator-gated for capital) | SCREEN_PASS_CANDIDATE_spreadMR_GC_2026-07-01.md deepen_sprea |
| INB-20260702-003 | 2026-07-02 | source | PROMOTED_TO_PACKET | P1 | carry_commodity | CME roll methodology docs -> roll-window pressure: index/ETF funds mus | — | src_roll_window_pressure |
| INB-20260702-004 | 2026-07-02 | source | PROMOTED_TO_PACKET | P1 | gamma_dealer | Options dealer-hedging (SqueezeMetrics/Nomura) -> GEX-regime pin: deal | — | src_gex_regime_pin |
| INB-20260616-001 | 2026-06-16 | old report | RETEST_REQUIRED | P2 | rescue (Lane F) | dormant inventory | retest under truth-gated harness, ranked | Lane F rescue |
| INB-20260625-002 | 2026-07-02 | bug | TRIAGED | P2 | automation | stale tripwire not firing | resolved: freshness enforced every cycle | guardrail #3 stale-automation freshness check covers loop lo |
| INB-20260626-002 | 2026-06-26 | bug | TRIAGED | P2 | harness hygiene | duplicate/bypassed harness | none | guardrail unrun-harnesses + forge_trial_ledger dedup |
| INB-20260630-003 | 2026-06-30 | bug | TRIAGED | P2 | data integrity | save-time column loss | none — validator guards | validate_data_file.py |
| INB-20260701-004 | 2026-07-01 | bug | TRIAGED | P2 | review calibration | side-share over all days not active | none — fixed | adversarial_result_review.py (active-side + SPARSE_LOW_N) |
| INB-20260702-007 | 2026-07-02 | bug | TRIAGED | P2 | — | failure_class labeler mis-tagged negative-Sharpe as concentration (max | sweeps use classify_failure going forward | forge_trial_ledger.classify_failure() canonical order |
| INB-20260702-010 | 2026-07-02 | claude discovery | TRIAGED | P2 | execution_cost | bbo-1m: ES spread uniform 1-tick(0.25pt) all hours, 95pct 2-tick. VALI | time-of-day spread only material for less-liquid i | data/databento/ES_bbo_1m_sample.csv analysis |
| INB-20260702-005 | 2026-07-02 | source | PROMOTED_TO_PACKET | P2 | intraday_micro | Microstructure (Kyle/VPIN/Easley) -> liquidity-hole reversal: informed | — | src_liquidity_hole |
| INB-20260701-007 | 2026-07-01 | validation failure | CLEAN_KILL | P2 | carry_commodity | cross-asset generalization | gold-specific noted; not a family win | — |