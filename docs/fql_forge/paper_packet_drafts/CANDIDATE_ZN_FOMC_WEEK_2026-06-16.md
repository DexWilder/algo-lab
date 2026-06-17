# Candidate (REVIEW-ONLY) — ZN FOMC-week rates seasonal — 2026-06-16

> **Status:** PASS-grade RESEARCH candidate → **PAPER_PACKET_CANDIDATE for operator review.** REVIEW-ONLY. NOT promoted, NOT wired. Activation frozen (Phase 1C pending). Lane B / report-only.
> **Significance:** First **deployable-grade non-equity diversifier** of the whole search — non-MNQ, non-equity (rates), non-momentum (calendar/event), beta-controlled, prop-survivable.
> Artifacts: `research/forge_cycle_2026-06-16d_*` + inline shaping/window-family runs.

## Strategy
- **Mechanism:** long ZN (10y note) over the FOMC week — enter close 2 trading days before a scheduled FOMC decision, exit close 2 td after; **hard stop $1,200/contract** (caps prop drawdown).
- **Calendar:** OFFICIAL_FED_GOV FOMC (`forge_fomc_calendar_official`, deterministic, scheduled meetings only) — the good-grade calendar.
- **Archetype:** EVENT/TAIL (event-frequency, ~8/yr), not workhorse.

## Evidence (all gates)
| Gate | Result |
|---|---|
| PF (base 2→2, $1200 stop) | **1.945** |
| Expectancy / median | +$243 / **+$44** (positive) |
| Beta-control vs generic ZN | **2.46×** (generic rates-long PF 0.79 — *loses*; this is real alpha, not beta) |
| Window-family (10 variants) | **all profitable** (core cluster PF 1.24–1.95) — not one overfit window |
| Era H1/H2 | 1.57 / 2.38 (both >1) |
| Concentration (max-year) | **30.2%** (<50%) |
| Cost/stop robustness | PF 1.86–1.95 across stop None/1800/1500/1200 — stop is a robust risk cap, not a fit |
| **Prop survivability** | largest loss **−$1,234**, max-adverse-window **−$1,200 → Tradeify $2K SAFE at 1 micro** |
| Asset/factor | **rates / non-equity / event-calendar → genuine diversifier** |
| n | 54 FOMC events (event-frequency; matches the FOMC-MNQ tail-engine precedent) |

ZF/FOMC-week is a weaker secondary (PF ~1.45, conc ~45%). ZB too volatile (DD). MGC/MCL: no calendar structure.

## Honest caveats / remaining pre-packaging gates (same gauntlet as any Lane A candidate)
1. **ZN data-integrity audit not yet done** for the FOMC windows — must run clean-events + the `.c.0` vs `.v.0` roll-gap check (cf. MGC) before trusting the metrics for capital. *(DSCL/data gate.)*
2. **No executable out-of-band event-path** exists for ZN-FOMC (same gap as FOMC-MNQ Phase 1D — the event executor was never built). Wiring would require building it.
3. n=54 is event-frequency (small) — label EVENT/TAIL, evaluate on tail-engine gates.
4. Multi-day hold → overnight/weekend exposure, bounded by the $1,200 stop.
5. Full Packet Standard V1 packaging + concentration/cost re-audit before any promotion.

## Disposition
**WATCH → PASS-grade research candidate. Review-only.** Do NOT promote/wire (activation frozen + operator-gated). This is offered for operator review as the first non-equity diversifier lead worth advancing through the Lane A gauntlet (data-audit → executable port → packet → wiring), when activation reopens.

## Boundaries
Report-only; no promotion/wiring/mutation; canonical feeds + active books untouched. Phase 1C frozen pending PHASE1C_24H_VERIFY.

---

