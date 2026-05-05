# Component Cross-Pollination — Hybrid Candidates 2026-05-05

**Filed:** 2026-05-05 (Lane B / Forge — no Lane A surfaces touched)
**Companion to:** `docs/fql_forge/source_yield_and_gap_review_2026-05-04.md` (yesterday's gap-map) + `research/data/harvest_triage/2026-05-04.md` (yesterday's donor surface)
**Purpose:** Concrete hybrid candidate recipes per the operator's spec from 2026-05-04 evening. Output target: ≥2 candidates ready for cheap validation, with full 7-field recipe per row.

---

## Donor surface (the working catalog)

| Layer | Source | Count |
|---|---|---|
| 1 | `proven_donors` (top-tier validated, XB-ORB family) | 3 |
| 2 | `component_validation_history` validated/salvaged/potentially_reusable | 9 |
| 3 | Rejected/archived parents with non-empty `extractable_components` | 41 |
| 4 | Yesterday's triage 11 fresh donor candidates (registry append pending) | 11 |
| **Total** | | **64** |

**Notable donors actually usable today:**
- **Top-tier proven (3):** `profit_ladder` (exit, R-ratchet), `ema_slope` (filter, EMA21>EMA50), `orb_breakout` (entry, 30-min OR break) — all validated in XB-ORB-EMA-Ladder × {MNQ, MCL, MYM}
- **Top-tier validated CVH (6):** `inverse_vol_sizing` (sizing, VolManaged), `carry_rank_monthly_rebalance` (entry, Treasury-Rolldown), `impulse_threshold_1.5x` (filter, ZN-Afternoon), `fixed_time_exit_25m` (exit, ZN-Afternoon), `60pct_retracement_target` (exit, ZN-Afternoon), `high_vol_regime_preference` (regime, ZN-Afternoon)
- **Salvaged from failures (3):** `session_transition_entry_concept` (FXBreak-6J-Short-London), `lunch_compression_regime_filter` (SPX-Lunch-Compression), `afternoon_session_reversion_timing` (Treasury-Cash-Close)
- **Rejected/archived parents — most extractable:** VWAP-MNQ-Long, Donchian-MNQ-Long-GRINDING, ORION-VolBreakout, BBKC-Squeeze-Classic, Equity-Overnight-Drift, Gold-Overnight-Drift, several FXBreak variants

---

## Active gaps to target (from 2026-05-04 review)

| Gap | Severity | Relevance to candidates |
|---|---|---|
| **FX** | HIGH | All FXBreak family rejected/archived; salvaged session-transition concept available |
| **STRUCTURAL primary session-transition** | MEDIUM | Several CVH validated rates-afternoon components; lunch-compression salvage available |
| **VOLATILITY** | GAP per dashboard | `inverse_vol_sizing` validated; can layer onto any workhorse |
| **Workhorse diversity** | Implicit (XB-ORB is the only workhorse family) | VWAP-MNQ entry + proven trio template = sister workhorse candidate |
| **CARRY breadth** | Filled by Treasury-Rolldown spread only | `carry_rank` + `inverse_vol_sizing` could extend |

---

## Constraints applied to all candidates

- Bounded recombination per Phase 0 §3.3: 2-3 components only
- Must use one of the 6 §3.4 pairing templates
- Avoid 8 suppression clusters + 4 closed families (mean_reversion×equity_index, ict×any, gap_fade, overnight equity premium)
- Avoid the 3 new pile-on clusters identified yesterday (mean-reversion stress release, profit ladder duplicate variants, cross-country bond ridge)
- All hybrids enter as `status: idea`, `triage_route: hybrid_generation_lane`, full `relationships.components_used` populated when the registry-append step happens
- **No registry append today.** Operator confirms before any append. Today's deliverable is recipes only.

---

## Top hybrid candidates (5)

### CANDIDATE 1 — HYB-FX-SessionTransition-ImpulseGated

