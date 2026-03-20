# Harvest Backlog Triage — 2026-03-20

**Notes reviewed:** 61 (from 2026-03-17 through 2026-03-20)
**Refinement pending:** 0
**Registry strategies:** 110

---

## Classification Summary

| Category | Count | Action |
|----------|-------|--------|
| **ARCHIVE** | 18 | Duplicate, infra-heavy, or no path to testability |
| **SALVAGE LATER** | 24 | Blocked by data/engineering but real mechanism; revisit when blocker clears |
| **CONVERT NOW** | 6 | Testable with existing data, fills a gap, worth a spec |
| **ALREADY CONSUMED** | 1 | `treasury_rolldown_carry_spread` — already in registry |
| **NEEDS REVIEW** | 4 | Ambiguous mechanism or overlap — need human judgment |
| **KEEP AS IDEAS** | 8 | Accepted, testable, but lower priority than convert-now candidates |

---

## ARCHIVE (18 notes)

*Duplicate of existing registry entry, too infrastructure-heavy for near-term,
or mechanism doesn't hold up under scrutiny.*

| # | Note | Factor | Reason |
|---|------|--------|--------|
| 1 | `2026-03-17_03_cross_asset_carry_optimized.md` | CARRY | Duplicate of Family 41 (ManagedFutures-Carry-Diversified). Same concept, needs same blockers. |
| 2 | `2026-03-17_04_currency_ppp_value_rotation.md` | VALUE | Duplicate of FX-PPP-Value already in registry. Blocked by same OECD data. |
| 3 | `2026-03-17_05_commodity_value_reversion.md` | VALUE | No clear value anchor — "commodity fair value" is undefined. Needs definition before it's even an idea. |
| 4 | `2026-03-17_06_rebalance_close_dislocation.md` | STRUCTURAL | Needs closing auction imbalance data we don't have and can't get from futures. Infra-blocked indefinitely. |
| 5 | `2026-03-17_07_treasury_rolldown_carry_spread.md` | CARRY | **Already consumed** — this IS Family 45. In registry as Treasury-Rolldown-Carry-Spread. |
| 6 | `2026-03-17_13_btc_global_market_closed_seasonality.md` | STRUCTURAL | BTC not in asset universe. No CME BTC micro data. Not on roadmap. |
| 7 | `2026-03-18_02_nyse_dorder_auction_pressure.md` | STRUCTURAL | Needs NYSE D-Order/imbalance feed — not available in futures data. Cash equity infra required. |
| 8 | `2026-03-18_03_indicative_close_convergence.md` | STRUCTURAL | Same blocker as above — needs exchange-specific closing auction data. |
| 9 | `2026-03-18_04_cross_asset_normalized_carry_rotation.md` | CARRY | Duplicate of Family 41 concept with normalization twist. Same blockers. |
| 10 | `2026-03-18_08_treasury_curve_rolldown_carry_bucket.md` | CARRY | Near-duplicate of Family 45 (Treasury Rolldown). Slightly different bucketing but same mechanism. |
| 11 | `2026-03-18_09_g10_ppp_value_convergence.md` | VALUE | Duplicate of `2026-03-17_04_currency_ppp_value_rotation`. Same idea, different framing. |
| 12 | `2026-03-18_14_commodity_real_price_value_reversal.md` | VALUE | Needs CPI-adjusted commodity price history — heavy data construction, low testability. |
| 13 | `2026-03-19_10_g10_fx_ppp_value_convergence.md` | VALUE | Third instance of FX PPP value. Duplicate of 03-17_04 and 03-18_09. |
| 14 | `2026-03-19_11_global_equity_index_earnings_yield_value_rotation.md` | VALUE | Duplicate of `2026-03-18_11`. Same concept, different batch. |
| 15 | `2026-03-19_14_bitcoin_metcalfe_value_dislocation.md` | VALUE | BTC not in asset universe. On-chain data not available. |
| 16 | `2026-03-20_01_cross_market_value_everywhere_basket.md` | VALUE | Meta-strategy (basket of value strategies). Needs all value components built first. Not actionable. |
| 17 | `2026-03-20_01_agricultural_stocks_to_use_value_rotation.md` | VALUE | USDA WASDE data not in pipeline. Agricultural futures not onboarded. |
| 18 | `2026-03-20_06_treasury_real_yield_gap_value.md` | VALUE | Needs TIPS real yield curve — not available in current data. |

---

## SALVAGE LATER (24 notes)

*Real mechanism, blocked by specific data or engineering need. Revisit when
the blocker clears. Ordered by factor priority (CARRY/VOL gaps first).*

### CARRY blockers (7)

