# Pre-Check: Treasury-Cash-Close-Reversion-Window

**Date:** 2026-03-20
**Purpose:** Go/no-go verdict before writing strategy.py

---

## 1. Data Sufficiency

### Bar Coverage in the 14:45-15:30 Window

| Bar Time | ZN Coverage (weekdays) | ZB Coverage (weekdays) | MES Control |
|----------|----------------------|----------------------|-------------|
| 14:45 (entry) | 82.4% | 78.6% | 94.2% |
| 14:50 | 82.3% | 78.6% | 94.2% |
| 14:55 | 84.1% | 80.6% | 94.2% |
| 15:00 | 82.5% | 79.5% | 94.2% |
| 15:05 | 81.5% | 78.3% | 94.2% |
| 15:10 | 80.6% | 77.8% | 94.2% |
| 15:15 | 82.1% | 77.4% | 94.2% |
| 15:20 | 80.4% | 78.2% | 94.2% |
| 15:25 (exit) | 80.3% | 77.4% | 94.2% |
| 15:30 | 79.9% | 78.3% | 94.2% |

### Root Cause of Missing Bars

- **Not session truncation.** 640 of 682 missing-15:25 days have data
  AFTER 15:25 — the bars exist elsewhere in the session but not at 15:25
  exactly. This is a **sparse bar problem**, not a session-end problem.

- **Not weekends.** 338 of 682 missing days are Sundays (globex-only,
  expected). The remaining 344 are weekdays with genuinely missing bars.

- **The pattern is consistent across years.** 2020-2026 weekday coverage
  at 15:25 is 79.8% — no improvement over time. This is a structural
  property of ZN/ZB Databento data, not a transient gap.

- **Cause: low-volume 5m bars.** Treasury futures have lower tick volume
  than equity micros. When volume is thin in a 5-minute window, Databento
  may not produce a bar. ZN averages 5,714 contracts at 15:25 vs MES
  which is rarely below 10,000. ZB is worse at 1,460 avg.

### Usable Days

| Metric | ZN | ZB |
|--------|----|----|
| Total weekdays | 1,743 | 1,743 |
| Days with BOTH 14:45 AND 15:25 bars | 1,360 (78%) | ~1,250 (72%) |
| Usable years of data | 5.4 | ~5.0 |
| Expected trades (~20% of usable days) | ~272 | ~250 |
| Days with complete 10-bar window | 1,316 (75%) | 1,287 (74%) |

### Verdict: Data is ADEQUATE but DEGRADED

The data is not clean. 20-25% of weekdays are missing critical bars.
However:
- **1,360 usable days (5.4 years) is sufficient** for a first-pass test
- **272 expected trades** is well above the 30-trade ADVANCE threshold
- The missing days introduce survivorship bias: we can only test days
  when bars exist, which are likely higher-volume days. The strategy
  may look better in backtest than in reality if low-volume days
  (where the close reversion may not work) are systematically excluded.

**This bias must be explicitly noted in the first-pass report.**

---

## 2. Session and Timestamp Risks

### CME Treasury Futures Session Structure

- RTH: 07:20-14:00 CT (08:20-15:00 ET) for cash session
- Globex: 17:00-16:00 CT (18:00-17:00 ET) near-continuous
- **Key: Treasury "cash close" is 15:00 ET (14:00 CT).** This is when
  the cash bond market closes and the fixing occurs.

### Timestamp Alignment Issues

1. **The spec says "14:45-15:00 ET move."** This is the last 15 minutes
   of the cash bond session. The 15:00 ET bar is the close bar.

2. **Entry at 15:01 ET, exit by 15:30 ET.** This is post-cash-close
   trading in the globex continuation. The reversion hypothesis is that
   the cash-close impulse fades once the fixing pressure lifts.

3. **Data is in ET.** Confirmed: bars are timestamped in ET. No timezone
   conversion needed.

### Holiday / Early-Close Risk

- Treasury futures have early closes (13:00 ET) before major holidays.
  These days will have NO bars in the 14:45-15:30 window.
- The strategy should naturally skip these days (no entry bar = no trade).
- Estimated ~10-12 early-close days per year — minor impact.

### Roll Risk

