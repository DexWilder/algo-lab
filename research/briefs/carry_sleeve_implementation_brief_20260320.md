# FQL Research Brief: Carry Factor — Active Push + Salvage Lane

**Date:** 2026-03-20 (Friday)
**Status:** Implementation-grade
**Author:** Claude (automated research pipeline)
**Families:** 41–45 (Carry cluster)

---

## Executive Summary

The carry cluster contains 5 families. This brief establishes the
execution hierarchy:

- **Primary active push:** Family 45 (Treasury Rolldown Carry Spread) —
  enters forward runner immediately as a real contender for the June 1
  MomIgn displacement. 79 trades, rubric 20, fills CARRY + Rates gaps.
- **Secondary salvage lane:** Family 42 (Commodity TS Carry) — cheap
  long-only re-test this week, but the 60-day proxy conflates carry with
  momentum. Remains SALVAGE until decomposition is resolved.
- **System fix:** Patch vitality monitor for sparse event strategies.
- **Retain:** TV-NFP-High-Low-Levels on probation pending corrected
  vitality framework.

Family 41 is a conceptual anchor, not a build target. Families 43-44
are deferred dependencies.

The CARRY factor is the single largest gap in the portfolio (0 active,
0 probation, 0 conviction). Any carry strategy that clears PF > 1.1 with
stable walk-forward is more portfolio-valuable than another momentum
strategy at PF > 1.5.

---

## 1. Family 45: Treasury Rolldown Carry Spread — Active Probation Push

### Status: Forward-Runner Challenger (Not Research-Only)

Family 45 is the strongest carry candidate FQL has. It is not queued
behind Family 42 — it leads the carry effort.

**Evidence basis:**
- Implementation: `strategies/treasury_rolldown_carry/strategy.py` (production-ready)
- First-pass: PF 1.11 (equal-notional), **79 trades** — 4x the sample of any other carry idea
- Rubric: 18/24 raw, **effective 20** with +2 gap bonus (CARRY + Rates)
- Carry signal: APPROXIMATE quality via `engine/carry_lookup.py` (price-derived yield + rolldown)
- Displacement target: MomIgn-M2K-Short (watch, 14/24) at June 1 deadline

**What makes this a real contender, not just "interesting":**
- Fills the two biggest portfolio gaps simultaneously (CARRY factor, Rates asset class)
- Has more backtest trades than most probation strategies
- Displacement math is decisive: eff. 20 vs MomIgn 14
- Implementation exists — no build required, only evidence accumulation

**Immediate action:** Enter forward runner at MICRO tier, 1 contract per
spread leg, monthly rebalance. Begin accumulating forward evidence now.
The June 1 displacement decision should be based on real forward PnL,
not backtest extrapolation.

**Promotion path:**

| Gate | Criterion | Timeline |
|------|-----------|----------|
| Forward entry | Add to forward runner, MICRO tier | This week |
| Evidence accumulation | ≥ 3 monthly rebalance cycles with forward PnL | March–May 2026 |
| June 1 displacement | Forward PnL positive + rubric ≥ 18 → displace MomIgn | June 1, 2026 |
| Conviction probation | 8+ forward trades, PF > 1.1, Sharpe > 0.3 | ~October 2026 |
| Core promotion | 16+ forward trades, stable walk-forward confirmed | ~March 2027 |

**Key risk:** PF 1.11 is marginal. The 2025-2026 segment is negative
(-$15K on equal-notional variant). If this is a secular decline rather
than a regime artifact, the strategy doesn't survive conviction. The
forward runner will answer this directly.

---

## 2. Family 42: Commodity Term-Structure Carry — Salvage Lane

**Status: SALVAGE. Not the carry family lead.** The 60-day proxy blends
carry with momentum. Until decomposition separates the two, this cannot
be labeled a carry strategy with confidence. It remains a cheap hypothesis
test, not a portfolio candidate.

### 2a. Simplest Futures-Native Design

The v1 implementation already exists at `strategies/commodity_carry_proxy/strategy.py`.
The "simplest first-pass" is the current design with one critical scope reduction:

**Long-only on MGC.**

Rationale from first-pass data:
- MGC long: PF 10.03, 10 trades, $25,709 PnL — the signal works
- MGC short: PF 0.17, 10 trades, -$5,245 — the signal fails
- MCL both: PF 1.15, 17 trades — marginal, dominated by MGC
- All other assets: MONITOR or REJECT classification

The cross-sectional pair trade (long one / short the other) is premature
with only 2 assets. The first-pass question narrows to: **Does the
60-day carry proxy produce a long-only edge on MGC that survives
walk-forward and regime decomposition?**

