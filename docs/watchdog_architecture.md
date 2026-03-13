# Watchdog Architecture — Detailed Design Spec

## Status: DESIGN PHASE (pre-broker)

This document is the implementation blueprint for the safety/watchdog layer.
It defines every failure scenario, detection rule, halt action, recovery rule,
alert severity, and reconciliation logic required before broker-connected execution.

**Core Principle:**
> It is much better for the system to stop unnecessarily than to continue
> trading while confused. Prefer **false positive halt** over **false negative
> continue trading**.

**Automation Philosophy:**
| Condition | Behavior |
|---|---|
| Normal | Trade normally |
| Suspicious | Pause and verify |
| Unknown | Halt immediately |

---

## Severity Levels

| Level | Meaning | System Action |
|---|---|---|
| **INFO** | Routine update | Log only |
| **WARNING** | Non-fatal issue, may degrade | Log + alert |
| **CRITICAL** | Trading should pause | Log + alert + pause new entries |
| **HALT / SAFE_MODE** | System locks down | Log + alert + cancel pending + freeze all + require human recovery |

---

## Module Map

```
execution/
├── watchdog_controller.py      # Top-level orchestrator, runs all checks
├── system_heartbeat.py         # Connection & infrastructure health
├── position_reconciler.py      # Expected vs actual position matching
├── failsafe_controller.py      # Order safety, duplicate detection, limits
├── alert_manager.py            # Notification routing (log, email, push)
└── incident_logger.py          # Structured incident CSV + JSON log
```

---

## The 12 Failure Scenarios

### 1. Broker Disconnect

**What happens:** Broker API connection drops mid-session.

**Risk:**
- Orders not sent
- Orders sent but not confirmed
- Open positions unmanaged (no stop updates, no exits)

**Detection:**
- Heartbeat ping to broker API every 30s
- Track consecutive failures (threshold: 3 consecutive = CRITICAL)
- Monitor order submission response times (>5s = WARNING)

**Halt Actions:**
1. Pause all new order submissions
2. Cancel resting orders (if API still partially available)
3. Verify open positions via last known state
4. Enter SAFE_MODE if disconnected >90s

**Recovery:**
1. Auto-retry connection every 30s for 5 minutes
2. On reconnect: reconcile positions before resuming
3. If still disconnected after 5 min: remain in SAFE_MODE, require human restart
4. Log full disconnect duration and any orders that were in-flight

**Severity:** CRITICAL → HALT (if >90s)

---

### 2. Data Feed Disconnect

**What happens:** Price feed freezes or delivers stale bars.

**Risk:** System generates signals on stale prices → bad entries/exits.

**Detection:**
- Compare `latest_bar_timestamp` vs `expected_bar_timestamp` (based on market hours + bar interval)
- Staleness threshold: 2× bar interval (e.g., 10 min for 5m bars)
- Compare data feed clock vs system clock
- Monitor bar-to-bar gaps (missing bars = WARNING)

**Halt Actions:**
1. Stop signal generation immediately
2. Halt order submission
3. Keep existing positions with broker-native stops
4. Log last valid bar timestamp

**Recovery:**
1. Wait for fresh bar with valid timestamp
2. Verify bar continuity (no gaps)
3. If gaps detected: backfill before resuming signal generation
4. Resume only after 3 consecutive valid bars

**Severity:** WARNING (1 late bar) → CRITICAL (2× interval) → HALT (5× interval)

---

### 3. Position Mismatch

**What happens:** Internal state says flat; broker shows open position (or vice versa).

**Risk:** Double entries, accidental hedges, runaway exposure, unmanaged positions.

**Detection:**
- Reconciliation check every 5 minutes during market hours
- Compare three sources:
  1. Expected positions (from `account_state.json`)
  2. Broker positions (from API query)
  3. Open/pending orders (from API query)
- Mismatch = any disagreement between expected and actual

