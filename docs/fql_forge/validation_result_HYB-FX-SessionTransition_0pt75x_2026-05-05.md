# Validation Result — HYB-FX-SessionTransition-ImpulseGated @ 0.75× threshold (2026-05-05)

**Filed:** 2026-05-05 (third and final calibration run for this candidate)
**Plan:** `docs/fql_forge/_DRAFT_validation_plan_HYB-FX-SessionTransition.md` + 1.0× and 0.75× one-parameter follow-ups
**Authority:** T1 Lane B / Forge — no Lane A surfaces touched
**Verdict:** **FAIL** (Run B PF 0.952 < 1.0; per operator decision tree → retire this salvage thread)

---

## 4-way comparison (the full calibration sequence)

| Metric | A: baseline (no filter) | B: 1.5× | B: 1.0× | B: **0.75×** |
|---|---:|---:|---:|---:|
| n_trades | 179 | 12 | 24 | **33** ← finally hits 30 minimum |
| Net PnL | $175 | $62.50 | $200 | **-$62.50** |
| **PF** | 1.030 | 1.139 | **1.308** ★ peak | **0.952** ↓ below 1.0 |
| Median trade | $6.25 | $21.88 | $21.88 | $12.50 |
| Win rate | 50.3% | 58.3% | **62.5%** ★ peak | 54.5% |
| Max DD ($) | -$1,625 | -$400 | -$425 | -$606 |
| Sharpe (annualized) | 0.056 | 0.073 | **0.206** ★ peak | -0.040 |
| Max single-instance % | 3.8% | 24.7% | 15.8% | 12.7% (best filter level) |

---

## What the calibration sequence revealed

The donor `impulse_threshold` IS portable across rates and FX session-transition contexts (proven by 1.0× quality improvement over baseline) — but its **optimal calibration band on 6J is narrow**: somewhere between 0.85× and 1.0×.

**The trend across thresholds:**
- 1.5× → 1.0× : sample DOUBLES, PF improves 1.139 → 1.308 (loosening helps — was over-tightened)
- 1.0× → 0.75× : sample grows 24 → 33 (finally hits minimum), but PF collapses 1.308 → 0.952 (loosening too far admits unprofitable trades)

The "loosen-improves" relationship is non-monotonic. The donor has a sweet spot, and that sweet spot for 6J is in the 1.0× neighborhood — which produced 24 trades, just below the 30-trade minimum sample bar.

**The honest tension:**
- 1.0× had the best quality metrics (PF 1.308, Sharpe 0.206) but failed sample size (24 < 30)
- 0.75× had sample size (33 ≥ 30) but failed quality (PF 0.952 < 1.0)
- A finer calibration test (e.g., 0.85× or 0.9×) MIGHT find both — but that starts to look like optimization sprawl per the operator's decision tree

---

## Verdict per operator decision tree

The operator's tree from 2026-05-05:
> "PASS: candidate becomes operator-review eligible for registry relationship fields.
> WARN positive: consider one final bounded calibration or extend sample only if justified.
> **FAIL: retire this salvage thread and move to the next hybrid.**
> INCONCLUSIVE: document why, then pick the next highest-leverage Forge action."

At 0.75× the verdict is strict FAIL (PF < 1.0). Per the rule: **retire this salvage thread**.

This does NOT mean the salvaged `session_transition_entry_concept` is permanently retired. It means:
- This specific hybrid recipe (FXBreak salvage + impulse_threshold filter on 6J) is shelved at this calibration cycle
- The donor `session_transition_entry_concept` could re-emerge in a future hybrid with a DIFFERENT filter component (volume confirmation, ATR floor, regime gate, etc.)
- The donor `impulse_threshold` could re-emerge on a DIFFERENT asset (6E/6B may have wider optimal calibration bands)
- The portability evidence already saved to memory (`project_donor_portability_evidence.md`) preserves the calibration learning

---

## Item 2 cross-pollination criterion impact