| Field | Value |
|---|---|
| **§3.4 template** | #5 — Parent strategy + salvaged failed-parent component (the path that populates `relationships.salvaged_from` for the first time) |
| **Donor 1 (salvaged)** | `session_transition_entry_concept` from FXBreak-6J-Short-London (rejected, status=rejected; CVH result: `parent_failed_concept_potentially_reusable`) |
| **Donor 2 (validated)** | `impulse_threshold_1.5x` from ZN-Afternoon-Reversion (CVH: validated filter) |
| **Reusable component(s)** | (1) Asian-range-break / session-handoff entry logic, abstracted from FX context; (2) impulse-magnitude filter |
| **Target family / gap** | **FX (HIGH severity gap)** |
| **Proposed hybrid concept** | Asian-range/London-handoff entry on 6E or 6B (NOT 6J, which already failed standalone), gated by an impulse-threshold filter requiring the breakout move to exceed 1.5× the 20-day median range. The original FXBreak-6J failed because it traded all session-transition signals; the impulse gate filters out the false-positive band where the handoff produces noise rather than directional commitment. |
| **Why portfolio value** | (a) Fills FX HIGH gap with first viable candidate. (b) Tests cross-asset extension of FXBreak concept on 6E/6B (different liquidity profile than 6J). (c) First-ever populated `relationships.salvaged_from` — moves Item 2 cross-pollination criterion from 0 toward 2. (d) Uncorrelated to current XB-ORB portfolio (different asset class, different session). |
| **Cheap validation test** | Backtest on 6E first (largest FX micro contract). Sample window: 2019-01 → 2026-04 (~7 years). Tail-engine archetype (sparse session-handoff signals expected); pass bars per `post_may1_build_sequence.md` §4.1: PF≥1.15 VIABLE / ≥1.30 STRONG; max single-instance < 35%; positive-instance fraction ≥ 60%. **Time budget: ≤30s/candidate.** Fast-reject if PF < 1.15 OR if instance concentration > 50%. |
| **Gap classification** | **FX** (primary) + STRUCTURAL session-transition (secondary) |

### CANDIDATE 2 — XB-VWAP-EMA-Ladder (sister workhorse)

| Field | Value |
|---|---|
| **§3.4 template** | #2 (entry donor + exit donor) + #1 (entry + regime filter donor) — combined; uses 3 components which is at the §3.3 Phase 0 max |
| **Donor 1 (rejected parent extract)** | `entry` from VWAP-MNQ-Long (rejected, VWAP-trend continuation entry) |
| **Donor 2 (proven)** | `ema_slope` (proven_donor filter — only filter maintaining positive median cross-asset) |
| **Donor 3 (proven)** | `profit_ladder` (proven_donor exit — only known exit producing positive median trade) |
| **Reusable component(s)** | (1) VWAP-anchored trend continuation entry (price above session VWAP + ATR confirmation); (2) ema_slope direction filter; (3) ratcheting profit ladder |
| **Target family / gap** | **Workhorse diversity** (currently XB-ORB is the only workhorse family in probation) |
| **Proposed hybrid concept** | Sister-workhorse to XB-ORB-EMA-Ladder. Replaces the ORB entry with VWAP-trend-continuation. Same regime filter (ema_slope) and same exit (profit_ladder). The hypothesis: if ema_slope and profit_ladder are the load-bearing components (per `proven_donors` `alternatives_tested` data showing all alternatives produce negative median), then a different entry that ALSO clears the proven-donor bar on those two would extend the workhorse family. |
| **Why portfolio value** | (a) Tests whether `proven_donors` are entry-agnostic — a load-bearing question for Phase 0. (b) If passes: doubles workhorse family from 1 to 2 (XB-ORB + XB-VWAP). (c) If fails: produces the cleanest possible test that ORB is essential to the assembly, not interchangeable — informs Phase 1 generator's exploration quota. Either outcome is high-information. (d) Cross-asset: validate same MNQ/MCL/MYM trio that XB-ORB family already proved. |
| **Cheap validation test** | Backtest on MNQ first (the canonical XB-ORB workhorse asset). Workhorse archetype: ≥500 trades expected over 7-year window; PF > 1.2 baseline; walk-forward H1/H2 both > 1.0; top-3 < 30%, top-5 < 45%, top-10 < 55% concentration; median trade ≥ 0; max single year < 40%. **Fast-reject if PF < 1.0** OR median trade < 0 (proves ORB-specific advantage rather than ema_slope/profit_ladder doing the work). |
| **Gap classification** | **Workhorse diversity** (primary). No specific factor gap — extends an existing successful family. |

### CANDIDATE 3 — HYB-LunchComp-RatesAfternoon