| # | Note | Blocker | Revisit When |
|---|------|---------|-------------|
| 1 | `2026-03-17_10_agricultural_term_structure_carry.md` | Ag futures data (ZS/ZC/ZW) | Asset expansion to agriculture |
| 2 | `2026-03-17_11_energy_convenience_yield_carry.md` | Energy carry formula + vol gate | After carry_lookup v2 |
| 3 | `2026-03-17_12_conditional_fx_carry_basket.md` | Macro risk filter definition | After FX carry is validated |
| 4 | `2026-03-18_07_agricultural_seasonal_carry_rotation.md` | Ag roll window + seasonal data | Asset expansion to agriculture |
| 5 | `2026-03-19_08_crude_hedging_pressure_carry.md` | CFTC positioning data normalization | External data feed |
| 6 | `2026-03-19_13_g10_fx_neutral_rate_dispersion_carry.md` | Global neutral rate construction | Macro data infrastructure |
| 7 | `2026-03-20_08_stir_policy_path_carry.md` | SOFR pack implied path | Rates infrastructure |

### VOLATILITY blockers (5)

| # | Note | Blocker | Revisit When |
|---|------|---------|-------------|
| 8 | `2026-03-17_08_treasury_macro_vol_targeting.md` | Macro vol feature spec | After vol-managed equity validates |
| 9 | `2026-03-18_05_treasury_vol_of_vol_stability_targeting.md` | Rates vol-of-vol thresholds | After rates strategies mature |
| 10 | `2026-03-18_06_commodity_basket_volatility_managed_beta.md` | Commodity benchmark definition | Asset expansion |
| 11 | `2026-03-18_13_treasury_basket_constant_vol_targeting.md` | Treasury basket weights | After rates carry proves out |
| 12 | `2026-03-20_03_equity_index_dividend_carry_rotation.md` | Implied dividend basis data | External data feed |

### STRUCTURAL blockers (5)

| # | Note | Blocker | Revisit When |
|---|------|---------|-------------|
| 13 | `2026-03-17_06_close_auction_follow_through.md` | Cash close imbalance proxy | Needs REVIEW — may be testable |
| 14 | `2026-03-19_06_tokyo_prelondon_fx_orderflow_break.md` | Tokyo session orderflow proxy | FX session data improvement |
| 15 | `2026-03-19_07_asia_metals_nightspillover.md` | SHFE night session data | External data feed |
| 16 | `2026-03-20_02_base_metals_inventory_curve_carry.md` | Exchange inventory series | External data feed |
| 17 | `2026-03-20_03_fx_internalizer_inventory_release_reversal.md` | FX flow threshold definition | Needs REVIEW |

### VALUE blockers (7)

| # | Note | Blocker | Revisit When |
|---|------|---------|-------------|
| 18 | `2026-03-17_04_cross_asset_adjusted_yield_value.md` | Value signal mapping | After carry_lookup v2 |
| 19 | `2026-03-17_05_rates_relative_yield_value.md` | Rates value lookup | After rates carry validates |
| 20 | `2026-03-18_01_equity_treasury_yield_gap_value.md` | Equity vs bond yield definition | External data feed |
| 21 | `2026-03-18_11_global_equity_earnings_yield_value.md` | Global equity earnings data | External data feed |
| 22 | `2026-03-18_15_treasury_term_premium_value_rotation.md` | Term premium estimation | Macro data infrastructure |
| 23 | `2026-03-19_09_softs_historical_basis_rotation.md` | Historical basis window + softs data | Asset expansion |
| 24 | `2026-03-20_06_gold_real_rate_value_dislocation.md` | Gold fair value model | After carry_lookup v2 |

---

## CONVERT NOW (6 notes)

*Testable with existing data and infrastructure. Worth a spec this cycle.*

| # | Note | Factor | Why Convert Now |
|---|------|--------|----------------|
| 1 | **`2026-03-19_01_gap_statistics_regime_filter.md`** | STRUCTURAL | High testability. Gap classification using existing intraday data. Enhances existing gap strategies as a filter, not a standalone. |
| 2 | **`2026-03-19_02_rth_gap_table_level_interaction.md`** | STRUCTURAL | High testability. RTH gap + prior level interaction. Mechanical rules, existing data. |
| 3 | **`2026-03-19_04_overnight_z_volratio_open_drive.md`** | VOLATILITY | High testability. Overnight gap z-score + vol ratio as open-drive filter. Fills VOL gap. Existing data sufficient. |
| 4 | **`2026-03-19_05_mtf_true_gap_breakaway_filter.md`** | STRUCTURAL | Very high testability. Multi-timeframe true gap breakaway. Mechanical, existing data. |
| 5 | **`2026-03-20_04_treasury_cash_close_reversion_window.md`** | STRUCTURAL | High testability. Treasury intraday close reversion. Rates-native structural — rare combination. |
| 6 | **`2026-03-20_07_spx_lunch_compression_afternoon_release.md`** | STRUCTURAL | High testability. SPX lunch compression → afternoon release. Session microstructure, existing MES data. |