**Halt Actions:**
1. Immediately halt all trading (all strategies)
2. Log full state snapshot: expected, actual, open orders
3. Do NOT auto-flatten (could make it worse)
4. Alert with full details

**Recovery:**
1. Human must review mismatch
2. Options: (a) update internal state to match broker, (b) flatten broker position, (c) investigate further
3. System does not resume until human confirms resolution
4. Post-recovery: force immediate re-reconciliation

**Severity:** HALT (always — position uncertainty is never acceptable)

---

### 4. Duplicate Order Submission

**What happens:** Retry logic, lag, or race condition causes same order sent twice.

**Risk:** Oversized position, doubled risk, prop rule violation.

**Detection:**
- Every order gets a UUID (strategy + asset + direction + bar_index)
- Duplicate-order lockout: same strategy + direction within 5 bars = blocked
- Order state machine: PENDING → SUBMITTED → CONFIRMED → FILLED / CANCELLED
- Cannot submit new order while previous order for same strategy is PENDING or SUBMITTED

**Halt Actions:**
1. Block the duplicate order
2. Log incident with both order IDs
3. If duplicate somehow fills: treat as position mismatch (Scenario 3)

**Recovery:**
1. Lockout clears after 5 bars or explicit acknowledgment
2. If oversized position detected: trigger position reconciliation
3. Strategy resumes normal operation after lockout window

**Severity:** WARNING (blocked successfully) → CRITICAL (if duplicate filled)

---

### 5. Partial Fill Confusion

**What happens:** Order partially fills; system treats as full fill or no fill.

**Risk:** Incorrect stop placement, wrong position size, bad exit sizing.

**Detection:**
- Track fill state per order: UNFILLED → PARTIAL → FILLED
- Compare `filled_qty` vs `requested_qty` on every fill event
- Never assume full fill until broker confirms `filled_qty == requested_qty`

**Halt Actions:**
1. Recalculate position size after every fill event
2. Place stops/targets based on actual filled quantity, not requested
3. If partial fill leaves odd lot: flag for review

**Recovery:**
1. Wait for remaining fill or timeout (configurable, default 60s)
2. If timeout with partial: cancel remaining, adjust stops to actual fill
3. Log partial fill with details (requested, filled, remaining, time)

**Severity:** WARNING (partial detected) → CRITICAL (if stops placed on wrong size)

---

### 6. Stale Resting Orders

**What happens:** Signal invalidated but resting limit/stop order remains at broker.

**Risk:** Late fill in wrong context (regime changed, strategy disabled, etc.).

**Detection:**
- TTL (time-to-live) on every resting order: default 30 minutes for entry orders
- Track signal validity: if regime changes or strategy disables, all pending orders become stale
- End-of-session sweep: cancel all resting orders 15 min before close

**Halt Actions:**
1. Cancel stale order immediately
2. If cancel fails: retry 3×, then alert
3. If cancel-failed order fills: treat as unexpected position (Scenario 3)

**Recovery:**
1. Confirm cancellation via broker API
2. Update order state machine
3. Log stale order incident with original signal context

**Severity:** WARNING (stale detected + cancelled) → CRITICAL (cancel failed)

---

### 7. Process Crash / Script Death

**What happens:** Execution process dies silently — no monitoring, no exits, no awareness.

**Risk:** Open positions unmanaged, no kill switch, no state updates.

**Detection:**
- Process heartbeat: write timestamp to `logs/process_heartbeat.json` every 30s
- External supervisor (launchd/systemd) monitors process
- Heartbeat file staleness check: if >120s old, process is dead

**Halt Actions:**
1. Supervisor auto-restarts process
2. On restart: do NOT resume trading immediately
3. First action: full state reconciliation
4. Check broker positions, open orders, account balance
5. Verify state file integrity

**Recovery:**
1. Load last valid state from `account_state.json`
2. Reconcile against broker
3. If clean: resume with WARNING logged
4. If mismatch: enter SAFE_MODE, require human review
5. Log crash event with uptime, last action, restart time