### 2b. Signal Logic (Simplified)

```
Input:  MGC continuous front-contract 5m bars
Signal: 60-day trailing return > 0 → LONG
        60-day trailing return ≤ 0 → FLAT
Rebal:  Monthly (last trading day)
Exit:   Next rebalance OR 2.5x ATR stop
Size:   1 micro contract (MICRO tier)
```

No cross-sectional ranking. No spread filter. No short leg.
This is the minimum viable carry signal.

### 2c. Known Limitations (Accepted for First Pass)

1. **Proxy conflation:** 60-day return mixes carry with momentum (~0.4-0.6
   correlation historically). We cannot claim pure carry until v2 data
   (front/back contract spreads) decomposes the signal.
2. **Single-asset concentration:** MGC only. Not a "commodity carry factor" —
   it's a "gold carry proxy." The label is honest.
3. **Recency bias:** MGC PF 10.03 long is driven by the 2024-2026 gold rally.
   H1 PF 0.52 vs H2 PF 14.26 — this is regime-concentrated, not stable.
4. **Low trade count:** 10 long trades in backtest. Marginal for any
   statistical conclusion.

### 2d. Required Data Fields

| Field | Source | Status |
|-------|--------|--------|
| MGC 5m OHLCV | `data/processed/MGC_5m.csv` | Available |
| MGC daily close | Derived from 5m bars | Available |
| 60-day trailing return | Computed in strategy | Available |
| 20-day ATR | Computed in strategy | Available |
| Carry score via lookup | `engine/carry_lookup.py` | Available (PROXY quality) |

No new data purchases required for v1.

### 2e. Assumptions and Simplifications

| Assumption | Justification | Risk If Wrong |
|------------|--------------|---------------|
| 60-day return ≈ carry direction | Carry and momentum correlate ~0.5 on commodities | Signal is momentum, not carry — mislabeled factor |
| Monthly rebalance is sufficient | Carry is slow-moving | Missing short-duration carry reversals |
| Long-only captures the edge | Short leg PF 0.17 destroys value | If regime shifts, long-only has no hedge |
| Front-contract continuous data adequate | Panama-canal adjustment preserves trend | Roll yield hidden in adjustment — cannot measure directly |
| MGC alone represents "commodity carry" | Only asset with signal | Not a factor — it's an asset bet |

---

## 3. Validation Battery (Family 42 Salvage Gate)

### 3a. Walk-Forward

| Test | Method | Pass Criteria |
|------|--------|---------------|
| Year splits | 50/50 time split (H1/H2) | Both halves PF > 1.0 |
| Rolling windows | 12-month rolling, 6-month step | ≥ 75% of windows PF > 1.0 |
| **Current status** | H1 PF 0.52, H2 PF 14.26 | **FAILS** — all profit in H2 |

**Action required:** The walk-forward failure is the critical blocker.
Before proceeding to validation battery, investigate whether the H1/H2
split aligns with a gold regime change (it does — 2019-2022 gold was
range-bound, 2023-2026 is a secular rally). If the carry proxy only works
in trending gold, it's a momentum strategy with a carry label.

### 3b. Cross-Regime

| Regime | Test Method | Pass Criteria |
|--------|-------------|---------------|
| Vol regime (LOW/NORMAL/HIGH) | Segment trades by ATR percentile | No cell with ≥3 trades has PF < 0.5 |
| Trend regime (TRENDING/RANGING) | Segment by 20d EMA slope | Edge present in both regimes |
| Gold-specific: rally vs range-bound | Manual regime tag (pre-2023 vs post-2023) | Edge must exist outside the 2023+ rally |

**Key question:** Does the carry proxy produce PF > 1.0 in ranging gold
(2019-2022)? If not, the strategy is momentum-in-disguise and should be
tagged MOMENTUM, not CARRY.

### 3c. Parameter Stability

| Parameter | Base | Perturbation Range | Pass Criteria |
|-----------|------|-------------------|---------------|
| CARRY_LOOKBACK_DAYS | 60 | 40, 50, 70, 80 | ≥ 60% of variants PF > 1.0 |
| SL_ATR_MULT | 2.5 | 1.5, 2.0, 3.0, 3.5 | ≥ 60% of variants PF > 1.0 |
| USE_STOP | True | True, False | Both variants positive |

With only 10 trades, parameter stability testing is nearly meaningless.
Report results but do not gate on them.

### 3d. Portfolio Contribution / Overlap

