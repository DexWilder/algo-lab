# Prop-Firm Cost Unlock Template — Operator-Fillable

> **Status:** Awaiting operator input. DO NOT fabricate numbers below.
> **Purpose:** Verify actual prop-firm execution costs for MCL, MNQ, MES against the conservative-bias backtest assumptions. If verified costs are materially lower, multiple OBSERVATIONAL candidates may unlock to PAPER_PACKET_CANDIDATE without further infrastructure investment.
> **Trigger:** Cumulative-evidence hypothesis surfaced 2026-06-08 (3 new primitives RCB/VRC/BBKC all produce thin-margin candidates that FAIL_STRESS at conservative-bias cost ladder).
> **Authority:** Lane B research; no registry mutation. Cost-change requires explicit operator verification + downstream re-classification.

## Section 1 — Operator-fillable fields

Fill one block per (prop firm × account type × product). Multiple firms welcome for comparison.

### Block A — MCL (Micro WTI Crude Oil)

```
prop_firm:                        ____________________________________
account_type:                     [ ] evaluation [ ] funded
product:                          MCL
date_of_rate_sheet:               ____________________________________
source_or_screenshot_path:        ____________________________________

commission_per_side:              $______ per contract per side
exchange_fees_per_side:           $______ per contract per side (CME MCL exchange + clearing)
nfa_fee_per_side:                 $______ per contract per side (if separately itemized)
platform_or_data_fee:             $______ per month (prorated per contract if known)
all_in_round_trip_fee:            $______ per contract round-trip (sum of above × 2)

assumed_slippage_ticks_per_side:  ___ ticks
tick_value:                       $1.00 (MCL spec; do not change)
round_trip_slippage_dollar:       $______ (= 2 × slippage_ticks × tick_value)

total_round_trip_cost_dollar:     $______ (= all_in_round_trip_fee + round_trip_slippage_dollar)

costs_differ_funded_vs_eval:      [ ] yes (specify) [ ] no
notes:                            ____________________________________
```

### Block B — MNQ (Micro E-mini Nasdaq-100)

```
prop_firm:                        ____________________________________
account_type:                     [ ] evaluation [ ] funded
product:                          MNQ
date_of_rate_sheet:               ____________________________________
source_or_screenshot_path:        ____________________________________

commission_per_side:              $______ per contract per side
exchange_fees_per_side:           $______ per contract per side
nfa_fee_per_side:                 $______ per contract per side
platform_or_data_fee:             $______ per month
all_in_round_trip_fee:            $______ per contract round-trip

assumed_slippage_ticks_per_side:  ___ ticks
tick_value:                       $0.50 (MNQ spec; do not change)
round_trip_slippage_dollar:       $______

total_round_trip_cost_dollar:     $______

costs_differ_funded_vs_eval:      [ ] yes (specify) [ ] no
notes:                            ____________________________________
```

### Block C — MES (Micro E-mini S&P 500)

```
prop_firm:                        ____________________________________
account_type:                     [ ] evaluation [ ] funded
product:                          MES
date_of_rate_sheet:               ____________________________________
source_or_screenshot_path:        ____________________________________

commission_per_side:              $______ per contract per side
exchange_fees_per_side:           $______ per contract per side
nfa_fee_per_side:                 $______ per contract per side
platform_or_data_fee:             $______ per month
all_in_round_trip_fee:            $______ per contract round-trip

assumed_slippage_ticks_per_side:  ___ ticks
tick_value:                       $1.25 (MES spec; do not change)
round_trip_slippage_dollar:       $______

total_round_trip_cost_dollar:     $______

costs_differ_funded_vs_eval:      [ ] yes (specify) [ ] no
notes:                            ____________________________________
```

## Section 2 — Current backtest assumptions (REFERENCE — do not modify)

From `engine/asset_config.py` (verified 2026-06-08):

| Asset | commission/side | slippage_ticks | tick_value | RT cost @ 1× | RT cost @ 2×+2tick |
|---|---:|---:|---:|---:|---:|
| MCL | $0.62 | 2 | $1.00 | **$5.24** | $10.48 |
| MNQ | $0.62 | 1 | $0.50 | **$2.24** | $4.24 |
| MES | $0.62 | 1 | $1.25 | **$3.74** | $6.74 |

These are the "conservative-bias" assumptions baked into all current prop-stress results. Operator-verified costs above will be compared against these benchmarks.

## Section 3 — Break-even costs for key OBSERVATIONAL candidates