**Severity:** CRITICAL (crash detected) → HALT (if state corrupted on restart)

---

### 8. State Corruption

**What happens:** `account_state.json` becomes corrupted, incomplete, or unwritable.

**Risk:** Duplicate trades, bad DD tracking, missing reconciliation data, prop rule violations.

**Detection:**
- Validate state file on every load:
  - JSON parseable
  - Required fields present (balance, positions, daily_pnl, trade_count)
  - Values within sane ranges (balance > 0, positions count <= max_strategies)
  - Checksum/hash matches (written alongside state)
- Atomic writes: write to temp file, then rename (prevents partial writes)
- Rolling backups: keep last 5 state snapshots

**Halt Actions:**
1. Enter SAFE_MODE immediately
2. Do not trust any state values
3. Fall back to most recent valid backup
4. Alert with corruption details

**Recovery:**
1. Load most recent valid backup
2. Reconcile backup state against broker positions
3. If backup + broker agree: resume with WARNING
4. If disagree: remain in SAFE_MODE, require human reconciliation
5. Investigate cause of corruption (disk full? concurrent write? encoding?)

**Severity:** HALT (always — state uncertainty is never acceptable)

---

### 9. Clock / Time Sync Problems

**What happens:** System clock drifts from market time.

**Risk:** Wrong bar boundaries, wrong session open/close logic, early/late orders.

**Detection:**
- Compare system time vs NTP server on startup and every 5 minutes
- Drift threshold: WARNING at 2s, CRITICAL at 5s, HALT at 10s
- Monitor bar timestamps for consistency with expected schedule

**Halt Actions:**
1. At WARNING: log drift, continue with caution
2. At CRITICAL: pause new entries, alert
3. At HALT: full SAFE_MODE, cancel pending orders

**Recovery:**
1. Sync clock with NTP
2. Verify sync successful (drift < 1s)
3. Resume trading only after confirmed sync
4. Log drift magnitude and duration

**Severity:** WARNING (2-5s) → CRITICAL (5-10s) → HALT (>10s)

---

### 10. Strategy Runaway / Logic Bug

**What happens:** Bug causes nonstop signal firing or abnormal trade frequency.

**Risk:** Account blown through overtrading, commission death, prop rule violation.

**Detection:**
- Max trades per strategy per day: configurable (default: 10)
- Max trades per asset per session: configurable (default: 15)
- Abnormal frequency detector: if trades_last_hour > 3× rolling_avg, flag
- Rapid-fire detector: >3 entries within 5 bars from same strategy = CRITICAL

**Halt Actions:**
1. Auto-disable the offending strategy for remainder of session
2. Keep other strategies running (isolated failure)
3. Cancel any pending orders from disabled strategy
4. Alert with trade log from runaway period

**Recovery:**
1. Strategy remains disabled until next session
2. Human reviews trade log and strategy logic
3. Strategy re-enabled only with human approval
4. If multiple strategies runaway simultaneously: full SAFE_MODE

**Severity:** WARNING (high frequency) → CRITICAL (exceeds limit) → HALT (multi-strategy runaway)

---

### 11. Risk Layer Failure

**What happens:** Kill switch or max-position logic fails to trigger when it should.

**Risk:** Losses continue unchecked past prop DD limit, account blown.

**Detection:**
- Independent risk check process (separate from strategy controller)
- Portfolio-wide hard stop: checked on every fill event, not just on bar close
- Strategy-level hard stop: max loss per strategy per day
- Broker-native protective orders: bracket stops placed at broker, not just tracked internally
- Cross-check: if paper_trading_engine kill switch fires, verify controller also agrees

**Halt Actions:**
1. If risk layer detects failure in itself: immediate SAFE_MODE
2. Flatten all positions if possible
3. Cancel all pending orders
4. Alert with full portfolio snapshot

**Recovery:**
1. Full state reconciliation
2. Verify kill switch thresholds are correct
3. Verify all positions have broker-native stops
4. Human must approve restart
5. Consider reducing position sizes on restart

