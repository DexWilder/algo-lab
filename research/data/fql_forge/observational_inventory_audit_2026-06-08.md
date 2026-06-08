# OBSERVATIONAL Inventory Audit — 2026-06-08

> **Status:** One-cycle audit per operator decision #103-D.
> **Authority:** Lane B research-only; no registry mutation; no relaxed gates.
> **Source:** kill_taxonomy.json + cycle reports + insight docs already on file.
> **Method:** Apply current doctrine (PL-default, saturation rule, asymmetric-P&L-NEVER-packet, concentration-load-bearing, Era3-weakness) to each OBSERVATIONAL candidate. No new backtests required (data already exists).

## Doctrine gates applied

1. **PL-default** (codified #91): daily-workhorse exit = profit_ladder; fixed_ratio thesis-specific only
2. **Saturation rule** (codified #95): paused families do not reclaim until new primitive/data/asset/thesis/operator-override
3. **Asymmetric P&L NEVER packet-grade**: PF > 1.2 with median < 0 → KILL
4. **Concentration load-bearing**: max-year ≤ 40% workhorse, ≤ 50% relaxed
5. **Era 3 weakness**: Era3 median ≤ 0 → CURRENT_REGIME_WARNING, blocks promotion
6. **Prop-stress mandatory**: PASS at 2× cost + 2 ticks for packet-grade

## Bucket 1 — PASS_STRESS blocked by family overlap

| Candidate | Current class | Why blocked | Doctrine check | Final disposition |
|---|---|---|---|---|
| DIR-MES-ORB-Long-PL | PORTFOLIO_COMPLEMENT | corr 0.42 to MNQ probation | Same family (XB-ORB-EMA-Ladder); subset/sibling rule applies | **NO CHANGE** — OBSERVATIONAL PORTFOLIO_COMPLEMENT per operator #88 OK A |
| DIR-MES-ORB-Short-PL | PORTFOLIO_COMPLEMENT | corr 0.62 to MNQ probation | Same family; tighter corr | **NO CHANGE** — same as above |
| DIR-MYM-ORB-Long-PL | DIRECTIONAL_INSIGHT | 100% day-overlap subset of existing MYM probation | Subset by construction | **NO CHANGE** — directional insight only |
| DIR-MYM-ORB-Short-PL | DIRECTIONAL_INSIGHT | 100% day-overlap subset of existing MYM probation | Subset by construction | **NO CHANGE** |
| DIR-MNQ-ORB-Long-PL | DIRECTIONAL_INSIGHT | 100% day-overlap subset of existing MNQ probation | Subset by construction | **NO CHANGE** |
| DIR-MNQ-ORB-Short-PL | DIRECTIONAL_INSIGHT | 100% day-overlap subset of existing MNQ probation | Subset by construction | **NO CHANGE** |

**Bucket 1 result: 0 upgrades.** All PASS_STRESS family-overlap candidates were correctly classified at the time of finding under doctrine consistent with current rules.

## Bucket 2 — PASS_STRESS blocked by concentration / current-regime warning

| Candidate | Current class | Why blocked | Doctrine check | Final disposition |
|---|---|---|---|---|
| RCB15-MYM-Short-PL | OBSERVATIONAL (08g) | 71.6% max-year + Era3 median -$4.24 | Asymmetric-P&L in Era3 (PF 1.86 + median<0) = NEVER packet-grade | **NO CHANGE** — operator #100 OK A confirmed |
| RCB15-MYM-Short-VolLo-PL | OBSERVATIONAL (08i) | 70.8% max-year + Era3 median -$4.24 (essentially identical to baseline) | Same as above | **NO CHANGE** — vol overlay redundant |

**Bucket 2 result: 0 upgrades.** Concentration + Era3 weakness correctly blocks both per locked doctrine.

## Bucket 3 — YELLOW audit / portfolio complement candidates

| Candidate | Current class | Why blocked | Doctrine check | Final disposition |
|---|---|---|---|---|
| PB-VolLow-MNQ | OBSERVATIONAL PORTFOLIO_COMPLEMENT (#65 OK A) | YELLOW audit verdict; classified PORTFOLIO_COMPLEMENT not packet | Saturation: similar family-class to non-ORB on commodities (paused 08c); MNQ-side not formally paused, but same pattern | **NO CHANGE** — already correctly OBSERVATIONAL |

**Bucket 3 result: 0 upgrades.** YELLOW-audit dispositions remain valid under current doctrine.

## Bucket 4 — Replacement-candidate insights (MCL family review)

| Candidate | Current class | Why blocked | Doctrine check | Final disposition |
|---|---|---|---|---|
| MCL Short-FR2 (XB-ORB family) | OBSERVATIONAL — REPLACEMENT_CANDIDATE_LIKELY pending prop-cost (#85) | Break-even at 1.5× cost + 1 tick; FR2 cost-fragile | PL-default doctrine: PL is preferred; MCL Short-PL is the PL variant | **NO CHANGE** — OBSERVATIONAL pending DATA_REQUIRED (prop-firm rate sheet) |
| MCL Short-PL (XB-ORB family) | OBSERVATIONAL — parallel insight, more cost-robust | Same DATA_REQUIRED constraint | PL-default applies; PL variant is preferred per doctrine | **NO CHANGE** — OBSERVATIONAL pending DATA_REQUIRED |

**Bucket 4 result: 0 upgrades.** Both blocked by DATA_REQUIRED (prop-firm cost verification) — operator decision required for unblock.

**Note on PL-default applied:** MCL Short-PL is the doctrine-aligned variant. If/when prop-cost data unblocks, the PL variant has the stronger cost-robustness profile per the n=10 fragility study.

## Bucket 5 — Modest WATCH candidates with positive median and broad years

| Candidate | Cycle | n | PF | Median | yrs+ | Concentration | Stress | Doctrine reassessment | Disposition |
|---|---|---:|---:|---:|---|---|---|---|---|
| DC-MGC-Long-PL | 08c | 586 | 1.272 | $5.76 | 5/8 | TEMPORAL_SPLIT (max-yr ≥50%) | KNIFE_EDGE | Saturated family (non-ORB MCL/MGC paused 08c); ≥50% concentration | **NO CHANGE** — OBSERVATIONAL (paused family) |
| DC-MCL-Short-FR2 | 08c | 550 | 1.376 | $0.26 | 5/6 | TEMPORAL_SPLIT | FAIL_STRESS | Saturated family + FR2 (PL-default prefers PL) + FAIL_STRESS | **NO CHANGE** — OBSERVATIONAL (paused family) |
| PDB-MGC-Long-FR2 | 08c | 251 | 1.351 | $0.76 | 6/8 | TEMPORAL_SPLIT | FAIL_STRESS | Saturated family + FR2 + FAIL_STRESS; PL variant existed and was tested | **NO CHANGE** — OBSERVATIONAL (paused family) |
| PDF-MGC-Short-PL | 08c | 72 | 1.544 | $1.76 | 4/8 | TEMPORAL_SPLIT + CURRENT_REGIME_WARNING | FAIL_STRESS | Saturated family + n=72 borderline + CURRENT_REGIME_WARNING + FAIL_STRESS | **NO CHANGE** — OBSERVATIONAL (paused family) |
| RCB-MGC-Short-PL | 08e | 222 | 1.165 | $3.26 | 4/8 | TEMPORAL_SPLIT | FAIL_STRESS | RCB primitive → RESEARCH_ONLY per #104 | **NO CHANGE** — RESEARCH_ONLY absorbs |
| RCB-MGC-Both-PL | 08e | 589 | 1.173 | $0.76 | 7/8 | clean | FAIL_STRESS | RCB RESEARCH_ONLY | **NO CHANGE** |
| RCB-MES-Both-PL | 08e | 1211 | 1.210 | $1.26 | 5/8 | clean | FAIL_STRESS | RCB RESEARCH_ONLY | **NO CHANGE** |
| RCB-MYM-Both-PL | 08e | 395 | 1.462 | $0.76 | 3/3 | 68.4% high | FAIL_STRESS + CURRENT_REGIME_WARNING | RCB RESEARCH_ONLY + concentration + Era3 weakness | **NO CHANGE** |

**Bucket 5 result: 0 upgrades.** All blocked by combinations of: paused family, FAIL_STRESS, concentration, or RCB RESEARCH_ONLY classification.

## Bucket 6 — Pre-doctrine rejections (before prop-stress / family-review / PL-default)

| Candidate | Cycle | Original rejection | Current doctrine | Disposition |
|---|---|---|---|---|
| DAILY-DC-EMA-MNQ | 2026-06-04 | DUPLICATE_EXPOSURE_REJECT (corr 0.72 + median $21.76 vs ORB-MNQ $42.76) | Family-review doctrine + median quality rules confirm DUPLICATE | **NO CHANGE** — correct under current doctrine |
| FXBreak-6J-Short-London | (archived earlier) | Verified concentration catastrophe | Concentration rule (load-bearing) confirms | **NO CHANGE** — archived per CLAUDE.md |
| MomPB-6J-Long-US | (archived earlier) | Archived | n/a | **NO CHANGE** — archived |
| NoiseBoundary-MNQ-Long | (archived earlier) | Archived | n/a | **NO CHANGE** |
| PreFOMC-Drift-Equity | (rejected earlier) | Rejected | n/a | **NO CHANGE** |

**Bucket 6 result: 0 upgrades.** Pre-doctrine rejections were largely on grounds (concentration, duplicate, regime) that current doctrine reinforces. No false-OBSERVATIONAL detected.

## Aggregate audit result

| Bucket | Candidates audited | Upgrades | Notes |
|---|---:|---:|---|
| 1 — PASS_STRESS + family overlap | 6 | 0 | All correctly classified |
| 2 — PASS_STRESS + concentration/regime | 2 | 0 | Correct under asymmetric-P&L doctrine |
| 3 — YELLOW audit / portfolio complement | 1 | 0 | Correct |
| 4 — Replacement-candidate insights | 2 | 0 | Pending DATA_REQUIRED only |
| 5 — Modest WATCH+median+years | 8 | 0 | Saturated families or RCB RESEARCH_ONLY |
| 6 — Pre-doctrine rejections | 5 | 0 | Original verdicts hold |
| **TOTAL** | **24** | **0** | **NO UPGRADES** |

## Conclusion: D found no upgrade

The OBSERVATIONAL inventory was already classified correctly under doctrine that was either (a) explicit at the time of finding, or (b) implicit and now codified. Forge's classification discipline has been consistent throughout the campaign.

**Per operator #103 rule: "If no candidate upgrades, explicitly say D found no upgrade and then move to next search basis."**

## D-result: ZERO UPGRADES → move to 103-A

Default next direction per operator: **build ONE new primitive** (volatility_regime_compound or microstructure_imbalance, whichever easier + more candidate-unlock).

### Recommendation: volatility_regime_compound

**Rationale for choosing volatility_regime_compound over microstructure_imbalance:**

| Criterion | volatility_regime_compound | microstructure_imbalance |
|---|---|---|
| Data requirement | Uses existing ATR + dc_high/low series (already in features) | Requires tick-level data OR volume-microstructure proxies |
| Build complexity | Medium — combines ATR-of-ATR or vol-conditional ATR thresholds | Higher — proxy construction + validation |
| Mechanism novelty vs RCB | Different (vol-of-vol regime detection vs static low-vol compression) | Higher (order-flow-derived) |
| Candidate unlock count | Estimated 10-15 across MGC/MCL/MES/MYM/MNQ × 2 directions | Estimated 8-12 |
| Risk of redundancy with existing RCB | Low — RCB is compression-trigger; vol-of-vol is regime-conditioning, can compose | n/a |
| Time-to-first-batch | ~2-4h | ~6-10h |

**Proposed minimum-viable volatility_regime_compound:**
- Compute rolling stdev of ATR (vol-of-vol)
- Detect "vol-regime-shift" = vol-of-vol moves from low percentile to high percentile
- Entry: at vol-regime-shift, direction by ema_slope filter
- Stop/target ATR-multiplied, PL exit by default
- Configurable lookback (default 60 bars rolling vol-of-vol over 240-bar percentile rank)

This is a genuinely different mechanism from RCB (which is single-condition compression-then-break) and ORB (session-bound). It targets the regime-shift moment specifically — which is when the 2025 RCB outlier captured edge.

## Constraints

- No registry mutation, no scheduler change, no portfolio allocation change.
- No paper/live promotion.
- Lane B research-only.
- One primitive at a time per Hybrid D-A pattern.

## Source artifacts

- `research/data/fql_forge/kill_taxonomy.json` (campaign trail)
- `research/data/fql_forge/reports/forge_cycle_2026-06-08{a,b,c,d,e,f,g,h,i}.json` (cycle data)
- `docs/fql_forge/exit_design_pl_workhorse_default.md` (PL-default doctrine)
- `docs/fql_forge/asset_family_saturation_rule.md` (saturation doctrine)
- `docs/reports/prop_cost_verification/2026-06-08_MCL_prop_cost_verification.md` (MCL prop-cost DATA_REQUIRED)
