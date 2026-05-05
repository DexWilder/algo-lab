# DRAFT — Validation Plan: HYB-FX-SessionTransition-ImpulseGated

**Status:** Draft / pre-execution test spec. Staged 2026-05-05 per operator's selection of this candidate as the first cheap-validation run. **No backtest executed today.** This document specifies the test; the actual run waits for operator authorization.

**Authority:** T1 Lane B / Forge work. No Lane A surfaces touched at execution time. No registry append until validation result is reviewed.

**Companion to:** `docs/fql_forge/hybrid_candidates_2026-05-05.md` Candidate 1.

---

## 1. Hypothesis under test

**Primary:** Adding ZN-Afternoon's validated `impulse_threshold_1.5x` filter to FXBreak-6J-Short-London's salvaged `session_transition_entry_concept` produces a strategy with positive median trade and PF ≥ 1.15 on 6J — succeeding where the unfiltered original parent failed (FXBreak-6J was rejected for failed_dual_archetype_gates).

**Secondary:** A salvaged component from a rejected parent can be combined with a validated component from a probation parent to produce viable forward edge — the first concrete proof of the donor-economy concept that Item 2's day-14 gate flagged as "plumbing exists, no traffic flowed."

**Null:** The filter does not improve the strategy's median trade or PF over the unfiltered baseline. (If null holds, the original FXBreak rejection is reaffirmed and the salvaged component should be retired from the donor catalog.)

---

## 2. Strict scope (per operator: "Keep the first validation narrow")

**In-scope:**
- Asset: **6J only** (Japanese yen micro futures). NOT 6E/6B/6A (cross-asset extension is a Phase 1 question, not a Phase 0 first-validation question).
- Session: session-transition window only (Asian range close → London handoff). Concretely: entry signal evaluated at 02:55-03:05 ET on US weekdays; positions exited at 08:00 ET (London close) or earlier on time-stop.
- Comparison: A/B — `impulse_filter=on` vs `impulse_filter=off`, identical entry logic otherwise.
- Cost/slippage: realistic transaction costs included (per-side fee + 1-tick slippage assumption — match what the existing forward runner uses).
- Window: full 6J 5m data history available in `data/processed/6J_5m.csv`.

