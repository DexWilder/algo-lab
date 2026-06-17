# Feed-Dependent Candidate Packets — Batch 2 (FRED daily drivers) — 2026-06-17

> State: `FRED_YIELD_CURVE_BRANCH_CLOSED__FORGE_DISCOVERY_CONTINUES`. Information-surface expansion: FRED daily market-based drivers acquired (structural only — `fred_drivers_batch2_2026-06-17.json`). **Priority = research leverage + feed availability, NOT edge.** Every packet is zero-evidence until screened with the locked sequence (validate → no-lookahead/timestamp audit → join → coverage → first-cut → brutal board). NEW feeds now in `data/feeds/`: `real_rates.csv`, `inflation_expectations.csv`, `dollar_index.csv`, `vix.csv`, `energy_spot.csv`, `credit_oas.csv`.

> **Caution (carry-over from prior OOS catch):** the killed gold×ZN-price-trend gate (OOS sign-inversion) means any gold-conditioning idea below MUST be screened with a date-split OOS as a first-class gate, not just full-sample. Real yield / dollar are the *actual* macro drivers (vs ZN price proxy), so they may differ — but they get NO free pass.

Per-packet fields: mechanism · feed · join key/timestamp · instruments · min sample · no-lookahead traps · cheap-screen plan · kill criteria.

---

## P8 — Real-rate-driven gold (TIER 1, daily, our live asset + new driver)
- **Mechanism:** 10y TIPS real yield (DFII10) is the canonical gold driver (gold ↑ as real yields ↓). Daily directional/gating on MGC by real-yield level/Δ state. The economic driver itself, not a price proxy.
- **Feed:** `real_rates.csv` (DFII10, daily, 2003+). **Acquired.**
- **Join/timestamp:** real yield dated D published ~EOD D → LAG 1 trading day; merge_asof backward, allow_exact_matches=False.
- **Instruments:** MGC.
- **Min sample:** daily 2019+ (futures overlap), ≥2 real-rate regimes (the 2022 hiking + 2024+ easing both present).
- **No-lookahead traps:** same-day real-yield use; vintage (FRED revises rarely but check); regime-recency (the OOS inversion trap).
- **Cheap-screen plan:** predeclared real-yield state (lagged) → MGC daily position; **date-split OOS mandatory** (train/test halves must agree in sign); board + corr to MNQ.
- **Kill criteria:** OOS sign-inversion (like the ZN gate) → KILL; PF ≤1.2 cost-aware; concentration; works only full-sample not per-half.

