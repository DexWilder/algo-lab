# DATA-UNLOCK SPRINT — 2026-07-07

**Directive:** stop mining convenient-OHLCV scraps; unlock better raw material. Rank blocked mechanisms by EV, give minimum dataset + exact acquisition commands for the top 5, and every week add new *testable* mechanisms from outside the OHLCV universe.

**Premise validated this turn.** The last data-ready HIGH-EV mechanism on convenient data (M47 settlement-basis) was KILLED, alongside COT-fade and the overnight anomaly (real gross, cost-fragile). Convenient transforms are exhausted. **But the richer vein is partly already staged and unused.**

---

## WIN #1 — 6 mechanisms unblocked from data ALREADY IN THE BUILDING ($0)

Re-inventory of `data/feeds/` + `ES_OPT_statistics` (per the `inventory-before-blocked` rule) moved these off the blocked list — no acquisition needed:

| Mechanism | EV | Unblocked by (staged data) |
|---|---|---|
| ~~M46/M77 options-skew~~ **CORRECTED 2026-07-07** | H | ❌ NOT unblocked — held `ES_OPT_statistics` is a **5-day sample** (2025-06-02..06), not history. Back to Blocked; needs full option-settlement pull (now acquisition #0). I over-unblocked this last turn; owning it. |
| M48/M75 repo/funding stress | M | `funding.csv` = SOFR/EFFR/DFF/RRP_vol/WALCL, 2018–2026 |
| M50/M81 natgas seasonal | M | `energy_spot.csv` Henry Hub NG spot (daily) |
| M63/M82 cross-currency basis | M | 6E/6J/6B 1m + `treasury_yield_curve` + `policy_rates` → CIP deviation |
| M26 crypto liquidation (proxy) | M | `funding.csv` + `deribit_BTC_PERPETUAL` (carry) |
| M45/M85 vol-of-vol / IV-momentum | M | `vix.csv` |
| **+ NEW** M73 COT positioning | M | `cot.csv` spec/comm net, 8 instruments, 2019–2026 |
| **+ NEW** M74 HY-credit regime | M | `credit_oas.csv` |

→ **6 pre-registered packets queued and runnable now** (`pkt_commodity_roll_carry`, `pkt_treasury_auction_cycle`, `pkt_sofr_funding_stress`, `pkt_skew_meanrev`, `pkt_gold_real_rate`, `pkt_cot_positioning_follow`).

---

## RANKED ACQUISITION — genuinely-missing data (EV × unlock-count × attainability)

### #0 (NEW TOP PRIORITY) — Full ES option settlement history  ·  EV **H**  ·  gates the entire observability test
This is now the highest-value purchase because it is the **only** way to run the observability discriminator (`RESEARCH_UNIVERSE_FALSIFICATION.md` Test 1). Held stats file is a 5-day sample. Need daily settlement price per option strike (stat_type=3) + definition, 2019–2026, to invert a real IV surface → signed dealer GEX → test as a conditioner vs the killed max-OI proxy. Exact command (operator, key required):
```python
import os, databento as db
c = db.Historical(os.environ["DATABENTO_API_KEY"])
c.timeseries.get_range(dataset="GLBX.MDP3", symbols=["ES.OPT"], stype_in="parent",
    schema="statistics", start="2019-01-01", end="2026-06-30").to_csv("data/databento/ES_OPT_statistics_full.csv")
# (chunk by quarter if the range is too large; definition schema pull in parallel for strike/cp/expiry)
```
Cost: moderate (statistics is lighter than trades/mbo; chunk to stay near budget). **Without it, H-observability cannot be tested at all.**

### #1 — VIX futures term structure  ·  EV **H**  ·  ~$8 (auto-approve)
Unlocks **M69 vix_term_structure_carry** (short VX front in contango — Simon-Campasano 2014), strengthens M32/M45.
Minimum dataset: VX continuous front + 2nd month, daily, 2019–2026.
**Attempted this session → FAILED: no `DATABENTO_API_KEY` in the sandbox (key lives on operator machine).** Exact operator command:
```python
import os, databento as db
c = db.Historical(os.environ["DATABENTO_API_KEY"])
c.timeseries.get_range(dataset="GLBX.MDP3", symbols=["VX.c.0","VX.c.1"],
    stype_in="continuous", schema="ohlcv-1d", start="2019-01-01", end="2026-06-30"
).to_csv("data/databento/VX_termstructure_1d.csv")
```

### #2 — EIA weekly inventory (crude + natgas)  ·  EV **M**  ·  FREE key
Unlocks **M80 eia_inventory_surprise** + fundamentals for M81; conditions MCL.
Minimum dataset: weekly crude stocks (WCESTUS1) + NG storage, 2015–now.
Operator: register free key `https://www.eia.gov/opendata/register.php` (1 min), then:
```bash
curl "https://api.eia.gov/v2/petroleum/stoc/wstk/data/?api_key=$EIA_KEY&frequency=weekly&data[0]=value&facets[series][]=WCESTUS1&start=2015-01-01&length=5000" -o data/feeds/eia_crude_stocks.json
curl "https://api.eia.gov/v2/natural-gas/stor/wkly/data/?api_key=$EIA_KEY&frequency=weekly&data[0]=value&start=2015-01-01&length=5000" -o data/feeds/eia_natgas_storage.json
```

### #3 — Index reconstitution calendar + add/delete lists  ·  EV **M**  ·  FREE
Unlocks **M79 russell_reconstitution** (front-run June Russell rebalance).
Minimum dataset: rebalance dates (deterministic — Russell: rank last trading day of April, effective last Friday of June; S&P: 3rd Fri Mar/Jun/Sep/Dec) + preliminary add/delete lists (FTSE Russell / S&P DJI press releases, published ~2 weeks prior, free PDF). Dates are hardcodable now; only the name lists need the announcement.

### #4 — Economic consensus / surprise  ·  EV **M**  ·  free reaction-proxy first
Unlocks **M29/M43** + conditions M66 (FOMC), CPI/NFP mechanisms.
Cheapest path (no acquisition): use the market's own 8:30-ET reaction as the surprise proxy (held 1m data) — partially reclassifies M29 as testable-now. Full path: scrape a free economic calendar (consensus vs actual) or FRED ALFRED vintages for actuals.

### #5 — Single-name equity options (top-10 SPX weights)  ·  EV **M**  ·  moderate (OPRA, heavier)
Unlocks **M78 index_dispersion** (index IV vs weighted single-name IV = correlation premium).
Minimum dataset: statistics/IV for AAPL/MSFT/NVDA/AMZN/GOOGL/META/… options, 2023–now. Lower priority (heavy data, moderate cost) — defer until #1–#4 produce a survivor.

---

## Weekly quota tracker (new standing rule — no week ends on kills alone)
| Target | This week | Status |
|---|---|---|
| ≥20 new external mechanisms | **20** (M66–M85, named-source) | ✅ |
| ≥5 new test packets | **6** pre-registered, runnable | ✅ |
| ≥1 dataset staged or explicitly failed | VX futures → **explicit-fail (no key), command handed off** | ✅ |
| Updated priority ranking | this doc | ✅ |

**Next execution:** run the 6 queued packets (all on held data) → any survivor gets full DSR/adversarial validation; operator runs the #1 VX pull to open the vol-carry vein. The goal is not another local mutation — it is a bigger, richer input funnel.
