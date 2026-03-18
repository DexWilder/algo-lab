# Implementation Plan: Carry Lookup Table v1

*Highest-leverage unlock in the blocked-unlock roadmap (Leverage #1).*
*This is a PLAN. Do not build until approved.*

---

## 1. Scope: What v1 Is and Isn't

**v1 is:** A minimal, single-file carry signal lookup that provides a
daily carry score per asset using only data we already have. No new data
purchases. No new Databento fetches. Derivations and static tables only.

**v1 is NOT:** A full multi-contract term-structure engine. That's v2,
and it requires front/back contract data we don't have yet.

**Design target:** Replace the 60-day return proxy in `commodity_carry_proxy`
with a cleaner carry signal on the assets where we can compute one, and
provide a carry ranking function for cross-asset strategies.

---

## 2. Assets Covered in v1

| Asset Class | Assets | Carry Signal Source | Method |
|-------------|--------|---------------------|--------|
| **FX** | 6J, 6E, 6B | Interest rate differential | Static quarterly rate table (free, hardcoded) |
| **Rates** | ZN, ZF, ZB | Yield slope + rolldown estimate | Price-to-yield formula + static roll calendar |
| **Commodity** | MCL, MGC | 60-day proxy (no change from current) | Retain existing proxy until v2 brings front/back data |
| **Equity** | MES, MNQ | Not included in v1 | Needs dividend yield + financing rate (deferred) |

### Why This Order

- **FX is the cheapest win.** Interest rate differentials are public,
  stable (change quarterly), and can be hardcoded in 30 minutes. The
  6J strategies already benefit from a carry bias filter — this formalizes
  and centralizes it.

- **Rates are derivable.** We have ZN/ZF/ZB daily prices. Yield can be
  estimated from price using the CME DV01/coupon convention. Rolldown
  can be approximated from the maturity schedule. This is formula work,
  not a data purchase.

- **Commodities stay on the proxy** until v2. The 60-day return proxy
  is already being tested via `commodity_carry_proxy`. We can't improve
  it without front/back spread data. But the lookup table still registers
  the commodity carry score (from the proxy) so that cross-asset ranking
  works.

- **Equity is deferred.** Dividend yield and financing rate require
  external data feeds. Low priority because equities are not a carry
  gap — they're the overcrowded asset class.

---

## 3. Inputs and Data Sources

### FX Carry (Static Rate Table)

```python
# Updated quarterly. Source: central bank published rates.
FX_RATES = {
    "6J": {"domestic": "USD", "foreign": "JPY",
           "domestic_rate": 0.045, "foreign_rate": -0.001},
    "6E": {"domestic": "USD", "foreign": "EUR",
           "domestic_rate": 0.045, "foreign_rate": 0.025},
    "6B": {"domestic": "USD", "foreign": "GBP",
           "domestic_rate": 0.045, "foreign_rate": 0.045},
}
# Carry score = domestic_rate - foreign_rate
# 6J carry = 0.045 - (-0.001) = +0.046 (positive = long USD/short JPY)
# 6E carry = 0.045 - 0.025 = +0.020 (positive = long USD/short EUR)
# 6B carry = 0.045 - 0.045 = 0.000 (neutral)
```

**Update cadence:** Manual, quarterly, after central bank decisions.
**Source:** Fed, ECB, BOJ, BOE published policy rates (public, free).

### Rates Carry (Price-Derived Yield + Rolldown)

```python
# CME convention for price-to-yield approximation
TREASURY_PARAMS = {
    "ZN": {"coupon": 0.06, "maturity_years": 10, "dv01": 78.0},
    "ZF": {"coupon": 0.06, "maturity_years": 5,  "dv01": 47.0},
    "ZB": {"coupon": 0.06, "maturity_years": 30, "dv01": 195.0},
}

# Yield estimate from price:
#   yield ≈ coupon + (100 - price) / maturity_years
# This is a rough linear approximation. Adequate for ranking.

# Rolldown estimate:
#   rolldown_per_month ≈ yield_slope / (12 * maturity_years)
#   where yield_slope = yield(ZB) - yield(ZN) (crude but directional)

# Carry score = yield + rolldown - financing_rate
# financing_rate ≈ Fed Funds rate (hardcoded quarterly)
```

**What this gives us:** A daily carry score for ZN, ZF, ZB that tells us
which tenor has the best carry. Positive = worth holding. Negative = costs
to hold. The ranking across tenors enables the Treasury Rolldown Carry
strategy (#45).

**Accuracy:** This is a first-order approximation. Real rates desks use
Bloomberg yield curves. But for ranking tenors relative to each other,
the approximation is sufficient — we need the direction, not the bps.

### Commodity Carry (Proxy — Unchanged)

```python
# Same 60-day return proxy from commodity_carry_proxy/strategy.py
# carry_score = close.pct_change(60)
# Retained for cross-asset ranking compatibility
# Replaced by front/back spread in v2
```

---

## 4. Storage and Maintenance

### File Location

```
engine/carry_lookup.py          # The lookup module
engine/carry_rates.json         # Static rate table (versioned, quarterly)
```

### Module Interface

```python
# engine/carry_lookup.py

def get_carry_score(asset: str, price_series: pd.Series = None,
                    date: str = None) -> float:
    """Return the current carry score for an asset.

    For FX: uses static rate differential (no price_series needed).
    For rates: derives yield from price_series, computes carry.
    For commodities: computes 60-day return proxy from price_series.

    Returns a float: positive = carry-positive, negative = carry-negative.
    Magnitude is comparable across asset classes (annualized %).
    """

def rank_carry(assets: list, price_data: dict = None,
               date: str = None) -> list:
    """Rank assets by carry score, highest to lowest.

    Returns list of (asset, carry_score) tuples.
    Used by cross-asset carry strategies for position assignment.
    """

def get_carry_table(date: str = None) -> dict:
    """Return full carry lookup table for all supported assets.

    Returns {asset: carry_score} dict.
    """
```

### Maintenance Rules

- `carry_rates.json` updated manually after each central bank meeting
  (Fed, ECB, BOJ, BOE — roughly 8 decisions/year each)
- Treasury params updated if CME changes contract specs (rare)
- Claude can update the rate table during Monday sessions when a
  central bank decision has occurred since last update
- A staleness check warns if rates are >100 days old

---

## 5. Ideas Unlocked or Improved

### Immediately Improved (v1)

| Idea | Current State | What v1 Enables |
|------|--------------|-----------------|
| **Commodity-TermStructure-Carry** (in testing) | 60-day proxy, carry/momentum conflated | No change to commodity signal, but cross-asset ranking now uses real carry for FX/rates alongside commodity proxy |
| **MomPB-6J-Long-US** (probation) | Carry bias filter is ad-hoc 60-day return | Replace with formal FX carry score from rate differential. Cleaner signal. |
| **FXBreak-6J-Short-London** (probation) | No carry awareness | Can add carry-direction filter: prefer shorts when JPY carry is negative |

### Unblocked from `blocked` to `testable` (v1)

| Idea | Blocker Removed | What Becomes Possible |
|------|-----------------|----------------------|
| **Treasury-Rolldown-Carry-Spread** (#45) | `blocked_by_data_pipeline` → resolved | Can rank ZN/ZF/ZB by estimated carry, build duration-neutral spread. First-pass testable. |
| **FX-Carry-Trade** (#2) | `blocked_by_data` partially resolved | FX leg fully testable with rate differential. Bond/commodity legs still blocked. |

### Partially Improved (v1 helps, v2 completes)

| Idea | What v1 Does | What Still Needs v2 |
|------|-------------|---------------------|
| **ManagedFutures-Carry-Diversified** (#41) | FX + rates legs become testable | Commodity + equity legs still need front/back data + dividend yields |
| **Commodity-Carry-TailRisk-Overlay** (#43) | Stress filter can be built on existing vol data | Commodity carry leg still needs front/back spreads |

---

## 6. v1 vs v2 Comparison

| Dimension | v1 (This Plan) | v2 (Future) |
|-----------|---------------|-------------|
| **Data required** | None new. Existing prices + static tables | Front/back contract data from Databento (~$100-200) |
| **Cost** | $0 | ~$100-200 + ongoing |
| **Engineering time** | ~1 day | ~3-5 days |
| **FX carry** | Real (rate differential) | Same |
| **Rates carry** | Approximate (price-derived yield + rolldown) | Real (if Bloomberg/external yield curve added) |
| **Commodity carry** | Proxy (60-day return, momentum-conflated) | Real (front/back spread, pure term-structure) |
| **Equity carry** | Not included | Dividend yield + financing rate |
| **Cross-asset ranking** | Mixed (real FX + approximate rates + proxy commodities) | Full (all asset classes use real carry inputs) |
| **Ideas fully unblocked** | 2 (Treasury-Rolldown, FX-Carry partial) | 4+ (adds Commodity-TS-Carry, Carry-TailRisk, full Diversified MF) |

### v2 Trigger

Build v2 when:
- v1 has been live for 2+ weeks
- At least one v1-enabled strategy enters testing with real carry signal
- The commodity_carry_proxy first-pass shows the signal has promise
  (SALVAGE or better) and decomposition is the natural next step
- Budget for Databento front/back contract data is approved

---

## 7. 2-Week Verification Plan

Per the blocked-unlock roadmap rule: "Verify within 2 weeks that at
least one unblocked idea enters testing."

### Week 1 (Build + Quick Test)

- [ ] Build `engine/carry_lookup.py` with FX rates, treasury yield
      estimation, and commodity proxy passthrough
- [ ] Create `engine/carry_rates.json` with current central bank rates
- [ ] Unit test: `get_carry_score()` returns sensible values for all
      supported assets
- [ ] Integration test: `rank_carry()` produces a cross-asset ranking
      that makes economic sense (6J should show strong positive carry,
      ZB rolldown should be estimable)
- [ ] Update `commodity_carry_proxy/strategy.py` to optionally use
      `carry_lookup` instead of raw 60-day return (toggle, not replace)
- [ ] Update MomPB-6J carry bias filter to use formal lookup instead
      of ad-hoc 60-day return

### Week 2 (First Unblocked Idea Enters Testing)

- [ ] Write spec for Treasury-Rolldown-Carry-Spread using v1 carry
      lookup yields
- [ ] Convert to strategy.py using `carry_lookup.rank_carry()` for
      tenor ranking
- [ ] Run batch_first_pass on Treasury-Rolldown-Carry-Spread
- [ ] Update registry: Treasury-Rolldown-Carry-Spread from
      `blocked_by_data_pipeline` to `testing`
- [ ] Log the leverage result: was the unlock worth it?

### Success Criteria

The unlock is verified as worthwhile if:
1. Treasury-Rolldown-Carry-Spread enters testing within 2 weeks
2. The carry lookup produces economically sensible rankings
   (not just random numbers)
3. At least one existing strategy (MomPB-6J or commodity_carry_proxy)
   shows different behavior with the real carry signal vs the proxy

### Failure Criteria

The unlock was lower-leverage than expected if:
1. Treasury-Rolldown-Carry-Spread fails first-pass (PF < 1.0)
   AND the carry rankings don't improve any existing strategy
2. The yield approximation is too noisy to produce meaningful rankings
3. No idea enters testing within 2 weeks of completion

If failure: log the lesson, don't build v2 until the signal quality
issue is understood.
