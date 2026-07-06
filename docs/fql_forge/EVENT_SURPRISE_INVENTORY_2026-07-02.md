# Event-Surprise Data Inventory (T5, WH1) — 2026-07-02

> WH1 event edges need ACTUAL vs EXPECTED (surprise) + release timestamp, not just date-flags/levels. Honest inventory.

| Event | Have actual? | Have consensus/expected? | Release timestamp? | Local path | Cost/source to complete | First WH1 packet unlocked |
|---|---|---|---|---|---|---|
| CPI | LEVEL only (cpiaucsl) | **NO** | no (monthly date only) | data/feeds/cpi_levels.csv | consensus via calendar API (free-ish: scrape / FRED has no consensus) | CPI-surprise → MES/MNQ reaction-path |
| NFP | **NO** | **NO** | no | — | BLS actual + consensus source | NFP-surprise → index open drift |
| FOMC | rates only (policy_rates) | **NO** (no path/dots) | decision dates only | data/feeds/policy_rates.csv | statement/dot-plot timing | FOMC-day vol-crush → index |
| EIA | **NO** | **NO** | no | — | EIA free API (actual) + consensus | inventory-surprise → CL regime (index only if crude=regime) |
| Treasury auction | yield/amt/reopening | **NO tail/bid-to-cover/indirect** | auction date | data/feeds/treasury_auctions.csv | TreasuryDirect API (tail/BTC) | auction-tail → rates regime → index |
| VIX | LEVEL (usable regime) | n/a | daily | data/feeds/vix.csv | HAVE (regime input) | VIX-regime → index (tested, weak) |

**Verdict: event-surprise is the biggest missing WH1 frontier.** We have levels/dates/yields but NOT the surprise (actual−expected) that drives index reaction. **Next data unlock (P1):** a consensus/actual event feed (CPI/NFP/FOMC). Until then, event-conditioned WH1 is DATA_STATUS_UNPROVEN (not blocked — sourceable). VIX is the only usable event/regime input we hold, and it tested weak.
