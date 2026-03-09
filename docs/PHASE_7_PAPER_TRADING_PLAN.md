# Phase 7 — Paper Trading Plan

**Start Date:** 2026-03-08 (preparation), live sim TBD (pending Tradovate sim setup)
**Duration:** Minimum 2 weeks, target 4 weeks
**Portfolio:** Regime-gated PB-MGC-Short + ORB-009 MGC-Long

---

## Portfolio Configuration

| Parameter | Value |
|-----------|-------|
| Strategies | PB-MGC-Short + ORB-009 MGC-Long |
| Asset | MGC (Micro Gold Futures) |
| Regime gate | Skip low-vol days (ATR < 33rd percentile) |
| Sizing | Equal weight (1 contract each) |
| Session | 08:30–15:15 ET (PB), 09:30–15:15 ET (ORB) |
| EOD flatten | 15:15 ET |
| Costs | $0.62/side commission + 1 tick adverse slippage |

### Expected Behavior (from backtest)

| Metric | Expected Range |
|--------|---------------|
| Trades per week | 2–5 |
| Win rate | ~52% |
| Avg winner | ~$100 |
| Avg loser | ~$60 |
| Weekly PnL | $50–$200 (avg) |
| MaxDD | <$703 (backtest observed) |
| Days with no trades | Common (regime gate + low signal frequency) |

---

## Daily Logging Requirements

Each trading day, record:

1. **Regime state:** ATR percentile rank, regime label (low/medium/high), gate decision (trade/skip)
2. **Signals generated:** Strategy, time, direction, stop/target prices
3. **Trades taken:** Entry time, entry price, exit time, exit price, P&L
4. **Skipped signals:** Reason (regime gate, prop controller, already in position)
5. **Controller state:** Current equity, trailing floor, phase (P1/P2), daily P&L
6. **Operational notes:** Any anomalies, data issues, timing problems

### Log Format

```
research/paper_trade_sim/daily_logs/YYYY-MM-DD.json
```

```json
{
  "date": "2026-03-10",
  "regime": {"atr_pctrank": 45.2, "label": "medium", "gate": "trade"},
  "signals": [
    {"strategy": "ORB-009", "time": "10:15", "direction": "long", "action": "taken"}
  ],
  "trades": [
    {"strategy": "ORB-009", "entry": "10:20", "exit": "11:45", "pnl": 85.50}
  ],
  "controller": {"equity": 50085.50, "floor": 46000.00, "phase": "P1"},
  "notes": ""
}
```

---

## Pass/Fail Conditions

### PASS (continue to live deployment)
All of the following must hold after 2+ weeks:
- [ ] No prop DD floor breached
- [ ] Signal timing matches backtest assumptions (signals at bar close, fills at next open)
- [ ] Regime gate correctly identifies low-vol days
- [ ] No operational failures (data feed, timing, logging)
- [ ] P&L directionally consistent with backtest (not expecting exact match)
- [ ] No evidence of edge decay (win rate >40%, expectancy >$0)

### FAIL (halt and investigate)
Any of the following triggers a halt:
- Equity drops below trailing floor at any point
- 10+ consecutive losing trades
- Win rate below 35% after 20+ trades
- Regime gate systematically wrong (trades on days that should be skipped)
- Signals arrive too late (after next bar opens)
- Data feed failures >2 per week

### INVALIDATES DEPLOYMENT READINESS
These would require returning to research:
- Edge appears to have decayed (PF < 1.0 after 30+ trades)
- Regime gate makes performance worse (not better) on live data
- Systematic slippage exceeds 2x backtest assumptions
- Prop controller logic errors (incorrect floor tracking)

---

## Weekly Review Checklist

Every Friday, evaluate:
1. Cumulative P&L vs expected range
2. Trade count vs expected frequency
3. Regime gate accuracy (were skipped days actually low-vol?)
4. Any skipped trades or halted days
5. Slippage comparison (sim fills vs expected)
6. Decision: continue / extend / halt

---

## Transition Criteria

### Paper → Live (requires ALL)
- Minimum 2 weeks of clean operation
- Minimum 10 trades executed
- No FAIL conditions triggered
- P&L positive or within expected drawdown range
- All operational systems verified
- Execution adapter tested and working

### Scale-Up (after live deployment)
- After 30 days of live trading at 1 contract
- If metrics remain consistent with backtest
- Increase to ERC or vol-target sizing
- Add prop controller phase rules

---

## Parallel Activities During Paper Trading

While paper trading runs:
1. **Diversification search:** Screen MES/MNQ candidates from triage queue
2. **Evolution engine design:** Architecture doc for automated strategy generation
3. **Execution adapter:** Build Tradovate API integration (test on sim)
4. **Monitoring:** Set up alerts and daily reconciliation process

---
*Plan created 2026-03-08*
