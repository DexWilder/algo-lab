# Regime Gate Optimization — Extended Data Analysis

**Date**: 2026-03-14
**Data**: 6.7 years (2019-07 → 2026-03)
**Purpose**: Tighten regime gates to eliminate catastrophic regime cells identified in extended validation.

## Summary

Total potential PnL recovery from improved gating: **~$4,738** (across all 6 strategies).

The strategy controller's `avoid_regimes` lists were calibrated on ~2 years of data.
Extended-history validation revealed additional catastrophic cells that current gates miss.

## Recommended Changes

### 1. VWAP-MNQ-Long
**Problem**: `HIGH_VOL_TRENDING_LOW_RV` — 52 trades, PF=0.552, PnL=-$1,166
- Current gates: `["RANGING"]`
- **No safe single-component gate** — adding "HIGH_VOL" blocks 0 good trades but this is a composite issue
- **Recommendation**: Add composite gate for `HIGH_VOL + LOW_RV` combination
- Or simpler: raise conviction_threshold_outside when HIGH_VOL is active

```python
# Option A: Add HIGH_VOL (blocks 0 profitable cells with >=10 trades on extended data)
"avoid_regimes": ["RANGING", "HIGH_VOL"],

# Option B (conservative): Keep current, rely on portfolio coordination
# This cell is trending (strategy's preferred), just volatile — hard to gate cleanly
```

**Recovery**: ~$1,166

### 2. XB-PB-EMA-MES-Short
**Problem**: `NORMAL_TRENDING_LOW_RV` — 15 trades, PF=0.518, PnL=-$246
- Current gates: `["LOW_VOL", "RANGING"]` — already catch 4 of 5 bad cells
- **Recommendation**: Add `LOW_RV` (blocks 37 good trades but saves $246)

```python
"avoid_regimes": ["LOW_VOL", "RANGING", "LOW_RV"],
```

**Recovery**: ~$246

### 3. ORB-MGC-Long ← BIGGEST WIN
**Problem**: LOW_VOL cells bleed heavily (83 trades, -$777 combined)
- `LOW_VOL_TRENDING_LOW_RV`: 53 trades, PF=0.643, PnL=-$512
- `LOW_VOL_TRENDING_NORMAL_RV`: 30 trades, PF=0.696, PnL=-$265
- Current gates: `["RANGING"]`
- **Recommendation**: Add `LOW_VOL` — blocks 0 good trades (no profitable LOW_VOL cells exist for this strategy)

```python
"avoid_regimes": ["RANGING", "LOW_VOL"],
```

**Recovery**: ~$777 (54% of baseline PnL!)

### 4. Donchian-MNQ-Long-GRINDING ← BIGGEST SINGLE CELL
**Problem**: `HIGH_VOL_TRENDING_HIGH_RV` — 15 trades, PF=0.354, PnL=-$2,199
- Current gates: `[]` (relies on GRINDING filter)
- **Recommendation**: Add `HIGH_RV` — blocks 0 good trades with >=10 samples

```python
"avoid_regimes": ["HIGH_RV"],
```

**Recovery**: ~$2,199 (39% of baseline PnL!)

### 5. BB-EQ-MGC-Long
**Problem**: `NORMAL_TRENDING_HIGH_RV` — 19 trades, PF=0.384, PnL=-$350
- Current gates: `["RANGING", "LOW_RV"]`
- **Recommendation**: Add `HIGH_RV` — blocks 0 good trades for this strategy

```python
"avoid_regimes": ["RANGING", "LOW_RV", "HIGH_RV"],
```

**Recovery**: ~$350

### 6. PB-MGC-Short
- Current gates already sufficient. No changes needed.

## Impact Estimate

| Strategy | Current PnL | Est. Recovery | New Est. PnL | PF Improvement |
|---|---|---|---|---|
| VWAP-MNQ-Long | $6,426 | +$1,166 | $7,592 | 1.26 → ~1.40 |
| XB-PB-EMA-MES-Short | $3,851 | +$246 | $4,097 | 1.27 → ~1.30 |
| ORB-MGC-Long | $1,429 | +$777 | $2,206 | 1.16 → ~1.30 |
| Donchian-MNQ-Long | $5,593 | +$2,199 | $7,792 | 1.60 → ~2.00 |
| BB-EQ-MGC-Long | $2,437 | +$350 | $2,787 | 1.68 → ~1.80 |
| PB-MGC-Short | $339 | +$0 | $339 | 1.13 (unchanged) |
| **TOTAL** | **$20,075** | **+$4,738** | **$24,813** | **+23.6%** |

## Safe vs Risky Gates

**High confidence (zero collateral damage on extended data):**
- ORB-MGC-Long: + `LOW_VOL`
- Donchian-MNQ-Long: + `HIGH_RV`
- BB-EQ-MGC-Long: + `HIGH_RV`

**Medium confidence (minimal collateral):**
- XB-PB-EMA-MES-Short: + `LOW_RV`
- VWAP-MNQ-Long: + `HIGH_VOL`

## Deployment Notes

- `strategy_controller.py` is FROZEN during Track 1 forward validation
- These changes should be applied when the forward freeze lifts
- Alternatively, can be tested in a separate research branch first
- All recommendations are based on 6.7-year extended data, not short-window optimization
