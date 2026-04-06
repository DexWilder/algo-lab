# Prototype Sprint Results — 5 Candidates

*2026-04-06*

---

## Summary

| # | Candidate | PF | Trades | Verdict | Gap Filled? |
|---|-----------|-----|--------|---------|-------------|
| 1 | MCL Settlement Reversion | 0.98 | 89 | REJECTED | No — Energy still 0 |
| 2 | IBS-MR-M2K (Daily) | ~1.07 | — | MONITOR | No — thin edge |
| 3 | HV Percentile MCL | 1.68 | 5 | REJECTED | No — too few trades |
| 4 | RSI2-Bounce M2K (Daily) | 1.17 | 212 | MONITOR | Partial — long-only viable? |
| 5 | ATR-Filtered VWAP-MNQ | +0.12 PF | — | MODERATE | Yes — component validated |

**Promoted: 0.  Monitor: 3.  Rejected: 2.**

---

## Detailed Results

### #1 MCL Settlement Reversion — REJECTED

Settlement window (14:00-15:00 ET) reversion on crude oil.
Falsification design: settlement window vs generic afternoon vs unconditional.
PF 0.98, no edge. Settlement window not special on MCL.

### #2 IBS-MR-M2K — MONITOR

Daily IBS mean reversion. PF ~1.07 overall, H2 half fails walk-forward.
Edge is thin and unstable. Monitor for convergent academic evidence.

### #3 HV Percentile MCL — REJECTED

Only 5 trades in 4.7 years. Vol compression breakouts on crude too rare.
PF 1.68 statistically meaningless. 2025: both trades lost.
Energy gap remains the biggest unfilled hole.

### #4 RSI2-Bounce M2K (Daily) — MONITOR

212 trades, PF 1.17, WR 62.7%. Avg hold 4.3 days.
- Long: PF 1.39, WR 66.0% — **this is the real edge**
- Short: PF 0.97, WR 59.4% — flat, no edge
- H1: PF 1.11 | H2: PF 1.25 (walk-forward passes)
- 2020: PF 0.34, -$3,117 (catastrophic)
- 4/8 years negative

Year consistency too poor for direct promotion. Long-only variant may be
salvageable if 2020 drawdown can be regime-filtered. Monitor.

### #5 ATR-Filtered VWAP-MNQ — MODERATE

ATR vol regime filter adds +0.12 PF to VWAP-MNQ parent. Fewer trades,
higher quality. Validates the component catalog concept. Not a standalone
strategy — component integration for core workhorse improvement.

---

## Portfolio Gap Status After Sprint

| Gap | Status | Next Action |
|-----|--------|-------------|
| Energy (MCL) | **UNFILLED** — 0/2 prototypes worked | Wait for Claw harvest new MCL ideas |
| Non-morning session | Partially filled (ZN-Afternoon probation) | Accumulate forward evidence |
| Mean reversion stabilizer | IBS/RSI2 both MONITOR | Long-only RSI2 variant worth revisiting |
| Daily horizon | IBS/RSI2 both daily MONITOR | Same as above |
| M2K short exposure | RSI2 short side flat | No viable short M2K edge found |
| Vol expansion (non-equity) | HV Percentile REJECTED | Need different approach for non-equity vol |

**Key insight:** Energy remains the hardest gap to fill. Two independent
MCL approaches (settlement reversion, vol compression) both failed.
The market may simply not offer the same microstructure edges that
equities/rates provide. Need fundamentally different Energy ideas from
Claw harvest — possibly EIA event, crack spread, or seasonal patterns.

---

## System Posture

Sprint complete. Return to monitoring mode:
1. Let forward evidence accumulate for probation strategies
2. Let Claw harvest produce new Energy ideas
3. RSI2-Bounce long-only variant queued for future revisit
4. No new builds unless data forces it
