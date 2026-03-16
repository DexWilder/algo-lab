# Forward Paper Trading — Operator Checklist

## Morning Startup (6:25 AM ET)

```bash
cd "/Users/chasefisher/projects/Algo Trading/algo-lab"
./scripts/start_forward_day.sh
```

**Verify:**
- [ ] Pre-flight checks pass (python3, data files exist)
- [ ] Data update completes without errors
- [ ] Data integrity check passes (no warnings)
- [ ] Forward runner processes new bars (not "No new bars to process")
- [ ] Monitor displays without errors

**If data update fails:**
- Check Databento API key: `echo $DATABENTO_API_KEY`
- Check internet connection
- Try single symbol: `python3 scripts/update_daily_data.py --symbol MES`
- Skip update if needed: `./scripts/start_forward_day.sh --skip-update`

---

## Intraday Check (optional)

Run the health report:
```bash
python3 scripts/forward_health_report.py
```

Or open the dashboard:
```bash
streamlit run scripts/dashboard.py
```

**What to glance at:**
- [ ] Status is HEALTHY (not WARNING or CRITICAL)
- [ ] Kill switch is OFF
- [ ] Equity is within expected range
- [ ] No duplicate bar warnings in logs

---

## After Close

Run the scorecard:
```bash
python3 scripts/forward_scorecard.py
```

**Check:**
- [ ] Trades today: 0-5 is normal, 0 for multiple consecutive days is a flag
- [ ] Strategies active: at least 3-4 of 6 should be allowed by controller
- [ ] Controller filtering: 25-40% filtered is normal (backtest: ~30%)
- [ ] Kill switch: should be OFF
- [ ] Daily PnL: volatile is fine, consistent large losses are a flag
- [ ] Regime detected: should match market conditions

---

## Stop Conditions (action required)

| Condition | Action |
|---|---|
| Kill switch fires | Investigate reason. Check `logs/kill_switch_events.csv`. Do NOT disable the kill switch. |
| Data update fails 2+ days | Fix data pipeline before next run. Check Databento status. |
| Runner crashes | Check Python traceback. File a bug. Do NOT modify frozen files. |
| 0 trades for 3+ consecutive days | Check if regime is blocking everything. Review signal_log.csv. |
| Duplicate bars detected | Stop running. Check `state/account_state.json` for correct `last_processed_bar`. |
| Equity drops >$2,000 from start | Review trades for unexpected behavior. Compare to backtest expectations. |

---

## Weekly Review

Every Friday or weekend:
```bash
python3 research/forward_validation_analyzer.py
python3 scripts/forward_scorecard.py --period weekly
```

**Assess:**
- [ ] Trade frequency within 0.5-2x of backtest (1.1/day)
- [ ] Win rate within ±15pp of backtest (52%)
- [ ] Strategy distribution roughly matches backtest expectations
- [ ] No persistent kill switch events
- [ ] PnL trajectory is plausible (not necessarily positive — variance is expected)

---

## What NOT To Do During Forward Validation

- Do NOT modify strategies, controller, engine, or runner
- Do NOT change prop configs that affect the live path
- Do NOT reset account state unless there's a confirmed bug
- Do NOT disable the kill switch
- Do NOT run `--reset` without good reason

**Safe activities:**
- Running monitoring/analysis scripts
- Building new research tools
- Improving the dashboard
- Running the prop firm optimizer

---

## Key File Locations

| File | Purpose |
|---|---|
| `state/account_state.json` | Persisted account state (equity, HWM, last bars) |
| `logs/trade_log.csv` | All executed trades |
| `logs/daily_report.csv` | Daily summary rows |
| `logs/signal_log.csv` | Signal generation and filtering stats |
| `logs/kill_switch_events.csv` | Kill switch activations (may not exist) |
| `state/data_update_state.json` | Last data update metadata |
