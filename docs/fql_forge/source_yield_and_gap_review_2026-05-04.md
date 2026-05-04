# Source-Yield + Gap-Map Review — 2026-05-04

**Filed:** 2026-05-04 (Lane B / Forge work — no Lane A surfaces touched)
**Companion to:** `research/data/harvest_triage/2026-05-04.md` (today's triage; this review reads from it + registry + portfolio truth table)
**Purpose:** Answer the operator-defined questions from option 2 of today's hot-lane menu — which sources produce useful candidates, which produce noise, which families/regimes/assets are undercovered, where harvest should be targeted next.

---

## 1. Source-yield analysis

### Registry-wide accept rates (n=151 strategies)

| source_category | n | idea | rejected | archived | probation | core | monitor | accept-rate* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **academic** | 43 | 24 | 7 | 8 | 2 | 0 | 2 | **65.1%** |
| **tradingview** | 37 | 19 | 11 | 6 | 1 | 0 | 0 | **54.1%** |
| internal | 21 | 3 | 10 | 5 | 0 | 3 | 0 | 28.6% |
| **github** | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 100.0% (unproven) |
| expansion | 7 | 3 | 2 | 2 | 0 | 0 | 0 | 42.9% |
| other | 7 | 7 | 0 | 0 | 0 | 0 | 0 | 100.0% (unproven) |
| practitioner | 5 | 4 | 1 | 0 | 0 | 0 | 0 | 80.0% |
| ict | 3 | 0 | 2 | 1 | 0 | 0 | 0 | **0.0%** (closed family — see §4) |
| user | 3 | 0 | 0 | 3 | 0 | 0 | 0 | **0.0%** |
| factory | 3 | 0 | 1 | 1 | 1 | 0 | 0 | 33.3% |
| unknown | 3 | 0 | 0 | 0 | 3 | 0 | 0 | 100.0% (small n) |
| reddit | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 100.0% (small n) |
| claw_synthesis | 2 | 0 | 2 | 0 | 0 | 0 | 0 | **0.0%** |

*(accept-rate = non-rejected, non-archived; rough proxy)*

**Three observations that matter:**

1. **Academic is the only source with proven downstream survival.** 43 entries, 2 in probation (VolManaged-EquityIndex-Futures, Treasury-Rolldown-Carry-Spread), 2 in monitor. Highest absolute accept rate (65%) AND non-zero post-validation movement. **Academic is the workhorse source.**

2. **GitHub looks 100% accept but is unproven.** 14 entries, ALL still in idea status — none have moved to probation/core/monitor. Recently surged (per today's triage, 37 of 83 incoming notes = 45% are GitHub-sourced — up from ~27% in the prior batch). High volume + unvalidated quality = highest current pile-on risk source.

3. **Three sources have 0% accept rate and should be deprioritized:** `ict` (closed family — recurring failure pattern), `user` (3/3 archived), `claw_synthesis` (2/2 rejected). Combined: 8 entries / 0 survivors. Worth filtering at the harvest-engine intake level rather than passing through triage every time.

### Today's harvest mix vs. registry baseline

| source_category | Today's intake (83 notes) | Registry baseline % | Trend |
|---|---:|---:|---|
| github | 37 (45%) | 9.3% | ⬆ Major surge |
| other (uncategorized) | 23 (28%) | 4.6% | ⬆ Surge in unattributed |
| academic | 12 (14%) | 28.5% | ⬇ Declining as % of intake |
| reddit | 10 (12%) | 1.3% | ⬆ Up from rare to material |
| youtube | 1 (1%) | 0% | New source |
| tradingview | 0 (0%) | 24.5% | ⬇ Disappeared from this batch |

**Headline:** intake mix has shifted dramatically. **GitHub + Reddit + uncategorized "other" together = 85% of today's batch**; academic + tradingview together = 14%. Per registry baseline, the long-run accept-quality pattern was inverted (academic + tradingview = 53% of historical intake).

The shift correlates with the rise in pile-on rate (15% at 04-27 → 52% today). Higher GitHub/Reddit volume + lower academic/tradingview share = more saturated-cluster duplicates.

### Per-source noise indicators (today's batch)

Categorical assessment from today's triage classifications:

| Source | Approx ACCEPT (HIGH+COMP) | Approx DEPRIORITIZE | Noise rate |
|---|---:|---:|---:|
| github (37) | ~6 | ~22 | ~60% |
| other (23) | ~5 | ~12 | ~52% |
| academic (12) | ~6 | ~3 | ~25% |
| reddit (10) | ~3 | ~5 | ~50% |
| youtube (1) | 0 | 1 | 100% (small n) |

**Academic is noticeably quieter on noise** (25% deprioritize vs 50%+ for others). This reinforces the registry-wide pattern: academic produces fewer saturating duplicates per unit volume.

---

## 2. Gap-map review (where coverage is thin)

From `docs/PORTFOLIO_TRUTH_TABLE.md` + `research/operating_dashboard.py` FACTOR COVERAGE:

### Active gaps

| Factor / asset class | Gap status | Current coverage | Doctrine note |
|---|---|---|---|
| **FX** | HIGH severity | 0 active strategies | "FXBreak family verified unsalvageable. Fresh design required; lane NOT open." |
| **STRUCTURAL (primary)** | MEDIUM | ZN-Afternoon (microstructure), TV-NFP (event levels) — no pure session-transition primary | "Fresh design required; lane NOT open." |
| **VOLATILITY** | GAP per dashboard | VolManaged-EquityIndex-Futures (probation, separate review path) | Open lane could absorb; not currently one |
| **CARRY** (per dashboard) | GAP per dashboard, CLOSED per truth table | Treasury-Rolldown (out-of-band monthly, just rerun-cleared today) | Truth table marks closed; dashboard sees no intraday carry |
| Energy breadth | Thin | Single XB-ORB-MCL only | LOW priority per truth table |
| Rates beyond ZN (directional) | 0 | Treasury-Rolldown spans ZN/ZF/ZB as spread legs only | No directional ZF/ZB primary |

### Out-of-instrument-scope opportunities surfaced today

Today's triage produced 4 ACCEPT-tier notes blocked by current instrument universe:

| Note | Asset class | Status |
|---|---|---|
| 05-01_11 wasde_relative_revision_grain_value_spread | Grains (ZW/ZC/ZS) | Out-of-scope; novel value mechanism |
| 05-01_12 cattle_on_feed_supply_shock_followthrough | Livestock (LE/HE) | Out-of-scope; novel event family |
| 04-30_10 soft_commodity_contango_oversupply_filter | Soft commodities | Out-of-scope; novel CARRY filter |
| 05-01_13 eia_storage_surplus_natural_gas_value_filter | NG-specific | In-scope (NG covered indirectly via energy) but blocked by no NG-specific data feed |

**These represent latent demand for an instrument-expansion lane.** Currently deferred — would require operator T3 decision at a clean checkpoint.

### Coverage strengths (no gap)

- Treasury auction family — covered (5 ACCEPT HIGH between 04-20 and 04-26 batches)
- VALUE breadth via PPP / Kalman / cross-asset — covered (multiple ACCEPT HIGH; family now saturated per today's triage)
- Workhorse trend (XB-ORB family) — 3 active probation strategies (MNQ, MCL, MYM)

---

## 3. Where the system is OVER-producing (cluster saturation)

From today's triage, 3 new pile-on clusters emerging beyond the existing 8-cluster suppression layer:

| Cluster | Instances this batch | Direct duplicates | Status |
|---|---:|---:|---|
| Mean-reversion stress release confirmation | 4 | 1 | Recommend add to suppression |
| Profit ladder / fractional pyramid (non-equity trends) | 7 | 2 | Recommend add to suppression (1 canonical accepted, others DEP) |
| Cross-country bond futures ridge value w/ turnover gate | 4 | 1 | Recommend add to suppression (1 canonical accepted, others DEP) |

Plus the 8 existing suppression clusters: 5 holding, 3 not holding (#1 dual-thrust, #2 London FX vol-cap, #7 fee/slippage). Specifically, **fee/slippage cluster #7 produced 4 instances including a dead-on filename duplicate (05-04_03 = 05-01_03)** — strongest evidence the layer needs refresh.

**Pattern:** Claw is rediscovering the same mechanisms repeatedly. Per CLAUDE.md "vocabulary drift" framing — same idea, slightly different words. Suppression layer was added 04-24 to address this; it's degrading after 10 days of accumulated intake.

---

## 4. Where harvest should target NEXT (recommendations)

Sequenced by leverage:

### Highest-leverage targets (pursue immediately)

1. **Academic + practitioner sources for FX systematic strategies.** FX is the highest-severity gap. Academic FX literature (e.g., currency carry modifications, FX value beyond PPP, FX vol surface) and practitioner sources (Carver, Clenow trend-following texts) are the clean-quality lanes. Reddit / TradingView FX intake is mostly the closed FX-breakout family — low yield.

2. **STRUCTURAL primary (session-transition) from academic only.** Same story — TradingView/GitHub flood this space with breakout variants that hit suppression cluster #2 (London FX) or pile up in already-DEP'd clusters. Academic session-transition microstructure papers are far rarer but higher-yield.

3. **Treasury auction subcomponents from academic.** Auction family is well-covered for full strategies; what's still missing is per-component validation (dealer-backstop filters, allotment-stress proxies — both ACCEPT COMPONENT today). Academic auction microstructure literature would compound the donor catalog for Phase 0.

### Medium-leverage targets

4. **VOLATILITY component additions.** VOLATILITY is in dashboard GAP. Most VOLATILITY notes today were either suppression hits (hidden-instability) or the new mean-reversion-stress cluster (pile-on). One legitimate VOLATILITY ACCEPT today (variance-correlation crash filter for FX carry). Need more diverse VOLATILITY mechanisms — options term-structure, realized-implied spread, vol-of-vol.

5. **Energy breadth — only if instrument-scope expands.** Currently low-priority per truth table. If grains/livestock/softs expansion lane opens, the deferred WASDE / cattle / contango notes from today become immediately deployable.

### Targets to STOP (or strictly suppress)

6. **FX support-bounce, FX vol-cap, dual-thrust, fee/slippage variants.** All in suppression layer or new-cluster recommendations. GitHub + Reddit are the primary generators of these. Recommend tightening Claw's source-helper intake to filter these patterns at fetch time, not triage time.

7. **Kalman/half-life VALUE subcomponent fragmentation.** Saturated. The 8 NEEDS-REVIEW notes today are all subcomponent claims within suppression cluster #6. Recommend tightening cluster #6 suppression to require explicit cross-source validation before accepting another subcomponent.

8. **`ict`, `user`, `claw_synthesis` source categories.** 0% accept rate combined (8/151 entries, 8 rejected/archived). Deprioritize at intake.

---

## 5. Source-targeting guidance for next Claw cycle

Updated source priorities for Claw to consume (recommend operator review before applying to `inbox/_priorities.md`):

**Increase pull from:**
- Academic Q-fin (SSRN, arxiv) — especially FX systematic, microstructure
- Practitioner books / blog posts (Carver, Clenow, Lopez de Prado adjacent)
- Federal Reserve research (FEDS notes, NY Fed publications) — Treasury auction depth

**Decrease pull from:**
- GitHub general algo repos (without paper backing) — high pile-on rate
- Reddit r/algotrading lower-position notes (top-of-batch is ok, deeper queue is noise)
- Generic TradingView script-of-the-day intake

**Filter at intake:**
- Closed-family patterns (mean_reversion x equity_index, ict x any, gap_fade, overnight equity premium) — auto-reject before triage
- Suppression-cluster patterns (8 + recommended 3 new) — auto-deprioritize
- Out-of-instrument-scope (grains/livestock/softs) — flag and queue for instrument-expansion lane review, not triage

---

## 6. Forward look — what a clean second cycle could unlock

If TRS-2026-06 fires cleanly next month (1st business day of June = Monday 2026-06-01), the second-clean-cycle threshold opens hot lane Phase 0 Track A as operator-eligible. At that point, the donor catalog becomes the gating ingredient.

**Donor catalog state if today's triage is registered next batch:**
- Existing documented components: 17 (per Item 2 day-14 gate, 14 in CVH + 3 in proven_donors)
- Today's harvest contributes: 11 fresh donor candidates (filter / exit / sizing components — see triage §"Top accepted donors")
- Combined potential: ~28 candidates

This is meaningful for Phase 0 — the §3.4 pairing templates need bounded combinations, and 28 donors with ~half labeled by component_type provides enough surface for ~5-10 hybrid generations per twice-weekly run without immediate exhaustion.

**Recommendation:** when next batch register pre-flight runs (whenever the next clean cycle clears), prioritize registering the COMPONENT-class accepts first. Full-strategy accepts can defer; components compound the donor catalog for Phase 0.

---

## 7. What this review is NOT

- Not an action plan. Recommendations require operator T1 confirmation before any change to suppression list, intake config, or registry append.
- Not a Lane A surface — no runtime, portfolio, scheduler, or hold-state changes implied.
- Not a substitute for the next batch register. Today's ACCEPT items are NOT registered today; they wait for the next clean batch register cycle, same operating discipline.
- Not a guarantee that academic-source pivot will work — claim is based on the registry's accept-rate evidence, but academic sources also produce out-of-instrument-scope notes (grains, livestock) that don't immediately help.

---

## Summary: the four operator questions answered

| Question | Answer |
|---|---|
| Which sources produce useful candidates? | **Academic** (65% accept, only source with downstream-validated survivors). Practitioner (80%, small n). TradingView (54%) is solid but starting to plateau on novelty. |
| Which sources produce noise? | **GitHub** (100% historical accept BUT all unvalidated; today 60% deprioritize rate; surging in volume). **Reddit lower-position** (50% deprioritize). **`ict` / `user` / `claw_synthesis`** (0% accept rate — should be filtered at intake). |
| Which families/regimes/assets are undercovered? | **FX** (HIGH gap). **STRUCTURAL primary session-transition** (MEDIUM gap). **VOLATILITY components** (GAP per dashboard). **Out-of-scope: grains, livestock, soft commodities** (latent ACCEPT-tier demand surfaced today, blocked by instrument universe). |
| Are we overproducing in any narrow cluster? | **YES** — 3 new pile-on clusters this week (mean-reversion stress, profit ladder, cross-country bond ridge value) on top of 3-of-8 existing suppression clusters not holding (#1 dual-thrust, #2 London vol-cap, #7 fee/slippage). Saturated VALUE Kalman/half-life subcomponents continue producing borderline NEEDS-REVIEW notes. Total pile-on rate: 52% today vs 15% baseline at 04-27. |
| Where should the next harvest target? | **Increase** academic FX, academic STRUCTURAL session-transition, FED auction research, practitioner texts. **Decrease** GitHub generic, Reddit deep queue, generic TradingView intake. **Filter at intake** closed families + suppression clusters + out-of-instrument-scope notes. |

---

*Filed 2026-05-04 alongside `research/data/harvest_triage/2026-05-04.md`. Lane B Forge work. Companion to today's triage. Recommendations are for operator review and confirmation; no automatic application to suppression layer, intake config, or registry.*
