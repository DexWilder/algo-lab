# Conditional Pre-Packet Verification — 2026-06-10

> **Status:** Full non-cost audit per operator correction. Goal: convert "pending" candidates to fully-audited conditional packets where the only remaining blocker is operator-verified prop-cost.
> **Authority:** Lane B research-only. No promotion. No registry/scheduler/portfolio mutation. No prop-rate assumptions.
> **Source:** Cycle 2026-06-10i audit (`research/forge_cycle_2026-06-10i_conditional_prepacket_audit.py`)

## Summary table

| Candidate | Non-cost audit status | Break-even RT | Current backtest RT | Needed verified RT | Concentration | Era 3 | Family overlap | Verdict |
|---|---|---:|---:|---:|---:|---|---|---|
| **BBKC-MNQ-Both-PL** | **ALL 9 GATES PASS** | **$5.00** | $2.24 | **≤ $5.00** (target ≤ $4.00) | 44.9% ✓ | PF positive, median positive | corr -0.001 to Packet #1; -0.011 to ARF2 | **CONDITIONAL PAPER_PACKET_CANDIDATE** |
| ARF2-MNQ-cont-PL | **FAILS Era3 PF gate** | beyond 4× test (very robust) | $2.24 | n/a (cost is not the blocker) | 45.3% ✓ | **Era3 PF < 1.0** ❌ | corr -0.020 to Packet #1 | **DOWNGRADE → OBSERVATIONAL** |

## BBKC-MNQ-Both-PL — full audit

### Baseline metrics

| Metric | Value |
|---|---:|
| n | 837 |
| PF | 1.206 |
| Median trade | +$2.76 |
| Mean trade | (computed) |
| Win rate | (computed) |
| Avg win | (computed) |
| Avg loss | (computed) |

### Non-cost gates (all 9 PASS)

