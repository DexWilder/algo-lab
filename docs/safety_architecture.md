# Safety & Watchdog Architecture

## Status: DESIGN PHASE (no broker connection yet)

This document defines the safety architecture for when the system
transitions from paper trading to broker-connected execution.

---

## Current Safety (Paper Trading)

Already implemented in `engine/paper_trading_engine.py`:
- Kill switch: daily loss $800, trailing DD $4K, 8 consecutive losses, correlated loss
- Strategy controller: regime gating, soft timing, portfolio coordination
- State persistence: account_state.json survives restarts
- Duplicate bar protection: skips already-processed bars

---

## Broker-Connected Safety (Future Build)

### Module: execution/watchdog.py

**Heartbeat checks (every 60s):**
- Broker connection alive?
- Data feed alive?
- Account balance readable?
- Last heartbeat timestamp recent?
- Disk space > 1GB?
- Clock sync within 5s of NTP?
- State file writable?

**If any check fails:**
1. Set system to SAFE_MODE
2. Stop sending new orders
3. Log incident with timestamp + failed check
4. Write incident to logs/incidents.csv

### Module: execution/failsafe_controller.py

**Order safety:**
- Unique order IDs (UUID per order)
- Duplicate-order lockout (same strategy+direction within 5 bars)
- Max contracts per strategy: configurable per prop config
- Max contracts per asset: configurable
- Max total portfolio exposure: configurable
- Daily loss hard-stop: from prop config trailing_dd

**Position reconciliation (every 5 minutes):**
- Compare expected positions (from state) vs broker positions (from API)
- If mismatch: HALT trading, log discrepancy, alert

**Broker disconnect protocol:**
1. Cancel all resting orders (if API available)
2. Freeze new entries
3. Keep existing positions (broker-native stops should be set)
4. Escalate alert
5. Auto-retry connection every 30s for 5 minutes
6. If still disconnected: SAFE_MODE

### Module: execution/incident_logger.py

**Incident types:**
- HEARTBEAT_FAIL
- POSITION_MISMATCH
- BROKER_DISCONNECT
- KILL_SWITCH_TRIGGERED
- ORDER_REJECTED
- DUPLICATE_ORDER_BLOCKED
- SAFE_MODE_ENTERED

**Format:** CSV with timestamp, type, severity, detail, resolution

---

## Control Architecture

### Strategy lifecycle:
```
DISCOVERY → VALIDATION → PROBATION → PROMOTED → ACTIVE → MONITORING → DECAY/REPLACE
```

### Approval gates (require human approval):
- Promotion from probation to active
- Adding new strategy to live portfolio
- Changing position sizing
- Enabling broker-connected mode
- Disabling safety checks

### Automatic (no approval needed):
- Regime-based strategy on/off (already implemented)
- Kill switch activation
- SAFE_MODE entry
- Daily/weekly report generation
- Opportunity scanning
- Edge decay detection

---

## Implementation Priority

1. **Now**: Scheduler layer (daily/weekly runners) ✅
2. **Now**: Auto-review reports ✅
3. **Now**: Opportunity scanner ✅
4. **Before broker**: Watchdog + heartbeat
5. **Before broker**: Position reconciliation
6. **Before broker**: Order safety layer
7. **Before broker**: Failsafe controller
8. **Before broker**: Incident logger