**Severity:** HALT (always — risk layer failure is existential)

---

### 12. Network / API Latency or Ack Failure

**What happens:** Order sent to broker, no confirmation received.

**Risk:** System doesn't know if order is live, creating phantom positions or missed entries.

**Detection:**
- Order submission timeout: 10s for acknowledgment
- Track order state: SUBMITTED → (waiting for ACK) → CONFIRMED or TIMEOUT
- If TIMEOUT: order is in UNKNOWN state

**Halt Actions:**
1. Lock the strategy — no further orders until status resolved
2. Query broker for actual order status
3. Do NOT submit replacement order (could cause duplicate)
4. Alert with order details

**Recovery:**
1. Poll broker API for order status (3 retries, 5s apart)
2. If found: update state to match actual status
3. If not found: assume not filled, log as WARNING, unlock strategy
4. If found AND filled: update position state, place stops
5. If ambiguous after all retries: enter SAFE_MODE for that strategy

**Severity:** WARNING (slow ack) → CRITICAL (timeout) → HALT (unresolvable ambiguity)

---

## The Four Core Safety Systems

### 1. System Heartbeat (`execution/system_heartbeat.py`)

Runs every 30 seconds. Checks:

| Check | Method | Fail Threshold |
|---|---|---|
| Broker connection | API ping | 3 consecutive failures |
| Data feed | Bar timestamp freshness | 2× bar interval |
| Execution engine | Process heartbeat file | 120s stale |
| Strategy controller | Controller state check | Unresponsive 60s |
| State writer | Test write to temp file | Any write failure |
| Disk space | `os.statvfs` | < 1 GB free |
| Clock sync | NTP comparison | > 5s drift |

**Output:** `HeartbeatStatus` object with per-check pass/fail + overall health.

### 2. Position Reconciler (`execution/position_reconciler.py`)

Runs every 5 minutes during market hours.

**Compares three data sources:**
1. Internal state (`account_state.json`) — what we think we have
2. Broker positions (API) — what we actually have
3. Open orders (API) — what's pending

**Match rules:**
- Position match: same asset, same direction, same quantity
- Order match: every internal pending order has broker counterpart
- No orphans: no broker positions without internal tracking

**On mismatch:**
- Log full snapshot of all three sources
- Classify mismatch type: `PHANTOM_POSITION`, `MISSING_POSITION`, `SIZE_MISMATCH`, `ORPHAN_ORDER`
- HALT trading, alert, require human resolution

### 3. SAFE_MODE Controller (`execution/failsafe_controller.py`)

**SAFE_MODE is a system-wide state with defined entry and exit rules.**

**Entry triggers (any one):**
- Broker disconnect > 90s
- Data feed stale > 5× bar interval
- Position mismatch detected
- State corruption detected
- Clock drift > 10s
- Risk layer self-check failure
- Multi-strategy runaway
- Manual trigger (human command)

**SAFE_MODE behavior:**
1. Stop all new entries (all strategies)
2. Cancel all pending/resting orders
3. Place broker-native protective stops on all open positions (if not already set)
4. Log SAFE_MODE entry with trigger reason
5. Alert immediately
6. Continue monitoring (heartbeat keeps running)
7. Do NOT auto-flatten (human decides)

**Exit rules:**
1. Human must explicitly clear SAFE_MODE
2. Before clearing: system runs full reconciliation
3. All heartbeat checks must pass
4. Human confirms state is consistent
5. System resumes with WARNING-level monitoring for 30 minutes

### 4. Alert Manager (`execution/alert_manager.py`)

**Alert routing by severity:**

| Severity | Log | Console | Push/Email | Requires Ack |
|---|---|---|---|---|
| INFO | Yes | No | No | No |
| WARNING | Yes | Yes | No | No |
| CRITICAL | Yes | Yes | Yes | No |
| HALT | Yes | Yes | Yes | Yes (to resume) |

