# MCL Prop-Cost Verification Note

> **Status:** DATA_REQUIRED for prop-firm fields. Backtest fields verified.
> **Trigger:** Operator decision #85 (OK C). MCL Short-FR2 is REPLACEMENT_CANDIDATE_LIKELY at retail/backtest costs but FAIL_STRESS at 1.5× cost + 1 tick. Verification of actual prop-firm execution costs is required before any deployment consideration.
> **Authority:** Research-only. NO registry mutation, NO portfolio change, NO paper/live promotion.
> **Source of cost truth:** `engine/asset_config.py` (FQL Evidence Law, locked 2026-05-19).

## §1 — Current MCL backtest cost assumptions (verified)

From `engine/asset_config.py["MCL"]`:

| Field | Value | Source |
|---|---|---|
| point_value | $100.00 / point | CME MCL spec |
| tick_size | 0.01 ($1.00 / tick) | CME MCL spec |
| commission_per_side | **$0.62** | conservative-bias estimate (Piece I 2026-05-20) |
| slippage_ticks | **2** | conservative-bias for micros vs full-size CL (Piece I 2026-05-20) |

**Derived round-trip cost (backtest baseline):**

| Component | Per side | Round-trip |
|---|---:|---:|
| Commission | $0.62 | $1.24 |
| Slippage (2 ticks × $1) | $2.00 | $4.00 |
| **Total cost** | **$2.62** | **$5.24** |

## §2 — Stress ladder cost translation (already applied)

| Rung | Comm/side | Slip ticks/side | $/side | $/round-trip | Δ vs baseline |
|---|---:|---:|---:|---:|---:|
| 1× baseline | $0.62 | 2 | $2.62 | **$5.24** | — |
| 1.5× cost + 1 tick | $0.93 | 3 | $3.93 | **$7.86** | +$2.62 |
| 2× cost + 1 tick | $1.24 | 3 | $4.24 | **$8.48** | +$3.24 |
| 2× cost + 2 ticks | $1.24 | 4 | $5.24 | **$10.48** | +$5.24 |
| 4× cost + 2 ticks | $2.48 | 4 | $6.48 | **$12.96** | +$7.72 |

## §3 — Prop-firm cost scenarios (DATA_REQUIRED)

Major retail prop-firm structures known to be relevant to micro futures (Apex, TopStep, MyFundedFutures, Earn2Trade, others). Exact rates change frequently and depend on account tier + clearing arrangement. **DO NOT fabricate.**

| Field | Backtest assumption | Prop-firm actual | Status |
|---|---|---|---|
| Commission per side (per contract) | $0.62 | _TO VERIFY_ | DATA_REQUIRED |
| Exchange/clearing fees per side | (bundled) | _TO VERIFY (CME fee schedule + clearing)_ | DATA_REQUIRED |
| Platform/data fees prorated | (excluded) | _TO VERIFY (monthly/RT)_ | DATA_REQUIRED |
| Realistic round-trip slippage in ticks | 2 ticks/side | _TO VERIFY (execution venue, latency, order type)_ | DATA_REQUIRED |
| Funded-account profit split | (n/a backtest) | _TO VERIFY (often 80/20 or 90/10 after threshold)_ | DATA_REQUIRED |

### Suggested verification workflow (operator-led)

1. Pull current Apex Trader Funding fee schedule for MCL micro WTI (or whichever prop firm is the deployment target).
2. Confirm whether commission includes CME exchange + clearing or whether they are billed separately.
3. Confirm slippage assumption against any available execution sample (if a paper account has been run on the prop platform, pull average realized slippage).
4. Fill the table above. Update this note with verified figures + date stamp.
5. Re-run `prop_stress_screen` with verified prop costs as the **baseline** rather than the conservative-bias backtest.

## §4 — Decision math for MCL Short-FR2

**Question:** What round-trip cost can MCL Short-FR2 tolerate before its median trade goes negative?

From most recent stress sweep (cycle 2026-06-05c):

| Stress rung | Median trade | Round-trip cost |
|---|---:|---:|
| 1× baseline | +$3.76 | $5.24 |
| 1.5× cost + 1 tick | **-$0.86** | $7.86 |
| 2× cost + 1 tick | -$1.48 | $8.48 |

**Break-even round-trip cost ≈ between $5.24 and $7.86.**

Linear-interpolating between the two known points:
- Δcost = $2.62; Δmedian = $4.62 (from +$3.76 to -$0.86)
- Slope ≈ -$1.76 of median per +$1.00 of round-trip cost
- Break-even (median = 0) ≈ baseline + ($3.76 / $1.76) ≈ baseline + $2.14
- **Break-even round-trip ≈ $7.38** (linear estimate, near 1.5× cost + 1 tick rung)

**Minimum prop-firm round-trip cost ceiling for FR2 to remain viable:** must be **< $7.38** round-trip with realistic slippage **AND** leave a safety margin (median ≥ $1.00 buffer). Practical ceiling: **≤ $6.50 round-trip.**

**Compare to MCL Short-PL** (more cost-robust):

| Stress rung | Median trade | Round-trip cost |
|---|---:|---:|
| 1× baseline | +$7.76 | $5.24 |
| 1.5× cost + 1 tick | +$3.14 | $7.86 |
| 2× cost + 1 tick | +$2.52 | $8.48 |
| 2× cost + 2 ticks | -$1.48 | $10.48 |

PL break-even ≈ between $8.48 and $10.48 → linear estimate ≈ **$9.74** round-trip. PL tolerates ~$2.36 more round-trip cost than FR2.

## §5 — Disposition

- **MCL Short-FR2:** REPLACEMENT_CANDIDATE_LIKELY at backtest costs, **OBSERVATIONAL** until prop-firm round-trip cost is verified ≤ $6.50.
- **MCL Short-PL:** PARALLEL directional insight, **OBSERVATIONAL**, more cost-robust (break-even ≈ $9.74). Better candidate to revisit if prop costs land in the $7-$9 range.
- **DATA_REQUIRED:** prop-firm fee + slippage data. Until verified, no progression past OBSERVATIONAL for either MCL Short variant.
- **No registry mutation. No portfolio allocation change. No paper/live promotion.**

## §6 — When this note updates

Re-open this note when:
- Operator returns with verified prop-firm rate sheet.
- Execution evidence from a paper-trading prop account is available (≥ 30 fills).
- A different deployment venue is identified with materially different cost structure.

Re-run `prop_stress_screen` with the verified baseline costs. If MCL Short-FR2 retains positive median ≥ $1.00 at 1.5× cost + 1 tick on the verified baseline, it advances to **PAPER_PACKET_CANDIDATE** review with a fresh evidence-integrity audit.

## §7 — Source artifacts

- `engine/asset_config.py` (current MCL backtest cost truth)
- `research/data/fql_forge/reports/forge_cycle_2026-06-05c.json` (stress break-even diagnostic)
- `research/data/fql_forge/mcl_orb_directional_weighting_insight.md` (directional asymmetry)
- `research/data/fql_forge/kill_taxonomy.json` key `_HEADLINE_2026-06-05c_MCL_FAMILY_REVIEW`
