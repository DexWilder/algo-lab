# Incumbent Action Reviews — 2026-03-18

*Research outputs for four queued portfolio actions.*

---

## 1. FXBreak-6J-Short-London: Carry Filter Research

### Question
Does applying a formal carry_lookup filter meaningfully improve FXBreak-6J?

### Comparison

| Variant | Trades | PF | WR | PnL |
|---------|--------|-----|-----|------|
| **Baseline (both directions)** | 125 | 1.47 | 55% | +$3,638 |
| **Carry-filtered (short-only)** | 59 | 1.49 | 61% | +$1,662 |
| Long side alone | 76 | 1.20 | 50% | +$1,125 |
| Short side alone | 59 | 1.49 | 61% | +$1,662 |

### Findings

1. Carry filter raises PF marginally (1.47 → 1.49) but **halves trade count**
   (125 → 59) and **reduces total PnL by 54%** ($3,638 → $1,662).
2. The long side IS profitable (PF 1.20). Removing it discards real edge.
3. 6J carry has been negative for **100% of the data period** (2024-2026).
   We cannot test carry-positive behavior. The comparison is inherently
   one-sided.
4. Short-only year-by-year is more volatile (2024: PF 0.66, 2025: PF 3.69).
   Both-directions smooths the equity curve.

### Verdict

**Do NOT apply binary carry filter.** The cost (half the trades, half the
PnL) exceeds the benefit (2bp PF improvement). The carry direction is
correct in principle but the available data can't validate a carry-flip
scenario. FXBreak's raw edge (PF 1.47, 125 trades, 55% WR) is actually
solid — the strategy's real constraint is 2-year data depth, not carry
alignment.

**Rubric impact:** FXBreak stays at 17/24 (MARGINAL+). The carry filter
does not lift it to STRONG as originally hoped.

**Post-probation option:** If 6J data extends to cover a carry-positive
period (BOJ rates above Fed), revisit the filter with regime diversity.

---

## 2. Donchian-MNQ-Long-GRINDING: Archive Review

### Question
Should Donchian-MNQ be archived given NoiseBoundary-MNQ's existence?

### Head-to-Head

| Metric | Donchian-MNQ | NoiseBoundary-MNQ | Winner |
|--------|-------------|-------------------|--------|
| PF | 1.60 | 1.28 | Donchian |
| Trades (6yr) | 47 | 609 | **NoiseBoundary** (13x more) |
| Validation score | 5.0 | **10.0 (PERFECT)** | **NoiseBoundary** |
| WF stability | Adequate | **10/10 PERFECT** | **NoiseBoundary** |
| Param stability | 100% | 100% | Tie |
| Activation score | 0.64 | 0.58 | Donchian (marginal) |
| Cross-asset | MNQ only | MES + MYM confirmed | **NoiseBoundary** |
| Academic source | None | Zarattini/Aziz/Barbon 2024 | **NoiseBoundary** |
| Correlation | — | 0.374 (with Donchian) | Redundant pair |
| Genome cluster | trend_persistence | volatility_expansion | Different clusters |
| Kill flag | None | redundancy (keep NB) | NoiseBoundary favored |

### Analysis

Donchian has the higher PF (1.60 vs 1.28) but on a fraction of the trades
(47 vs 609). NoiseBoundary wins on every robustness metric: walk-forward
(PERFECT vs adequate), cross-asset validation (3 assets vs 1), academic
backing, and statistical significance (609 trades provides far more
confidence than 47).

The kill_details field explicitly states: "NoiseBoundary is stronger —
keep this, archive Donchian."

The correlation of 0.374 confirms these are effectively the same bet.
Running both is paying double attention cost for correlated returns.

### Verdict

**RECOMMEND ARCHIVE.** Donchian-MNQ-Long-GRINDING is the inferior
representative of the MNQ-long-breakout family. Archiving it:
- Frees 1 probation slot (currently 9, cap is 8)
- Removes a redundancy kill flag from the portfolio
- Reduces MNQ concentration (from 4 to 3 strategies)
- Reduces morning session concentration

**No counter-evidence found.** The higher PF on 47 trades is not
statistically meaningful enough to override NoiseBoundary's 10/10 WF
on 609 trades.

---

## 3. RangeExpansion-MCL: Decay Review

### Question
Is RangeExpansion's edge actively dying, and should it be archived?

### Decay Evidence

| Window | Sharpe | Trend |
|--------|--------|-------|
| Full 6-year | 2.39 | — |
| Trailing 1-year | 0.46 | -81% from full |
| Trailing 6-month | **-0.13** | Negative — edge is gone |

### Additional Context

- **WF 10/10 PERFECT** — the edge was real historically
- **PF 1.46, 214 trades** — strong base metrics
- **100% param stability** — not parameter-sensitive
- **Kill flag: decay** — half-life monitor flagged ARCHIVE_CANDIDATE
- **Activation score: 0.485** — below the 0.50 neutral line
- **Controller action: PROBATION** — not promoted to active
- **Asset: MCL** — first and only energy strategy

### Analysis

This is a textbook decay scenario. The strategy had a genuine edge
(documented by WF 10/10 and high Sharpe) that has degraded to
negative performance over the most recent 6 months. The decay is
monotonic (2.39 → 0.46 → -0.13) — not choppy but steadily declining.

Possible causes:
- MCL market microstructure changed (crude vol regime shifted)
- The range-expansion pattern became crowded or arbitraged
- COVID and 2022 energy crises were the edge, not the normal state

The MCL energy slot is valuable (fills an asset gap), but this strategy
is no longer earning it. Keeping a decaying strategy in a valuable slot
is the opposite of elite standard.

### Verdict

**RECOMMEND IMMEDIATE DOWNGRADE to status=testing, controller_action=OFF.**

Do NOT archive permanently yet — the WF 10/10 and the MCL slot value
justify one more check. Set a hard deadline: if trailing 3-month Sharpe
remains negative at next monthly review, archive permanently. If it
recovers above 0.5, reassess.

This frees the MCL slot for a different energy candidate if one emerges
from the catalog (e.g., Commodity-TermStructure-Carry on MCL, or a
future energy-native strategy).

---

## 4. VWAP-MNQ-Long: Session Restriction Research (Queued)

### Scope (Not Executed Yet — Queued Behind FXBreak)

The hypothesis: VWAP-MNQ-Long's afternoon session shows ALARM-level
degradation (7 trades, 14.3% WR, -$41 avg PnL) while the morning
session may still be healthy. Restricting to morning-only could save
the strategy.

### What the Research Would Test

1. Split VWAP-MNQ trades by session (morning vs midday vs afternoon)
2. Compare PF, WR, and PnL per session
3. If morning is STRONG and afternoon is WEAK, the session restriction
   is justified
4. If morning is also degraded, VWAP-MNQ should be replaced by
   NoiseBoundary as the MNQ-long workhorse

### Current Status

**QUEUED.** Will execute after the Donchian archive and RangeExpansion
downgrade decisions are made, since those affect the portfolio composition
that VWAP-MNQ session analysis depends on.

---

## Summary of Recommendations

| # | Strategy | Action | Urgency |
|---|----------|--------|---------|
| 1 | FXBreak-6J | **No carry filter.** Keep as-is. Raw edge is solid. | Complete — no action needed |
| 2 | Donchian-MNQ | **Archive.** NoiseBoundary supersedes on every robustness metric. | Ready for approval |
| 3 | RangeExpansion-MCL | **Immediate downgrade** to testing/OFF. Hard deadline for archive. | Urgent — active decay |
| 4 | VWAP-MNQ | **Queued** — session restriction research pending. | After #2 and #3 |