**Alert payload:**
```json
{
  "timestamp": "2026-03-13T16:30:00Z",
  "severity": "CRITICAL",
  "scenario": "BROKER_DISCONNECT",
  "detail": "3 consecutive heartbeat failures to Tradovate API",
  "action_taken": "Paused new orders, entered SAFE_MODE",
  "positions_at_risk": ["MNQ-long x1", "MGC-short x1"],
  "requires_human": true
}
```

**Channels (configurable):**
- File log: always (`logs/incidents.csv`)
- Console/stdout: WARNING+
- Email: CRITICAL+ (via SMTP or API)
- Push notification: CRITICAL+ (via Pushover, Slack webhook, etc.)
- SMS: HALT only (via Twilio or similar)

---

## Incident Log Format

**File:** `logs/incidents.csv`

| Column | Type | Description |
|---|---|---|
| timestamp | ISO 8601 | When incident occurred |
| severity | enum | INFO / WARNING / CRITICAL / HALT |
| scenario | enum | One of 12 scenario codes |
| detail | string | Human-readable description |
| action_taken | string | What the system did |
| resolution | string | How it was resolved (filled post-recovery) |
| duration_sec | float | How long the incident lasted |
| human_required | bool | Whether human intervention was needed |

**Scenario codes:**
```
BROKER_DISCONNECT
DATA_FEED_STALE
POSITION_MISMATCH
DUPLICATE_ORDER
PARTIAL_FILL
STALE_ORDER
PROCESS_CRASH
STATE_CORRUPTION
CLOCK_DRIFT
STRATEGY_RUNAWAY
RISK_LAYER_FAILURE
ORDER_ACK_TIMEOUT
KILL_SWITCH_TRIGGERED
SAFE_MODE_ENTERED
SAFE_MODE_EXITED
```

---

## Implementation Priority

| Priority | Module | Depends On |
|---|---|---|
| 1 | `incident_logger.py` | Nothing (standalone) |
| 2 | `alert_manager.py` | incident_logger |
| 3 | `system_heartbeat.py` | alert_manager |
| 4 | `failsafe_controller.py` | alert_manager, heartbeat |
| 5 | `position_reconciler.py` | failsafe_controller |
| 6 | `watchdog_controller.py` | All of the above |

**Build order rationale:** Logger first (everything needs it), alerts second (everything
reports through it), then heartbeat (simplest safety check), then failsafe (needs heartbeat
to trigger), then reconciler (needs failsafe for SAFE_MODE), finally the orchestrator that
ties them together.

---

## Integration Points

**With existing engine:**
- `engine/paper_trading_engine.py` — kill switch already exists; watchdog adds broker-level safety on top
- `engine/strategy_controller.py` — controller manages strategy enable/disable; watchdog can force-disable via SAFE_MODE
- `controllers/prop_controller.py` — prop rules (DD limits) are the inner safety ring; watchdog is the outer ring

**With schedulers:**
- `schedulers/daily_runner.sh` — could include post-run heartbeat verification
- Watchdog runs independently as a background process, not tied to scheduler cadence

**With state:**
- `account_state.json` — watchdog validates integrity, reconciler uses as truth source
- Watchdog maintains its own state: `logs/watchdog_state.json` (last check times, SAFE_MODE status, incident counts)

---

## Testing Strategy

Before broker connection, validate watchdog logic with simulated failures:

1. **Heartbeat**: Mock broker API returning errors → verify SAFE_MODE entry
2. **Reconciliation**: Inject position mismatch → verify halt + alert
3. **State corruption**: Write bad JSON to state file → verify detection + backup load
4. **Runaway**: Simulate 20 trades in 5 bars → verify strategy disable
5. **Clock drift**: Mock NTP returning offset → verify severity escalation
6. **Order timeout**: Simulate no ACK → verify strategy lock + polling

All tests should verify:
- Correct severity assigned
- Correct action taken
- Incident logged
- Alert sent (to test channel)
- Recovery path works
