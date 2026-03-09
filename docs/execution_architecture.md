# Execution Architecture

*Design document for live trading infrastructure. No code deployed yet.*

---

## System Overview

```
Data Feed (5m bars)
    ↓
Strategy Engine (generate_signals)
    ↓
Regime Gate (ATR percentile filter)
    ↓
Prop Controller (trailing DD, daily limits, phases)
    ↓
Execution Adapter (order formatting)
    ↓
Broker API (Tradovate / Rithmic)
    ↓
Fill Confirmation → Trade Log → Reconciliation
```

---

## 1. Signal Generation Pipeline

### Data Feed
- **Source:** Broker-provided real-time bars (Tradovate WebSocket or Rithmic)
- **Timeframe:** 5-minute bars, CME RTH session (09:30-16:00 ET)
- **Asset:** MGC (Micro Gold Futures)
- **Warmup:** First 15 minutes after open (3 bars) used for indicator warmup
- **Fallback:** If real-time feed drops, use 1-minute bars aggregated to 5-minute

### Strategy Execution
- **Strategies:** PB-MGC-Short + ORB-009 MGC-Long
- **Timing:** Signal generated at bar close, order placed for next bar's open
- **Latency budget:** ~5 minutes (entire bar duration), no HFT requirements
- **Independence:** Each strategy runs independently — no shared state

### Regime Gate
- **Computation:** ATR percentile rank computed at session open from prior day's data
- **Decision:** If ATR < 33rd percentile → skip all signals for the day
- **Timing:** Gate decision made once per day before first signal

---

## 2. Order Routing

### Order Types
- **Entry:** Market order at next bar's open (fills at market)
- **Stop loss:** Stop order placed immediately after entry fill
- **Take profit:** Limit order placed immediately after entry fill
- **EOD flatten:** Market order at 15:15 ET if position open

### Order Flow
```
Signal generated (bar close)
    ↓
Pre-trade checks:
  - Prop controller: daily loss limit ok?
  - Prop controller: contract cap ok?
  - Prop controller: trailing DD ok?
  - Position check: already in position?
    ↓
If all pass → place market order
    ↓
Fill confirmed → place SL/TP bracket
    ↓
Monitor until exit (SL, TP, or EOD flatten)
```

### Position Management
- **Max 1 position per strategy at any time**
- **Max 1 trade per direction per day (ORB-009)**
- **No pyramiding, no scaling**
- **Flatten all by 15:15 ET — no overnight positions**

---

## 3. Broker Options

### Option A: Tradovate REST API (Recommended)

**Advantages:**
- REST + WebSocket API, well-documented
- Direct CME access for micro futures
- Supports bracket orders (entry + SL + TP)
- Free demo/sim environment for testing
- PickMyTrade.trade integration available (TradingView → Tradovate)

**API Flow:**
```
POST /order/placeorder → market entry
POST /order/placeoco → bracket (SL + TP)
GET /position/list → position check
DELETE /order/cancelorder → cancel pending
POST /order/placeorder → flatten (market close)
```

**Authentication:** OAuth2 token refresh, session-based

### Option B: Rithmic (via NinjaTrader or Direct)

**Advantages:**
- Lower latency (direct exchange connection)
- Better fill quality on micros
- NinjaTrader provides strategy framework

**Disadvantages:**
- More complex API (Protocol Buffers)
- Requires NinjaTrader license for strategy hosting
- Less documentation than Tradovate

### Recommendation

Start with **Tradovate** for simplicity. Migrate to Rithmic if fill quality becomes an issue (unlikely at 1-contract micro scale).

---

## 4. Failure Handling

### Connection Loss
- **Detection:** WebSocket heartbeat timeout (30 seconds)
- **Action:**
  1. Attempt reconnect (3 retries, exponential backoff)
  2. If reconnect fails → flatten all positions via backup REST call
  3. Log error, send alert
  4. Halt trading until manual review

### Partial Fills
- **Unlikely at 1-contract micro scale** (deep liquidity)
- **If occurs:** Treat partial as full position, adjust SL/TP proportionally
- **Log:** Track fill rate for monitoring

