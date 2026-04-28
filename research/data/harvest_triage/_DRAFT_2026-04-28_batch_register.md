# DRAFT — Tuesday 2026-04-28 Batch Register Pre-flight

**Status:** Draft / pre-flight only. NO registry mutations today. Document staged Monday 2026-04-27 to make Tuesday's execution surgical-clean per established discipline.

**Authority:** T2 (registry append, additive only — no status mutations) per `docs/authority_ladder.md`. Hold-compliant.

---

## Count correction

Earlier commit messages referenced "33 HIGH canonical registry appends." Pre-flight recount across all 5 triage files (2026-04-20 / 21 / 22 / 23 / 27) shows the actual count is **34**.

Source of error: Friday's commit-summary count missed the 04-23 Donchian-non-equity single HIGH; today's commit propagated the same number. Now corrected.

---

## Schema findings (use existing convention, no new fields)

Existing `idea` entries in `research/data/strategy_registry.json` already include all needed provenance fields:

| Existing field | Use in batch register |
|----------------|------------------------|
| `triage_date` | YYYY-MM-DD of the harvest_triage file the disposition came from |
| `triage_reason` | Short reason (e.g., `convert_canonical`, `fills_value_gap`, `blocker_clearing`) |
| `triage_route` | `weekly_harvest_batch_register_2026-04-28` (uniform for this batch) |
| `source` | Verbatim attribution from harvest note's source URL field |
| `source_category` | Category (`academic` / `github` / `reddit` / `tradingview` / etc.) inferred from URL |
| `created_date` | Triage date (matches `triage_date`) |
| `last_review_date` | Triage date |
| `notes` | Composed: `"Triage ACCEPT HIGH on YYYY-MM-DD per harvest_triage/YYYY-MM-DD.md. <one-line canonical reason>."` |
| `lifecycle_stage` | `"discovery"` (initial state) |
| `state_history` | `[]` (empty for new) |
| `validation_score` / `parameter_stability` / `profit_factor` / `trades_6yr` | `null` (not yet tested) |
| `extended_history_status` | `"not_tested"` |
| `convergent_sources` | `[]` (could populate if cluster review cited cross-source verification — defer to v1.1) |
| `relationships` | `{parent: null, children: [], related: [], salvaged_from: null, components_used: []}` |
| `regime_tag` | `"unclassified"` (default for new ideas) |
| `crossbreeding_eligible` | `false` for full_strategy initially; `true` for filter/exit/sizing components |
| `extractable_components` | Derived from component_type |
| `why_not_now` | `"awaiting_validation_battery"` for full_strategies; `"component_awaiting_assembly_into_strategy"` for components |

**No new schema fields introduced.** This is a pure additive operation respecting existing conventions.

---

## The 34 canonical entries (ordered by triage date, then by note position)

### From 04-20 (18 entries, all VALUE/CARRY/EVENT priority families)

| # | strategy_id (proposed) | source_note | factor | family | component_type |
|---|------------------------|-------------|--------|--------|----------------|
| 1 | `fx-value-spread-dispersion-basket` | 2026-04-17_02 | VALUE | fx_value_dispersion_basket | full_strategy |
| 2 | `fx-relative-ppp-momentum-conflict-gate` | 2026-04-17_06 | VALUE | fx_relative_ppp_value | full_strategy |
| 3 | `eur-value-quality-classifier-filter` | 2026-04-17_10 | VALUE | fx_value_quality_filter | filter |
| 4 | `cross-asset-vol-managed-value-overlay` | 2026-04-19_07 | VALUE | cross_asset_value_overlay | sizing_overlay |
| 5 | `weekly-commercial-extremes-value` | 2026-04-19_09 | VALUE | commercial_positioning_value_reversion | full_strategy |
| 6 | `kalman-spread-slope-value-entry-rates-fx` | 2026-04-19_14 | VALUE | kalman_relative_value_entry | entry_logic |
| 7 | `kalman-cointegration-residual-entry-metals-rates` | 2026-04-20_03 | VALUE | kalman_relative_value_spread | entry_logic |
| 8 | `half-life-gated-spread-reversion-fx-rates` | 2026-04-20_04 | VALUE | half_life_spread_filter | filter |
| 9 | `wti-term-structure-carry-momentum-switch` | 2026-04-17_01 | CARRY | energy_curve_carry | full_strategy |
| 10 | `cross-sector-carry-rank-tsmom-confirmation` | 2026-04-17_07 | CARRY | diversified_futures_carry_rank | full_strategy |
| 11 | `natural-gas-adaptive-carry-momentum-selector` | 2026-04-17_08 | CARRY | natural_gas_adaptive_carry | full_strategy |
| 12 | `volatility-gated-fx-carry-switch` | 2026-04-19_03 | CARRY | volatility_gated_fx_carry | filter |
| 13 | `annualized-curve-extremes-overlay` | 2026-04-19_05 | CARRY | annualized_curve_extremes_overlay | filter |
| 14 | `duration-neutral-treasury-rolldown-spread` | 2026-04-19_08 | CARRY | treasury_rolldown_relative_value | full_strategy |
| 15 | `jgb-ust-yield-differential-carry` | 2026-04-19_10 | CARRY | sovereign_yield_differential_carry | full_strategy |
| 16 | `treasury-auction-dispersion-reaction` | 2026-04-17_02 (event) | EVENT | treasury_auction_microstructure | entry_logic |
| 17 | `treasury-auction-dispersion-regime-gate` | 2026-04-17_15 | EVENT | treasury_auction_regime_quality | filter |
| 18 | `treasury-auction-instability-pre-filter` | 2026-04-19_05 (event) | EVENT | treasury_auction_instability_filter | filter |

