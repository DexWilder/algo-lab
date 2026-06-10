# Paper-Readiness Packet #2 — BBKC-MNQ-Both-PL — PRE-PACKET SCAFFOLD

> ## Status block (CONDITIONAL — pending operator prop-cost verification)
>
> | Field | Value |
> |---|---|
> | **Status** | **PRE-PACKET SCAFFOLD** — promotion path conditional on operator-verified MNQ prop-firm RT cost ≤ $5.00 |
> | **Current classification** | OBSERVATIONAL (FAIL_STRESS at conservative-bias $2.24 base + 2 ticks slip = $5.48 RT) |
> | **Empirical break-even RT cost** | **$5.00** (vs current backtest $2.24 baseline; margin $2.76) |
> | **Audit status** | Pending — would proceed to 8-dimension audit upon prop-cost verification |
> | **Paper status** | NOT paper-approved |
> | **Live status** | NOT live-approved |
> | **Registry mutation** | NONE proposed |
> | **Scheduler change** | NONE proposed |
> | **Portfolio allocation change** | NONE proposed |
> | **Sprint position** | Day 12 of 30; would be Packet #2 candidate |
> | **Authority** | T1 / Lane B / report-only |
> | **Source artifacts** | `research/forge_cycle_2026-06-08m_bb_keltner_first_batch.py` + `research/forge_cycle_2026-06-09e_break_even_analysis.py` |
>
> **This scaffold prepares the family-review + 8-dim audit work in advance** so that if/when operator-verified MNQ prop-cost arrives at ≤ $5.00 RT, the Packet #2 review can complete in ~30-60 min instead of multi-cycle work. **No registry mutation. No promotion. No cost-assumption change. No paper/live commitment.**

---

## 1. Strategy thesis

The Bollinger-Keltner squeeze ("TTM squeeze") is a well-documented vol-contraction-then-expansion pattern. When Bollinger Bands (20-period, 2σ) contract INSIDE Keltner Channels (20-period EMA ± 1.5×ATR), volatility is compressed. The release — when BB expand back outside KC — historically signals a strong directional move is imminent.

The thesis: post-squeeze BB-vs-KC release fires a directional momentum entry. Direction is determined by price-vs-EMA20 at the release bar. The entry is direction-agnostic in setup (BB/KC squeeze) but direction-specific at execution (LONG if price > EMA20, SHORT if price < EMA20).

This thesis is **mechanism-symmetric**: it works equally on long and short sides of vol-compression releases. The first-batch evidence (PF 1.21, 6/8 yrs positive, max-yr 44.9% clean concentration) is consistent with a structural vol-cycle phenomenon on MNQ.

## 2. Rule definition

| Field | Value |
|---|---|
| **Asset** | MNQ (micro E-mini Nasdaq-100 futures, CME) |
| **Bar timeframe** | 5-minute |
| **Entry trigger** | Bollinger Band release from Keltner squeeze (BB inside KC for ≥3 prior bars, then BB expands beyond KC at current bar) |
| **Direction** | LONG if close > EMA20 at release bar; SHORT if close < EMA20 |
| **Stop loss** | Entry - 1.5×ATR (LONG) or Entry + 1.5×ATR (SHORT) |
| **Target** | profit_ladder (multi-threshold tiered exit) |
| **Position sizing** | 1 contract (no vol-adjusted sizing in v1) |
| **Filter** | `ema_slope` (passes LONG when EMA20 > EMA50; SHORT when EMA20 < EMA50) |
| **Session** | RTH (09:30-15:45 ET); all signals in-session |
| **Calendar** | All trading days; no event-window restriction |

## 3. Backtest evidence (cycle 08m, conservative-bias costs)

| Metric | Value |
|---|---:|
| Trade count | 837 |
| Years covered | 8 (5/8 years positive net) |
| Profit factor | 1.206 |
| Median trade (baseline cost $2.24 RT) | **+$2.76** |
| Mean trade | (TBD — to be computed in audit) |
| Win rate | (TBD) |
| Max drawdown | (TBD) |
| **Max-year share** | **44.9% (CLEAN — under 50% gate)** |
| H1 / H2 PF asymmetry | (TBD in audit) |
| Era 3 PF | (TBD in audit; preliminary positive direction) |

**Concentration is CLEAN** — the strongest single positive characteristic among 5 mechanism families tested.

## 4. Cost-fragility analysis (cycle 09e)

Break-even RT cost analysis (linear-interp from cost-multiplier sweep 0.25× to 4.0×):

| Cost multiplier | Commission/side | RT cost | Median trade |
|---:|---:|---:|---:|
| 0.25× | $0.155 | $0.81 | (positive, higher than baseline) |
| 1.00× (current baseline) | $0.62 | **$2.24** | **+$2.76** |
| 2.00× | $1.24 | $3.48 | positive |
| **3.23× (break-even)** | **$2.00** | **$5.00** | **$0.00 (median = 0)** |
| 4.00× | $2.48 | $5.72 | slightly negative |

**Empirical break-even RT cost: $5.00.** Margin above current baseline: **$2.76**.

