# Lane 2 — MNQ Workhorse Improvement Board — 2026-06-17

> Report-only. Replacement/addition evaluation vs the INCUMBENT MNQ books — **NOT a WH2 search** (MNQ = equity exposure; no result here is a diversifier regardless of metrics). Evidence: `forge_cycle_2026-06-17l_mnq_improvement.json`. No sweep, no mutation, no promotion.

## Incumbents (benchmarks)
| Book | PF | net | median | max-DD | worst-day | n |
|---|--:|--:|--:|--:|--:|--:|
| orb_breakout (XB-ORB-EMA-Ladder-MNQ) | 1.628 | $51,560 | $43.01 | −$2,331 | −$850 | 1222 |
| stop_run_reversal (WH-MNQ-stop_run_reversal) | 1.477 | $35,516 | $15.76 | −$4,018 | −$1,457 | 1418 |
| **Combined (1 micro each)** | **1.635** | — | — | **−$4,088** | −$1,457 | — |

## Candidates
| Candidate | PF | max-DD | corr orb/srr | +portfolio PF / DD | Verdict |
|---|--:|--:|---|---|---|
| **first_impulse_pullback** | 1.329 | −$1,804 | **0.43 / 0.10** | 1.635→1.634 / −4088→**−2615** | **ADDITION_CANDIDATE** (risk-reducing) |
| donchian_breakout | 1.622 | −$2,822 | 0.73 / 0.24 | 1.635→1.718 / −4088→−4971 | REDUNDANT (dup of orb) |
| range_compression_break | 1.346 | −$1,235 | 0.50 / 0.23 | 1.635→1.651 / −4088→−4885 | NEUTRAL (deepens DD) |
| pb_pullback | 1.393 | — | — | — | KILL (quality fail) |
| vwap_continuation | 1.068 | — | — | — | KILL |

## The one find: first_impulse_pullback (ADDITION_CANDIDATE)
- **What it is:** a *risk-reducing same-sleeve addition* — low correlation to both incumbents (esp. 0.10 to stop_run_reversal), cuts the combined MNQ sleeve max-DD by ~36% while leaving PF essentially unchanged. For a prop context where DD is the binding constraint, that's a meaningful contribution.
- **What it is NOT:** not a replacement (PF 1.329 < both incumbents), not WH2 (it's MNQ/equity).
- **Caveats / required deeper review before any promotion (all gated, report-only):**
  1. **OOS stability of the DD reduction** — is the −36% combined-DD cut consistent across train/test halves, or a one-period artifact? (Must hold OOS.)
  2. **Bad-day overlap detail** — it shares 87% of *trading days* with orb but corr only 0.43 (same days, different outcomes); confirm it's genuinely diversifying, not orb-with-noise.
  3. **Equity-concentration cost** — adding a 3rd MNQ book deepens the portfolio's already-dominant equity exposure (implicit MNQ/equity cap, analogous to the MGC soft-cap). A DD cut *within* the MNQ sleeve doesn't reduce *portfolio* equity concentration.
  4. Regime exposure; cost-aware confirmation.

## Disposition
- **first_impulse_pullback** → banked **ADDITION_CANDIDATE** (risk-reducing), pending the 4 deeper-review checks. Not promoted, not wired, not WH2.
- donchian_breakout → REDUNDANT (no-repeat as an MNQ addition; it's orb-equivalent).
- range_compression_break → NEUTRAL; pb_pullback / vwap_continuation → KILL.

## State
`FRED_YIELD_CURVE_BRANCH_CLOSED__FORGE_DISCOVERY_CONTINUES`. Lane 2 produced a real risk-reducing MNQ addition candidate (gated on deeper review). Lane 1 priority remains structural feeds (auctions first). No activation/registry/scheduler/portfolio/paper/live/prop mutation.