### From 04-21 (2 entries, VALUE)

| # | strategy_id (proposed) | source_note | factor | family | component_type |
|---|------------------------|-------------|--------|--------|----------------|
| 19 | `ppp-currency-value-quarterly-basket` | 2026-04-21_01 | VALUE | fx_ppp_value | full_strategy |
| 20 | `kalman-half-life-residual-entry-stack` | 2026-04-21_06 | VALUE | kalman_relative_value_spread | entry_logic |

### From 04-22 (3 entries, CARRY/EVENT)

| # | strategy_id (proposed) | source_note | factor | family | component_type |
|---|------------------------|-------------|--------|--------|----------------|
| 21 | `curve-steepening-flattening-carry-regime-switch` | 2026-04-22_06 | CARRY | curve_dynamics_regime_carry | filter |
| 22 | `treasury-auction-tail-shock-reaction` | 2026-04-22_07 | EVENT | treasury_auction_microstructure | entry_logic |
| 23 | `pre-auction-concession-follow-through` | 2026-04-22_08 | EVENT | treasury_auction_concession | full_strategy |

### From 04-23 (1 entry, STRUCTURAL)

| # | strategy_id (proposed) | source_note | factor | family | component_type |
|---|------------------------|-------------|--------|--------|----------------|
| 24 | `donchian-breakout-atr-stop-non-equity-futures` | 2026-04-23_01 | STRUCTURAL | non_equity_donchian_breakouts | full_strategy |

### From 04-27 (10 entries — combined Fri 04-24 + Sun 04-26 batches)

| # | strategy_id (proposed) | source_note | factor | family | component_type |
|---|------------------------|-------------|--------|--------|----------------|
| 25 | `relative-issuance-richness-auction-short` | 2026-04-24_04 (relative_issuance) | VALUE | auction_probability_relative_value | entry_logic |
| 26 | `monthly-front-second-roll-yield-ranker-g10-fx-carry` | 2026-04-24_10 | CARRY | cme_fx_futures_carry_ranker | full_strategy |
| 27 | `smoothed-front-second-curve-sort-cross-commodity-carry` | 2026-04-24_11 | CARRY | cross_commodity_term_structure_carry | full_strategy |
| 28 | `vol-model-gated-short-vix-carry` | 2026-04-24_12 | VOLATILITY | short_vol_carry_timing | entry_logic |
| 29 | `treasury-auction-concession-buildup-entry` | 2026-04-26_03 | EVENT | treasury_auction_concession | full_strategy |
| 30 | `commodity-curve-inventory-stress-filter` | 2026-04-26_05 | CARRY | commodity_curve_inventory_carry | filter |
| 31 | `quarterly-refunding-supply-drift-treasury` | 2026-04-26_06 | EVENT | treasury_supply_cycle | full_strategy |
| 32 | `us-real-yield-fx-value-divergence` | 2026-04-26_08 | VALUE | macro_real_yield_value | full_strategy |
| 33 | `auction-tenor-divergence-curve-steepener` | 2026-04-26_09 | EVENT | treasury_auction_tenor_divergence | full_strategy |
| 34 | `curve-maturity-selected-commodity-carry` | 2026-04-26_10 | CARRY | curve_segment_commodity_carry | full_strategy |