| Test | Method | Pass Criteria |
|------|--------|---------------|
| Factor overlap | Correlate daily PnL with existing portfolio | Correlation < 0.20 |
| Marginal Sharpe | Add to existing portfolio, measure Sharpe delta | Delta ≥ 0 |
| Drawdown overlap | Check if MGC carry DD coincides with portfolio DD | < 50% DD overlap |
| Momentum decomposition | Compare to pure 60-day momentum on MGC | If correlation > 0.8, relabel as MOMENTUM |

**The momentum decomposition test is the single most important validation.**
If carry proxy and pure momentum are > 0.8 correlated, the strategy fills
the MOMENTUM bucket (overcrowded at 61%), not the CARRY bucket (gap at 0%).
The portfolio construction value collapses.

---

## 4. Family 42 Decision Gate: Hard Criteria for This Week

### Gate 1: First-Pass Classification (Current Stage)

| Criterion | Threshold | Status |
|-----------|-----------|--------|
| Overall PF | > 1.0 | PASS (3.23 on MGC both, but asset-concentrated) |
| Walk-forward | Both halves PF > 1.0 | **FAIL** (H1 0.52, H2 14.26) |
| Trade count | ≥ 30 | **FAIL** (20 trades both, 10 long-only) |
| Classification | ADVANCE | **FAIL** (SALVAGE) |

**Current verdict:** SALVAGE. Cannot advance to validation battery.

### Gate 2: Path A Re-Test (This Week — Hard Decision)

**Run `batch_first_pass` with MGC long-only mode.** Cost: 30 minutes, $0.

**Hard gate after Path A completes:**

| Result | Decision | Next Step |
|--------|----------|-----------|
| Long-only H1 PF > 1.0 AND H2 PF > 1.0 AND trades ≥ 15 | **ADVANCE** — enter validation battery | Run full 6-test battery |
| Long-only remains rally-dependent (H1 < 1.0) | **STAY SALVAGE** — do not advance | Queue Path B evaluation |
| Long-only has < 8 trades in either half | **STAY SALVAGE** — insufficient sample | Queue Path B evaluation |

**Path A staying SALVAGE does not automatically fund Path B.** Path B
(Databento front/back contract data, ~$50-100) is only worth funding if:
1. The momentum decomposition case is still compelling — i.e., there is
   reason to believe the proxy is masking a real carry signal, not just
   adding noise to a momentum signal
2. Family 45 (Treasury Rolldown) is showing promise in the forward runner,
   validating that the carry_lookup infrastructure produces real edges
3. The budget is available in the next data investment cycle

If Path A fails AND the decomposition case is weak (e.g., carry proxy
correlates > 0.8 with pure 60-day momentum), **archive Family 42** and
redirect carry effort entirely to Family 45.

### Gate 3: Validation Battery

Only entered after ADVANCE classification. Full 6-test battery per
`research/validation/run_validation_battery.py`:
- Walk-forward, regime stability, asset robustness, timeframe robustness,
  Monte Carlo/bootstrap, parameter stability
- Promotion threshold: ≥ 7/10 with 0 hard failures

### Gate 3: Validation Battery

Only entered after ADVANCE classification. Full 6-test battery per
`research/validation/run_validation_battery.py`:
- Walk-forward, regime stability, asset robustness, timeframe robustness,
  Monte Carlo/bootstrap, parameter stability
- Promotion threshold: ≥ 7/10 with 0 hard failures

### Gate 4: Conviction Probation (Applies to Both Family 42 and 45)

| Criterion | Threshold |
|-----------|-----------|
| Forward trades | ≥ 8 (event-pace, ~1/month) |
| Forward PF | > 1.1 |
| Forward Sharpe | > 0.3 |
| Factor confirmed | Carry (not momentum) via live decomposition |
| Max DD | < $3K single-strategy |
| Duration | 8 months max (monthly signal = slow evidence) |

### Gate 5: Promotion to Core Carry Sleeve

A "carry sleeve" in the portfolio requires:
- ≥ 1 promoted carry strategy with forward evidence
- Factor tag verified as CARRY (not momentum-in-disguise)
- Portfolio contribution confirmed positive (marginal Sharpe ≥ 0)
- If only 1 strategy: it's a "carry pilot," not a "carry sleeve"
- True sleeve requires ≥ 2 carry strategies across different asset classes

---

## 5. Family 41: Managed Futures Carry Diversified — Conceptual Anchor

### Recommendation: Conceptual Anchor Only. Do Not Build in Parallel.

**Reasoning:**

