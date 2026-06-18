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

## DEEP REVIEW (cycle 17m) → first_impulse_pullback DOWNGRADED to NEUTRAL (DD benefit not robust)
The first-cut −36% combined-DD reduction does NOT survive the 5 checks. **Auto-label `REWEIGHT_CANDIDATE` OVERRIDDEN → NEUTRAL/effectively-KILL** (the auto-rule missed per-year concentration + bad-day failure):
1. **NOT OOS-stable — a 2025 artifact.** Combined DD improves in only **3/8 years**; train improvement trivial (−$2,373→−$2,353); the entire headline cut is one year (2025: −$4,088→−$2,615). "Lucky period," as warned.
2. **Does NOT offset incumbent bad days — piles on.** Worst 10/20/40 incumbent days: fip net *negative* (mean −$39/−$76/−$40; only 30–38% positive). The DD reduction is fip's own positive drift padding equity, NOT hedging.
3. **Substantially duplicates orb.** Same entry hour (10am: orb 862 / fip 908), 68% same-direction, **same-day PnL corr 0.523** — largely the same opening-hour MNQ momentum, not a distinct mechanism.
4. **ADD vs REPLACE:** orb+srr+fip PF 1.634 DD −2615 net $99.6k; REPLACE-srr orb+fip PF 1.602 DD −2483 net $64.1k (lower DD but sacrifices ~$23k net for ~$1.6k DD — not clearly better).
5. **Cost/prop (the one genuine positive):** fip standalone cost-robust (PF 1.329→1.269 @3x slip), worst day −$472, maxDD −$1,804 — a clean prop-friendly book on its own, just not an additive/reweight improvement to the sleeve.

**Verdict: NEUTRAL (lean REDUNDANT-with-orb).** Not promoted, not an addition, not a reweight, not WH2. The "DD reducer" was a 2025 + drift artifact, not a robust hedge. Archived. (The deep-review discipline prevented banking a single-year offset as a risk improvement.)

## State
`FRED_YIELD_CURVE_BRANCH_CLOSED__FORGE_DISCOVERY_CONTINUES`. **This MNQ improvement batch produced no robust add/reweight candidate** (first_impulse_pullback downgraded NEUTRAL on deep review). **MNQ is NOT exhausted** — the current sleeve remains strong and hard to improve, but future MNQ research stays open for a genuinely distinct or replacement-quality mechanism. Lane 2 live item = MGC-prior_day_break addition review. Lane 1 priority = structural feeds (auctions first). No activation/registry/scheduler/portfolio/paper/live/prop mutation.
