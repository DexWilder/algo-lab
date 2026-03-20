# VOLATILITY Candidate Selection — 2026-03-20

**Context:** VOLATILITY is the #1 portfolio gap (0 active, 0 probation).
The portfolio gap dashboard governs this selection.

---

## Ranked Candidates

### #1: VolManaged-EquityIndex-Futures (CONVICTION-READY)

| Dimension | Assessment |
|-----------|-----------|
| **Status** | TESTING — conviction-ready since 2026-03-18 |
| **Asset** | MES (equity index) |
| **Session** | Daily close (daily rebalance) |
| **Direction** | Long only |
| **Factor** | VOLATILITY — sizing regime, not a directional signal |
| **Rubric** | 22 effective (highest challenger in the entire system) |
| **Backtest** | Sharpe improvement 0.64 → 0.92 (+44%) on MES buy-and-hold |
| **Portfolio fit** | Marginal Sharpe +0.089, portfolio corr 0.088 |
| **Overlap** | NoiseBoundary pairwise 0.368 but portfolio-level 0.088 |
| **Blocker** | Tier restricted: MICRO/REDUCED until forward evidence confirms crisis DD |

**Why #1:** This is the strongest candidate in the entire FQL system by
rubric score (22 effective). It has already passed first-pass, counterfactual,
and portfolio contribution analysis. It was explicitly tagged
`UPGRADE_SEQUENCE #2` — enters conviction when next slot opens after June 1.
The mechanism (vol-managed sizing) is academically replicated across decades.

**Why not immediately:** MES long-only on daily close. This IS equity index
morning-adjacent (rebalances daily, holds continuously). However, the
dashboard concern about morning crowding is about signal timing, not
position holding. VolManaged doesn't generate morning entry signals — it
adjusts position size at the daily close. The crowding risk is different
from adding another 09:45 entry on MNQ.

**Honest drawback:** Long-only MES adds to the 2.7:1 long bias. But the
mechanism is fundamentally different from every other strategy — it's the
only sizing regime in the portfolio. Factor independence justifies the
directional tilt.

---

### #2: TV-Gold-Bandwidth-Squeeze (IDEA — needs spec + conversion)

| Dimension | Assessment |
|-----------|-----------|
| **Status** | IDEA — no spec, no strategy.py, no first-pass |
| **Asset** | MGC (metal) |
| **Session** | Intraday |
| **Direction** | Both |
| **Factor** | VOLATILITY (vol compression → expansion breakout) |
| **Blocker** | MGC at 4-strategy hard limit |

**Why #2:** Gold-specific vol squeeze. Different mechanism from equity
squeeze (TTMSqueeze rejected on MGC, but bandwidth squeeze is a different
filter). Both-direction gives short exposure.

**Why not #1:** MGC is at the 4-strategy hard limit. Adding a 5th MGC
strategy violates portfolio construction policy unless it displaces one.
The weakest MGC strategy is PB-MGC-Short (rubric 16) — a squeeze strategy
would need to score higher to displace it. Untested, so this is speculative.
Also, "intraday MGC morning" adds to morning crowding, not away from it.

**Verdict:** Queue for conversion only if MGC slot opens (PB-MGC
displaced or archived) or if another asset variant is viable.

---

### #3: TV-Crude-OVX-Regime-Shift (IDEA — blocked)

| Dimension | Assessment |
|-----------|-----------|
| **Status** | IDEA — blocked by proxy data |
| **Asset** | MCL (energy) |
| **Session** | Daily |
| **Direction** | Both |
| **Factor** | VOLATILITY (OVX regime shifts) |
| **Blocker** | Needs OVX proxy data and finished playbook |

**Why #3:** Energy-native VOL fills two gaps simultaneously (VOLATILITY
factor + Energy asset class). MCL has 0 strategies. Both-direction helps
long bias. Different from everything in the portfolio.

**Why not higher:** Blocked. OVX data is not in the pipeline. The strategy
needs an OVX proxy (crude oil implied vol from options) which requires
external data. Not testable now.

**Verdict:** Park until OVX proxy data is available. Include in the
targeted harvest directive for Energy + VOL.

---

## Other Candidates Reviewed (Not Ranked)

| Candidate | Reason for Exclusion |
|-----------|---------------------|
| NR7-Breakout (M2K) | MOMENTUM-like (contraction → breakout is momentum, not VOL); M2K morning adds to crowding |
| BBW-Percentile (M2K) | Same concern; fires very rarely (low trade count risk) |
| HVPercentile-Expansion (multi) | Underdefined — needs spec work before it's assessable |
| RangeExpansion (multi) | DOWNGRADED — active Sharpe decay, pending archive at Apr 18 review |
| TV-VIX-Term-Structure-Hedge (MES) | Blocked by tail risk controls; MES morning adds to crowding |
| TV-VVIX-VIX-Divergence (MES) | Blocked by strategy ambiguity; MES morning |
| TV-Treasury-Macro-Vol-Targeting (ZN) | Sizing overlay, not standalone; blocked by engineering |
| THEME-VolGated-Structural (MES) | Research theme, not a testable strategy |

---

## Recommendation: Proceed with #1 (VolManaged-EquityIndex-Futures)

**Rationale:**

1. It's conviction-ready — no spec writing, no first-pass needed. The
   work is already done. Rubric 22 (highest in the system).

2. It fills VOLATILITY (0 active, 0 probation) — the #1 gap.

3. Portfolio contribution is confirmed positive (marginal Sharpe +0.089,
   correlation 0.088).

4. The dashboard concern about equity morning crowding is mitigated: this
   strategy rebalances at daily close, not morning entry. It doesn't
   compete for the same execution window as VWAP-MNQ or ORB-MGC.

5. The long-only bias concern is real but tolerable: the mechanism is
   fundamentally unique (sizing regime vs all other strategies being
   entry/exit timing). It adds a new dimension to the portfolio.

6. Tier restriction (MICRO/REDUCED) limits the risk while forward
   evidence accumulates.

**What to do:**
- Enter VolManaged into the forward runner at MICRO tier
- Set probation targets: 30 forward days, Sharpe > 0.5, crisis-DD check
- Add to probation scoreboard and rates challenger review equivalent
- Do NOT wait for June 1 — the upgrade sequence said "after June 1" but
  the slot is available now (probation has room)

**What NOT to do:**
- Do not convert TV-Gold-Bandwidth-Squeeze until MGC slot opens
- Do not attempt OVX-Regime-Shift until data is available
- Do not convert any M2K NR7/BBW ideas (MOMENTUM-like, morning crowded)

---

## Parallel: Targeted Harvest Directive

Issue to Claw for next week's gap harvest:

**Priority targets:**
1. **Energy VOL** — crude oil or natural gas vol strategies testable
   without OVX data (e.g., ATR-based crude regime, energy squeeze
   on MCL with existing data)
2. **VALUE on any asset** — 0 ideas in catalog, biggest blind spot
3. **Commodity VOL** — MGC/MCL vol strategies that could work on
   non-crowded assets
4. **Short-biased strategies on any non-equity asset** — portfolio
   long:short is 2.7:1

**Exclusions:**
- No more equity morning momentum ideas
- No more overnight continuation ideas (family closed)
- No cross-asset baskets requiring multiple data feeds not in pipeline
