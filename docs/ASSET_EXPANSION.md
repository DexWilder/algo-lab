# Asset Expansion Framework

*How to onboard new assets into FQL and run the first research batch.*
*Last updated: 2026-03-16*

---

## Why This Matters

FQL currently trades 3 primary assets (MES, MNQ, MGC) with ~0.85-0.95 correlation
between MES and MNQ. This gives ~2-3 independent bets across 6 strategies.

Adding low-correlation asset classes (rates, FX, agriculture) is the single
highest-impact improvement for risk-adjusted returns. Portfolio Sharpe scales
with sqrt(independent_bets).

---

## Expansion Batches

### Batch 1: Rates + FX (highest priority)

| Symbol | Name | Class | Correlation to Equities | Status |
|--------|------|-------|------------------------|--------|
| ZN | 10-Year Treasury Note | rate | ~0.0-0.3 | data available |
| ZB | 30-Year Treasury Bond | rate | ~0.0-0.3 | data available |
| ZF | 5-Year Treasury Note | rate | ~0.0-0.3 | planned |
| 6E | Euro FX | fx | ~0.1-0.4 | planned |
| 6J | Japanese Yen | fx | ~-0.1-0.2 | planned |
| 6B | British Pound | fx | ~0.1-0.3 | planned |

### Batch 2: Agriculture + Commodities

| Symbol | Name | Class | Correlation to Equities | Status |
|--------|------|-------|------------------------|--------|
| ZC | Corn | agriculture | ~0.0-0.2 | planned |
| ZS | Soybeans | agriculture | ~0.0-0.2 | planned |
| ZW | Wheat | agriculture | ~0.0-0.2 | planned |
| SI | Silver | metal | ~0.2-0.5 | planned |
| HG | Copper | metal | ~0.3-0.6 | planned |

---

## Asset Onboarding Checklist

For each new asset, complete these steps in order:

### 1. Configuration
- [ ] Add asset to `engine/asset_config.py` with all fields
- [ ] Verify point_value, tick_size, commission, session hours
- [ ] Set status to "planned" initially

### 2. Data
- [ ] Add Databento symbol to `data/databento_loader.py`
- [ ] Run `python3 data/databento_loader.py --symbol {SYM}` to fetch 1m data
- [ ] Run `python3 scripts/update_daily_data.py --symbol {SYM}` to resample to 5m
- [ ] Verify data integrity: check for gaps, correct session hours, reasonable prices
- [ ] Update status to "available" in asset_config.py

### 3. Regime Baseline
- [ ] Run regime engine on new asset: `RegimeEngine().classify(df)`
- [ ] Verify regime distribution is reasonable (not all one category)
- [ ] Document regime characteristics vs equity index behavior

### 4. Discovery Batch
- [ ] Run existing strategy families against new asset
- [ ] Use batch validation: `python3 research/batch_harvest_validation.py --asset {SYM}`
- [ ] Log results in registry (even failures — institutional memory)

### 5. Validation
- [ ] Run validation battery on promising candidates
- [ ] Confirm asset family cross-validation works (ASSET_FAMILIES in asset_config.py)
- [ ] Check correlation with existing portfolio strategies

### 6. Promotion
- [ ] Strategy passes validation battery (score >= 7.0)
- [ ] Portfolio contribution is positive (marginal Sharpe > 0)
- [ ] Correlation with existing portfolio < 0.3
- [ ] Update status to "active" in asset_config.py

---

## Data Requirements

### Per Asset
- Minimum 2 years of 1-minute data (for 5m resampling)
- Continuous contract (front-month roll)
- Clean session boundaries
- No significant gaps during regular trading hours

### Data Source
- **Primary:** Databento (1m bars, continuous contracts)
- **Symbols:** Use `.c.0` suffix for continuous front-month
- **Storage:** `data/databento/{SYMBOL}/` (1m), `data/processed/{SYMBOL}_5m.csv` (5m)

### Cost Estimate
- Databento: ~$5-15/month per additional instrument
- Storage: negligible (~50MB per year per asset at 5m bars)

---

## What's Already Asset-Agnostic (no changes needed)

These modules work with any asset out of the box:
- `engine/backtest.py` — accepts symbol parameter, configurable costs
- `research/validation/run_validation_battery.py` — uses ASSET_CONFIG + ASSET_FAMILIES
- `research/fql_research_scheduler.py` — runs jobs on whatever strategies exist
- `research/portfolio_regime_controller.py` — scores any strategy in registry
- `research/allocation_tiers.py` — asset-independent sizing
- `research/strategy_state_machine.py` — asset-independent lifecycle

## What Needs Minor Updates

- `data/databento_loader.py` — add new symbols to SYMBOLS dict
- `scripts/update_daily_data.py` — add new symbols to processing loop
- Strategy implementations — some may need session/tick_size adjustments

---

## Expected Impact

Adding 3 FX strategies + 2 rate strategies (uncorrelated to equities):
- Current independent bets: ~2-3
- New independent bets: ~5-7
- Expected Sharpe improvement: 40-80% (sqrt scaling)

This is the highest-ROI improvement available to FQL.