### Priority Order for Conversion

1. **`overnight_z_volratio_open_drive`** — fills VOLATILITY gap (0 active), testable now
2. **`treasury_cash_close_reversion_window`** — rates-native STRUCTURAL, fills Rates gap
3. **`gap_statistics_regime_filter`** — enhances existing gap strategies (filter, not standalone)
4. **`mtf_true_gap_breakaway_filter`** — very high testability, STRUCTURAL
5. **`rth_gap_table_level_interaction`** — STRUCTURAL, existing data
6. **`spx_lunch_compression_afternoon_release`** — MES session microstructure

---

## KEEP AS IDEAS (8 notes)

*Accepted, testable or near-testable, but lower priority than convert-now.*

| # | Note | Factor | Status |
|---|------|--------|--------|
| 1 | `2026-03-17_01_treasury_auction_cycle.md` | EVENT | Needs auction calendar. Good idea, medium priority. |
| 2 | `2026-03-17_02_vol_managed_commodity_futures.md` | VOLATILITY | Needs basket definition. Keep in catalog. |
| 3 | `2026-03-17_09_ny_afternoon_fx_range_reversion.md` | STRUCTURAL | Testable but FX structural is thin priority. |
| 4 | `2026-03-19_03_overnight_gap_dominance_filter.md` | VOLATILITY | Filter note — needs a parent strategy to attach to. |
| 5 | `2026-03-19_12_treasury_futures_volatility_managed_duration_sleeve.md` | VOLATILITY | Good but needs duration weighting spec. |
| 6 | `2026-03-19_15_multiasset_futures_risk_parity_vol_target.md` | VOLATILITY | Meta-strategy. Needs component strategies first. |
| 7 | `2026-03-20_02_broad_commodity_curve_slope_carry.md` | CARRY | Testable but commodity carry is in SALVAGE (Family 42). Wait. |
| 8 | `2026-03-20_05_tokyo_fix_fx_reversal.md` | STRUCTURAL | Interesting but needs Tokyo fix timestamp. Keep in catalog. |

---

## NEEDS REVIEW (4 notes)

*Human judgment required — mechanism is ambiguous or overlap is unclear.*

| # | Note | Factor | Question |
|---|------|--------|----------|
| 1 | `2026-03-18_10_fx_internalization_hub_reversal.md` | STRUCTURAL | Is the FX liquidity shock proxy feasible? |
| 2 | `2026-03-18_12_london_close_ny_afternoon_fx_handoff.md` | STRUCTURAL | Overlaps with rejected London-Close FX Handoff? Check if this is the same idea. |
| 3 | `2026-03-20_07_gold_london_fix_handoff_reversion.md` | STRUCTURAL | LBMA fix proxy — testable or not? |
| 4 | `2026-03-20_08_crude_settlement_wash_reversion.md` | STRUCTURAL | Settlement timestamp convention — verifiable? |

---

## Factor Distribution of Backlog

| Factor | Archive | Salvage | Convert | Ideas | Review | Total |
|--------|---------|---------|---------|-------|--------|-------|
| CARRY | 4 | 7 | 0 | 1 | 0 | **12** |
| VALUE | 10 | 7 | 0 | 0 | 0 | **17** |
| VOLATILITY | 0 | 5 | 1 | 4 | 0 | **10** |
| STRUCTURAL | 4 | 5 | 5 | 2 | 4 | **20** |
| EVENT | 0 | 0 | 0 | 1 | 0 | **1** |
| MOMENTUM | 0 | 0 | 0 | 0 | 0 | **0** |

**Key observations:**
- VALUE is overrepresented (17 notes) but almost all are blocked by external data. Archive most, salvage a few.
- STRUCTURAL has the most convert-now candidates (5 of 6). This is where the harvest is richest.
- CARRY backlog is large (12) but mostly blocked or duplicate. Family 45 is already the active push.
- VOLATILITY has the best gap-fill convert candidate (`overnight_z_volratio_open_drive`).

---

## Recommended Next Steps

1. **Archive 18 notes** — move to `~/openclaw-intake/archived/` with triage tag
2. **Tag 24 salvage-later notes** with their specific blocker in the registry
3. **Convert top 2 candidates** this cycle:
   - `overnight_z_volratio_open_drive` (VOL gap fill)
   - `treasury_cash_close_reversion_window` (Rates STRUCTURAL)
4. **Defer remaining 4 convert-now notes** to next conversion cycle
5. **Present 4 NEEDS REVIEW notes** for human judgment