For each candidate, the table shows the maximum round-trip cost at which the candidate retains a positive median trade. If operator-verified cost is **below** the break-even, the candidate is potentially packet-grade pending the standard audit.

| Candidate | Asset | n | Baseline median | Break-even RT cost | Reclassify if verified cost ≤ |
|---|---|---:|---:|---:|---:|
| MCL Short-PL (XB-ORB) | MCL | 469 | $7.76 | **$9.74** | $8.74 (with $1 safety buffer) |
| MCL Short-FR2 (XB-ORB) | MCL | 469 | $3.76 | **$7.38** | $6.50 (with $1 safety buffer) |
| RCB15-MYM-Short-PL | MYM | 126 | $8.51 | beyond 4× (very robust) | n/a — concentration blocks separately |
| BBKC-MNQ-Both-PL | MNQ | 837 | $2.76 | (FAIL_STRESS at 2× cost + 2 ticks; linear est ~$3.20-$3.50 RT) | **$3.00** (with $0.76 buffer) — would unlock if MNQ RT ≤ ~$3.00 |
| DIR-MES-ORB-Long-PL | MES | 854 | $12.51 | beyond 4× (robust standalone, but PORTFOLIO_COMPLEMENT classification due to MNQ family overlap) | n/a — family overlap |
| DIR-MES-ORB-Short-PL | MES | 393 | $28.76 | beyond 4× (very robust) | n/a — family overlap |

### Most cost-sensitive candidate

**BBKC-MNQ-Both-PL** is the highest-leverage candidate for the prop-cost unlock. It is the only candidate where actual prop costs being slightly lower than the conservative-bias backtest (MNQ baseline $2.24 RT) would cleanly flip the stress verdict. With $2.76 baseline median and break-even around $3.20-$3.50 RT, a verified prop RT of **≤ $3.00** would unlock it for packet-grade evaluation.

### Most data-dependent candidate

**MCL Short-PL** and **MCL Short-FR2** are both pending the MCL prop-cost rate sheet. The PL variant is doctrine-aligned (PL-default heuristic #91) and has the higher cost-tolerance ($9.74 break-even vs $7.38). If MCL RT is verified ≤ $8.74, MCL Short-PL becomes a strong PAPER_PACKET_CANDIDATE pending family review and 8-dim audit.

## Section 4 — Decision flow once operator returns the filled template

1. **Operator submits Block A/B/C** filled with verified rate sheet data + source/screenshot path.
2. **Forge updates** `engine/asset_config.py` ONLY after explicit operator authorization (Lane A change — requires distinct approval per FQL Evidence Law).
3. **Re-run prop-stress** with verified costs for the candidates in Section 3.
4. **Re-classify** any candidate that now PASS_STRESS with verified costs.
5. **Family-review** any newly-PASS_STRESS candidate before promotion path.
6. **8-dim evidence-integrity audit** before any Packet #2 acceptance.

## Section 5 — Constraints (no shortcuts)

- **Do NOT fabricate any numbers** in this template. If unverified, leave blank.
- **Do NOT change** `engine/asset_config.py` without operator approval and a verified source attached.
- **Do NOT promote** any candidate based on speculative cost numbers.
- **Do NOT assume** funded costs match evaluation costs without explicit operator confirmation.
- **Do NOT accept** marketing-page costs without a rate-sheet screenshot or invoice as source.

## Section 6 — Suggested rate-sheet sources

(For operator reference only — operator selects which prop firms apply)

- Apex Trader Funding (apextraderfunding.com)
- TopstepTrader (topsteptrader.com)
- Earn2Trade (earn2trade.com)
- MyFundedFutures (myfundedfutures.com)
- Leeloo Trading (leelootrading.com)
- Take Profit Trader (takeprofittrader.com)

The actual rate-sheet links and screenshots must be operator-sourced and verified; Forge will not fetch them.

## Section 7 — When this template updates

Update this document when:
- Operator submits filled Block A/B/C with verified data.
- A new prop firm or account tier becomes relevant.
- The break-even table needs refresh after new OBSERVATIONAL candidates emerge.

## Source artifacts

- `engine/asset_config.py` (current backtest cost truth)
- `docs/reports/prop_cost_verification/2026-06-08_MCL_prop_cost_verification.md` (prior MCL analysis from #85)
- `research/data/fql_forge/kill_taxonomy.json` (OBSERVATIONAL candidate evidence)
- `research/data/fql_forge/source_mining_packet_2_2026-06-08.md` (cost-fragility hypothesis)
