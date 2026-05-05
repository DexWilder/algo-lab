# DRAFT — Validation Plan: HYB-VolMan-Workhorse-SizingOverlay

**Status:** Draft / pre-execution test spec. Staged 2026-05-05 per operator's selection of this candidate as the second cheap-validation run. **No backtest executed today.** This document specifies the test; the actual run waits for operator authorization.

**Authority:** T1 Lane B / Forge work. No Lane A surfaces touched at execution time. No registry append; no controller / runner changes.

**Companion to:** `docs/fql_forge/hybrid_candidates_2026-05-05.md` Candidate 5; `_DRAFT_validation_plan_HYB-FX-SessionTransition.md` (Candidate 1, runs first).

---

## 1. Hypothesis under test

**Primary:** Layering VolManaged-EquityIndex-Futures' validated `inverse_vol_sizing` overlay onto XB-ORB-EMA-Ladder-MNQ's existing trade signals reduces PnL variance and max drawdown without degrading median trade by more than 10%.

**Secondary:** A validated sizing component is portable across strategies — `inverse_vol_sizing` was validated standalone on VolManaged; this tests whether it composes onto a different parent strategy.

**Operational secondary:** The overlay improves prop-sim pass rate (max DD survival, daily loss limit survival) at the same expected return.

**Null:** The sizing overlay has no material effect on Sharpe / max DD when median trade is preserved (i.e., it just rescales notional with no meaningful risk-adjusted improvement).

---

## 2. Strict scope (per operator: "compare baseline vs overlay using identical trade signals")

**In-scope:**
- Asset: **MNQ only**.
- Parent: XB-ORB-EMA-Ladder-MNQ (the canonical XB-ORB workhorse, validated probation strategy).
- Comparison: A/B — same entry/exit signals; baseline uses fixed 1-contract sizing; overlay applies `inverse_vol_sizing` to compute contract count per trade.
- Identical trade signals: the overlay does NOT affect entry/exit decisions. It only changes the position size at each entry. This isolates the sizing question.
- Cost/slippage: realistic transaction costs included; per-contract fee scales with contract count.
- Window: full XB-ORB-EMA-Ladder-MNQ backtest history (per existing `xb_orb_*_sweep_results.json`, ~6 years × ~250 days).
- Prop-sim layer: simulate prop firm rules (e.g., FTMO-style: max 5% account DD, daily loss limit 2.5%, profit target 8%) on both runs; report pass/fail rate.

**Out-of-scope (explicit):**
- Cross-asset (MCL, MYM) — defer to deeper validation if MNQ passes
- Parameter sweeps on the inverse-vol sizing formula
- Modifying entry/exit logic
- Any change to live XB-ORB runner / controller / portfolio composition
- Registry mutation
- Promotion decisions

---

## 3. Components used (full traceability)

| Field | Value |
|---|---|
| `strategy_id` (proposed) | `HYB-XB-ORB-EMA-Ladder-MNQ-VolMan` (parent + sizing-overlay variant) |
| `parent_family` | `crossbreed_breakout` (same as XB-ORB family) |
| `factor` | STRUCTURAL (same as parent) + VOLATILITY (overlay contribution) |
| `entry_logic` | `orb_breakout` (proven_donor — UNCHANGED from parent) |
| `exit_logic` | `profit_ladder` (proven_donor — UNCHANGED from parent) |
| `filters_gates` | `ema_slope` (proven_donor filter — UNCHANGED from parent) |
| `sizing_overlay` | `inverse_vol_sizing` (validated from VolManaged-EquityIndex-Futures) — **NEW** |
| `target_asset` | MNQ |
| `target_session` | morning (US, same as XB-ORB-EMA-Ladder-MNQ) |
| `relationships.components_used` | `["orb_breakout", "ema_slope", "profit_ladder", "inverse_vol_sizing"]` |
| `relationships.parent` | `XB-ORB-EMA-Ladder-MNQ` (probation — providing entire entry/filter/exit assembly) |
| `relationships.salvaged_from` | `null` (no salvaged failed-parent component in this hybrid) |
| `rationale_for_combination` | The XB-ORB workhorse has positive median trade but PnL variance scales with notional. Inverse-vol sizing was validated standalone on VolManaged (different strategy, different asset). Compose it onto the workhorse to test sizing portability and risk-normalize the existing edge. |
| `expected_portfolio_role` | Risk-normalized variant of the existing XB-ORB-EMA-Ladder-MNQ workhorse; does not displace the original — they could coexist as paired strategies (one un-sized, one sized) for comparison |
| `cheap_test_path` | workhorse archetype (≥500 trades over window) — uses same archetype path as parent |

