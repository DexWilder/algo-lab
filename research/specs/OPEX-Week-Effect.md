# Strategy Spec: OPEX-Week-Effect

## Hypothesis
Equity indices tend to rise during the week of monthly options expiration (third Friday of each month). The mechanism is dealer gamma hedging: as options approach expiration, dealers who are short gamma must buy stock as prices rise and sell as prices fall, creating a stabilizing force that tends to push prices higher in a positive-gamma environment. This "pin" or "drift higher" effect is well-documented in academic and practitioner literature.

## OPEX Calendar Logic
- **OPEX day:** Third Friday of each month
- **OPEX week:** Monday through Friday of the week containing the third Friday
- **Entry:** Monday open of OPEX week
- **Exit:** Friday close of OPEX week (after expiration)
- **Frequency:** 12 events per year (every month)
- **Calendar construction:** third Friday = first Friday on or after the 15th of the month

## Entry
- Condition 1: Today is Monday of OPEX week
- Condition 2: Enter long at RTH open (~09:35 ET, first bar after 09:30)
- Condition 3: No directional filter in v1 — the hypothesis is the drift is positive regardless of trend
- Direction: long only (test short as comparison)

## Exit
- Primary: close of OPEX Friday (~15:55 ET)
- Alternative: close of Thursday before OPEX (exit before the actual expiration day to avoid pin risk)
- Stop: toggle — test with no stop and with 2.0x ATR stop (wider for weekly hold)
- No trailing stop — fixed-window weekly hold

## Target Assets
- Primary: MES (S&P 500 — most options volume, strongest gamma effect)
- Secondary: MNQ (Nasdaq — may show different OPEX dynamics)

## Parameters (initial)
- OPEX_WEEK_ENTRY: Monday open of OPEX week (09:35 ET)
- EXIT_VARIANT: "friday_close" or "thursday_close"
- USE_STOP: toggle (True/False)
- ATR_LEN: 20
- SL_ATR_MULT: 2.0 (wider for weekly hold)

## Source
- Academic: multiple studies on options expiration effects (Ni, Pearson, Poteshman 2005)
- Quantpedia: "OPEX Week Trading Strategy"
- QuantifiedStrategies: documented SPY OPEX week positive bias
- Registry: OPEX-Week-Effect accepted as idea, EVENT priority

## Key Failure Mode to Watch
- **Bear markets:** The OPEX drift-higher effect may reverse in strong bear markets where dealers are in negative gamma (must sell into declines). 2022 bear market would be the key test.
- **Monthly variation:** Not every OPEX week drifts higher. Some months have strong directional moves that overwhelm the gamma effect. Year-by-year stability is critical.
- **Overlap with PreFOMC:** Some FOMC meetings fall during OPEX week. Need to check whether the OPEX effect is distinct from or conflated with the pre-FOMC drift.

## Important Notes
- With ~12 events/year and 6.7 years of data: ~80 trades. Good sample size.
- Weekly hold means larger per-trade PnL swings than overnight or intraday strategies.
- The OPEX effect is likely partially explained by the equity long premium — need to test whether OPEX weeks outperform random weeks, not just whether they're positive.

## Diversification Role
- **Factor:** EVENT — calendar-driven options expiration dynamics
- **Distinctness from PreFOMC/NFP:** Different mechanism (dealer hedging vs Fed anticipation vs employment data). Different calendar (monthly third Friday vs 8x FOMC vs first Friday NFP). Different hold period (weekly vs overnight vs multi-day).
- **Session:** Weekly hold (Monday open to Friday close) — longest hold in the EVENT sleeve
- **Expected contribution:** Third EVENT type in the portfolio. Proves EVENT works across three different mechanisms (anticipation, data reaction, options flow).