**No movement.** The criterion remains at 0/2. The salvage path was exercised three times today (1.5×, 1.0×, 0.75×) but no formal PASS achieved. Item 2's day-14 gate verdict of "DO NOT ACTIVATE" stands.

The next opportunity to move the criterion is via a different salvage-based candidate from the catalog (Candidate 4 below).

---

## Donor catalog updates

| Donor | Status after today's 3 runs | Catalog note |
|---|---|---|
| `session_transition_entry_concept` (FXBreak-6J salvage) | uncertain × 3 (1 sample-fail, 1 sample-fail-quality-up, 1 quality-fail-sample-up) | Re-eligible for future hybrids with different filter pairings; not retired permanently |
| `impulse_threshold` (ZN-Afternoon validated at 1.5×) | portable mechanism; 6J optimal band 0.85-1.0× (narrower than ZN's apparent 1.5×) | Catalog should record per-context calibration bands, not single threshold values |

---

## Next safe hot-lane action (immediately, per new operating rule)

**Operator rule (locked 2026-05-05):** "Standing by is no longer the default for Lane B. Default = run next safe Forge action, then surface next queue item."

**My pick: HYB-CashClose-Salvage-RatesWindow (Candidate 4 from `hybrid_candidates_2026-05-05.md`).**

Rationale:
1. **Uses the salvage path again** (Template #5 = parent + salvaged failed-parent component) — second attempt to populate `relationships.salvaged_from` and move Item 2's cross-pollination criterion. After three uncertain HYB-FX runs, a second salvage candidate gives us a real second data point.
2. **Targets STRUCTURAL session-transition (rates)** — different gap than FX, complementary to the abandoned HYB-FX work; rates-afternoon is where ZN-Afternoon already validates the impulse filter, so the calibration question doesn't repeat (same context).
3. **Conceptually simpler test setup** — A/B against ZN-Afternoon baseline at a different time window (cash-close 14:45-15:00 vs existing 13:45-14:00). Two components only (vs HYB-FX's 2; vs Candidate 2/3's 3 components). Cheap to validate.
4. **Reuses validated proven trio infrastructure** — the validation harness already proven works on ZN data; today's two scratch scripts give a pattern.

Alternative options surfaced for operator override:
| Option | Argument | Why my pick beat it |
|---|---|---|
| Candidate 2: XB-VWAP-EMA-Ladder (sister workhorse) | Tests proven-donor entry-substitutability — load-bearing question for Phase 0 | Higher-cost test (3 components, full XB-ORB infrastructure rerun); doesn't move Item 2 cross-pollination |
| Candidate 3: HYB-LunchComp-RatesAfternoon | Salvage path + 3-component combination | Higher complexity; 3 components at Phase 0 §3.3 max |
| Re-run HYB-FX at 0.85× or 0.9× as final calibration | Could find the sweet spot | Operator decision tree says FAIL → retire, not "iterate one more"; honoring that rule |

---

## Files

- Plan: `docs/fql_forge/_DRAFT_validation_plan_HYB-FX-SessionTransition.md`
- Scratch script: `research/scratch/validate_HYB_FX_session_transition.py` (now at 0.75× threshold; see comments for calibration sequence)
- Memos in chronological order:
  - 1.5× original: `docs/fql_forge/validation_result_HYB-FX-SessionTransition_2026-05-05.md`
  - 1.0× follow-up: `docs/fql_forge/validation_result_HYB-FX-SessionTransition_1pt0x_2026-05-05.md`
  - 0.75× retirement: `docs/fql_forge/validation_result_HYB-FX-SessionTransition_0pt75x_2026-05-05.md` (this file)

---

*Filed 2026-05-05. Lane B / Forge work. No Lane A surfaces touched. Per operator decision tree: HYB-FX salvage thread retired at this calibration cycle. Next safe hot-lane action: HYB-CashClose-Salvage-RatesWindow (operator confirms scope before execution).*