## DATA AUDIT UPDATE — 2026-06-16 → **DATA_AUDIT_GREEN**
Audit `research/forge_cycle_2026-06-16e_zn_fomc_data_audit.py` (+ `.json`):
- **Lineage:** Databento GLBX.MDP3 `ZN.c.0` (calendar-roll). File clean: 0 dupes, monotonic, 0 zero-volume; hash `89cc66f7`.
- **FOMC calendar:** 58 events, all scheduled / 14:00 ET / federalreserve.gov (`OFFICIAL_FED_GOV`). n=54 in span.
- **Contamination (the decisive test):** 13 ZN roll-stitch gaps exist over 7y, but **0 of 54 FOMC windows contaminated** (FOMC mid-month ≠ ZN late-prior-month roll). `.c.0` clean on all windows → no `.v.0` swap needed.
- **Clean rebuild == raw rebuild** (PF 1.945 unchanged) → edge is NOT a data/roll artifact (where MGC collapsed).
- **Packet reconciles exactly** to audited rebuild; signal hash `3695298c5aa7a9bc`.
- **Scope (locked):** DATA_AUDIT_GREEN = feed-internal reproducibility ONLY; external feed correctness (vs CME) still DSCL-gated. Live/prop NOT cleared.

**Status: review-track candidate, DATA_AUDIT_GREEN.** Still NOT approved for paper/live. Remaining gates before wiring (when activation reopens): out-of-band FOMC event executor (unbuilt), full V1 packet, EVENT/TAIL archetype evaluation. Activation freeze maintained.

---

## ROBUSTNESS-MAP UPDATE — 2026-06-16 → ⚠️ REGIME-DEPENDENT (material caveat)
Robustness trickle (`forge_cycle_2026-06-16` regime split): the ZN-FOMC-week long edge is **concentrated in the rates-UP regime** (ZN rising / yields falling / easing-biased):
- rates-UP: n=22, **PF 4.20**, median +$395, net +$11,701
- rates-DOWN (hiking, e.g. 2022): n=31, **PF 0.99**, median −$128, **net −$99 (flat/no edge)**

**Implication:** NOT all-weather. The sleeve is a rates-easing-conditional FOMC event edge — expect ~flat performance in sustained hiking regimes (like OPEX's 2022 weakness). Still real / DATA_AUDIT_GREEN / prop-safe / decorrelated from MNQ momentum (still a diversifier), but **must be labeled REGIME_DEPENDENT** and sized/expected accordingly. Does NOT downgrade from DATA_AUDIT_GREEN, but is a required disclosure before any promotion/wiring.

## REGIME GATE — HARD, AUDITED, VISIBLE (operator-locked 2026-06-16; boundary-tested `forge_cycle_2026-06-16j`)
The regime filter is **NOT optional** and **NOT "lower confidence"** — it is a hard gate: **rates-DOWN/hiking → BLOCKED (fail-closed, no fire).** Boundary-sensitivity test result (`forge_cycle_2026-06-16j_zn_fomc_regime_boundary.json`):
- **`REGIME_GATE_DIRECTIONALLY_ROBUST`** — across the full grid (lookback 21/42/63/84/126 td × threshold 0–0.02), the rates-UP regime is an edge in **18/18 (100%)** configs and beats rates-DOWN by ≥0.8 PF in **18/18 (100%)**. The block is not a knife-edge artifact.
- **Stronger than "flat":** at the natural cut (sign of trend, thr=0), the rates-DOWN regime is *losing*, not merely flat — at the pre-registered 42-td lookback, DOWN = n31 **PF 0.60, net −$4,862**. Blocking it removes a money-loser, not just dead weight.
- **OVERFIT TRAP (do NOT optimize):** tightening to lb=21/thr=0.01 manufactures UP PF 39.6 at n=9 — small-sample inflation. The gate threshold is **PRE-REGISTERED conservatively**, not tuned to max PF.
- **PRE-REGISTERED GATE DEFINITION (locked):** block the firing if **ZN 42-trading-day price trend ≤ 0** (simple sign of trend; ZN rising = yields falling = easing = eligible). At this definition: UP n22 PF 11.1 / DOWN n31 PF 0.60. Any future change to lookback/threshold is a gated re-validation.
