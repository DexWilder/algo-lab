# Strategy Spec: Treasury-CPI-Day-Long

## Hypothesis
Treasury futures tend to rally on CPI release days. The mechanism is that inflation data, even when higher than expected, tends to be priced in by the time of release — and the resolution of uncertainty creates a risk-premium compression that benefits bond longs. Additionally, in tightening cycles, high CPI prints increase expectations of peak rates approaching, which is paradoxically bullish for intermediate/long bonds. This is a rates-native EVENT strategy fundamentally different from equity pre-FOMC drift.

## Event Window
- **CPI release:** Monthly, typically second or third Tuesday/Wednesday of the month at 08:30 ET
- **Frequency:** 12 events per year
- **Entry:** Buy at close of the day BEFORE CPI release (~15:55 ET)
- **Exit:** Close of CPI release day (~15:55 ET) or before next session
- **Hold period:** ~24 hours (overnight through CPI day)
- **Calendar:** CPI dates are published by BLS months in advance

## Entry
- Condition 1: CPI release is scheduled for tomorrow
- Condition 2: Buy ZN (or ZF/ZB) at the last bar before close (~15:55 ET)
- Condition 3: No directional filter — the hypothesis is the rally occurs regardless of the CPI number
- Direction: long only

## Exit
- Primary: sell at close of CPI day (~15:55 ET)
- Stop: toggle — test with no stop and with 1.5x ATR(20) stop
- No trailing stop, no target — fixed-window event hold

## Target Assets
- Primary: ZN (10-Year Treasury Note) — most liquid, benchmark rate instrument
- Secondary: ZF (5-Year) — shorter duration, may show different CPI sensitivity
- Tertiary: ZB (30-Year Bond) — longer duration, higher volatility per move

## Parameters (initial)
- CPI_DATES: hardcoded list of CPI release dates (BLS calendar)
- ENTRY_HOUR: 15, ENTRY_MIN: 55
- EXIT_HOUR: 15, EXIT_MIN: 55 (next day)
- USE_STOP: toggle (True/False)
- ATR_LEN: 20
- SL_ATR_MULT: 1.5

## Source
- Academic: multiple studies document Treasury rally tendency on macro data release days
- OpenClaw harvest note: Treasury-CPI-Day-Long (accepted as idea, EVENT conversion priority #2)
- The CPI-day effect on bonds is distinct from the equity pre-FOMC effect (different asset, different event, different mechanism)

## Key Failure Mode to Watch
- **Rate regime dependency:** The CPI-day Treasury rally may be regime-specific. In aggressive tightening cycles (2022), CPI upside surprises may cause bond selloffs rather than rallies. The hypothesis assumes uncertainty resolution is bullish, but if CPI consistently surprises to the upside in a hawkish regime, bonds sell off.
- **Current data depth:** ZN has ~511 trading days (~2 years). At 12 CPI events/year, that's ~24 trades. Borderline for validation. The $12.59 rates backfill would provide ~80 trades (2019-2026).
- **Test both with and without the backfill data** if possible — but initial test on current data is still informative.

## Important Notes
- This is the first rates-native EVENT strategy. All previous rate attempts (transfer, intraday MR, daily momentum, DualThrust) failed. CPI-day is a fundamentally different approach — event-specific, not pattern-based.
- With only ~24 trades in current data, the result will likely be MONITOR (insufficient sample) or SALVAGE rather than ADVANCE. The strategic value is proving whether rates respond to calendar events even if the pattern-based approaches failed.
- If this shows promise, the $12.59 rates backfill becomes immediately justified — it would triple the sample size.

## Diversification Role
- **Factor:** EVENT — calendar-driven macro release, zero correlation to momentum or structural strategies
- **Asset class:** Rates — the #1 missing asset class in the portfolio (0 active strategies)
- **Distinctness from existing EVENT:** Different event (CPI vs FOMC/NFP), different asset (bonds vs equities), different mechanism (uncertainty resolution vs anticipation drift)
- **Expected contribution:** If it works, this opens both the EVENT factor on rates AND the rates asset class simultaneously. Double diversification value.
