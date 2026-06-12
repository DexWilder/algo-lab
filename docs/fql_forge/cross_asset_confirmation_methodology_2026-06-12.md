# Cross-Asset Confirmation Methodology — 2026-06-12

> **Authority:** Operator #194 A (2026-06-12). Methodology first; rushed candidate later.
> **Status:** Lane B research design note. No code yet.
> **Strategic question:** Can cross-asset or regime context make the 3 GREEN workhorses safer, less crowded, and more selective WITHOUT curve-fitting?

## Two distinct goals

This methodology must distinguish two different research questions, because they require different tests:

### Goal A — Improve existing Lane A workhorses (filter layer)

**Hypothesis:** Cross-asset context can identify subsets of existing entries that are systematically better than the average entry. Apply as a filter LAYER on top of the existing entry primitive.

Test: for each existing workhorse (stop_run, range_compression, first_impulse_pullback), apply candidate cross-asset filters and measure:
- Reduction in trade count (acceptable: ~30-50% reduction; rejected: > 75% reduction = over-fitting)
- Improvement in PF (target: +0.15 PF or better)
- Improvement in Era 3 PF specifically (durable improvement, not historical noise)
- Improvement in stress survival (target: stress PF +0.10 minimum)
- Reduction in max-yr concentration (target: lower or equal)

**Anti-curve-fit guardrails:**
- Reject filter if it improves PF but hurts Era 3 PF (would be overfitting to old regime)
- Reject if trade count drops by > 75% (filter too narrow)
- Reject if improvement < 0.10 PF (not material vs noise)
- Reject if filter requires more than 1 parameter (avoid degrees of freedom inflation)

### Goal B — Find genuinely independent confirmation layer (standalone)

**Hypothesis:** A cross-asset signal exists that itself produces entry conditions independent of the existing primitives. Build as a NEW entry primitive that uses cross-asset state.

Test: produce a workhorse PAPER_PACKET_CANDIDATE that:
- Passes V1 workhorse hard gates standalone
- Has corr < 0.30 vs all 3 existing GREEN workhorses
- Has corr < 0.30 vs XB-ORB-MNQ probation
- Demonstrates the cross-asset edge in family review

**Goal B is harder.** If Goal A produces material improvements, Goal B can wait.

## Candidate cross-asset filter signals

Ranked by simplicity (fewest parameters) and theoretical priority:

### Signal 1: MNQ-MES alignment / divergence (RUNNABLE_NOW)

- **Filter (Goal A):** require MNQ entry signal AND MES same-direction confirmation
  - Long MNQ only if MES is also above its EMA20 (or vice versa)
- **Theory:** equity index family alignment = institutional risk-on; divergence = retail/single-name noise
- **Risk:** highly correlated → filter trivially accepts most trades (no edge improvement)
- **Cost:** trivial (MES already loaded)

### Signal 2: ZN (rates) risk-on/risk-off filter (RUNNABLE_NOW)

- **Filter (Goal A):** require ZN to be in a specific regime (e.g., falling for equity LONG = risk-on)
- **Theory:** rates falling typically = equity rally environment
- **Risk:** the rates-equity correlation is regime-dependent (positive 2010s, negative 2022-2024)
- **Cost:** trivial (ZN loaded)

### Signal 3: MGC (gold) divergence (RUNNABLE_NOW with caveat)

- **Filter (Goal A):** when MGC rallies hard intraday, equity LONG may be at risk (USD weakening from inflation fear)
- **Theory:** MGC rally + USD weakness can signal equity downside
- **Risk:** MGC data has known gap issues (per R4 finding) — must use clean filter
- **Cost:** moderate (need to handle data gaps)

### Signal 4: VIX-based regime filter (NEEDS_DATA)

- **Filter (Goal A):** trade only in specific VIX ranges (e.g., 12-25 = normal regime)
- **Theory:** vol-regime-dependent edge — too low VIX = complacency reversal risk; too high VIX = chaos
- **Risk:** VIX data not yet in `data/processed/`
- **Cost:** higher (data integration needed)