- ZN/ZB roll quarterly (Mar/Jun/Sep/Dec). Continuous contract data from
  Databento uses Panama-canal adjustment.
- Roll dates may produce unusual price action in the close window.
  Estimate ~4 roll days per year where the close reversion signal
  may be contaminated by roll mechanics.
- **Mitigation:** Not worth building a roll-date exclusion filter for
  first-pass. Note in the spec and monitor in first-pass results.

---

## 3. Falsification Design

The first-pass must decompose into 3 variants to separate the reversion
signal from confounds:

### Variant A: True Close-Window Reversion (the hypothesis)

```
Entry: 15:01 ET if 14:45-15:00 move > 1.5x median(20d)
Direction: Fade the 14:45-15:00 move
Exit: 15:30 ET or 60% retracement
```

This is the strategy as specified. It tests whether the cash-close
impulse reverses in the post-close window.

### Variant B: Generic Afternoon Reversion (control)

```
Entry: 14:01 ET if 13:45-14:00 move > 1.5x median(20d)
Direction: Fade the 13:45-14:00 move
Exit: 14:30 ET or 60% retracement
```

Same logic, shifted 1 hour earlier — BEFORE the cash close. If Variant B
performs equally well, the "cash close" part of the hypothesis is noise.
The edge would be generic afternoon mean-reversion, not close-specific.

### Variant C: Unconditional Close-Window Direction (baseline)

```
Entry: 15:01 ET unconditionally (no impulse filter)
Direction: Short if 14:45-15:00 was up, long if down (always fade)
Exit: 15:30 ET
```

No threshold filter. Just fade whatever the pre-close move was.
If Variant C ≈ Variant A, the threshold filter isn't adding value
(same conclusion path as the overnight z-volratio test).

### Advancement Criteria

| Condition | Decision |
|-----------|----------|
| A >> B and A >> C | ADVANCE — true close-specific reversion edge |
| A ≈ B | ARCHIVE — generic afternoon reversion, not close-specific |
| A ≈ C | ARCHIVE — threshold filter doesn't add value |
| A PF < 1.0 | REJECT — no reversion edge at all |

---

## 4. Go / No-Go Verdict

### GO — with explicit caveats

**Rationale:**
- 1,360 usable ZN days (5.4 years) is sufficient for first-pass
- 272 expected trades exceeds all thresholds
- The falsification design is clear and the test is cheap (~30 minutes)
- ZN data quality is better than ZB — test ZN only in first-pass
- The mechanism (cash-close impulse reversal) is testable and falsifiable

**Caveats that must be documented in the first-pass report:**
1. **Survivorship bias from sparse bars.** 20% of weekdays are excluded
   because they lack the required bars. These are likely low-volume days
   where the reversion may behave differently.
2. **ZB is too sparse for reliable testing.** Use ZN only in first-pass.
   ZB can be tested if ZN advances, but its ~1,400 avg volume at 15:25
   makes bar reliability questionable.
3. **Macro release contamination.** The spec mentions excluding days with
   macro releases in the 14:45-15:00 window. For first-pass, skip this
   filter — the falsification variants already control for generic
   afternoon effects. If the strategy advances, add the filter in v2.

### Why Not No-Go

The alternative (next convert-now candidate) would be one of:
- `gap_statistics_regime_filter` — STRUCTURAL, but a filter/enhancement,
  not a standalone strategy
- `mtf_true_gap_breakaway_filter` — same issue, a filter on existing
  gap strategies
- `rth_gap_table_level_interaction` — STRUCTURAL on MES, adds to morning
  crowding
- `spx_lunch_compression_afternoon_release` — testable but MES again

Treasury-Cash-Close-Reversion remains the strongest standalone candidate
because it opens a new asset class (rates) and session (afternoon) where
FQL has zero presence. The data issues are manageable, not disqualifying.

---

## 5. Implementation Guidance (if proceeding)

- **Primary asset:** ZN only (ZB deferred to v2)
- **Skip days with missing 14:45 or 15:25 bars** — do not interpolate
- **Run all 3 falsification variants** before reporting results
- **Note survivorship bias explicitly** in the first-pass output
- **Do not build a macro calendar exclusion filter** for first-pass
- **Probation-only** even if metrics look strong — the data quality
  concern means forward evidence matters more than usual