| Dimension | Family 42 (Commodity TS Carry) | Family 41 (MF Carry Diversified) |
|-----------|-------------------------------|----------------------------------|
| Data readiness | MGC/MCL available now | Requires FX, rates, commodities, equities — 4 asset class feeds |
| Signal readiness | Proxy available, v2 acquirable | Requires carry_lookup v2 for commodities + equity dividend yields |
| Complexity | Single-asset, single-signal | Multi-asset cross-sectional ranking, 4+ legs |
| Trade count | ~10/year (testable in 1 year) | Unknown (depends on rebalance frequency) |
| First-pass cost | 0 (already run) | ~2-3 days engineering + data costs |

Family 41 is a **portfolio-level carry strategy** (rank all assets by
carry, go long high-carry / short low-carry). This is the academic ideal
but requires:
- Real carry scores across all asset classes (needs v2 carry lookup)
- Enough assets per class to rank meaningfully (we have 2-3 per class)
- Correlation structure across carry bets (unknown until built)

**What 41 provides today:** A design target. When FQL has 3+ carry
strategies across different asset classes, Family 41 becomes the
aggregation framework — not a strategy itself, but the portfolio
construction logic for the carry sleeve.

**Action:** Retain Family 41 in the registry as `status: BLOCKED` with
`blocked_by: carry_lookup_v2 + asset_expansion`. Do not convert to code.
Revisit when ≥ 2 individual carry strategies are in conviction.

---

## 6. Family 45 vs 42 Interaction

Family 45 is the active push. Family 42 is the salvage lane. They run
in parallel but are not co-dependent.

| Condition | Effect on 45 | Effect on 42 |
|-----------|-------------|-------------|
| 45 forward PnL positive after 3 months | Strengthens June 1 displacement case | Validates carry_lookup infra → supports Path B funding |
| 45 forward PnL negative after 3 months | Weakens displacement case, extend to Sept | No effect — 42 has its own gate |
| 42 Path A → ADVANCE | No effect — 45 continues independently | Enter validation battery |
| 42 Path A → SALVAGE, decomposition weak | No effect | Archive Family 42 |
| 42 Path A → SALVAGE, decomposition compelling | No effect | Fund Path B in next data cycle |

---

## 7. Family Sequencing Summary

| Priority | Family | Action | Timeline | Blocker |
|----------|--------|--------|----------|---------|
| **1** | 45 Treasury Rolldown | **Active push.** Enter forward runner now. Accumulate evidence toward June 1 displacement. | Immediate | None — implementation exists |
| **2** | 42 Commodity TS Carry | **Salvage lane.** Run Path A re-test. Hard gate: advance, archive, or fund Path B. | This week (Path A) | Walk-forward failure, proxy conflation |
| **3** | 41 MF Carry Diversified | Retain as design target. Do not build. | After ≥ 2 carry strategies in conviction | carry_lookup v2, asset expansion |
| **4** | 43 Commodity Carry Tail-Risk | Dependency on 42's carry signal. Not standalone. | After 42 resolves | Family 42 outcome |
| **5** | 44 Treasury Cash-Futures Basis | Infra-heavy (CTD identification, basis calculation). Defer. | 6+ months | Significant engineering investment |

---

## 8. Architecture Alignment

### FQL/FISH Compliance Check

| Principle | Compliance | Notes |
|-----------|-----------|-------|
| `generate_signals(df) → DataFrame` | YES | Both carry strategies follow the contract |
| Signal fires on bar close, fill at next open | YES | Monthly rebalance via daily close evaluation |
| `engine/carry_lookup.py` for carry scores | YES | Centralized, honest quality labels |
| `engine/asset_config.py` for asset defs | YES | MGC/MCL/ZN/ZF/ZB all defined |
| `research/data/strategy_registry.json` as SoT | YES | Both carry strategies registered |
| Validation battery gates promotion | YES | 6-test suite applies |
| Prop overlay (Layer B) sizing: MICRO tier | YES | 1 contract per signal |
| Factor tagging honest | **REQUIRES VERIFICATION** | Must run momentum decomposition before tagging as CARRY |

### What This Brief Does NOT Propose

- No new data purchases (v1 only)
- No new infrastructure (carry_lookup already built)
- No new strategy files (commodity_carry_proxy and treasury_rolldown_carry exist)
- No portfolio changes (no promotion, no slot changes)
- No changes to the validation framework or promotion criteria

This brief defines the evaluation path, not the build path. The build is
done. The question is whether the evidence supports promotion.

---

# SYSTEM FIX: Vitality Monitor — Sparse Event Strategy Patch

## Problem

