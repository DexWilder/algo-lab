# Prototype Sprint — 5 Candidates

*Selected by portfolio gap analysis. Each fills a different hole.*
*Date: 2026-04-06*

---

## Selection Criteria

- Low overlap with current core/probation
- Fills a gap: factor, session, asset, direction, or horizon
- Testable with current data (no new data purchases)
- Fast first-pass backtest possible (~30 min each)

## Current Gaps Being Targeted

| Gap | Candidate |
|-----|-----------|
| Non-morning session | #1 MCL Settlement Reversion |
| Non-equity + short-bias | #1 MCL Settlement Reversion |
| Mean reversion stabilizer | #2 IBS-MR-M2K |
| Daily horizon diversification | #2 IBS-MR-M2K |
| Vol-expansion (non-equity) | #3 HVPercentile on MCL/MGC |
| M2K short exposure | #4 RSI2-Bounce-M2K (both dir) |
| Crossbred child | #5 ATR-filtered VWAP-MNQ |

---

## Candidate 1: MCL Settlement Window Reversion

**Thesis:** Crude oil (MCL) has a settlement window around 14:30 ET.
The same afternoon reversion mechanism validated on ZN (+0.48 PF with
ATR filter) may exist on energy. This fills the Energy asset gap AND
the afternoon session gap simultaneously.

**Why it helps:** Energy = 0 strategies. Afternoon = 1 strategy (ZN only).
Short-biased reversion on MCL would add 3 gap fills at once.

**Regime role:** Stabilizer / afternoon diversifier

**Data:** MCL 5m available, 6.7 years. Session window 14:00-15:00 ET.

**Method:** Same falsification design as ZN — test 3 variants
(settlement window, generic afternoon, unconditional) to see if the
settlement window is special.

---

## Candidate 2: IBS Mean-Reversion M2K (Daily)

**Thesis:** Internal Bar Strength (IBS = (close-low)/(high-low)) on
daily bars. When IBS is very low (close near the low), next day tends
to reverse up. Documented 78% win rate on broad indices. M2K's thin
liquidity may amplify the signal.

**Why it helps:** Daily horizon (reduces 5m concentration). MEAN_REVERSION
factor. M2K adds to a different asset than current MR strategies.
Both-direction capability adds short exposure.

**Regime role:** Stabilizer (daily mean reversion)

**Data:** M2K 5m available, resample to daily. 6.7 years.

**Method:** Simple: IBS < 0.2 → long next day, IBS > 0.8 → short next
day. Exit at close. Fixed time hold (1 day).

---

## Candidate 3: HV Percentile Expansion on MCL

**Thesis:** When realized volatility drops to extreme lows (bottom 10th
percentile of its 1-year range), the next vol expansion tends to be
directional. Trade the breakout when vol starts expanding from
compression. Different from BB/KC squeeze — uses realized vol percentile
instead of bandwidth.

**Why it helps:** VOLATILITY factor (thin — 1 probation). Energy asset
(0 strategies). Both-direction.

**Regime role:** Tail engine (vol expansion)

**Data:** MCL 5m available, 6.7 years.

**Method:** Compute 20-day realized vol percentile rank over 252 days.
When percentile drops below 10th, watch for breakout. Entry on first
daily close outside the compression range. Exit on vol mean-reversion
or 3x ATR target.

---

## Candidate 4: RSI2-Bounce on M2K (Both Directions)

**Thesis:** RSI(2) extreme oversold (< 10) bounces are documented on
Russell 2000. The micro future (M2K) should show the same behavior.
Test both directions: long on RSI < 10, short on RSI > 90.

**Why it helps:** M2K adds direction balance (current M2K strategies
are all short). Both-direction test. Mean reversion factor.

**Regime role:** Stabilizer

**Data:** M2K 5m available, resample to daily. 6.7 years.

**Method:** Daily RSI(2). Long when RSI < 10, exit when RSI > 60.
Short when RSI > 90, exit when RSI < 40. Fixed 1 contract.

---

## Candidate 5: ATR-Filtered VWAP-MNQ (Crossbred Child)

**Thesis:** The ATR vol regime filter (+0.48 PF on ZN-Afternoon, +0.12
on VWAP-MNQ) is a validated component. Test it as a formal child of
VWAP-MNQ-Long — same entry logic, but only trade when ATR > 70th
percentile. This is an assembled strategy, not a discovered one.

**Why it helps:** Tests whether validated components actually improve
parents in practice (not just backtest). Proves the component catalog
works. VWAP-MNQ is a core workhorse — improving it is high-leverage.

**Regime role:** Enhanced workhorse (fewer trades, higher quality)

**Data:** MNQ 5m available. Same data as current strategy.

**Method:** Run VWAP-MNQ-Long with and without the ATR filter. Compare
PF, trade count, walk-forward stability.

---

## Sprint Execution Order

| # | Candidate | Est. Time | Priority |
|---|-----------|----------|----------|
| 1 | MCL Settlement Reversion | 45 min | Highest (3 gaps) |
| 2 | IBS-MR-M2K | 30 min | High (daily MR) |
| 3 | HV Percentile MCL | 45 min | High (Energy + VOL) |
| 4 | RSI2-Bounce M2K | 30 min | Medium |
| 5 | ATR-Filtered VWAP-MNQ | 20 min | Medium (assembly test) |