| Field | Value |
|---|---|
| **§3.4 template** | #1 — Entry donor + regime filter donor |
| **Donor 1 (salvaged)** | `lunch_compression_regime_filter` from SPX-Lunch-Compression-Afternoon-Release (rejected; CVH: `parent_failed_concept_potentially_reusable`) |
| **Donor 2 (validated)** | `high_vol_regime_preference` from ZN-Afternoon-Reversion (CVH: validated regime_logic) |
| **Donor 3 (validated)** | `impulse_threshold_1.5x` from ZN-Afternoon-Reversion (CVH: validated filter) |
| **Reusable component(s)** | (1) Lunch-compression detector (price range narrows during 11:30-13:30 ET window); (2) high-vol regime preference (only fire when realized vol > regime threshold); (3) impulse threshold |
| **Target family / gap** | **STRUCTURAL session-transition** (MEDIUM severity gap), specifically rates-afternoon |
| **Proposed hybrid concept** | A rates-afternoon variant of ZN-Afternoon-Reversion that ONLY fires on days where lunch compression was detected. The hypothesis: lunch compression filters for "consolidation → release" sessions, which historically have cleaner afternoon-reversion behavior in rates. SPX-Lunch-Compression failed because the equity afternoon-release was already saturated; rates afternoon (where ZN-Afternoon already validates) may be the right venue. |
| **Why portfolio value** | (a) Tightens ZN-Afternoon's signal generation to the higher-quality subset. (b) Salvages a flagged-reusable component from a failed parent (populates `relationships.salvaged_from`, moves Item 2 toward activation). (c) If the regime filter improves edge, it suggests the lunch-compression detector is portable — useful donor for future strategies. (d) Same asset/session as existing ZN-Afternoon — easy to A/B test. |
| **Cheap validation test** | A/B backtest: ZN-Afternoon-Reversion baseline vs ZN-Afternoon + lunch-compression filter. Same window. Compare: (i) sample size (filter should reduce ~30-50%); (ii) per-trade PF; (iii) median trade. Pass: PF improves AND median trade ≥ 0 AND sample remains ≥ 60 trades over 7 years. Fast-reject: filter reduces sample to <40 trades OR PF degrades. |
| **Gap classification** | **STRUCTURAL session-transition** (rates) |

### CANDIDATE 4 — HYB-CashClose-Salvage-RatesWindow

| Field | Value |
|---|---|
| **§3.4 template** | #5 — Parent strategy + salvaged failed-parent component |
| **Donor 1 (salvaged)** | `afternoon_session_reversion_timing` from Treasury-Cash-Close-Reversion-Window (rejected; CVH: `salvaged`) |
| **Donor 2 (validated)** | `impulse_threshold_1.5x` from ZN-Afternoon-Reversion (CVH: validated filter) |
| **Reusable component(s)** | (1) Cash-close session timing (14:45-15:00 ET window); (2) impulse-magnitude filter |
| **Target family / gap** | **STRUCTURAL session-transition** (rates), specifically the cash-close window |
| **Proposed hybrid concept** | Treasury-Cash-Close-Reversion-Window failed because the cash-close impulse-fade entry mechanism (`cash_close_impulse_fade`) was rejected, but the afternoon-session-timing component was salvaged. Combine the salvaged session timing with ZN-Afternoon's validated impulse threshold — essentially a different time-window variant of ZN-Afternoon (cash-close window vs the existing 13:45-14:00 window). |
| **Why portfolio value** | (a) Extends rates-afternoon coverage to a different intraday window. (b) Diversifies entry timing within the same asset/family. (c) Tests whether ZN-Afternoon's edge is window-specific or window-portable. (d) Salvages component from rejected parent (moves Item 2 cross-pollination toward activation). |
| **Cheap validation test** | Backtest on ZN at the cash-close window (14:45-15:00 entry, 15:25 exit) with the impulse filter. Same 7-year window. Tail-engine archetype expected (sparse — cash-close window has fewer impulse events than 13:45-14:00). Pass bars: PF ≥ 1.15; max single-instance < 35%; positive-instance fraction ≥ 60%. Fast-reject: PF < 1.0 OR fewer than 30 trades. |
| **Gap classification** | **STRUCTURAL session-transition** (rates, cash-close window) |

### CANDIDATE 5 — HYB-VolMan-Workhorse-SizingOverlay

| Field | Value |
|---|---|
| **§3.4 template** | #6 — Sizing-overlay donor + workhorse parent |
| **Donor 1 (validated)** | `inverse_vol_sizing` from VolManaged-EquityIndex-Futures (CVH: validated sizing_overlay) |
| **Donor 2 (proven workhorse parent)** | XB-ORB-EMA-Ladder-MNQ (current probation workhorse) |
| **Reusable component(s)** | (1) Inverse-realized-volatility position sizing (sizes contract-count down when realized vol is high, up when low); (2) all of XB-ORB-EMA-Ladder-MNQ as the workhorse parent |
| **Target family / gap** | **VOLATILITY (GAP per dashboard) + workhorse risk-normalization** |
| **Proposed hybrid concept** | XB-ORB-EMA-Ladder-MNQ with inverse-vol sizing layered as a position-sizing overlay. Hypothesis: the workhorse's positive median trade comes from the entry/filter/exit assembly; absolute PnL volatility from notional exposure. Inverse-vol sizing should preserve median trade while reducing PnL variance — improving Sharpe without changing edge. |
| **Why portfolio value** | (a) Reduces XB-ORB-MNQ's PnL variance without changing edge structure. (b) Tests whether inverse_vol_sizing is portable beyond VolManaged's standalone use. (c) Operationally meaningful: workhorse strategies are core portfolio risk; volatility-normalization is exactly the kind of "risk-managed core" outcome the portfolio benefits from. (d) Fills VOLATILITY gap by re-using the validated sizing overlay rather than creating new VOLATILITY strategies. |
| **Cheap validation test** | A/B backtest: XB-ORB-EMA-Ladder-MNQ baseline vs same with inverse_vol_sizing overlay. Compare: (i) Sharpe; (ii) max DD; (iii) median trade (should be ~unchanged); (iv) PnL variance per trade. Pass: Sharpe improves AND median trade unchanged within 10%. Fast-reject: median trade degrades >10% (indicates sizing changed entry quality, not just exposure). |
| **Gap classification** | **VOLATILITY** (overlay) + workhorse improvement |

