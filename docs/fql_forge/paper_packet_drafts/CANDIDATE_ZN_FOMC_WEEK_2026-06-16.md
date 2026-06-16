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