---

## 4. Test methodology

### 4.1 Step 1 — Reconstruct XB-ORB-EMA-Ladder-MNQ baseline trade list

Pull (or recompute) the complete trade list from XB-ORB-EMA-Ladder-MNQ's existing backtest:
- Source: `research/data/xb_orb_*_sweep_results.json` OR re-run `strategies/xb_orb_ema_ladder/strategy.py` directly
- Each trade row: entry_date, entry_time, entry_price, exit_date, exit_time, exit_price, side
- Confirm trade count matches the registry's `trades_6yr` field for XB-ORB-EMA-Ladder-MNQ (~1183 per CLAUDE.md)
- **Pass:** trade count and aggregate PF reproduce within ±2% of registry baseline
- **Fail:** baseline diverges → halt; the trade-list extraction has drifted; report and stop

### 4.2 Step 2 — Compute baseline run (A) PnL with fixed 1-contract sizing

For each trade in the baseline list:
- PnL = (exit_price - entry_price) × side × tick_value × 1 contract (the existing baseline)
- Apply realistic per-contract fees and 1-tick slippage
- Aggregate: cumulative equity curve, per-trade PnL distribution, max DD, Sharpe, etc.

This should reproduce the existing XB-ORB-MNQ backtest results.

### 4.3 Step 3 — Compute overlay run (B) PnL with inverse-vol sizing

For each trade in the SAME baseline list:
- At entry time, compute realized volatility (e.g., 20-day ATR on MNQ daily bars at trade date)
- Compute contract count = max(1, round(target_dollar_vol / (ATR × tick_value)))
  - Calibration: target_dollar_vol set so the overall notional exposure roughly matches baseline (e.g., scale so average contract count ≈ 1 over the window)
  - Cap at reasonable max (e.g., 3 contracts) to avoid runaway sizing in unusually-low-vol periods
- PnL = (exit_price - entry_price) × side × tick_value × contract_count
- Apply per-contract fees scaled with contract count, same slippage assumption
- Aggregate same metrics as Run A

### 4.4 Step 4 — Metrics to compute (per run, then comparative)

| Metric | Definition | Compare A vs B |
|---|---|---|
| Total trades | Should be identical (same trade list) | Same; sanity check |
| Net PnL | Sum of all per-trade PnL after fees | B vs A — % delta |
| Median trade | Per-trade $ PnL, median | B should be within 10% of A |
| PF | Gross profit / gross loss | B vs A |
| Sharpe (annualized) | Mean / std of daily returns × √252 | B should improve |
| Max DD ($) | Peak-to-trough equity drop | B should be lower OR comparable |
| Max DD (%) | As % of starting capital | B should improve materially |
| Worst-day PnL | Largest single-day loss | B should improve |
| Tail loss (5th percentile of trade PnL) | 5th percentile of per-trade PnL | B should improve |
| PnL variance per trade | std² of per-trade PnL | B should reduce |

### 4.5 Step 5 — Prop-sim layer

Simulate prop firm rules on both runs. Use FTMO-style as the canonical (operator can swap rules later if needed):
- Account size: $50,000 (representative)
- Max account DD: 5% trailing
- Max daily loss: 2.5%
- Profit target: 8%

Walk-forward simulation:
- Start each "evaluation" at month boundaries (or week boundaries — operator preference)
- Run trades forward until either profit target hit (PASS) or DD/daily loss breached (FAIL)
- Compute pass rate per run
- Compute average days-to-pass for passing runs

This isolates the prop-survivability question that operator flagged as a key portfolio-utility test.

---

## 5. Pass / Fail / Inconclusive verdicts

