# Forge — Non-equity event-seasonal BENCH — 2026-06-16

> **Mode:** Lane B / REPORT-ONLY; freeze maintained (no executor/wiring/mutation). ZN/FOMC stays review-track/GREEN.
> **Result:** The non-equity event-seasonal vein yields a small, coherent bench: **FOMC-week on the 5y–10y rates curve.** NFP/CPI-week are NOT rates seasonals; gold/crude/auction add nothing.
> Artifacts: `research/forge_cycle_2026-06-16f_event_seasonal_bench.py` + `.json`; ZF clean-events follow-up inline.

## Bench (long, 2td-pre→2td-post FOMC, $1500 stop)
| Candidate | PF | beta-ctrl | median | conc | prop | contam | verdict |
|---|---|---|---|---|---|---|---|
| **ZN/FOMC-week** | 1.86–1.95 | 2.46× (gen 0.79) | +$44 | 30% | <$2K | **0/54** | **PASS_REVIEW_TRACK / DATA_AUDIT_GREEN** (primary) |
| **ZF/FOMC-week** | raw 1.45 → **clean 1.77** | ~2.2× (gen 0.80) | +$36 | 44% | <$2K | 3 (removed → *improves*) | **PASS_REVIEW_TRACK-eligible** (curve confirm; own data-audit pending) |
| ZB/FOMC-week | 1.28 | (gen 0.73) | −$159 | — | — | 7 | KILL (too volatile/contaminated) |

## Other calendars (decisive negatives / defers)
- **NFP-week** (deterministic calendar) on ZN/ZF/ZB/MGC → **all KILL** (PF 0.6–1.0). Rates have **no** NFP-week long edge.
- **CPI-week** (recall calendar) on ZN/ZF/ZB/MGC → **all KILL** on strict gates (MGC contaminated; recall-grade caveat).
- **MGC** FOMC/NFP/CPI → KILL (no edge + recurring MGC data gaps).
- **Treasury auction / OPEC** → **DEFER** (no official calendar; did not improvise).

## Findings
1. **The rates edge is FOMC-policy-week-specific** — not a generic event-week effect (NFP/CPI-week KILL). A real monetary-policy-week phenomenon on rates.
2. **Cross-instrument confirmed:** FOMC-week works on ZN (10y) + ZF (5y), not ZB (30y) → coherent 5y–10y curve structure. ZN+ZF are correlated (one diversifying edge, two instruments) — ZF *confirms* ZN's robustness (the XB-ORB cross-asset analogy).
3. **Portfolio role:** ZN+ZF FOMC-week = one **rates-FOMC-week sleeve** (non-equity, non-momentum, calendar/event, beta-controlled, prop-survivable). Trade ZN primary; ZF as cross-confirmation / small basket.

## Disposition
- **Bench = ZN/FOMC-week (GREEN, primary) + ZF/FOMC-week (clean-confirming, data-audit pending).** Both review-track, NOT paper/live-approved, NOT wired.
- Vein well-characterized: FOMC-week-on-rates is THE non-equity diversifier edge available on current calendars; NFP/CPI/gold/crude do not extend it.
- Next (gated): ZF formal data-audit (quick, like ZN's); then both await out-of-band event executor + V1 packets + activation reopen.

## Boundaries
Report-only; no promotion/wiring/mutation; canonical feeds + active books untouched. Phase 1C frozen pending PHASE1C_24H_VERIFY (separate).
