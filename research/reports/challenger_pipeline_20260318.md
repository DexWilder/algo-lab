# Challenger Pipeline Status — 2026-03-18

*Two lanes running in parallel: live displacement battles + emerging challengers.*

---

## Lane 1: Active Displacement Battles

| # | Battle | Score | Target | Status | Timeline |
|---|--------|-------|--------|--------|----------|
| 1 | Treasury-Rolldown → MomIgn | 20 vs 14 | Watch slot | Decision-grade, evidence accumulating | June 1 (74d) |
| 2 | VolManaged → Conviction | 22 | Open slot | **CONVICTION-READY**, all conditions met | After June 1 |
| 3 | VolManaged → PB-MGC-Short | 22 vs 16 | Core slot | Needs 8w conviction + fwd Sharpe > 0.5 | ~6 months |

No changes to this lane. Evidence accumulates. Decisions are date-gated.

---

## Lane 2: Emerging Challengers

### Tier 1: Code exists, testable now, fills priority gaps

**Gold-BW-Squeeze-MGC (VOLATILITY)**
- Code exists: `strategies/gold_bw_squeeze/`
- Quick test: Long-only PF 3.46, 13 trades. Short fails (PF 0.17).
- Factor: VOLATILITY (0 in core, 1 in watch)
- Assessment: Strong long-only tail engine potential on MGC, but 13 trades
  is too few for statistical confidence. The mechanism (bandwidth squeeze
  → expansion breakout) is well-documented. Gold-specific vol pattern is
  different from equity squeeze (TTMSqueeze).
- Gap value: VOL factor (+2) but MGC is at soft cap (4 strategies)
- **Next action:** Run formal first-pass with walk-forward split. If
  long-only WF is stable across both halves, this is a serious candidate.
- **Could compete for:** Watch slot (if WF holds, rubric ~16-18) or
  eventually displace TTMSqueeze (17) as the stronger VOL representative.

### Tier 2: Ideas with high gap value, need conversion

**Treasury-CPI-Day-ZB-Short (EVENT + Rates)**
- Status: MONITOR in registry. ZB short PF 2.81, 19 trades, 63% WR.
- Original long-bias hypothesis rejected, but ZB SHORT during CPI days
  showed standout results — hawkish regime CPI reaction.
- Factor: EVENT (fills gap beyond FOMC/NFP)
- Asset: ZB (rates — 0 active)
- Gap value: HIGH (EVENT + Rates = 2 gaps)
- **Next action:** Spec the ZB-short CPI-day variant as a separate
  strategy. 19 trades is marginal but the PF is strong.
- **Could compete for:** Watch slot. Different event family from
  PreFOMC and NFP.

**EIA-Inventory-Surprise-MCL (EVENT + Energy)**
- Status: REJECT (PF 0.85-0.93 on both first-pass runs)
- Factor: EVENT
- Asset: MCL (energy — 0 active)
- **Dead end for now.** Two first-pass runs, both REJECT. The EIA
  event on MCL does not produce a testable edge with current logic.
- **Salvage potential:** Low. The rejections are structural (event
  doesn't produce consistent direction on 5m bars).

### Tier 3: High-concept ideas, not yet actionable

**THEME-VolGated-Structural-Intraday**
- Research direction, not a single strategy. The idea that structural
  strategies (gap-fade, session-open) work ONLY in specific vol regimes.
- Factor: STRUCTURAL + VOLATILITY
- **Not convertible yet.** This is a meta-research direction that would
  produce multiple strategies, not one. Park for a future research sprint.

**ManagedFutures-Carry-Diversified**
- Cross-asset carry basket. Needs the carry lookup table to be more
  mature (more assets, real signals not proxies).
- Factor: CARRY
- **Blocked by carry lookup v2.** If Treasury-Rolldown's carry signal
  proves useful in forward, this becomes the next carry expansion.

---

## Pipeline Summary

| Tier | Candidate | Gap | Next Step | Competition |
|------|-----------|-----|-----------|-------------|
| **Active** | Treasury-Rolldown | CARRY+Rates | Evidence → June 1 | vs MomIgn (14) |
| **Active** | VolManaged | VOL+MES | Conviction entry post-June 1 | vs PB-MGC (16) later |
| **Emerging #1** | Gold-BW-Squeeze Long | VOL | First-pass WF needed | vs TTMSqueeze (17) if strong |
| **Emerging #2** | Treasury-CPI-Day ZB-Short | EVENT+Rates | Spec + convert needed | New event family |
| **Dead** | EIA-Inventory MCL | — | Rejected (2x) | — |
| **Parked** | Theme-VolGated | STRUCTURAL+VOL | Future sprint | — |
| **Blocked** | MF-Carry-Diversified | CARRY | Needs carry v2 | — |

---

## Highest-Leverage Emerging Task

**Gold-BW-Squeeze formal first-pass** is the highest-leverage emerging
task. Why:

1. Code already exists — no conversion needed
2. Long-only PF 3.46 is very strong (if it holds in walk-forward)
3. Fills VOLATILITY gap (same as VolManaged but different mechanism
   and asset)
4. If WF holds, it could compete with TTMSqueeze-M2K (watch, 17) as
   the stronger VOL representative — different asset (MGC vs M2K),
   different mechanism (bandwidth squeeze vs TTM squeeze)
5. 13 trades is the risk — may not survive WF split

**Treasury-CPI-Day ZB-Short** is #2 — needs a spec and conversion but
would open a new event family (CPI) on a gap asset (rates). The 19-trade
PF 2.81 is compelling if regime-conditioned.