The vitality framework is calibrated for intraday strategies (50+
trades/month). Event strategies like TV-NFP (~8/year) and PreFOMC
(~8/year) will always score FADING because:

1. Forward deviation is computed from sparse data (1-2 trades in 4 weeks)
2. Forward decay comparison has near-zero statistical power
3. Half-life decay uses trailing windows that capture mostly flat periods

TV-NFP's vitality 0.26 reflects data sparsity, not edge decay.

## Implementation Tasks

### Task 1: Add `event_cadence` field to registry

**File:** `research/data/strategy_registry.json`
**Affected strategies:** TV-NFP-High-Low-Levels, PreFOMC-Drift-Equity

Add to each entry:
```json
"event_cadence": {
  "trades_per_month": 0.8,
  "cadence_class": "sparse_event"
}
```

### Task 2: Patch vitality monitor for sparse event strategies

**File:** `research/edge_vitality_monitor.py`

When `cadence_class == "sparse_event"`:
- Extend measurement window: use `max(default_window, 4 / trades_per_month)`
  months of data (≥5 months for TV-NFP)
- Re-weight components: backtest stability 50%, forward deviation 30%,
  forward decay 20% (inverse of default — backtest evidence dominates
  when forward sample is tiny)
- FADING threshold: only trigger if ≥ 4 event occurrences show declining
  PnL trend (not if the monitor simply has too few data points)

### Task 3: Re-run vitality classification after patch

**Command:** Re-run `edge_vitality_monitor.py` for TV-NFP and PreFOMC.
Confirm vitality scores are recalculated under the sparse-event logic.
Log before/after scores.

### Task 4: Update probation review criteria

**File:** `docs/PROBATION_REVIEW_CRITERIA.md`

Add a note under TV-NFP and PreFOMC entries:
> Vitality monitor uses sparse-event calibration (extended window,
> backtest-weighted). Do not act on FADING alerts unless ≥ 4 event
> occurrences show declining PnL.

---

# TV-NFP-High-Low-Levels: Status Decision

## Evidence Summary

| Metric | Value | Assessment |
|--------|-------|-----------|
| Vitality score | 0.26 (FADING) | **Measurement artifact** — sparse event, not real decay |
| Backtest PF | 1.66 (65 trades) | Strong |
| Walk-forward | H1 1.50, H2 1.61 | **Stable** — unusual for this portfolio |
| NFP specificity | 26.8x | Strong — genuinely event-driven |
| Momentum correlation | 0.065 | Independent — confirmed not a momentum proxy |
| Bootstrap CI | 0.929 (< 1.0) | Real concern — thin edge relative to variance |
| Monte Carlo p(ruin) | 0.9992 | Real concern — but MICRO sizing limits dollar exposure |

## Decision: RETAIN on Probation

| Field | Value |
|-------|-------|
| **Status** | RETAIN at PROBATION, MICRO tier |
| **Vitality** | Recalculate after sparse-event patch (Tasks 1-3 above) |
| **Review trigger** | After 4 forward NFP events (~July 2026) |
| **Promote condition** | 8 forward trades, PF > 1.1 (unchanged) |
| **Downgrade trigger** | 3 consecutive NFP events with no trade generated, OR forward PF < 0.7 after 8 trades |
| **Archive trigger** | Forward PF < 0.5 after 12 trades |

**Do NOT downgrade based on vitality 0.26 alone.** The walk-forward
stability (both halves positive) is stronger evidence than the vitality
composite for strategies with < 2 trades per month.

---

# Next Actions (Ordered)

| Priority | Action | Timeline | Owner |
|----------|--------|----------|-------|
| **1** | Add Treasury-Rolldown-Carry-Spread to forward runner (MICRO, monthly rebalance) | This week | Claude automation |
| **2** | Run Family 42 Path A (MGC long-only re-test via `batch_first_pass`) | This week | Claude automation |
| **3** | Patch vitality monitor: add `event_cadence`, update weights for sparse events, re-run classification | This week | Claude automation |
| **4** | Apply Path A hard gate: ADVANCE → validation, or STAY SALVAGE → evaluate decomposition case | After Path A completes | Human review |
| **5** | If Path A SALVAGE + decomposition compelling: scope Path B (Databento front/back, ~$50-100) | Next data cycle | Human approval |
| **6** | June 1 checkpoint: Treasury-Rolldown vs MomIgn displacement decision | June 1, 2026 | Human review |

---

*Filed: `research/briefs/carry_sleeve_implementation_brief_20260320.md`*
*Registry impact: Family 45 → forward runner entry. Vitality monitor patch queued.*
*Next review: Week 8 formal probation review*
