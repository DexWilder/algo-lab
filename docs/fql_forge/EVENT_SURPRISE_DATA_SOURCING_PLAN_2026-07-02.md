# Event-Surprise Data Sourcing Plan (2026-07-02) — the biggest missing WH1 frontier

> Status: DATA_STATUS_UNPROVEN / SOURCE_REQUIRED (NOT data_blocked). Actuals are largely free; CONSENSUS is the real gap.

| Event | Desired fields | Release timestamp | Free actual source | Consensus source | Local status | First WH1 packet | Operator action? |
|---|---|---|---|---|---|---|---|
| CPI | actual, consensus, surprise (=act−cons), YoY/MoM, 08:30 ET stamp | 08:30 ET | FRED/BLS (free) | **gap** (calendar API / scrape) | level only | CPI-surprise → MES/MNQ open-drift + first-hour path | source consensus |
| NFP | actual, consensus, surprise, revisions, 08:30 ET | 08:30 ET | BLS (free) | **gap** | none | NFP-surprise → index open drift | source consensus |
| FOMC | decision, dot-path, statement time (14:00 ET), presser (14:30) | 14:00 ET | FRED policy_rates (have) | rate SURPRISE needs Fed-funds-futures-implied (gap) | rates only | FOMC-surprise → vol-crush/drift index | source FF-futures or Mked implied |
| Treasury auction | tail (high yield − WI), bid-to-cover, indirect/direct % | auction 13:00 ET | **TreasuryDirect API (free!)** | n/a (tail IS the surprise) | yield/amt only (no tail/BTC) | auction-tail → rates regime → index | pull TreasuryDirect |
| EIA | actual, consensus, surprise (crude/gasoline stocks), 10:30 ET Wed | 10:30 ET Wed | **EIA API (free)** | gap | none | EIA-surprise → CL regime (index only if crude=risk input) | pull EIA + consensus |
| VIX/vol | level, change, term-structure | daily | HAVE (vix.csv) | n/a | have (weak) | VIX-regime → index (tested weak) | none |

## Verdict & plan
- **Cheapest high-value unlock: TreasuryDirect API (free)** → auction tail/bid-to-cover (the tail IS the surprise, no consensus needed). Rates-regime → index. **P1, no operator cost.**
- **EIA API (free)** → crude inventory surprise (needs a consensus, but actual is free; proxy-surprise = actual vs AR-forecast as stopgap).
- **CPI/NFP consensus is the true gap** — needs a calendar API (paid) or scrape. Stopgap: **proxy-surprise = actual (FRED, free) − rolling-AR-forecast**; weaker than real consensus but testable now.
- Nothing here is data_blocked; all sourceable. Next data actions: (1) TreasuryDirect auction tails [free], (2) EIA stocks [free], (3) proxy-surprise CPI/NFP from FRED actuals.
