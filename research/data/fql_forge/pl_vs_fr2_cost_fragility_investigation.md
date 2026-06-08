# PL vs FR2 Cost-Fragility Investigation

> **Status:** Investigation per operator decision #87. **Do NOT codify yet.**
> **Recorded:** 2026-06-08.
> **Hypothesis:** profit_ladder is more cost-robust than fixed-ratio because partial exits capture smaller moves; fixed-ratio requires full target completion and is more sensitive to cost/slippage.

## Method

Five pairs of `(asset, entry, filter, mode)` candidates already run with both `profit_ladder` (PL) and `fixed_ratio` (FR2, ratio=2.0) exits. For each candidate, ran a 5-rung break-even ladder (1×, 1.5× + 1 tick, 2× + 1 tick, 2× + 2 ticks, 4× + 2 ticks) and identified the rung at which median trade goes from positive to negative.

## Results

| # | Pair | PL median@1× | PL break-even rung | FR2 median@1× | FR2 break-even rung | Δrungs (PL−FR2) |
|---:|---|---:|---|---:|---|---:|
| 1 | MCL-ORB-Short | $7.26 | 2× cost + 2 ticks | $3.76 | 1.5× cost + 1 tick | **+2** |
| 2 | MGC-ORB-Short | $8.76 | beyond 4× | $7.76 | beyond 4× | 0 (both extremely robust) |
| 3 | MGC-ORB-Long | $4.76 | 2× cost + 2 ticks | $3.76 | 2× cost + 2 ticks | 0 (tied) |
| 4 | MGC-PriorDayBreak-Long | $3.76 | 2× cost + 2 ticks | $0.76 | 1.5× cost + 1 tick | **+2** |
| 5 | MCL-Donchian-Short | $3.76 | 1.5× cost + 1 tick | -$0.24 (already negative at 1×) | n/a | **+1** |

**Pattern: PL more cost-robust in 3 of 5 pairs; TIED in 2 of 5; FR2 more robust in 0 of 5.**

## Tied case examination

The two tied cases are revealing:

- **MGC-ORB-Short (pair 2):** Both PL and FR2 survive ALL four stress rungs. The baseline edge is so strong (median $7.76-$8.76) that cost stress in our ladder doesn't expose either's fragility. This isn't evidence of equal fragility — it's evidence that a strong-baseline edge survives both exit choices. Would need higher-cost stress rungs to discriminate.
- **MGC-ORB-Long (pair 3):** Both break at 2× cost + 2 ticks. But FR2's baseline median ($3.76) is $1.00 lower than PL's ($4.76), and FR2 breaks at the SAME rung — meaning FR2 had **less margin to lose**. Not a true tie; rung resolution is too coarse.

## Refined verdict

- **PL is at least as cost-robust as FR2 in 5 of 5 pairs.** No counterexample found in this batch.
- **PL strictly more cost-robust in 3 of 5 pairs**, often by 1-2 stress rungs (worth ~$2-4 of additional round-trip cost tolerance).
- The mechanism aligns with the working hypothesis: PL's tiered partial exits capture moves at multiple thresholds, so cost increases only affect the marginal trades that no longer reach exit thresholds. FR2 requires full ratio achievement, so cost increases shift the entire profit calculation directly.

## Why not codify yet

Per operator decision #87: investigate, do NOT codify yet. Reasons to wait:

1. **n=5 pairs is small.** A pattern of 3+/5 with 0 counter-examples is suggestive but not yet decisive.
2. **Asset/entry mix is limited.** All pairs are micro futures (MCL/MGC) with ORB or PB-style entries. Need broader entry coverage (event-window exits, daily close, etc.) before codifying as a general exit-design rule.
3. **Tied cases need finer-resolution stress ladder.** The 2× → 4× jump is too coarse to distinguish "both very robust" from "FR2 slightly less robust." A 2.5× / 3× / 3.5× rung set would discriminate.
4. **Counterexample search not exhausted.** Should test cases where FR2 might be MORE robust: (a) high-frequency strategies where targets are hit quickly before cost stress matters, (b) low-volatility strategies where partial exits cluster near entry and offer little margin, (c) tail-strategies where partial exits never trigger.

## Recommendation

- **Do NOT add an exit-design heuristic to FQL doctrine yet.**
- **Recommend codification candidate** for re-evaluation after n=10 pairs across 3+ entry families.
- **Useful immediately as a candidate-design heuristic** when designing new candidates: prefer PL over FR2 when prop-cost stress is the binding constraint, all else equal.
- **Save as research finding** for future doctrine consideration.

## Constraints

- **No factory change. No primitive deletion. No default-exit change.**
- Research-only Lane B finding.

## Source artifacts

- `research/forge_cycle_2026-06-08a.py` (stress_break_even() with 5-rung ladder)
- `research/data/fql_forge/reports/forge_cycle_2026-06-08a.json` (track_C_fragility section with full rung tables)