---

## Acceptance criteria summary (all 5 candidates)

| Candidate | Template | Gap target | Cheap validation cost | Risk-fail signal |
|---|---|---|---|---|
| 1. HYB-FX-SessionTransition | #5 (parent + salvaged) | FX HIGH | Single-asset 7yr backtest (6E) | PF<1.15 OR concentration>50% |
| 2. XB-VWAP-EMA-Ladder | #1+#2 (entry + exit + filter, 3 components) | Workhorse diversity | Single-asset 7yr backtest (MNQ) | PF<1.0 OR median trade<0 |
| 3. HYB-LunchComp-RatesAfternoon | #1 (entry + regime filter) | STRUCTURAL session-transition | A/B against ZN-Afternoon baseline | Sample <40 trades OR PF degrades |
| 4. HYB-CashClose-Salvage-RatesWindow | #5 (parent + salvaged) | STRUCTURAL session-transition | Single-asset 7yr backtest (ZN cash-close window) | PF<1.0 OR <30 trades |
| 5. HYB-VolMan-Workhorse-SizingOverlay | #6 (sizing overlay + workhorse parent) | VOLATILITY + workhorse improvement | A/B against XB-ORB-EMA-Ladder-MNQ | Median trade degrades >10% |

**All 5 ready for cheap validation today** if the operator authorizes Phase 0 dry-run inside the investigation lane (would require lane scope expansion). Per current operating discipline, Phase 0 Track A is GATED on the second clean monthly cycle (TRS-2026-06 fires 2026-06-01) — so these recipes wait for that gate to clear, OR for a separate operator authorization to run cheap validation as Lane B research.

---

## Item 2 cross-pollination criterion impact

**Item 2 day-14 gate (filed 2026-04-28):** cross-pollination criterion = 0 of required ≥2.

**If just Candidates 1 + 4 enter validation,** they both populate `relationships.salvaged_from` for the first time in registry history. That moves the criterion from 0 → 2, satisfying Item 2's activation threshold.

**If Candidate 3 also enters,** it adds a third salvaged-component cross-pollination case.

**Item 2 activation would unlock:** the donor catalog formalization work, weekly donor-attribution scoring (per `post_may1_build_sequence.md` §5), and the hot lane's primary feedback loop for "which donors actually survive recombination."

---

## What this artifact is NOT

- **Not a registry append.** No status changes, no registry mutations today. The hybrid_generation_lane registry route doesn't activate until Phase 0 Track A starts.
- **Not a code build.** No `hybrid_generator.py` written today; the recipes are spec only.
- **Not a Lane A change.** Operator's explicit Lane B / Forge work; no runtime, portfolio, scheduler, or hold-state surfaces touched.
- **Not exhaustive.** 5 candidates is a curated set, not the full enumeration of the ~64-donor surface. Many other valid candidates exist (e.g., Donchian + ema_slope + profit_ladder for energy breadth; ORION-VolBreakout entry + impulse_threshold filter; etc.). Today's set targets highest-leverage gaps; deeper enumeration can come in subsequent Forge cycles.
- **Not a Phase 0 trigger.** Phase 0 Track A activation is gated on the second clean monthly cycle. These recipes are pre-flight inventory for when the gate opens.

---

## Recommended next-step queue

| Item | Lane | Authority | When |
|---|---|---|---|
| Operator review of these 5 candidates | T1 | This week (Lane B) | Operator |
| Pick top 2 for first cheap-validation runs | T1 | Decision Lane B | Operator |
| Deeper enumeration: 2-3 more Donchian / breakout-family candidates | T1 (Lane B) | Next Forge session if value | Claude |
| Wait for TRS-2026-06 to fire and clear (2026-06-01) | event-gated | Implicit | System |
| If clean → operator-eligible Phase 0 Track A start; these recipes become first-week input | T0 → T2 | Post-2026-06-01 | Joint |
| If not clean → second investigation lane; recipes wait | event-gated | Post-2026-06-01 | Joint |

---

*Filed 2026-05-05. Lane B / Forge work. No Lane A surfaces touched. Operator review before any registry append, code build, or Phase 0 activation.*
