# Source Mining Packet 2 — 2026-06-08

> **Status:** Produced per operator directive #111 ("if no viable candidate from BB-KC, immediately produce next Source Mining Packet").
> **Trigger:** BB-Keltner squeeze first batch (cycle 08m) produced 0 PAPER_PACKET / 1 OBSERVATIONAL / 5 KILL.
> **Authority:** Lane B research-only.
> **Method:** scan kill_taxonomy + primitive inventory + insight docs + intake; exclude saturated families and prior SMP-1 candidates.

## Cumulative state as of SMP-2 generation

- 3 new primitives shipped this campaign: RCB → RESEARCH_ONLY, VRC → ARCHIVED, BBKC → RESEARCH_ONLY
- 2 active filters never previously deployed: hurst_stable_mr (deployed 08l → anti-edge with bb_reversion), bandwidth_squeeze (never deployed in any cycle)
- 1 active filter never deployed: hurst_stable_trend (NEVER deployed)
- 4 active saturated families + 1 paused crude-event family
- 1 BB-KC OBSERVATIONAL candidate (BBKC-MNQ) at sub-packet margin

## Excluded from SMP-2 (would repeat saturated/exhausted paths)

- Any non-ORB existing primitive × MCL/MGC (saturated 08c)
- Any rates/FX × existing primitive pb_pullback/bb_reversion (saturated 08d)
- Any crude × calendar-time event (paused 08f+08h)
- ORB-family directional split on any asset (5-asset diagnostic complete)
- RCB / VRC / BBKC repeats (all classified)
- bb_reversion × hurst_stable_mr (anti-edge confirmed 08l)

## SMP-2 catalog — 15 genuinely new mechanism slots

### Tier 1 — RUNNABLE_NOW (5 mechanisms, existing primitives, no new build)

| # | Mechanism | Cells | Rationale |
|---:|---|---|---|
| 1 | **donchian + hurst_stable_trend × MES** | DC × HurstTrend × PL × both | FIRST hurst_stable_trend deployment; regime-conditioned trending DC break |
| 2 | **donchian + hurst_stable_trend × MNQ** | DC × HurstTrend × PL × both | Same on MNQ; trending DC on equity workhorse-asset |
| 3 | **orb_breakout + hurst_stable_trend × MGC** | ORB × HurstTrend × PL × both | Regime-conditioned ORB on metals (filter restricts to genuine trending regimes) |
| 4 | **vol_expansion × MYM × ema_slope** | VolExp × ema_slope × PL × both | Vol_expansion never tested on MYM (was 06-04b MES/MNQ/ZN/MGC) |
| 5 | **vol_expansion × MCL × ema_slope** | VolExp × ema_slope × PL × both | Same — MCL not tested with vol_expansion |

### Tier 2 — NEEDS_PRIMITIVE (3 mechanisms, focused build investment)

| # | Mechanism | Build estimate | Expected unlock |
|---:|---|---|---|
| 6 | **gap_fill_trigger** | 2-3h: detect open-vs-prior_day_close gap > N*ATR, fade direction toward prior_day_close | 5-10 candidates across MGC/MCL/MES/MYM/MNQ |
| 7 | **stop_run_reversal** | 4-6h: detect swing-high/swing-low pivots, fire when price sweeps through then reverses | 8-12 candidates (especially on volatile assets like MNQ) |
| 8 | **opening_drive_continuation** | 3-4h: detect sustained directional move in first 30min (different from ORB), continue with momentum | 5-8 candidates equity micros |

### Tier 3 — NEEDS_DATA (3 mechanisms, data ingestion required)

| # | Mechanism | Data required | Source |
|---:|---|---|---|
| 9 | Treasury auction directional drift | TreasuryDirect auction calendar by tenor (2Y/5Y/10Y/30Y) | treasurydirect.gov; complexity moderate (multi-tenor schedule + reopens) |
| 10 | Surprise-conditioned EIA crude | EIA inventory print vs consensus expectations | eia.gov + consensus survey (Bloomberg/Reuters not in tree); revival path for paused crude event family per #101 |
| 11 | COT-shift directional regime | CFTC Commitments of Traders weekly | cftc.gov CSV; multi-step primitive build for position-z-score signals |

### Tier 4 — NEEDS_RESEARCH (4 mechanisms, theory work first)

| # | Mechanism | Theory gap |
|---:|---|---|
| 12 | Cross-asset pair MR with HL-conditioned entry | Pair primitives scaffolded but not in combinatorial engine; requires pair-aware entry implementation + cointegration validation |
| 13 | Microstructure-derived signal (volume-imbalance proxy) | Existing 5-min OHLCV insufficient for true microstructure; would need proxy formula validation |
| 14 | Carry/curve term-structure mean-reversion | Multi-asset curve features not in tree (would need cross-tenor data) |
| 15 | Implied-vol / realized-vol spread reversal | No options/IV data in tree; deep data work required |

## Recommended next action per cumulative-evidence reading

The cumulative pattern across 3 new primitives + SMP-1 + BB-KC suggests something important:

**Every productive new mechanism so far (RCB, BBKC, BBKC-MNQ specifically) produces a thin-margin candidate that fails prop-stress.** The PF range is consistently 1.1-1.5 with positive median, but the median is small ($1-$5) relative to cost-stress impact at 2× cost + 2 ticks (~$5-10 round-trip cost increase).

**Hypothesis:** The micro-futures cost structure under conservative-bias assumptions is the actual binding constraint, not mechanism finding. Real prop-firm costs (lower than conservative bias) might unlock several existing OBSERVATIONAL candidates.

This redirects attention to **DATA_REQUIRED option B from §1 prop-cost verification queue** — operator-provided prop-firm rate sheet for MCL (and other relevant assets). With verified lower costs, the existing inventory of "PASS_STRESS-FAIL on conservative bias" candidates may include actual packet candidates.

## Highest-leverage operator decision option

Three options ranked by Packet #2 emergence probability:

1. **Run SMP-2 Tier 1 (RUNNABLE_NOW) batch** — 5 candidates, cheap. Probability of Packet #2 emergence: ~10-15% (extrapolating from prior cycles).
2. **Build SMP-2 Tier 2 gap_fill_trigger** (lowest-build-cost NEEDS_PRIMITIVE) — would test a different mechanism family. Probability of Packet #2 emergence: ~15-20%.
3. **Open prop-firm cost data unlock** (operator provides rate sheet for MCL + MNQ + MES). Probability of unlocking existing OBSERVATIONAL inventory: ~30-40% IF rates are materially lower than conservative-bias backtest.

**Recommended: Option 3 — prop-cost data unlock.** Reasoning: the cost-fragility pattern across RCB, BBKC, and OBSERVATIONAL inventory is too consistent to be coincidence. Verifying actual prop costs may unlock 1-3 candidates immediately without further infrastructure investment.

## Constraints

- No registry mutation, no scheduler change, no portfolio change, no paper/live promotion.
- Lane B research-only.
- One direction per operator decision.

## Source artifacts

- `research/data/fql_forge/source_mining_catalog_2026-06-08.md` (SMP-1 catalog)
- `research/data/fql_forge/kill_taxonomy.json` (campaign trail)
- `research/crossbreeding/crossbreeding_engine.py` (primitive inventory)
- `docs/reports/prop_cost_verification/2026-06-08_MCL_prop_cost_verification.md` (existing prop-cost note)
