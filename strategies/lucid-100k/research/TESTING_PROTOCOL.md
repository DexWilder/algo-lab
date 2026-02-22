# Lucid 100K — Testing Protocol

## Rules
1. **ONE variable at a time.** Never change multiple settings between tests.
2. **Log every test.** No test is wasted if it's recorded in `test_log.csv`.
3. **Never overwrite rows.** Each test gets a new row, forever.
4. **Baseline first.** No optimization until baseline behavior is understood.
5. **Screenshots required.** Save to the test's research folder.

---

## Test Sequence

### Phase A: Behavior Validation (do this FIRST)

#### Test 1 — Baseline (v6.3 defaults)
- **Folder**: `research/v6.3_baseline/`
- **Settings**: All defaults (paste script, change nothing)
- **Market**: MES1! (CME Micro E-mini S&P)
- **Timeframe**: 5 minute
- **Date range**: 3-6 months (use max available, note exact dates)
- **What to capture**:
  - Screenshot: Strategy Tester → Overview tab (net profit, PF, max DD, trades)
  - Screenshot: Equity curve
  - Screenshot: Settings panel (proof of defaults)
  - CSV export: Strategy Tester → export trades list
  - From status label: days-to-lock, green lock days, halt counts
- **Save all files to**: `research/v6.3_baseline/`
- **Log results in**: `research/test_log.csv`

#### Test 2 — No Green Lock
- **Folder**: `research/v6.3_no_green_lock/`
- **Change**: `p1GreenLockUsd = 0` (only this, nothing else)
- **Everything else**: identical to Test 1
- **Purpose**: Does green-day locking reduce clawback damage?

#### Test 2 Analysis — Compare:
| Metric | With Green Lock | Without | Delta |
|--------|----------------|---------|-------|
| Days-to-lock | ? | ? | ? |
| Max DD | ? | ? | ? |
| Net profit | ? | ? | ? |
| Red days (halts) | ? | ? | ? |
| Avg daily PnL | ? | ? | ? |
| Green lock days | ? | N/A | — |
| Lucid busted? | ? | ? | — |

**Decision**: If green lock improves days-to-lock AND reduces max DD → keep it.

---

### Phase B: Market Regime Tests (after Phase A)

#### Test 3 — Trending Period Only
- Find a 2-3 month window where MES had a clear trend
- Run v6.3 baseline on that window only
- **Purpose**: Is P1 trend-only capturing enough trades?

#### Test 4 — Choppy Period Only
- Find a 2-3 month window where MES was range-bound
- Run v6.3 baseline on that window only
- **Purpose**: Does P1 sit out correctly? Does P2 reversion help?

#### Test 5 — High Volatility (FOMC/CPI heavy month)
- **Purpose**: Do guardrails protect against event-driven spikes?

#### Test 6 — Low Volatility Month
- **Purpose**: Does minStopTicks floor prevent bad entries?

---

### Phase C: Single-Variable Optimization (after Phase B)

Only run these after Phases A and B are complete and logged.

#### Candidates (test ONE at a time):
1. `p1GreenLockUsd`: 400, 600, 800
2. `p2ProfitLockUsd`: 800, 1200, 1600
3. `tpATR_P1`: 1.8, 2.1, 2.5
4. `beR_P1`: 1.0, 1.25, 1.5
5. `adxMin`: 14, 16, 18, 20
6. `revDistATR`: 1.2, 1.4, 1.6
7. `maxTradesP1`: 2, 3
8. `minStopTicks`: 15, 20, 25
9. Power Windows ON vs OFF
10. `revRequireMTF`: ON vs OFF (P2 only, P1 is always off)

#### For each:
- Change ONLY the one parameter
- Same date range as baseline
- Log to `test_log.csv`
- Save to `research/v6.3_{parameter_name}_{value}/`

---

## How to Export from TradingView

1. **Overview screenshot**: Strategy Tester tab → Overview → screenshot
2. **Equity curve**: Strategy Tester tab → make sure equity curve is visible → screenshot
3. **Settings**: Click gear icon on strategy → screenshot all groups
4. **Trade CSV**: Strategy Tester tab → "Export" button (top right) → save CSV
5. **Label data**: Right-click the status label → note down values manually or screenshot

## How to Log Results

Open `test_log.csv` in any spreadsheet app and add a row:
```
test_id: T001, T002, T003...
version: v6.3
market: MES
timeframe: 5m
dates_start: 2025-09-01
dates_end: 2026-02-21
... (fill all metrics from TV)
changed_setting: "baseline" or "p1GreenLockUsd=0"
csv_file: v6.3_baseline/trades.csv
```

---

## The One Question We're Answering

> **Does this architecture get to +$3,100 faster and smoother than random trading?**

Everything else is noise until this is answered.