---

## Worked example #1 (verify template)

Strategy `#1` from list: `fx-value-spread-dispersion-basket`. Reading harvest note 2026-04-17_02_fx_value_spread_dispersion_basket.md to populate fields:

```json
{
  "strategy_id": "fx-value-spread-dispersion-basket",
  "strategy_name": null,
  "family": "fx_value_dispersion_basket",
  "asset": "FX-G10",
  "session": "daily",
  "direction": "both",
  "source": "<read from harvest note source URL>",
  "source_category": "<infer from URL — academic / github / etc.>",
  "rule_summary": "<read from harvest note 'summary' field, ~1-2 sentences>",
  "status": "idea",
  "validation_score": null,
  "parameter_stability": null,
  "extended_history_status": "not_tested",
  "portfolio_role": null,
  "trades_6yr": null,
  "profit_factor": null,
  "notes": "Triage ACCEPT HIGH on 2026-04-20 per harvest_triage/2026-04-20.md. Canonical: fills VALUE factor gap with cross-sectional dispersion basket framework, distinct from single-pair PPP/residual reversion. Blocker-clearing for strategy_ambiguity in VALUE.",
  "last_review_date": "2026-04-20",
  "source_category": "<from URL>",
  "lifecycle_stage": "discovery",
  "state_history": [],
  "convergent_sources": [],
  "relationships": {
    "parent": null,
    "children": [],
    "related": [],
    "salvaged_from": null,
    "components_used": []
  },
  "component_type": "full_strategy",
  "created_date": "2026-04-20",
  "triage_date": "2026-04-20",
  "triage_reason": "convert_canonical",
  "triage_route": "weekly_harvest_batch_register_2026-04-28",
  "session_tag": "daily",
  "regime_tag": "unclassified",
  "reusable_as_component": false,
  "extractable_components": [],
  "crossbreeding_eligible": false,
  "why_not_now": "awaiting_validation_battery"
}
```

**Open populate-tomorrow fields:** `source` (URL), `source_category` (inferred), `rule_summary` (from harvest note's summary field), `asset` (verify FX-G10 vs specific pair), `direction`, `session`. All available from harvest note text — pure read-and-transcribe operation.

---

## Tuesday execution plan

**Pre-execution:**
1. Read each of the 34 source harvest notes; extract `summary`, `target futures instruments`, `source URL`, `direction` (where stated)
2. Build the JSON entries off the template, one per row of the 34-entry table
3. Verify each entry's field count matches existing `idea` entries (avoid drift)

**Execution:**
4. Open `research/data/strategy_registry.json`
5. Append all 34 entries to the `strategies` array (preserving order at end)
6. Update `_generated` field if applicable
7. Save, verify count went 117 → 151

**Post-execution:**
8. Spot-check 3 random entries by re-reading
9. Run `python3 research/operating_dashboard.py` to confirm dashboard reads new entries cleanly
10. Single bundled commit

---

## Vocabulary for `triage_reason` (uniform across batch)

To keep the field structured, use these short tokens (matching existing convention):

| Token | When to use |
|-------|-------------|
| `convert_canonical` | New canonical mechanism in priority family (most full_strategy entries) |
| `fills_value_gap` | Specifically for VALUE factor canonicals (subset of convert_canonical) |
| `blocker_clearing` | Note explicitly resolves a registry `blocked_*` entry |
| `component_addition` | Component (filter/exit/sizing/overlay) addition to existing or new family |
| `priority_family_canonical` | Treasury-auction / CARRY canonical resolving ambiguity |

Each entry gets exactly one. Decided per-row at execution time based on which fits best.

---

## Tomorrow's risk surface (now reduced)

| Without pre-flight | With pre-flight |
|---------------------|-----------------|
| Discover schema mid-execution; risk drift | Schema confirmed; no new fields needed |
| Compose 34 strategy_ids on the fly | strategy_ids drafted, reviewable today |
| Mix design + execute (high cognitive load) | Pure execute against staged plan |
| Risk of count error | 33 → 34 corrected here |
| Risk of mid-batch reformat | Template locked |

**Tomorrow becomes pure transcription + verification, not design.**

---

*This is a draft. No commit today. Tomorrow merges this into actual registry and commits in one operation.*