**Out-of-scope (explicit):**
- Cross-asset extension (6E/6B/6A) — defer until 6J result is known
- Parameter sweeps on impulse threshold, time stops, or any other parameter
- Direction variation (the original was short-only — keep short-only for the comparison; long-side test is a separate question)
- Regime conditioning beyond the impulse filter (don't add ema_slope or any other filter — keep it bounded at 2 components per Phase 0 §3.3)
- Any registry mutation
- Any code added to runtime / scheduler / forward runner

---

## 3. Components used (full traceability)

Per Phase 0 §3.2 minimum-fields requirement, every hybrid spec must populate these. For this validation:

| Field | Value |
|---|---|
| `strategy_id` (proposed) | `HYB-FX-6J-SessionTransition-ImpulseGated` |
| `parent_family` | `fx_session_transition_breakout` (new — was `breakout / FXBreak-6J-Short-London`) |
| `factor` | STRUCTURAL (session-transition primary) |
| `entry_logic` | `session_transition_entry_concept` (salvaged from FXBreak-6J-Short-London) |
| `exit_logic` | Time-stop at 08:00 ET (London close) — same as original FXBreak |
| `filters_gates` | `impulse_threshold_1.5x` (validated from ZN-Afternoon-Reversion) |
| `target_asset` | 6J |
| `target_session` | `asian_range_to_london_handoff` (02:55-08:00 ET) |
| `relationships.components_used` | `["session_transition_entry_concept", "impulse_threshold_1.5x"]` |
| `relationships.parent` | `FXBreak-6J-Short-London` (rejected — providing scaffolding entry concept) |
| `relationships.salvaged_from` | `FXBreak-6J-Short-London` (the salvage parent) — **first-ever populated `relationships.salvaged_from` in registry history** |
| `rationale_for_combination` | Original FXBreak failed because it traded all session-transition signals; the impulse filter restricts to the higher-conviction subset where the breakout exceeds 1.5× 20-day median range |
| `expected_portfolio_role` | Fills FX HIGH severity gap with first viable FX strategy |
| `cheap_test_path` | tail-engine archetype (sparse session-handoff signals expected; <500 trades over 7 years) |

---

## 4. Test methodology

### 4.1 Step 1 — Reproduce original FXBreak-6J baseline (sanity)

Before A/B-ing the new hybrid, confirm that running the salvaged `session_transition_entry_concept` on 6J reproduces the rejected parent's known performance characteristics. If the baseline doesn't reproduce, the salvaged component isn't faithfully extracted and the comparison is invalid.

- Invoke the existing FXBreak-6J-Short-London strategy code (research/strategy module) on 6J 5m data, full window.
- Confirm: trade count, PF, median trade, max DD match the registry's `trades_6yr` / `profit_factor` fields for FXBreak-6J-Short-London.
- **Pass:** baseline reproduces within ±5% on PF and median trade.
- **Fail:** baseline diverges → halt validation; the extraction step has a bug; report and stop.

### 4.2 Step 2 — A/B comparison

Run two backtests on identical 6J 5m data, same window, same fee/slippage:

| Run | Entry | Filter | Exit | Direction |
|---|---|---|---|---|
| A (baseline) | session_transition_entry_concept | none | 08:00 ET time-stop | short |
| B (hybrid) | session_transition_entry_concept | impulse_threshold_1.5x | 08:00 ET time-stop | short |

The impulse threshold rule: at the entry signal time (02:55-03:05 ET window), require the move from the prior 4-hour Asian-range close to current price to exceed 1.5× the 20-day median Asian-range size. If below threshold, skip the trade.

### 4.3 Step 3 — Metrics to compute (per run)

| Metric | Definition | Pass bar (per Phase 0 §4.1 tail-engine) |
|---|---|---|
| Trade count | Total trades over window | ≥ 30 (minimum for tail-engine PF stability) |
| PF | Gross profit / gross loss | ≥ 1.15 VIABLE / ≥ 1.30 STRONG |
| Median trade | $ per trade, median | ≥ 0 |
| Max single-instance | Largest single trade % of total profit | < 35% |
| Positive-instance fraction | Wins / total trades | ≥ 60% (event-style) OR document |
| Max DD | Peak-to-trough equity drawdown | Reported, not gated at this stage |
| Trades after filter (Run B only) | Trades the filter accepted | Should be ~30-50% of Run A's count |

### 4.4 Step 4 — Comparative analysis

| Question | Pass criterion |
|---|---|
| Did the filter reduce sample size meaningfully? | Run B trade count is 30-70% of Run A's (filter is doing real work, not too aggressive nor too lax) |
| Did the filter improve PF? | Run B PF > Run A PF AND Run B PF ≥ 1.15 |
| Did the filter improve median trade? | Run B median trade > Run A median trade AND Run B ≥ 0 |
| Did the filter shift the loss distribution? | Run B max single-instance < Run A max single-instance |
| Is the result unambiguous? | Across all 4 above, Run B is at least as good on 3 of 4 AND strictly better on 2 of 4 |

---

## 5. Pass / Fail / Inconclusive verdicts

| Verdict | Criteria | Action |
|---|---|---|
| **PASS** | Step 4's "unambiguous" criterion met AND Run B trade count ≥ 30 AND Run B PF ≥ 1.15 | Hybrid candidate validated for first-pass. Operator decides: register as `idea` (Item 2 cross-pollination criterion 0 → 1 with this entry); proceed to deeper validation (cross-asset extension to 6E, longer window, regime decomposition). |
| **WARN** | Run B improves over Run A but PF stays in 1.0-1.15 range OR sample drops below 30 | Document. Salvaged component may have value but needs different filter pairing. Do NOT register. Surface as input for a different hybrid candidate (e.g., session_transition + ema_slope instead of impulse). |
| **FAIL** | Run B fails to improve over Run A on 2+ of the 4 questions, OR Run B PF < 1.0 | Salvaged component does not survive recombination with this filter. Mark `session_transition_entry_concept` donor as one-attempt-failed in donor catalog (per Phase 0 §3.5 attribution). Do NOT register. |
| **INCONCLUSIVE** | Run A baseline reproduction fails Step 1 | Halt. Bug in component extraction. Report and stop. |

---

## 6. What this test does NOT prove

- Does NOT prove cross-asset transferability (6J only). 6E/6B/6A are separate Phase 1 questions.
- Does NOT prove long-side viability (short-only, matching original FXBreak direction).
- Does NOT prove robustness to parameter changes (impulse threshold is fixed at 1.5×; sweep is out of scope).
- Does NOT prove forward-walk performance (this is single-window backtest; walk-forward is a deeper validation step).

A PASS here is necessary but NOT sufficient for hot-lane Phase 0 promotion. It earns the right to deeper validation, not registry promotion.

---

## 7. Compute / time budget

Per Phase 0 §4.1 cheap-screen ceiling: ≤30s/candidate.

This test is two backtests on a 6J 5m dataset (~7 years × ~250 days/yr × ~24 sessions × 12 5m bars × 1 asset = ~500K bars). Each backtest should run in <5s on the existing strategy infrastructure. Total expected: <15s including baseline reproduction.

If runtime exceeds 30s, either the strategy code is doing more than necessary OR the Phase 0 cheap-screen budget is too tight for this hybrid type. Surface for review.

---

## 8. Donor attribution updates (Phase 0 §3.5)

Whether the test passes or fails, attribution counters update:

| Donor | Counter +1 |
|---|---|
| `session_transition_entry_concept` (from FXBreak-6J-Short-London) | `attempts` += 1; `contributed_to_pass`, `_to_fail`, or `_uncertain` += 1 per verdict |
| `impulse_threshold_1.5x` (from ZN-Afternoon-Reversion) | same |

This is the first validation event that populates donor attribution. Item 2's component-economy infrastructure starts producing real signal here.

---

## 9. Pre-conditions before execution

Before this validation runs, all of the following must be true:

- ☐ Operator authorizes execution (lane scope expansion or Phase 0 Track A start)
- ☐ FXBreak-6J-Short-London strategy code is invocable as a function (not just as a registry record)
- ☐ ZN-Afternoon's `impulse_threshold_1.5x` is extractable as a callable filter (or re-implementable from CVH spec)
- ☐ A scratch script `research/scratch/validate_HYB_FX_session_transition.py` exists (build at execution time, NOT now)

If FXBreak-6J source code is no longer in the repo (rejected strategies sometimes get archived from `strategies/` even when the registry record remains), the salvaged-component extraction needs a Step 0 to re-implement from the registry's `rule_summary` field.

---

## 10. Output artifact (after execution)

`docs/fql_forge/validation_result_HYB-FX-SessionTransition_<date>.md` — single-page memo:
- Verdict (PASS / WARN / FAIL / INCONCLUSIVE)
- Reproduction step result (baseline PF / median trade / trade count vs registry record)
- Run A vs Run B headline metrics
- Comparative analysis table
- Donor attribution event recorded
- Operator decision: register as idea OR retire OR retest with different filter

---

## 11. What this draft is NOT

- Not a registry append (no entry created today)
- Not an executable backtest (the run happens after operator authorizes; today is spec only)
- Not a Phase 0 Track A start (Phase 0 remains gated on TRS-2026-06 clean cycle)
- Not a runtime change (the strategy doesn't enter the forward runner regardless of result; that's a later T3 promotion question)

---

*Filed 2026-05-05. Lane B / Forge pre-flight. Companion plan: `_DRAFT_validation_plan_HYB-VolMan-Sizing.md`. Operator review before execution.*
