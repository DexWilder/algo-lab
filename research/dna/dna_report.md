# Strategy DNA Report

*Structural fingerprinting and similarity analysis for all converted strategies.*

---

## Executive Summary

- **9 strategies** profiled across 9 families
- **8 structural clusters** identified
- **3 true diversifiers**, 2 component donors, 3 rejected-but-informative

### Key Finding

The lab has **genuine structural diversity** among its validated strategies. PB-Short (pullback + deep filter stack), ORB-009 (range breakout + VWAP confirmation), and VIX Channel (regime detection + RV-scaled channel) are structurally distinct — different entry mechanisms, different risk models, different regime preferences. This is not cosmetic diversity.

### Near-Duplicates Identified

No near-duplicates found (all pairwise distances > 0.3).

## Strategy Classifications

| Strategy | Classification | Confidence | Entry Type | Risk Model |
|----------|---------------|------------|------------|------------|
| ★ PB-MGC-Short | true_diversifier | medium | pullback | atr_adaptive |
| ★ ORB-009-MGC-Long | true_diversifier | high | breakout | range_based |
| ★ VIX-Channel-MES-Both | true_diversifier | medium | regime_detection | rv_scaled |
| ○ GAP-MOM-MGC-Long | watchlist | low | gap_signal | atr_adaptive |
| ✗ VWAP-006-MES-Long | rejected_but_informative | medium | crossover | atr_adaptive |
| ✗ RVWAP-MR-MES-Both | rejected_but_informative | medium | mean_reversion | atr_adaptive |
| ✗ ICT-010-MES-Both | rejected_but_informative | medium | pullback | fixed_points |
| ◇ ORION-VOL-MES-Both | component_donor | medium | breakout | compression_based |
| ◇ BBKC-SQUEEZE-MES-Both | component_donor | medium | squeeze_release | atr_adaptive |

## Structural Clusters

### cluster_0 (1 members)
- **Entry types:** pullback
- **Risk models:** atr_adaptive
- **Members:** PB-MGC-Short

### cluster_1 (1 members)
- **Entry types:** breakout
- **Risk models:** range_based
- **Members:** ORB-009-MGC-Long

### cluster_2 (1 members)
- **Entry types:** regime_detection
- **Risk models:** rv_scaled
- **Members:** VIX-Channel-MES-Both

### cluster_3 (1 members)
- **Entry types:** gap_signal
- **Risk models:** atr_adaptive
- **Members:** GAP-MOM-MGC-Long

### cluster_4 (1 members)
- **Entry types:** crossover
- **Risk models:** atr_adaptive
- **Members:** VWAP-006-MES-Long

### cluster_5 (2 members)
- **Entry types:** mean_reversion, squeeze_release
- **Risk models:** atr_adaptive
- **Members:** RVWAP-MR-MES-Both, BBKC-SQUEEZE-MES-Both

### cluster_6 (1 members)
- **Entry types:** pullback
- **Risk models:** fixed_points
- **Members:** ICT-010-MES-Both

### cluster_7 (1 members)
- **Entry types:** breakout
- **Risk models:** compression_based
- **Members:** ORION-VOL-MES-Both

## DNA Type Distribution

### Entry Types

| Type | Count | Strategies |
|------|-------|-----------|
| breakout | 2 | ORB-009-MGC-Long, ORION-VOL-MES-Both |
| crossover | 1 | VWAP-006-MES-Long |
| gap_signal | 1 | GAP-MOM-MGC-Long |
| mean_reversion | 1 | RVWAP-MR-MES-Both |
| pullback | 2 | PB-MGC-Short, ICT-010-MES-Both |
| regime_detection | 1 | VIX-Channel-MES-Both |
| squeeze_release | 1 | BBKC-SQUEEZE-MES-Both |

### Overrepresented Types

- **pullback** (2 strategies) — adding more of this type has diminishing portfolio value
- **breakout** (2 strategies) — adding more of this type has diminishing portfolio value

### Missing DNA Types


### Structural Gaps (beyond current schema)

- trend_following — no dedicated trend strategy (EMA/SuperTrend/Donchian)
- overnight — no globex/overnight session strategies
- event_driven — no CPI/FOMC/NFP targeted strategies
- pairs — no inter-market spread strategies
- higher_timeframe — all strategies operate on 5m only

## Component Donor Analysis

Rejected strategies with reusable structural components:

### ORION-VOL-MES-Both
- **Reusable component:** ana_gagua. Compression box concept (tightness + flatness filters) is structurally interesting. Box breakout is similar to ORB-009 in shape but triggered by compression, not time. Failed on MES/MNQ. Compression filters could be reused as entry components.

### BBKC-SQUEEZE-MES-Both
- **Reusable component:** LazyBear classic. Gross PF=1.49 but 1,295 trades × $3.74/RT = 50% friction impact. Momentum color state machine (lime/green/red/maroon) is unique exit logic. Structurally similar to ORION-VOL (both are compression→expansion). Component value: squeeze detection + momentum states could enhance other strategies.

## Recommendations

### For Portfolio Construction
1. The three validated/candidate strategies (PB-Short, ORB-009, VIX Channel) are **genuinely structurally distinct**. Portfolio diversity is real, not cosmetic.
2. ORION-VOL and BBKC-SQUEEZE are structurally similar (compression→breakout). Both failed. Avoid adding more compression breakout strategies.
3. VWAP-006 and RVWAP-MR share the VWAP-based entry DNA. Both failed due to friction. VWAP entry alone is insufficient on 5m futures.

### For Future Harvesting
1. **Prioritize missing DNA types**: trend_following, overnight, event_driven
2. **Avoid overrepresented types**: breakout (2 strategies), pullback (2 strategies) — adding more has diminishing returns
3. **Regime gap harvest**: target LOW_VOL + RANGING specialists (only VIX Channel covers this)

### For Evolution Engine
1. **ORION-VOL compression filters** (tightness + flatness) could enhance ORB-009 entries
2. **BBKC-SQUEEZE momentum state machine** (lime/green/red/maroon) is a unique exit logic worth testing on validated strategies
3. **ICT-010 sweep detection** is structurally unique but needs better confirmation filters — not the pullback entry itself

---
*Generated by build_dna_profiles.py*