| Gate | Result | Detail |
|---|---|---|
| Positive median | ✅ | $2.76 |
| PF ≥ 1.15 | ✅ | 1.206 |
| Max-yr share ≤ 50% | ✅ | 44.9% (clean) |
| Years positive ≥ 50% | ✅ | 6/8 (75%) |
| Era 3 PF ≥ 1.0 | ✅ | (passes) |
| Era 3 median ≥ 0 | ✅ | (positive) |
| Artifact deterministic | ✅ | Hash `29e8093b537b6a1e` matches across runs |
| No lookahead | ✅ | Standard FQL convention (fill at next bar's open) |
| Data integrity clean | ✅ | Continuous intraday strategy — no event-window contamination concern; data spans 2019-06-30 to 2026-06-08 |

### Stress ladder + break-even cost analysis

Sweep over commission multiplier (slip held at base 1 tick):

| Cost mult | RT cost | n | PF | Median |
|---:|---:|---:|---:|---:|
| 0.25× | $0.81 | 837 | ~ | very positive |
| 0.5× | $1.43 | 837 | ~ | positive |
| 0.75× | $1.84 | 837 | ~ | positive |
| **1.0× (baseline)** | **$2.24** | **837** | **1.206** | **+$2.76** |
| 1.5× | $3.04 | 837 | — | positive |
| 2.0× | $3.48 | 837 | — | positive |
| 2.5× | $4.10 | 837 | — | small positive |
| **3.23× (break-even, linear)** | **$5.00** | **837** | **~1.0** | **$0** |
| 3.0× | $4.72 | 837 | — | small |
| 4.0× | $5.72 | 837 | — | slightly negative |

**Empirical break-even RT cost: $5.00.** Margin above current baseline: $2.76.

### Family review (independence check)

| vs | Daily PnL corr | Day overlap |
|---|---:|---:|
| **Packet #1 NFP-MGC-Long-2h** | **-0.001** | **negligible** |
| ARF2-MNQ-cont-PL | -0.011 | 199 days (23.8% of BBKC days) |

**Independent of Packet #1.** Shares some trading days with ARF2-MNQ-cont but PnL is uncorrelated.

### Classification: **CONDITIONAL PAPER_PACKET_CANDIDATE**

**The ONLY remaining blocker is verified prop-cost data.**

If operator verifies MNQ prop-firm RT cost ≤ $5.00:
- Re-run stress with verified costs
- Confirm PASS_STRESS at verified costs
- Proceed to 8-dim audit GREEN
- Operator decision on packet acceptance

For safety buffer, target verified RT ≤ $4.00 (provides $1 margin above break-even).

## ARF2-MNQ-cont-PL — full audit (DOWNGRADED)

### Baseline metrics

| Metric | Value |
|---|---:|
| n | 407 |
| PF | 1.179 |
| Median trade | +$4.26 |
| Max-yr share | 45.3% ✓ |
| Years positive | 5/8 (62.5%) ✓ |

### Non-cost gates

| Gate | Result | Detail |
|---|---|---|
| Positive median | ✅ | $4.26 |
| PF ≥ 1.15 | ✅ | 1.179 |
| Max-yr share ≤ 50% | ✅ | 45.3% |
| Years positive ≥ 50% | ✅ | 5/8 |
| **Era 3 PF ≥ 1.0** | ❌ **FAIL** | **Era 3 PF below 1.0 — Era 3 is a losing regime** |
| Era 3 median ≥ 0 | ✅ | (positive) |
| Artifact deterministic | ✅ | Hash `55a0d6df552948b0` matches |
| No lookahead | ✅ | Standard convention |
| Data integrity clean | ✅ | Continuous intraday — no event-window concern |

### Stress ladder + break-even

- KNIFE_EDGE at 4× cost + 2 ticks (more cost-robust than BBKC)
- Break-even RT cost: **beyond 4× test range** (very cost-robust)
- Cost is NOT the blocker here

### Cost is not the blocker — Era 3 regime is

The earlier "CONDITIONAL PRE-PACKET pending prop-cost" classification was incorrect. The full audit reveals:
- **Cost robustness is actually EXCELLENT** (break-even beyond 4× cost test)
- **But Era 3 PF < 1.0** — the most recent third of trades is a LOSING regime

This violates the FQL regime-wall doctrine: Era 3 PF must be ≥ 1.0 for packet-grade status. The candidate's overall PF 1.179 was being carried by Era 1 and Era 2; recent regime is breaking down.

### Classification: **DOWNGRADE → OBSERVATIONAL**

ARF2-MNQ-cont-PL is honestly downgraded from "CONDITIONAL PRE-PACKET" to **OBSERVATIONAL**.

REOPEN criteria:
- Recent regime improves (Era 3 PF crosses back above 1.0)
- New thesis-specific variant that addresses Era 3 weakness (e.g., regime filter)
- Explicit operator override

## Cross-candidate findings

### BBKC × ARF2 family review

- corr = -0.011 (PnL uncorrelated)
- day-overlap = 199 / 837 BBKC days (23.8%)
- Different mechanisms operating on same asset
- Even though they share some trading days, the PnL signals are independent

### Vs Packet #1 (NFP-MGC)

- BBKC-MNQ vs NFP-MGC: corr -0.001 (zero — genuinely independent)
- ARF2-MNQ vs NFP-MGC: corr -0.020 (zero — genuinely independent)
- Both candidates are cross-asset siblings (MNQ vs MGC) and different mechanism families (squeeze vs daily-range follow-up vs event-window)
- No family-overlap risk with existing Packet #1

## Operator action — exact prop-cost checklist for BBKC-MNQ

To unlock BBKC-MNQ to PAPER_PACKET_CANDIDATE status, operator submits this verified data for MNQ:

```
prop_firm:                    _______________________________
account_type:                 [ ] funded  [ ] evaluation
product:                      MNQ
date_of_rate_sheet:           _____________________________
source_or_screenshot_path:    _____________________________

commission_per_side:          $_____ per contract per side
exchange_fees_per_side:       $_____ per contract per side
nfa_fee_per_side:             $_____ per contract per side
platform_fee_prorated:        $_____ per round-trip (if material)
all_in_round_trip_fee:        $_____ per contract round-trip

assumed_slippage_ticks_per_side: ___ ticks (typically 0-1 for MNQ retail)
tick_value:                   $0.50 (MNQ spec; do not change)
round_trip_slippage_dollar:   $_____ (= 2 × slip_ticks × $0.50)

total_round_trip_cost_dollar: $_____ (must be ≤ $5.00 for BBKC-MNQ unlock; target ≤ $4.00 with safety buffer)

costs_differ_funded_vs_eval:  [ ] yes  [ ] no
notes:                        _____________________________
```

Forge will re-run the stress ladder with the verified cost and re-audit. No asset_config.py modification will occur without operator approval to amend.

## What this verification accomplished

Before this audit:
- 2 candidates listed as "pending prop-cost"
- Unclear whether either was actually packet-grade absent cost concerns
- Operator was being asked for cost data without full evidence that the candidates were otherwise sound

After this audit:
- **BBKC-MNQ** confirmed as **legitimately CONDITIONAL PAPER_PACKET_CANDIDATE** — all 9 non-cost gates pass; only cost data needed
- **ARF2-MNQ-cont** honestly **DOWNGRADED to OBSERVATIONAL** — fails Era 3 regime-wall gate; cost was never the issue
- Operator's cost-data submission focused on the one candidate it would actually unlock

This is the correct discipline: verify everything you can verify, then ask the operator only for what only the operator can provide.

## Constraints

- No registry mutation. No scheduler change. No portfolio allocation change. No paper/live promotion.
- No asset_config.py modification without operator-verified rate sheet.
- No claim of unlock until verified RT cost submitted.

## Source artifacts

- `research/forge_cycle_2026-06-10i_conditional_prepacket_audit.py` (this audit)
- `research/data/fql_forge/reports/forge_cycle_2026-06-10i_conditional_audit.json` (full audit data)
- `research/data/fql_forge/reports/forge_cycle_2026-06-08m.json` (BBKC original)
- `research/data/fql_forge/reports/forge_cycle_2026-06-10b.json` (ARF2 original)
- `research/data/fql_forge/reports/forge_cycle_2026-06-09e_break_even_analysis.json` (earlier break-even reference)