## Recommended first test (smallest blast radius)

**Test 1: MNQ-MES alignment filter on WH-MNQ-stop_run_reversal (primary lead)**

Build a new filter `mes_alignment` that:
- For MNQ LONG signals: require MES close > MES EMA20 at the same bar
- For MNQ SHORT signals: require MES close < MES EMA20 at the same bar
- Otherwise: filter rejects the entry

Apply to stop_run_reversal × mes_alignment × profit_ladder. Compare to baseline stop_run_reversal × ema_slope × profit_ladder.

Success threshold: PF improvement ≥ 0.10, trade count reduction ≤ 50%, Era 3 PF stable or improving, stress survival improved or stable.

If Test 1 works on stop_run, replicate on first_impulse and range_compression. If it works on all 3, ratify mes_alignment as a workhorse filter family.

If Test 1 fails (no improvement or trade count too thin), drop and try Signal 2 (ZN) on the same candidate.

## Methodology rules

1. **One filter at a time.** Do not stack filters in a single test.
2. **One candidate at a time.** Apply each filter to ONE Lane A workhorse, not a sweep.
3. **Pre-declare success criteria.** Targets above are committed BEFORE running, not after.
4. **No discretion to preserve.** If a filter doesn't meet pre-declared targets, archive immediately. No "let me try one more parameter."
5. **Honest comparison.** Always compare filtered candidate to UNFILTERED baseline on same date range / same entry primitive.
6. **Per V1.1-Amendment-A:** any filter-improved candidate still counts as PORTFOLIO_COMPLEMENT to the unfiltered version, not a separate standalone packet, unless family review confirms genuine independence.

## What this methodology does NOT do

- ❌ Does NOT apply filter to Lane A candidates that are already in operator review (those stay in their packaged form)
- ❌ Does NOT mutate existing primitive code
- ❌ Does NOT pre-commit to building Goal B (cross-asset standalone primitive) — Goal A first
- ❌ Does NOT try filter combinations until single filters prove out

## Anti-curve-fit reminders

Curve-fitting risks specific to cross-asset filters:
- **Lookback parameter inflation:** if filter uses EMA20, don't also test EMA10, EMA50 — pick one based on theory and commit
- **Regime selection bias:** if filter only works post-2022, that's regime-specific and not durable
- **Day-of-week / time-of-day blending:** do not introduce time filters AND cross-asset filters in the same test
- **Sample size collapse:** if filter cuts trades by > 75%, the result is unreliable regardless of headline PF

## Path forward

1. **This doc (today):** methodology committed (no code)
2. **Next cycle (after operator review):** implement `mes_alignment` filter
3. **Test cycle:** apply to stop_run on MNQ
4. **Evaluate:** does it meet pre-declared targets?
5. **If yes:** test on first_impulse and range_compression
6. **If no:** archive mes_alignment, move to ZN regime filter (Signal 2)
7. **If no filter improves any workhorse:** cross-asset confirmation as filter layer is saturated; pivot to Goal B (standalone cross-asset primitive) OR new mechanism class

## Operator decision

After this methodology, the operator may:
- (A) Proceed with Test 1 immediately
- (B) Modify the methodology (e.g., start with ZN instead of MES)
- (C) Approve methodology + authorize Forge to choose first test
- (D) Defer for in-person review

Standing for operator response before building any cross-asset filter.

## Cross-reference

- [[packet_standard_v1]] — base spec
- [[feedback_asset_family_saturation_rule]] — narrow saturation framework
- [[feedback_concentration_is_load_bearing]] — gate primacy
- [[feedback_continuous_recombination]] — governed recombination doctrine
- `docs/fql_forge/paper_packet_drafts/LANE_A_BATCH_2026-06-12.md` — Lane A candidates being protected