| Verdict | Criteria | Action |
|---|---|---|
| **PASS** | Median trade preserved (within 10% of A); Sharpe improves ≥ 15%; Max DD% reduces ≥ 10%; Prop-sim pass rate improves ≥ 5 percentage points | Sizing overlay validated as portable. Operator decides: register as new sister strategy `idea`; consider promoting alongside existing XB-ORB-EMA-Ladder-MNQ (paired live, A/B in forward); add `inverse_vol_sizing` to donor catalog as cross-validated. |
| **PASS-with-WARN** | Most criteria met but one falls short (e.g., median trade degrades 10-15%, OR Sharpe improves but DD doesn't, OR prop-sim improves only marginally) | Document. Sizing overlay has partial value; may need calibration of target_dollar_vol or max-contract-cap. Iterate before registering. |
| **FAIL** | Median trade degrades > 15% (sizing changed entry quality somehow — should not happen if step 4.3 is correctly implemented) OR Sharpe degrades OR Max DD increases | Sizing overlay does NOT compose onto this workhorse. Mark `inverse_vol_sizing` as one-attempt-failed in donor catalog (per Phase 0 §3.5). Do NOT register. |
| **INCONCLUSIVE** | Step 1 baseline reproduction fails | Halt. Trade-list extraction has drifted. Report and stop. |

---

## 6. What this test does NOT prove

- Does NOT prove the overlay works on MCL or MYM (cross-asset extension is a separate Phase 1 question)
- Does NOT prove forward-walk performance (single-window backtest, not walk-forward)
- Does NOT prove robustness across volatility regimes (no regime decomposition at this stage)
- Does NOT prove the overlay would survive after-cost in live execution (transaction costs are estimated, not measured)

A PASS earns the right to deeper validation, not registry promotion or live deployment.

---

## 7. Why this is "cheap" (compute / time budget)

Per Phase 0 §4.1 cheap-screen ceiling: ≤30s/candidate.

This test is computationally lighter than Candidate 1's because there's no entry/exit recomputation — just resizing existing trades. Steps:
- Step 1: re-run XB-ORB-MNQ backtest OR load existing trade list (~2-5s)
- Step 2: compute Run A aggregates (~1s)
- Step 3: compute Run B aggregates with sizing overlay (~2s)
- Step 4: comparative metrics (~1s)
- Step 5: prop-sim walk-forward (~5-10s for ~20 evaluation windows)

Total expected: <20s. Well within budget.

---

## 8. Donor attribution updates (Phase 0 §3.5)

| Donor | Counter +1 |
|---|---|
| `inverse_vol_sizing` (from VolManaged-EquityIndex-Futures) | `attempts` += 1; pass/fail/uncertain += 1 per verdict |
| `orb_breakout` (proven_donor) | `attempts` += 1 (already validated; this is portability cross-check) |
| `ema_slope` (proven_donor) | `attempts` += 1 |
| `profit_ladder` (proven_donor) | `attempts` += 1 |

Note: this is a 4-component hybrid (entry + filter + exit + sizing) — at the upper edge of Phase 0's 2-3 component bound per §3.3. Accepted because the sizing overlay is mechanically additive (doesn't change entry/exit/filter logic) — it's a single overlay on top of an existing 3-component assembly. Operator may choose to enforce stricter 3-component max in which case this candidate becomes Phase 1 only.

---

## 9. Pre-conditions before execution

- ☐ Operator authorizes execution
- ☐ XB-ORB-EMA-Ladder-MNQ strategy code or trade list is reproducible
- ☐ VolManaged's `inverse_vol_sizing` formula is callable (or re-implementable from CVH spec)
- ☐ Prop-sim wrapper exists OR is built at execution time (small — ~50 LOC)
- ☐ Operator confirms target_dollar_vol calibration target (default: scale so average contract count ≈ 1)

---

## 10. Output artifact (after execution)

`docs/fql_forge/validation_result_HYB-VolMan-Sizing_<date>.md` — single-page memo:
- Verdict (PASS / PASS-with-WARN / FAIL / INCONCLUSIVE)
- Baseline reproduction result
- Run A vs Run B headline metrics table
- Prop-sim comparison
- Donor attribution events recorded
- Operator decision: register as new sister strategy idea OR iterate calibration OR retire

---

## 11. What this draft is NOT

- Not a registry append
- Not an executable backtest (spec only)
- Not a runtime change (the overlay is not added to live XB-ORB-MNQ runner regardless of result)
- Not a portfolio change (XB-ORB-EMA-Ladder-MNQ continues live unchanged)

---

*Filed 2026-05-05. Lane B / Forge pre-flight. Companion plan: `_DRAFT_validation_plan_HYB-FX-SessionTransition.md`. Operator review before either runs.*