### Order Rejection
- **Common causes:** Insufficient margin, market closed, invalid symbol
- **Action:** Log rejection, skip signal, continue to next bar
- **No retry on same signal** — stale by next bar

### Data Feed Issues
- **Missing bars:** If bar doesn't arrive within 30 seconds of expected time, use last known price
- **Bad data:** If bar OHLC is clearly wrong (>10% gap from prior close), skip signal
- **Stale data:** If no new bar for >10 minutes during RTH, assume feed failure

---

## 5. Kill Switch

### Manual Kill Switch
- **Endpoint:** `POST /killswitch` or keyboard shortcut
- **Action:**
  1. Cancel all pending orders
  2. Flatten all open positions (market order)
  3. Disable signal generation
  4. Log event with timestamp and reason

### Automatic Kill Switch
Triggers automatically if:
- Daily loss exceeds prop limit
- Trailing DD floor breached
- Connection lost for >5 minutes
- 3+ consecutive order rejections

### Recovery
- After kill switch, trading halts until next session
- Manual review required before re-enabling
- All trades between kill switch and recovery are logged for audit

---

## 6. Logging

### Trade Log (`logs/trades.jsonl`)
```json
{
  "timestamp": "2026-03-08T10:05:00-05:00",
  "strategy": "ORB-009",
  "action": "entry",
  "side": "long",
  "symbol": "MGCM6",
  "price": 2524.50,
  "contracts": 1,
  "order_id": "abc123",
  "fill_id": "def456"
}
```

### Signal Log (`logs/signals.jsonl`)
```json
{
  "timestamp": "2026-03-08T10:00:00-05:00",
  "strategy": "ORB-009",
  "signal": 1,
  "regime": "medium",
  "regime_gate": "pass",
  "prop_gate": "pass",
  "action_taken": "order_placed"
}
```

### Error Log (`logs/errors.jsonl`)
```json
{
  "timestamp": "2026-03-08T10:05:01-05:00",
  "level": "ERROR",
  "component": "broker_api",
  "message": "Order rejection: insufficient margin",
  "context": {"order_id": "abc123", "symbol": "MGCM6"}
}
```

### Daily Reconciliation
- **End of day:** Compare trade log with broker's fill report
- **Check:** Position count = 0 (all flattened)
- **Check:** P&L matches broker statement within $1
- **Alert:** If any mismatch, halt trading next day

---

## 7. Latency Considerations

| Stage | Expected Latency | Budget |
|-------|-----------------|--------|
| Data feed → signal | <1 second | 5 minutes |
| Signal → order submission | <100ms | 5 minutes |
| Order → fill | <500ms (market order) | 5 minutes |
| Fill → bracket placement | <200ms | immediate |
| Total round-trip | <2 seconds | 5 minutes |

**No HFT requirements.** The 5-minute bar timeframe provides an enormous latency budget. Even 30-second delays would not impact performance.

---

## 8. Monitoring

### Real-Time Dashboard
- Current positions (strategy, side, entry price, unrealized P&L)
- Daily P&L (running total)
- Trailing DD floor and current equity
- Regime status (low/medium/high)
- Connection status (green/yellow/red)

### Alerts
- **Critical:** Kill switch triggered, connection lost, bust approaching
- **Warning:** Daily loss >50% of limit, unusual fill slippage
- **Info:** Trade executed, daily summary, regime change

### Heartbeat
- System sends heartbeat every 60 seconds during RTH
- If heartbeat missed for 3 minutes → alert
- If heartbeat missed for 5 minutes → auto kill switch

---

## 9. Deployment Checklist

Before going live:
- [ ] Paper trade for minimum 2 weeks on Tradovate sim
- [ ] Verify fill prices match backtest assumptions
- [ ] Verify EOD flatten works at 15:15 ET
- [ ] Verify regime gate computes correctly from live data
- [ ] Verify prop controller tracks trailing DD accurately
- [ ] Test kill switch (manual and automatic)
- [ ] Test connection loss recovery
- [ ] Verify daily reconciliation process
- [ ] Verify logging captures all events
- [ ] Set up monitoring alerts (email/SMS/Discord)
- [ ] Start with 1 contract only (regardless of sizing model)
- [ ] Run for 30 days before scaling

---
*Document created 2026-03-08*
