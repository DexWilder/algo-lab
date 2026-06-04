# FQL Forge — Spec A: EVT-Treasury-Auction-Drift-Snap-ZN

**Date:** 2026-06-03 • Mode: dry-run / report-only / Lane B
**Authority:** T1; no registry mutation; no Lane A touch
**Harness:** `research/event_window_engine.py` (built 2026-06-02; smoke-passed 2026-06-03)
**Calendar:** Minimum viable — 2nd Wednesday/month @ 13:00 (96 events 2019-2026).

## Rules tested

- **LONG leg** (post-auction reversion): entry +1 bar after event, exit +24 bars later (~2h hold)
- **SHORT leg** (pre-auction concession): entry -12 bars before event (~1h before), exit at event

## LONG leg result

| Field | Value |
|---|---:|
| n | 84 |
| Net PF | 0.528 |
| Median | $-49.98 |
| Net PnL | $-3589 |
| Max DD | $-3723 |
| Win rate | 29.8% |
| Max-year share | 0.0% |
| Top-3 | 0.0% |
| Top-10 | 0.0% |
| H1 / H2 PF | 0.455 / 0.589 |
| Years+ | 2/8 |
| Archetype | UNKNOWN | gate | KILL |
| **Verdict** | **KILL** |

## SHORT leg result

| Field | Value |
|---|---:|
| n | 83 |
| Net PF | 0.391 |
| Median | $-49.98 |
| Net PnL | $-4695 |
| Max DD | $-4795 |
| Win rate | 25.3% |
| Max-year share | 0.0% |
| Top-3 | 0.0% |
| Top-10 | 0.0% |
| H1 / H2 PF | 0.356 / 0.415 |
| Years+ | 2/8 |
| Archetype | UNKNOWN | gate | KILL |
| **Verdict** | **KILL** |

## Safety

- No registry mutation • no Lane A touch • no scheduler change
- Calendar is a 2nd-Wed proxy; not a real auction calendar. Refine to actual auction
  dates (treasurydirect.gov) only if cheap-screen verdict warrants deeper screen.
