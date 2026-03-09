# Phase 8.5 Audit — Strategy DNA Clustering

*Completed: 2026-03-09*

## Objective

Create a structural fingerprinting system for all 9 converted strategies to detect duplicates, identify true diversifiers, classify portfolio roles, and guide future harvesting.

## Deliverables

| Artifact | File | Status |
|----------|------|--------|
| DNA schema | `research/dna/dna_schema.json` | COMPLETE |
| Profile builder | `research/dna/build_dna_profiles.py` | COMPLETE |
| Strategy catalog | `research/dna/dna_catalog.json` | COMPLETE (9 profiles) |
| Cluster analysis | `research/dna/dna_clusters.json` | COMPLETE (8 clusters) |
| Analysis report | `research/dna/dna_report.md` | COMPLETE |

## Methodology

### DNA Schema (20+ fields)

Each strategy fingerprinted across:
- **Structural identity:** family, asset, mode, entry_type, confirmation_type, filter_depth, exit_type, exit_features, risk_model
- **Behavioral fingerprint:** session_window, session_restriction, regime_dependency, holding_time_class, direction_bias, trade_frequency_bucket, cost_sensitivity
- **Portfolio metadata:** portfolio_role, overlap_risk, confidence_level, key_performance, structural_notes

### Clustering Algorithm

1. Convert 7 categorical features to numeric vectors: entry_type, risk_model, holding_time_class, direction_bias, trade_frequency_bucket, filter_depth (normalized), cost_sensitivity
2. Compute pairwise Euclidean distance (normalized 0-1)
3. Hierarchical clustering with distance threshold 0.45
4. Near-duplicate detection at threshold 0.3

### Classification Rules

| Classification | Criteria |
|---------------|----------|
| true_diversifier | deployment_ready or candidate_validated + singleton cluster |
| near_duplicate | distance < 0.3 from another strategy |
| component_donor | rejected but has reusable structural components |
| rejected_but_informative | rejected, no reusable components |
| watchlist | pending_validation or low confidence |

## Results

### Strategy Classifications

| Strategy | Classification | Confidence | Entry Type | Risk Model |
|----------|---------------|------------|------------|------------|
| PB-MGC-Short | true_diversifier | medium | pullback | atr_adaptive |
| ORB-009-MGC-Long | true_diversifier | high | breakout | range_based |
| VIX-Channel-MES-Both | true_diversifier | medium | regime_detection | rv_scaled |
| GAP-MOM-MGC-Long | watchlist | low | gap_signal | atr_adaptive |
| VWAP-006-MES-Long | rejected_but_informative | medium | crossover | atr_adaptive |
| RVWAP-MR-MES-Both | rejected_but_informative | medium | mean_reversion | atr_adaptive |
| ICT-010-MES-Both | rejected_but_informative | medium | pullback | fixed_points |
| ORION-VOL-MES-Both | component_donor | medium | breakout | compression_based |
| BBKC-SQUEEZE-MES-Both | component_donor | medium | squeeze_release | atr_adaptive |

### Cluster Structure

- **8 clusters** from 9 strategies — nearly all are singletons
- Only cluster with >1 member: RVWAP-MR + BBKC-SQUEEZE (distance 0.39) — both are band/compression strategies with ATR-adaptive risk
- All 3 validated strategies are structural singletons — portfolio diversity is genuine

### Near-Duplicate Analysis

**No near-duplicates detected.** All pairwise distances > 0.3. Closest pairs:
- RVWAP-MR ↔ BBKC-SQUEEZE: 0.39
- This pair shares mean-reversion/compression DNA + ATR risk model

### Component Donor Value

| Donor | Component | Potential Use |
|-------|-----------|--------------|
| ORION-VOL | Compression box (tightness + flatness) | Enhance ORB-009 entries |
| BBKC-SQUEEZE | Momentum state machine (lime/green/red/maroon) | Unique exit logic for any strategy |
| ICT-010 | Sweep detection | Needs better confirmation, not the entry itself |

### Structural Gaps

Missing DNA types that align with regime coverage gaps:
- **trend_following** — no EMA/SuperTrend/Donchian strategy
- **overnight** — no globex/session-transition strategy
- **event_driven** — no CPI/FOMC/NFP targeted strategy
- **higher_timeframe** — all strategies on 5m only

## Quality Checks

| Check | Result |
|-------|--------|
| All 9 strategies profiled? | YES |
| Validated strategies classified as diversifiers? | YES (all 3) |
| Rejected strategies not classified as diversifiers? | YES |
| Near-duplicate threshold reasonable? | YES (0.3 — no false positives) |
| Cluster threshold reasonable? | YES (0.45 — groups similar structures) |
| Confidence levels match trade counts? | YES (high: 100+, medium: 50-100, low: <50) |
| Structural gaps align with regime gaps? | YES (overnight, event_driven match MISSING regimes) |

## Risks & Limitations

1. **Clustering is structural, not performance-based.** Two strategies in the same cluster may have very different performance profiles.
2. **7-feature vector is a simplification.** The full DNA schema has 20+ fields but clustering uses only 7 most discriminative features.
3. **Distance threshold (0.45) is heuristic.** A tighter threshold would produce more singletons; a looser one would merge strategies that are genuinely different.
4. **Confidence levels based on trade count, not statistical significance.** A "high" confidence strategy (100+ trades) may still fail DSR.
5. **Catalog is static.** Must be re-run when new strategies are converted or existing strategies are modified.

## Alignment with Lab Architecture

DNA clustering integrates with the existing lab pipeline:

```
intake → triage → conversion → validation → DNA profiling → regime profiling → portfolio construction
```

The DNA system answers: "Is this new strategy structurally different from what we already have?" before investing in full validation. This prevents wasted effort on strategies that duplicate existing coverage.

---
*Audit completed: 2026-03-09*