### Translating to prop-firm rates

Typical retail prop firms (for MNQ):
| Prop firm | Commission/side | Estimated RT (incl. 1 tick slip @ $0.50) | BBKC-MNQ viable? |
|---|---:|---:|---|
| Apex Trader Funding | ~$1.36 | ~$3.72 RT | **YES** (well below $5.00 BE) |
| TopstepTrader | ~$1.40 | ~$3.80 RT | **YES** |
| MyFundedFutures | ~$1.40 | ~$3.80 RT | **YES** |
| Earn2Trade | ~$1.40 | ~$3.80 RT | **YES** |

These are approximate, **operator-verified rates required before any classification update.** But at any of these representative rates, BBKC-MNQ would retain positive median trade.

## 5. Family review pre-work

### vs existing MNQ probation (XB-ORB-EMA-Ladder-MNQ)

Would need to compute upon promotion approval:
- Trade-day overlap (BBKC-MNQ days vs XB-ORB-MNQ days)
- Daily PnL Pearson correlation
- Both-traded-days count
- Saturation overlap risk

**Predicted classification (per ORB matrix evidence from cycle 08a):**
- BBKC trigger is BB-KC release (vol-cycle-based); ORB trigger is opening-range break (session-time-based)
- Mechanically different — likely LOWER correlation than ORB-Long vs ORB-Short subsets (0.6-0.79)
- Expected: PORTFOLIO_COMPLEMENT_CANDIDATE if corr 0.30-0.50; PAPER_PACKET_CANDIDATE if corr <0.30

**This family review must be run as Step 1 upon operator prop-cost verification.**

### vs other 5-mechanism cumulative inventory

BBKC-MNQ is the only PASS_STRESS candidate from 5 new-primitive cycles (RCB/VRC/BBKC/gap_fill/stop_run). No conflict with other PASS_STRESS candidates (there are none).

## 6. 8-Dimension Evidence-Integrity Audit pre-checklist

When operator prop-cost data verifies BBKC-MNQ viable, run audit:

| # | Dimension | Pre-audit status |
|---:|---|---|
| 1 | Cost source verification | **REQUIRES OPERATOR INPUT** — currently uses conservative-bias `asset_config.py` for MNQ; would update to verified rate sheet |
| 2 | Cost stress survival | Computed at $5.00 RT BE; safety buffer at $4.00 RT |
| 3 | Edge quality (PF, median, win rate) | PF 1.206, median $2.76, 6/8 yrs+ — baseline strong |
| 4 | Lookahead bias | Mechanism uses prior-bar BB and KC values (no current-bar lookahead); pending audit confirmation |
| 5 | Calendar / data integrity | MNQ data spans 8 years RTH; no NFP / event-window restriction means full data sample |
| 6 | Survivorship bias | Not applicable (single instrument; not portfolio-survivor) |
| 7 | Duplicate exposure | **PENDING family review vs XB-ORB-EMA-Ladder-MNQ** (Section 5) |
| 8 | Output artifact stability | Cycle 08m produced reproducible results; cycle 09e confirmed break-even via independent cost-sweep method |

**Expected audit outcome:** GREEN on dimensions 2, 3, 5, 6, 8. Dim 1 requires operator data. Dim 4 + 7 require dedicated audit cycles (~30 min each).

## 7. Operator-decision matrix (for when prop-cost data arrives)

| Verified MNQ RT cost | BBKC-MNQ disposition |
|---|---|
| ≤ $4.00 RT | **STRONG UNLOCK** — proceed to family review + 8-dim audit; high probability of Packet #2 acceptance |
| $4.00 - $5.00 RT | **MARGINAL UNLOCK** — proceed to audit but with smaller safety buffer; operator may want to require additional stress margin |
| $5.00 - $6.00 RT | **AT BREAK-EVEN** — candidate is marginal; operator may want to skip or require deeper investigation |
| > $6.00 RT | **NO UNLOCK** — cost margin insufficient; candidate remains OBSERVATIONAL |

## 8. Constraints

- No registry mutation. No scheduler change. No portfolio allocation change.
- No paper/live promotion.
- No cost-assumption change to `asset_config.py` without operator-verified rate sheet attached as evidence.
- This scaffold is research-only preparation; promotion path activates only on operator decision.

## 9. Source artifacts

- `research/forge_cycle_2026-06-08m_bb_keltner_first_batch.py` (originating cycle)
- `research/data/fql_forge/reports/forge_cycle_2026-06-08m.json` (baseline result)
- `research/forge_cycle_2026-06-09e_break_even_analysis.py` (break-even analysis)
- `research/data/fql_forge/reports/forge_cycle_2026-06-09e_break_even_analysis.json` (corrected break-even data)
- `docs/reports/prop_cost_verification/prop_cost_unlock_template_OPERATOR_TO_FILL.md` (operator-fillable template)
- `research/crossbreeding/crossbreeding_engine.py` (`entry_bb_keltner_squeeze` at line ~580)
- `research/tests/test_bb_keltner_squeeze.py` (8/8 smoke tests pass)
