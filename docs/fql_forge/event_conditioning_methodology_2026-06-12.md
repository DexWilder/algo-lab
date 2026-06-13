# Event-Conditioning Methodology for Existing GREENs — 2026-06-12

> **Authority:** Operator #205 A (2026-06-12). Methodology-first pre-declared event exclusions.
> **Status:** Lane B research design note. No code yet.
> **Strategic framing:** This is FIRST a risk-cleanliness audit, SECOND a candidate-improvement test. Do not promote a filtered variant just because headline PF improves.

## §1 — Scope

Existing GREEN / Lane A batch candidates ONLY:

1. WH-MNQ-stop_run_reversal (primary daily workhorse lead)
2. WH-MNQ-first_impulse_pullback (second daily workhorse)
3. WH-MNQ-range_compression_break (third daily workhorse)

**Excluded from scope:** FOMC-MNQ-Long-1h (already event-driven; event-conditioning would be circular).

## §2 — Pre-declared event exclusions

### Tier 1: high-confidence event days (test first)

| Event | Calendar source | Cleanliness |
|---|---|---|
| **FOMC announcement days** | `research/forge_fomc_calendar_official.py` (Fed.gov MACHINE_FETCHED_OFFICIAL) | Clean — 58 dates 2019-2026 |
| **NFP release days** | `research/forge_nfp_calendar_verify.py` (operator-verified) | Clean — 96 dates 2019-2026 |

### Tier 2: tested only if Tier 1 results warrant continued work

| Event | Calendar source | Cleanliness |
|---|---|---|
| **CPI release days** | `research/forge_cpi_calendar_verified.py` (FORGE_COMPILED_DATA_REQUIRED) | Limited per V1 grade |

### Optional: event hold-through exposure

For intraday workhorses (which flatten daily), event hold-through is N/A — they never hold overnight. But if any GREEN has positions that span event window (e.g., enters 14:25, FOMC at 14:30), exclude those too.

## §3 — Three exclusion variants (pre-declared)

For each candidate × each exclusion variant, compare:

| Variant | What's excluded | Test purpose |
|---|---|---|
| **V0** | Baseline (no exclusion) | Reference — already known (Lane A packet) |
| **V1** | FOMC days only | Isolate FOMC contribution |
| **V2** | NFP days only | Isolate NFP contribution |
| **V3** | FOMC + NFP days | Combined macro-event exclusion |

**3 candidates × 3 exclusion variants = 9 filtered backtests** + 3 baselines for comparison.

CPI inclusion (V4 = V3 + CPI) deferred to Tier 2 only if V3 shows promise.

## §4 — Measurement framework

For EACH (candidate, variant) pair, report:

### Performance impact

| Metric | Compare baseline vs filtered |
|---|---|
| n (trade count) | absolute count + % reduction |
| PF | absolute + Δ |
| Median trade | absolute + Δ |
| Net | absolute + Δ |
| Mean trade | absolute + Δ |
| Year-exclusion PF range | are bad years removed? |
| H1/H2 split | does first/second half PF improve? |
| Era 3 PF | does recent regime improve? |

### Risk impact (mandatory per #207 deployment suitability)

| Metric | Compare baseline vs filtered |
|---|---|
| Largest single-day loss | absolute + Δ |
| Worst trade | absolute + Δ |
| Top-1 trade % of net | concentration |
| Top-3 trades % of net | concentration |
| Max-yr share | concentration |
| Tradeify $2K/$3K DD compat | binary outcome |
| Event-day exposure removed | count + % |

### Family review (carry over from V1 doctrine)

After filtering, re-check pairwise correlation:
- Filtered candidate vs unfiltered baseline
- Filtered candidate vs OTHER Lane A candidates
- Filtered candidate vs XB-ORB-MNQ probation

Family review is informational only — filtered candidates are refinements of baseline, not separate candidates, unless they pass V1 archetype gates independently.

## §5 — Pre-declared decision standard

| Outcome | Classification |
|---|---|
| Event exclusion improves RISK materially (e.g., Tradeify $2K DD now PASS) AND preserves edge (PF stable or improving) | **GREEN refinement / packet appendix candidate** — recommend operator review for Lane A amendment |
| Improves PF but kills sample size (> 50% trade reduction) OR creates concentration | **OBSERVATIONAL only** — don't recommend |
| Does not improve risk (DD unchanged) AND does not improve edge | **Archive filter** — preserve lesson "events don't drive risk for this primitive" |
| Damages edge (PF degrades + risk unchanged) | **Archive filter** — preserve lesson "events are PART of the edge for this primitive" |

Critical reminder: "Do not promote a filtered variant just because the headline improves" — risk audit is the primary lens.

## §6 — Anti-curve-fit rules

1. **Three pre-declared variants only.** No mid-stream additional event categories.
2. **No threshold tuning** (event days are binary include/exclude).
3. **No filter-stacking.** Test each variant independently against baseline.
4. **No discretion to preserve.** If decision standard says archive, archive.
5. **Headline improvement is NOT sufficient** — must demonstrate material risk improvement.

## §7 — Build plan

| Stage | Deliverable | Estimate |
|---|---|---|
| 1 | Wrapper that excludes signal bars on specified event dates | ~15 min |
| 2 | Cycle script — 9 filtered backtests + comparison report | ~30 min coding + ~10 min runtime |
| 3 | Apply #207 deployment suitability line to each result | included in cycle |
| **Total** | **~1 hour** |

This is significantly lighter than the multi-day harness (~3 hours) because:
- No new exit logic
- No new primitive
- Just bar-level exclusion in existing primitives
- Reuses existing crossbreeding engine

## §8 — What this methodology does NOT do

- ❌ Does NOT mutate Lane A candidates (filtered versions are refinements, not replacements)
- ❌ Does NOT modify existing primitive code (uses signal-level post-filtering)
- ❌ Does NOT test on FOMC-MNQ (already event-driven)
- ❌ Does NOT promote filtered candidates to Lane A without operator review
- ❌ Does NOT pre-commit to expanding to V2 / V3 candidates beyond the 3 GREENs

## §9 — Operator decision

After this methodology:
- (A) Proceed with build immediately
- (B) Modify methodology (e.g., test only FOMC first, defer NFP)
- (C) Approve + Forge picks first candidate to filter
- (D) Defer for in-person review

Standing for operator response before any code.

## Cross-reference

- [[packet_standard_v1]] — base spec
- [[packet_standard_v1_1_amendments]] — V1.1 doctrine
- `docs/fql_forge/daily_test2_harness_methodology_2026-06-12.md` — sibling harness methodology (NEGATIVE result)
- `docs/fql_forge/paper_packet_drafts/LANE_A_BATCH_2026-06-12.md` — the 4 candidates being protected
- `research/forge_fomc_calendar_official.py` — calendar source
- `research/forge_nfp_calendar_verify.py` — calendar source