## P9 — Breakeven-inflation regime rotation gold↔rates (TIER 1, daily — revives #T12 w/o consensus)
- **Mechanism:** 10y breakeven inflation (T10YIE) is a market-based, DAILY inflation expectation — no CPI consensus needed. Rising breakevens → favor MGC; falling → favor ZN. Rotation/gate.
- **Feed:** `inflation_expectations.csv` (T10YIE/T5YIE, daily, 2003+). **Acquired.** (This is the unblock for the #T12 inflation-driver idea that died on date-only CPI.)
- **Join/timestamp:** breakeven dated D ~EOD D → lag 1d; strictly prior.
- **Instruments:** MGC, ZN.
- **Min sample:** daily 2019+; rising + falling inflation-expectation regimes both present.
- **No-lookahead traps:** same-day breakeven; regime recency; ensure rotation is on lagged state.
- **Cheap-screen plan:** lagged breakeven Δ/level state → rotate MGC↔ZN; gold leg / rates leg / rotation separately; date-split OOS; board.
- **Kill criteria:** OOS inversion; PF ≤1.2; rotation no better than the better single leg (then it's not a rotation edge).

## P10 — Dollar-driven gold (TIER 1, daily)
- **Mechanism:** Broad USD index (DTWEXBGS); gold ↑ as USD ↓. Daily directional/gating on MGC by dollar trend/level state. A proper dollar driver (better than the 2024+ FX basket).
- **Feed:** `dollar_index.csv` (DTWEXBGS, daily, 2006+). **Acquired.**
- **Join/timestamp:** lag 1d; strictly prior.
- **Instruments:** MGC (and MCL/risk assets as secondary).
- **Min sample:** daily 2019+.
- **No-lookahead traps:** same-day dollar; the gold-conditioning OOS trap.
- **Cheap-screen plan:** lagged dollar state → MGC position; date-split OOS; board + corr.
- **Kill criteria:** OOS inversion; PF ≤1.2; collinear with P8 real-rate signal (then not additive — check mutual corr).

## P11 — VIX risk-state filter/driver (TIER 2, daily)
- **Mechanism:** VIX level/term-state as a risk-on/off gate applied to existing daily structures (equity/gold), or vol-regime directional. A state classifier more than a standalone edge.
- **Feed:** `vix.csv` (VIXCLS, daily, 1990+). **Acquired.** (VX futures curve would be richer — feed-blocked.)
- **Join/timestamp:** VIX close dated D ~EOD D → lag 1d.
- **Instruments:** MES/MNQ (as filter), MGC.
- **Min sample:** daily 2019+; calm + stress regimes.
- **No-lookahead traps:** same-day VIX close to gate same-day trade; survivorship of the calm regime.
- **Cheap-screen plan:** VIX-state gate on a live structure (e.g., MGC sleeve) → pre/post with predeclared retention floor (no 85%-cut overfit); board.
- **Kill criteria:** OVERFIT_RISK if PF lift only via heavy trade-cut; no improvement over ungated.

## P12 — WTI–Brent / energy dislocation (TIER 2, near-daily)
- **Mechanism:** WTI–Brent spread or WTI vs Henry Hub state; trade MCL on dislocation/reversion. Energy-fundamental driver, distinct from equity/gold/rates.
- **Feed:** `energy_spot.csv` (WTI/Brent/HenryHub, daily). **Acquired.** (Spots, not futures — proxy; true crack/curve needs product futures.)
- **Join/timestamp:** spot dated D (note WTI last 2026-06-08 — slight publication lag); lag 1d.
- **Instruments:** MCL.
- **Min sample:** daily 2021+ (MCL history).
- **No-lookahead traps:** spot-vs-futures basis; spot publication lag; MCL cost-fragility.
- **Cheap-screen plan:** lagged spread z-state → MCL position; explicit cost ratio; board.
- **Kill criteria:** cost eats edge (MCL history); PF ≤1.2; spot-proxy artifact.

## P13 — Credit-OAS risk-on/off (TIER 3, daily but SHORT history)
- **Mechanism:** HY credit OAS (BAMLH0A0HYM2) widening/tightening as a risk-state gate.
- **Feed:** `credit_oas.csv` — **only 2023-06+ in this pull (~786 rows)**; short sample.
- **Min sample:** INSUFFICIENT (2023+ single regime) → likely sample-blocked. Catalog only; needs longer OAS series.
- **Kill criteria:** insufficient sample (likely); single-regime.

---

## Priority when screening (research leverage + feed access — NOT edge)
1. **P8 real-rate gold** & **P9 breakeven rotation** — daily, our live gold asset + genuinely new macro driver, feed in hand. Each requires a date-split-OOS-first screen (the prior gold-conditioning died OOS — no free pass).
2. **P10 dollar gold** — daily, feed in hand; check non-collinearity with P8.
3. **P11 VIX gate** — state classifier; overfit-guarded.
4. **P12 energy dislocation** — near-daily, MCL cost caveat.
5. **P13 credit OAS** — sample-blocked (catalog).

## Still feed-blocked (operator-side download, documented in LEVER_B_QUEUE)
- Treasury auctions (`.gov` CSV) — WP-B1, runs first when it lands.
- Futures roll-yield P1 — multi-contract F2 rates futures (not on FRED).
- CPI *surprise* — pre-release consensus (proprietary; FRED has realized level only).
- EIA crude inventory — correct FRED EIA series ID TBD / or EIA-direct (`.gov` blocked).

## Boundaries
Packets + acquisition + structural validation only. No screens here, no edge claims, no labels, no synthetic fill, no mutation. Screens are the next discovery step (report-only), each with date-split OOS where gold-conditioning is involved.
