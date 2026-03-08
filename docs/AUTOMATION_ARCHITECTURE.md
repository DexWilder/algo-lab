# Automation Architecture

Execution architecture for a fully automated futures trading lab operating on micro contracts (MES, MNQ, MGC).

Four layers -- strategy, risk, execution, monitoring -- each with strict separation of concerns. Strategies produce pure signals. Controllers apply risk rules. Adapters talk to brokers. Monitors keep everything alive and safe.

---

## Architecture Layers

### Layer 1: Strategy Engine

Pure signal generation. No prop rules, no risk logic, no position sizing.

- Each strategy is a standalone Python module exposing a `generate_signals(df)` interface
- Deterministic: identical data always produces identical signals
- Output fields: `signal_direction`, `stop_price`, `target_price`, `signal_type`
- No discretionary inputs -- all parameters are fixed constants baked into the module
- Signals are based only on confirmed (closed) bars to eliminate repaint risk
- Current validated families: PB trend (MGC, MNQ, MES). REV module experimental.

### Layer 2: Risk Controller

Applies account-level rules and position sizing to raw signals. Config-driven -- swap the JSON file to change account behavior without touching strategy code.

- Existing configs: `lucid_100k.json`, `apex_50k.json`, `generic.json`, `cash_account.json`
- Controls:
  - Max daily loss (hard stop, flattens all positions)
  - Trailing drawdown (EOD trailing for prop accounts)
  - Position limits (max contracts per signal, per account)
  - Time lockouts (no new trades within N minutes of session end)
  - Consecutive loss limits (disable strategy after N consecutive stops)
- Implementation: `controllers/prop_controller.py` + `controllers/prop_configs/`
- Completely decoupled from strategy logic -- strategies never import or reference controllers

### Layer 3: Execution Adapter

Translates approved signals into broker orders and manages position lifecycle.

- **Order types**: market, limit, stop-limit
- **Position tracking**: entry price, contract count, unrealized/realized PnL
- **Session management**: auto-flatten at configured session end time
- **Reconnect logic**: handle disconnects, requote on reconnect, verify position state
- **Order state machine**:
  ```
  pending → submitted → filled
                      → cancelled
                      → rejected
  ```
- Adapter is stateless between sessions -- all state reconstructed from broker on connect

### Layer 4: Monitoring and Safety

Keeps the system alive, bounded, and observable.

- **Kill switch**: immediate flatten of all positions + disable all strategies
- **Daily PnL tracking**: real-time running total with hard stop enforcement
- **Heartbeat monitoring**: detect stuck or dead processes, restart or alert
- **Trade logging**: every order, fill, cancel, and rejection written to persistent store
- **Alert system**: email or webhook on anomalies (missed fills, unexpected positions, data gaps)
- **Circuit breakers**:
  - Max loss per trade
  - Max loss per day
  - Max loss per week
- **Graceful degradation**: if data feed drops, flatten open positions and wait for recovery

---

## Broker Integration

Broker-agnostic adapter pattern. The execution layer defines an interface; each broker gets its own adapter implementation.

**Adapter interface:**

```python
class BrokerAdapter:
    def connect(self) -> None
    def disconnect(self) -> None
    def place_order(self, order: Order) -> str       # returns order_id
    def cancel_order(self, order_id: str) -> bool
    def get_position(self, symbol: str) -> Position
    def get_fills(self, since: datetime) -> list[Fill]
    def flatten(self, symbol: str) -> None           # emergency close
```

**Primary broker candidates:**
- Tradovate API (REST + WebSocket)
- Rithmic (FIX protocol)
- Interactive Brokers (TWS API)

Paper trading mode is mandatory before any live deployment.

---

## Data Flow

```
Market Data → Strategy Engine → Risk Controller → Execution Adapter → Broker
                                                         |
                                                    Trade Logger
                                                         |
                                                   Monitor / Alerts
```

Signals flow forward only. No layer reaches back into a previous layer. The monitor observes execution output but never modifies signals or risk decisions.

---

## Safety Controls

### Pre-Trade Checks
- Session is active (within configured trading hours)
- Daily loss limit not exceeded
- Position size within account limits
- No time lockout in effect
- Strategy not disabled by consecutive loss breaker

### Post-Trade Checks
- Fill price is within expected slippage tolerance
- Realized PnL is within reasonable bounds
- Position state matches expected state after fill

### Emergency Procedures
- Kill switch flattens all positions across all symbols and disables all strategies
- Triggered manually or automatically by circuit breaker
- Max daily loss: configurable per account type via controller config
- Max consecutive losses: disable individual strategy after N consecutive stops
- Time lockout: no new entries within configurable window before session end
- Stale data detection: if no new bars received for N seconds, halt all trading

---

## Deployment Phases

**Phase 1: Paper Trading**
- Simulated fills against real-time data feed
- Full execution pipeline active (adapter routes to paper broker)
- Validate signal timing, fill assumptions, PnL tracking accuracy
- Minimum duration: 2 weeks or 100 trades, whichever is longer

**Phase 2: Single-Contract Live**
- 1 contract per signal, tight daily loss limits
- One strategy at a time
- Manual review of every trade for first 5 trading days
- Kill switch tested and verified before going live

**Phase 3: Scaled Live**
- Full position sizing per controller config
- Multiple strategies active simultaneously
- Automated monitoring with alert thresholds tuned from Phase 2 data

---

## Automation-Readiness Checklist

Every strategy must satisfy all items before entering the execution pipeline:

- [ ] No discretionary inputs -- all parameters are fixed constants
- [ ] Deterministic signals -- same data always produces same output
- [ ] Fixed session handling -- clear start/end times, no ambiguity
- [ ] Stable stop/target logic -- ATR-based or fixed, no floating levels
- [ ] No repaint risk -- signals only use confirmed (closed) bars
- [ ] Executable with standard order types -- market, limit, or stop orders only
- [ ] Controller layer separation -- zero prop/risk logic in strategy code
- [ ] Tested on 1+ year of data with documented results
- [ ] Parameter stability verified -- small parameter changes do not break performance

---

## File Structure

```
algo-lab/
├── strategies/          # Layer 1: signal generators
├── controllers/         # Layer 2: risk/prop controllers
│   ├── prop_controller.py
│   └── prop_configs/
│       ├── lucid_100k.json
│       ├── apex_50k.json
│       ├── generic.json
│       └── cash_account.json
├── execution/           # Layer 3: broker adapters (to build)
│   ├── adapter.py       # base adapter interface
│   ├── paper.py         # paper trading adapter
│   ├── tradovate.py     # Tradovate API adapter
│   └── session.py       # session manager
├── monitor/             # Layer 4: safety and monitoring (to build)
│   ├── kill_switch.py
│   ├── logger.py
│   ├── alerts.py
│   └── heartbeat.py
├── engine/              # backtest engine (research)
├── data/                # market data (Databento + TV exports)
└── docs/                # documentation
```

Layers 1 and 2 exist. Layers 3 and 4 are the build targets for full automation.
