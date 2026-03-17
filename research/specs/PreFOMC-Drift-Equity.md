# Strategy Spec: PreFOMC-Drift-Equity

## Hypothesis
Equity indices drift higher in the ~24 hours before scheduled FOMC announcements. This is one of the most documented calendar anomalies in finance (Lucca & Moench, NY Fed 2015). The effect is attributed to pre-announcement positioning, hedging unwinds, and risk premium compression as uncertainty resolves. The drift occurs before the announcement, not after — making it a pure calendar/anticipation trade, not a reaction trade.

## Entry
- Condition 1: FOMC announcement is scheduled for tomorrow (8 scheduled meetings per year, dates known in advance)
- Condition 2: Enter long at the close of the day BEFORE the FOMC announcement day (approximately 24 hours before the 14:00 ET announcement)
- Condition 3: No directional filter needed — the hypothesis is that the drift is positive regardless of what the Fed ultimately decides
- Direction: long only

## Exit
- Primary: exit at 13:55 ET on FOMC announcement day (5 minutes before the 14:00 ET release — capture the drift, avoid the announcement volatility)
- Alternative: exit at the close of FOMC announcement day (captures any post-announcement continuation, but adds announcement risk)
- Stop: 1.5x ATR(20) below entry (protect against unusual pre-FOMC selloff)
- No trailing stop (hold through the drift window, don't get shaken out by noise)

## Event Window
- FOMC meetings: 8 per year (January, March, May, June, July, September, November, December)
- Entry: close of trading day before FOMC day (~16:00 ET day before)
- Exit: 13:55 ET on FOMC day (or close of FOMC day for v2 test)
- Hold period: approximately 22 hours
- Total trades per year: ~8

## Assets
- Primary: MES (Micro E-mini S&P 500)
- Test also: MNQ (Nasdaq — may show stronger or weaker effect)

## Parameters (initial)
- FOMC_DATES: hardcoded list of FOMC announcement dates (known calendar, published by Federal Reserve)
- ENTRY_TIME: close of day before FOMC (last bar before 16:00 ET)
- EXIT_TIME: 13:55 ET on FOMC day (before 14:00 announcement)
- ATR_LEN: 20
- SL_ATR_MULT: 1.5
- EXIT_VARIANT: "pre_announcement" (13:55) vs "close" (16:00) — test both

## Source
- Lucca & Moench (2015): "The Pre-FOMC Announcement Drift" — NY Federal Reserve Staff Report
- Quantpedia: documented as a tradeable anomaly
- Registry notes: prior PreFOMC-Drift was rejected at PF 0.72 on MES — that version likely had different timing or included non-FOMC events. This version is strictly FOMC-only.

## Important Notes
- FQL already has a rejected PreFOMC-Drift (PF 0.72). The prior version may have included broader event windows or different entry/exit timing. This spec is intentionally narrower: FOMC only, entry day-before close, exit pre-announcement.
- With only ~8 trades per year and ~2 years of data, we get ~16 trades. This is below the normal validation threshold (30+). Classification will likely be MONITOR or SAMPLE_INSUFFICIENT rather than ADVANCE.
- The real value is the factor: pure EVENT with zero momentum correlation. Even if not immediately promotable, it proves the EVENT factory pipeline works.

## Diversification Role
- **Factor:** Pure EVENT — calendar-driven anticipation, not price patterns or momentum
- **Correlation to existing portfolio:** Near zero. The pre-FOMC drift fires on 8 specific dates regardless of trend, momentum, or regime.
- **Session:** Overnight hold (close-to-close), different from all intraday strategies
- **Expected contribution:** Opens the EVENT factor sleeve. Even at low trade count, each trade is an independent bet uncorrelated to everything else in the portfolio.
