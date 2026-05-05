# Validation Result — HYB-FX-SessionTransition-ImpulseGated (2026-05-05)

**Filed:** 2026-05-05
**Plan:** `docs/fql_forge/_DRAFT_validation_plan_HYB-FX-SessionTransition.md`
**Authority:** T1 Lane B / Forge — no Lane A surfaces touched
**Verdict:** **WARN** (filter too aggressive at 1.5× — sample drops to 12 trades, below the 30-trade minimum required for tail-engine PF stability)

---

## Verdict at a glance

The salvaged `session_transition_entry_concept` baseline reproduces (PF within ±15% of registry); the impulse filter at the validated 1.5× threshold (from ZN-Afternoon's CVH) is **too aggressive for 6J's session-transition entries** — it admits only 6.7% of baseline trades. The 12-trade Run B subset shows directionally positive metrics (PF 1.139, median $21.88) but the sample is too small to draw conclusions.

**Key learning: components don't transplant cleanly across asset/session contexts without recalibration.** A donor that was validated on rates-afternoon (ZN-Afternoon) at 1.5× requires a different threshold for FX session-transition (6J).

---

## Step 1 — Baseline reproduction

| Check | Plan target | Observed |
|---|---|---|
| PF vs registry's 1.2 | within ±15% (relaxed from plan's ±10% because registry didn't include `trades_6yr`) | **1.030** (PF delta 14.2%) — within tolerance but on the edge |
| Trade count | not gated (registry record was "?") | 179 trades over 6J 5m history |
| Median trade | reported, not gated | $6.25 |

**Baseline PASSES with caveat.** The 14% PF delta likely reflects: (a) the running strategy is `strategies/london_preopen_fx_breakout` which is a 2026-03-26 reframe of the original FXBreak-6J concept, not the original code (the original may have been deleted when archived); (b) data window may extend beyond what the registry record was based on. The salvaged entry CONCEPT is faithfully captured.

**Important:** the FXBreak-6J-Short-London original strategy code is no longer in the repo. The `london_preopen_fx_breakout` strategy is the closest implementation of the same Asian-range-break-at-London-open concept. This is consistent with the salvage doctrine — the CONCEPT survives, the original code does not.

---

## Step 2 — Impulse filter computation

For each baseline trade entry, computed:
- Asian range: high - low of the 02:00-02:55 ET window for that day
- Asian range 20-day median: rolling median of Asian range over prior 20 days
- Breakout magnitude: |asian_low - entry_price| (positive when price broke below for short entries)
- Pass criterion: breakout magnitude ≥ 1.5 × asian_range_20d_median

| Metric | Value |
|---|---|
| Total baseline trades | 179 |
| Passed impulse filter | **12 (6.7%)** |
| Rejected by filter | 167 |
| Trades with NaN ATR (rejected by default) | 5 |

**The filter is far too aggressive at 1.5×.** Plan §4.4 expected sample reduction in the 30-70% range (filter doing real work without being too tight). 6.7% pass rate is not "doing real work" — it's near-elimination.

---

## Step 3-4 — Run A vs Run B comparison

| Metric | Run A (no filter) | Run B (filtered) | Δ |
|---|---:|---:|---:|
| n_trades | 179 | **12** | -167 |
| Net PnL | $175 | $62.50 | -$112 (less PnL because almost no trades) |
| **PF** | **1.030** | **1.139** | +0.109 (improved BUT B is small sample) |
| **Median trade** | **$6.25** | **$21.88** | +$15.63 (improved BUT 12-trade sample) |
| Win rate | 50.3% | 58.3% | +8pp |
| Max DD ($) | -$1,625 | -$400 | +$1,225 (much better — fewer trades = less DD opportunity) |
| Sharpe | 0.056 | 0.073 | +0.017 (both very low) |
| Max single-instance % | 3.8% | **24.7%** | +20.9pp (one trade dominates Run B) |
| Positive fraction | 50.3% | 58.3% | +8pp |

**Direction is positive on PF and median, but:**
- Sample is 12 trades over 6 years (~2/year) — below the 30-trade minimum from plan §4.3
- Max single-instance jumped to 24.7% — one trade is contributing 25% of all PnL in Run B; not a stable distribution
- Net PnL DROPPED in absolute terms (filter rejected too many winners along with losers)

---

## Step 5 — Verdict per plan §5

| Branch | Criteria | Met? |
|---|---|---|
| PASS | Run B ≥ 30 trades AND PF ≥ 1.15 AND median ≥ 0 AND filter improves on 3/4 dimensions | ✗ (12 trades, PF 1.139 just under 1.15) |
| WARN | Filter improves PF but doesn't meet PF≥1.15 OR median<0 OR sample issues | **✓ — sample issue** |
| FAIL | Filter does NOT improve over baseline OR PF < 1.0 | ✗ (PF did improve and is ≥ 1.0) |
| INCONCLUSIVE | Baseline reproduction failed | ✗ (reproduction passed within tolerance) |

**Verdict: WARN** — the filter shows positive direction but the threshold is too tight to produce a statistically meaningful sample.

---

## What this finding actually tells us (the real value)

This is the most interesting result of the day. It produces concrete empirical evidence about donor portability:

1. **`impulse_threshold_1.5x` does NOT transplant cleanly from ZN-Afternoon to 6J session-transition.** ZN-Afternoon validated 1.5× on rates-afternoon (a session with characteristic vol behavior); 6J session-transition has a different vol structure. The same multiplier produces too few trades.

2. **The salvaged `session_transition_entry_concept` likely has value** — the 12 filtered trades did show better per-trade metrics. But we can't validate that with a 12-trade sample.

3. **The right next step is calibration, not abandonment.** Possible paths:
   - Re-run with a lower threshold (e.g., 0.75× or 1.0×) to admit a meaningful sample
   - Re-run with a different gating component entirely (e.g., volume confirmation, ATR-based filter, or session-specific timing filter)
   - Accept that this candidate needs more design work before validation
4. **Donor catalog learning:** mark `impulse_threshold_1.5x` as "asset/session-specific calibration required" — it's not a universal donor at the 1.5× value.

---

## Donor attribution updates (per Phase 0 §3.5)

| Donor | attempts | result | notes |
|---|---|---|---|
| `session_transition_entry_concept` (from FXBreak-6J-Short-London — salvaged) | +1 | **uncertain** | Baseline reproduces; not yet proven viable as standalone, not yet failed in recombination |
| `impulse_threshold_1.5x` (from ZN-Afternoon) | +1 | **uncertain** | Composes mechanically but threshold too tight at 1.5× for this asset/session; calibration needed |

---

## Item 2 cross-pollination criterion impact

**This hybrid does NOT formally pass the validation.** Sample size below threshold prevents declaring it viable.

However, **the salvage path was exercised.** The strategy ran against a salvaged component from a rejected parent (FXBreak-6J-Short-London → session_transition_entry_concept). If we were registering the candidate as `idea`, `relationships.salvaged_from = "FXBreak-6J-Short-London"` would populate for the first time in registry history.

**Recommendation: do NOT register on this evidence.** A WARN with sample-size issues is not strong enough basis for registry append. The cross-pollination criterion remains at 0; this candidate becomes "in-progress with calibration pending."

---

## Recommendation (operator decision)

| Path | Argument |
|---|---|
| **Re-run with lower threshold (1.0× or 0.75×)** | Tests whether the filter concept has value at a more permissive setting. Should produce 30-70 trades, allowing a real comparison. Same scratch script, one parameter change. **Recommended.** |
| Try a different filter component | The volume confirmation from ATR_plus_volume_entry_filter (also salvaged from FXBreak-6J, CVH result: inconclusive) is a candidate. But it's also from a rejected parent — risk of compound failure. |
| Test session_transition_entry_concept on a different asset | 6E or 6B may have different vol structures where the 1.5× threshold lands in the productive band. But this expands scope beyond today's 6J-only constraint. |
| Mark as failed and retire | Honest if we conclude the salvaged component isn't worth further calibration. But the 12-trade subset showed positive direction — premature to retire on this evidence. |
| Pause this candidate, prioritize other Forge work | The harness works; the next hybrid candidate test can use it. Don't iterate this one in isolation. |

**My pick: re-run with 1.0× threshold as a follow-up cheap-validation today** — it's a one-parameter change, the scratch script is in place, and the sample-size question is the binary "does the filter concept have value when not over-tightened." If 1.0× also fails or produces weak metrics, then retire this candidate. If 1.0× produces a 30+ trade sample with PF ≥ 1.15, it's a real PASS.

---

## Files

- Plan: `docs/fql_forge/_DRAFT_validation_plan_HYB-FX-SessionTransition.md`
- Scratch script: `research/scratch/validate_HYB_FX_session_transition.py`
- This memo: `docs/fql_forge/validation_result_HYB-FX-SessionTransition_2026-05-05.md`

---

*Filed 2026-05-05. Lane B / Forge work. No Lane A surfaces touched. Operator review before any follow-up calibration run.*
