# NFP surprise series — status: DATA_VENDOR_REQUIRED

**Date:** 2026-06-04
**Approval:** OK pull NFP surprise series (#32, operator 2026-06-04)
**Result:** DATA_VENDOR_REQUIRED — not pulled this cycle.

## What's needed

For the EVT-NFP-MGC-Long-2h paper packet C dimension (event-subtype split), the inputs are:

| Field | Vendor status |
|---|---|
| Actual NFP headline (monthly change, ths) | ✅ Free at BLS — https://www.bls.gov/ces/data/ |
| Actual unemployment rate | ✅ Free at BLS |
| Actual average hourly earnings (MoM/YoY) | ✅ Free at BLS |
| **Consensus expectations (Bloomberg / Reuters)** | ❌ **Paid vendor required** |
| Surprise series (actual − consensus) | ❌ Derived; depends on consensus |
| Beat/miss/inline classification | ❌ Derived; depends on consensus |

## Why not pulled

Per operator directive: "if consensus data is not clean/free/fast, report DATA_VENDOR_REQUIRED instead of overbuilding. Do not let this become a paid-data rabbit hole."

The BLS actuals are free. The blocker is consensus — which is owned by paid economic-data vendors (Bloomberg ECON, Reuters Estimates, Refinitiv, FactSet). Free aggregators (MarketWatch, Investing.com calendar) exist but require scraping and are inconsistent across years.

## Available free proxies (NOT pulled; flagged for operator decision)

If a paid consensus feed is not in budget, the next-best free proxies are:

1. **Trailing-trend baseline**: classify each NFP release by whether actual headline ≷ trailing 6-month average. This is a regime split (above-trend vs below-trend payrolls) not a surprise split. Useful but different.
2. **Same-direction-as-prior**: classify by whether actual is in the same direction as prior month's surprise (carry-over).
3. **Magnitude bucket**: split releases by absolute deviation from 12-month rolling mean.

These would be **diagnostic regime splits**, not true consensus-surprise classification. Worth running IF operator agrees they're useful, but they don't fully close the C-dimension as defined.

## Recommendation

For paper-readiness packet finalization:
- **Option A (cheapest):** Operator decides to ship the packet without consensus-conditioned split; document the gap as "thesis is direction-blind by design; positive unconditional drift is the basis, not surprise direction."
- **Option B (full close):** Operator authorizes a one-time vendor pull (Bloomberg ECON or equivalent) for NFP consensus history 2019-2026 to enable beat/miss/inline split.
- **Option C (proxy):** Operator authorizes the trailing-trend-baseline proxy classification as a diagnostic regime split — close C as a partial close.

**This file is the v1 status flag. No data pulled. No fabricated values stored.**
