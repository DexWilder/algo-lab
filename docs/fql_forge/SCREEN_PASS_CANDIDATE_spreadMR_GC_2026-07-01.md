# SCREEN_PASS candidate — GC calendar-spread mean-reversion (spreadMR_GC) — 2026-07-01

**Rung: SCREEN_PASS (5 of 10).** First candidate above the kill floor this session. NOT validated / tradeable / paper-ready.
Report-only. Capital gate fail-closed. Advancement past FAMILY_CONFIRMED requires the deepening below + operator gate.

## Mechanism
Gold front–deferred calendar spread (F1−F2) mean-reverts. Fade z-score extremes (|z|>1.5 vs own 252d baseline), hold to
reversion. Economic basis: gold carries lease-rate / financing / storage dynamics (a monetary metal) that transiently
dislocate the calendar spread; these revert. This is GOLD-SPECIFIC — it does NOT appear in crude (see cross-asset caveat).

## Evidence (real per-contract Databento GC ohlcv-1d, roll-handled)
| Check | Result |
|---|---|
| Sharpe (no cost / $60 / $120 / $200 per spread) | 2.89 / 2.42 / 1.93 / 1.24 |
| H1 / H2 Sharpe | 2.61 / 2.97 (stable) |
| Per-year net (2019-2026) | ALL 8 years positive ($2.8k–$44k) |
| Max-year concentration | 30% (passes <40%) |
| Median active-day PnL | +$270 |
| Active long-share (side balance) | 63% (non-degenerate) |
| Active days / total | 291 / 2304 (sparse; tail-engine gates apply) |
| **Causality (future-perturbation invariance)** | **CAUSAL — 0 violations / 14 perturbations** |
| Rollover-artifact scan | 1 large same-contract move / 2000 days (clean; sBoth guard) |
| **DSR costed-$120 layered-N** | N9=0.999, **N20=0.971**, N30=0.898, N50=0.708, N100=0.358, N1782=0.000 |
| Adversarial review | PASS (after sparse-calibration fix to DEGENERATE_SIDE) |

## DSR verdict (decisive, honest)
**DSR-BORDERLINE — credible (≥0.95) only at N≤20; FAILS at N≥30.** The no-cost Sharpe (2.89) flattered it to DSR≈1.0 up to
N=300; realistic $120 spread cost (Sh 1.93) collapses it — DSR 0.90–0.97 at the defensible search-N (~20–30 term-structure
expressions this session), essentially 0 at the full 1782-trial global-N. This is the most important number in the packet:
the edge is real on the screens but its multiple-testing credibility is fragile and cost-sensitive. It is **SCREEN_PASS, NOT
DSR-credible.** Advancement past SCREEN_PASS is BLOCKED until search-N is pinned AND execution/roll-concentration is resolved
(both could lower the effective Sharpe further).

## Caveats (why it is SCREEN_PASS, not higher)
1. **Cross-asset FAIL:** CL calendar-spread MR = Sh −0.01. Gold-specific, single-instrument — cannot claim a commodity-spread family win.
2. **Roll concentration:** 63% of PnL within ±3d of an F2 roll. MITIGATED (far-from-roll Sh 1.83 at $120 cost on 1116 days) but real — needs deferred-contract liquidity/execution realism before capital.
3. **Global-N DSR borderline** when costed; family-N clears. Layered-N judgment call — reported both.
4. **Micro $ small:** MGC retail mapping Sh 1.24–1.93 but only ~$6.6k–$10k/7yr; sizing/capacity study needed.
5. **Calendar-spread = 2-leg execution**; my cost model is a proxy, not a real spread book.

## Deepening plan (Lane G, before any FAMILY_CONFIRMED)
- Real 2-leg calendar-spread execution model (deferred-contract liquidity, bid/ask, near-roll fills).
- Resolve roll-concentration: is near-roll PnL tradeable roll-pressure or stale deferred prints? (needs 1m/tick).
- Capacity/sizing under tail-engine gates (factory tail path: PF≥1.15 VIABLE, instance CV<3, positive-instance ≥60%).
- Parameter robustness (z threshold 1.0/2.0, lookback 126/252, hold rule).
