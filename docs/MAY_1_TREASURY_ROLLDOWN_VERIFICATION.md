# May 1 Treasury-Rolldown First Live Rebalance — Verification Checklist

**Target date:** 2026-05-01 (Friday, first business day of May 2026).

**Context:** Treasury-Rolldown-Carry-Spread was re-probated 2026-04-14 via an
out-of-band monthly execution path. This is its first live production
rebalance. The checkpoint validates that the out-of-band path worked
end-to-end before any decision to extend the pattern to a second strategy.

---

## Background references

- **Strategy:** `Treasury-Rolldown-Carry-Spread` (ZN/ZF/ZB 3-tenor carry spread, monthly rebalance)
- **Execution script:** `research/run_treasury_rolldown_spread.py`
- **Launchd agent:** `com.fql.treasury-rolldown-monthly` (weekdays 17:10 local, first-business-day-of-month guard inside script)
- **Evidence log:** `logs/spread_rebalance_log.csv`
- **Launchd stdout/stderr:** `research/logs/treasury_rolldown_monthly_stdout.log`, `…_stderr.log`
- **Strategy code (source of truth for signals):** `strategies/treasury_rolldown_carry/strategy.py`

## Seeded historical baseline (for reconciliation)

| spread_id | rebalance_date | long | short | prior_long | prior_short | realized_pnl_prior |
|---|---|---|---|---|---|---|
| TRS-2026-03 | 2026-03-31 | ZF | ZB | ZB | ZF | -3359.38 |
| TRS-2026-04 | 2026-04-12 | ZF | ZB | ZF | ZB | +375.00 |

(TRS-2026-04's rebalance_date 2026-04-12 reflects end-of-available-data at seed time. Live TRS-2026-05 will use real May data.)

---

## Verification procedure

Run each check in order. Record outcomes in the table at the bottom.

### Check 1 — Launchd fired at least once on 2026-05-01

**Command:**
```bash
launchctl list | grep treasury-rolldown-monthly
ls -la ~/Library/LaunchAgents/com.fql.treasury-rolldown-monthly.plist
tail -30 "/Users/chasefisher/projects/Algo Trading/algo-lab/research/logs/treasury_rolldown_monthly_stdout.log"
```

**Pass:** The agent is loaded (`launchctl list` shows it), the stdout log has a 2026-05-01 timestamp, and the log message is either "Wrote TRS-2026-05: …" or a clean "Not first business day of month — skip" (if somehow 2026-05-01 wasn't the first business day).

**Warn:** Agent loaded but no 2026-05-01 log entry exists. launchd may have not been loaded or the plist isn't firing on the expected schedule.

**Fail:** Agent not loaded (`launchctl list` empty for this label), or stderr log has Python tracebacks.

### Check 2 — Exactly one new row in `logs/spread_rebalance_log.csv`

**Command:**
```bash
wc -l "/Users/chasefisher/projects/Algo Trading/algo-lab/logs/spread_rebalance_log.csv"
grep "TRS-2026-05" "/Users/chasefisher/projects/Algo Trading/algo-lab/logs/spread_rebalance_log.csv"
grep "TRS-2026-04" "/Users/chasefisher/projects/Algo Trading/algo-lab/logs/spread_rebalance_log.csv" | wc -l
grep "TRS-2026-03" "/Users/chasefisher/projects/Algo Trading/algo-lab/logs/spread_rebalance_log.csv" | wc -l
```

**Pass:** Line count = 4 (header + 3 rows). Exactly one `TRS-2026-05` row. Exactly one `TRS-2026-04` row. Exactly one `TRS-2026-03` row.

**Warn:** Line count > 4 but all extra lines are `TRS-2026-05` duplicates (would imply idempotency failure — script wrote more than once on the same day). See Check 3.

**Fail:** No `TRS-2026-05` row exists AND launchd agent shows it fired (means the script ran but failed silently to write). OR seeded rows got overwritten/removed.

### Check 3 — Idempotency verified

**Command (DO NOT skip even if Check 2 passed):**
```bash
cd "/Users/chasefisher/projects/Algo Trading/algo-lab"
python3 research/run_treasury_rolldown_spread.py --dry-run --date 2026-05-01
```

**Pass:** Output says "Rebalance for TRS-2026-05 already logged — skip." (This confirms re-invocation would NOT double-write.)

**Warn:** Output says "DRY RUN — would write: …" (This means the idempotency check didn't find the existing TRS-2026-05 row, suggesting a data-format issue in the CSV.)

**Fail:** Exception thrown.

### Check 4 — Row matches `generate_spread_signals()` expectation

**Command:**
```bash
cd "/Users/chasefisher/projects/Algo Trading/algo-lab"
python3 -c "
from strategies.treasury_rolldown_carry.strategy import generate_spread_signals
import pandas as pd
sigs = generate_spread_signals()
sigs['entry_date'] = pd.to_datetime(sigs['entry_date']).dt.date
may = sigs[sigs['entry_date'].apply(lambda d: d.year==2026 and d.month==5)]
print('May rebalance signals from strategy:')
print(may.to_string())
print()
log = pd.read_csv('logs/spread_rebalance_log.csv')
trs5 = log[log['spread_id']=='TRS-2026-05']
print('Logged TRS-2026-05 row:')
print(trs5.to_string())
"
```

**Pass:** The logged row's `long_leg_asset`, `short_leg_asset`, and entry prices match the strategy's computed May rebalance (when one exists in the signals output).

**Warn:** Signals output has no May entry (may mean the data refresh at 17:00 ET on 2026-05-01 hadn't completed by the time the 17:10 script fired, or 2026-05-01 wasn't actually a "month-end" in the strategy's convention). If the logged row also shows no TRS-2026-05, the guard correctly skipped. If a TRS-2026-05 row exists but signals are empty, real inconsistency — investigate.

**Fail:** Logged legs (long/short tenors) DISAGREE with what `generate_spread_signals()` produces for the same date. Indicates the script's path for selecting the signal row diverges from the strategy's logic.

### Check 5 — `realized_pnl_prior_spread` reconciles with TRS-2026-04 seed

**Command:**
```bash
cd "/Users/chasefisher/projects/Algo Trading/algo-lab"
python3 -c "
import pandas as pd
log = pd.read_csv('logs/spread_rebalance_log.csv')
trs4 = log[log['spread_id']=='TRS-2026-04'].iloc[0]
trs5 = log[log['spread_id']=='TRS-2026-05'].iloc[0] if not log[log['spread_id']=='TRS-2026-05'].empty else None
print('TRS-2026-04 legs:', trs4['long_leg_asset'], 'long @', trs4['long_leg_entry_price'], '/', trs4['short_leg_asset'], 'short @', trs4['short_leg_entry_price'])
if trs5 is not None:
    print('TRS-2026-05 previous_long/short:', trs5['previous_long_leg_asset'], '/', trs5['previous_short_leg_asset'])
    print('TRS-2026-05 realized_pnl_prior_spread:', trs5['realized_pnl_prior_spread'])
    # Expected: realized_pnl_prior = (trs5_entry_price_for_trs4_long - trs4_long_entry_price) * point_value
    #                              + (trs4_short_entry_price - trs5_entry_price_for_trs4_short) * point_value
    # Using 1000.0 point value for ZN/ZF/ZB
    print()
    print('Manual reconciliation:')
    print('  TRS-2026-04 long was ZF at', trs4['long_leg_entry_price'])
    print('  TRS-2026-05 closing ZF at (its entry price for ZF): look up ZF close on 2026-05-01')
    print('  Expected realized = (ZF_may01_close - 108.28125 approx) * 1000 + (ZB_may01_close - 113.90625 approx) * 1000 * -1')
"
```

**Pass:** `previous_long_leg_asset` = `ZF`, `previous_short_leg_asset` = `ZB` (matching TRS-2026-04's legs). `realized_pnl_prior_spread` is non-zero and sign-consistent with the price move between TRS-2026-04 entry prices and the equivalent 2026-05-01 closes.

**Warn:** Previous-leg fields match but `realized_pnl_prior_spread` looks off by a factor of 10, 100, or 1000. Likely a point-value bug.

**Fail:** Previous-leg fields do NOT match TRS-2026-04's legs (means the prior-row lookup logic is broken). OR `realized_pnl_prior_spread` is zero (means the script didn't find the prior row and treated this as the first-ever rebalance).

### Check 6 — No spillover into the intraday trade log

**Command:**
```bash
grep "Treasury-Rolldown-Carry-Spread" "/Users/chasefisher/projects/Algo Trading/algo-lab/logs/trade_log.csv" | head -5
grep "TRS-2026" "/Users/chasefisher/projects/Algo Trading/algo-lab/logs/trade_log.csv"
```

**Pass:** Both commands return empty. The out-of-band path writes only to the spread log; the intraday trade log is untouched by Treasury-Rolldown.

**Fail:** Either command returns rows. The out-of-band isolation was broken.

### Check 7 — Drift monitor still excludes Treasury-Rolldown cleanly

**Command:**
```bash
cd "/Users/chasefisher/projects/Algo Trading/algo-lab"
python3 research/live_drift_monitor.py 2>&1 | grep -i -E "treasury|TRS-|spread_rebalance"
```

**Pass:** Only the `EXCLUDED FROM STRATEGY DRIFT` block contains `Treasury-Rolldown-Carry-Spread`. No per-trade severity assigned.

**Warn:** Treasury-Rolldown appears with a tier (`full` / `reference-only` / `observational`). Someone moved it out of the excluded list.

**Fail:** Treasury-Rolldown appears in the `UNCATALOGUED LIVE` bucket. Means either the drift monitor is picking up rows from somewhere it shouldn't (e.g., trade_log.csv has stray entries) or the baseline `excluded_from_strategy_drift` block was removed.

---

## Outcome matrix

| Aggregate outcome | Definition | Action |
|---|---|---|
| **PASS** | All 7 checks PASS. | Record in table below. Treasury-Rolldown's first live rebalance is validated. Out-of-band execution pattern confirmed viable. **May consider opening the FX/STRUCTURAL lane as the next research move** (still research, not build). |
| **PASS with warn** | All checks PASS except 1–2 WARN. | Record in table below. Investigate each WARN and document root cause + fix in a follow-up commit. Do NOT open new lanes until WARNs are resolved. |
| **FAIL on checks 1 or 2** | Launchd didn't fire, or row wasn't written. | **Operational bug in execution path.** Diagnose launchd/script; do NOT manually write a substitute row — that would pollute the log with a non-scripted entry. Fix the script/agent, force a manual re-fire, re-run checks. Hold all other lanes. |
| **FAIL on check 3** | Idempotency broken. | **Data integrity risk.** Remove duplicate rows manually (preserve first-written), patch the idempotency guard in `run_treasury_rolldown_spread.py`. Re-run all checks after patch. Hold. |
| **FAIL on check 4** | Logged row diverges from strategy signals. | **Logic divergence.** The script's signal-selection path disagrees with `generate_spread_signals()`. Investigate `_build_row` in the script. Do not trust the written row; mark it invalid in the `notes` field until reconciled. Hold. |
| **FAIL on check 5** | Realized PnL reconciliation broken. | **Prior-row lookup bug.** Strategy's backtest evidence was trustworthy but the runtime PnL attribution is wrong. Investigate prior-row detection logic. The row is salvageable but the realized PnL field is not authoritative until patched. Hold. |
| **FAIL on check 6** | Treasury-Rolldown leaked into `trade_log.csv`. | **Isolation breach.** Out-of-band promise violated. Remove spurious rows from trade_log.csv, investigate how they got there, fix, re-run. Hold. |
| **FAIL on check 7** | Drift monitor mis-handling Treasury-Rolldown. | **Monitor configuration drift.** Check whether someone edited BASELINE. Restore `excluded_from_strategy_drift` entry. Re-run. Hold. |

**Strategic outcome (independent of operational checks):**

| Read | Action |
|---|---|
| Out-of-band path worked cleanly AND TRS-2026-05 rebalance direction/legs look strategically reasonable (e.g., yield-curve context supports the long-short choice) | Treasury-Rolldown earns 1 of 8 cycles toward promotion. Continue holding other lanes. |
| Out-of-band path worked cleanly BUT the rebalance direction looks strategically weak (e.g., contrarian to the obvious yield-curve read, or whipsaws from TRS-2026-04 without macro justification) | Continue probation but flag for review at TRS-2026-06 (second cycle). Do NOT open new lanes — probationary weakness is a reason to observe more, not add complexity. |
| Operationally the path failed | Do not proceed to strategic assessment until the operational path is fixed. |

---

## Where the review result gets recorded

1. **Append an entry to `logs/spread_rebalance_log.csv`'s `notes` field on TRS-2026-05.** If the review passes, append `"verified_2026-05-XX"`. If WARN, append `"verified_with_warn_2026-05-XX"`. If FAIL, append `"verification_failed_2026-05-XX"` + don't clear until resolved.

2. **Commit to main with a message like `"Treasury-Rolldown TRS-2026-05 verification: [PASS|PASS-with-warn|FAIL]"`**, referencing this checklist.

3. **Update `docs/PORTFOLIO_TRUTH_TABLE.md`**'s `Next Checkpoint` section to either (a) point at TRS-2026-06 as the next gate, or (b) flag the failure and name the hold condition.

4. **Fill out the outcome table below in this document** so the historical record of this verification survives review turnover.

---

## Outcome record (fill in after 2026-05-01)

| Check | Outcome (PASS/WARN/FAIL) | Notes |
|---|---|---|
| 1. Launchd fired | | |
| 2. Exactly one new row | | |
| 3. Idempotency | | |
| 4. Row matches strategy signals | | |
| 5. Realized PnL reconciles | | |
| 6. No spillover into trade_log | | |
| 7. Drift monitor exclusion clean | | |

**Aggregate outcome:** _____
**Strategic read:** _____
**Next checkpoint:** _____
**Reviewer / date:** _____
