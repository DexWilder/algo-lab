# FQL Forge Morning Digest — 2026-05-06

**Generated:** 2026-05-06T08:22:17
**Source fire date:** 2026-05-05
**Source artifacts:** `forge_daily_2026-05-05.{md,json}` + queue + tripwires + logs
**Scope:** Lane B / Forge — daily review packet (read-only)

**Safety contract:** report-only; no registry / Lane A / portfolio / runtime / scheduler / checkpoint mutation.

---

## 1. Executive Summary

### Last Forge run: ✅ **COMPLETE**

- date: **2026-05-05**
- run mode: dry-run
- candidates tested: 5
- runtime: 74.3s (limit 300s)
- verdicts: **PASS 2 / WATCH 3 / KILL 0 / RETEST 0**
- tripwires: 0

### Action needed

- REVIEW 2 PASS candidate(s) — see §2 for details

---

## 2. Candidate Results

| Candidate | Asset | Verdict | PF | n | Net PnL | Repeat? | Registered? |
|---|---|---:|---:|---:|---:|---|---|
| `XB-PB-EMA-Ladder-MES` | MES | **WATCH** | 1.151 | 1473 | $6627 | — | — |
| `XB-PB-EMA-Ladder-MGC` | MGC | **WATCH** | 1.187 | 855 | $5177 | — | — |
| `XB-PB-EMA-Ladder-MCL` | MCL | **PASS** | 1.309 | 1062 | $7346 | — | ✅ in registry |
| `XB-PB-EMA-Ladder-MYM` | MYM | **PASS** | 1.351 | 462 | $4044 | — | ✅ in registry |
| `XB-BB-EMA-Ladder-MES` | MES | **WATCH** | 1.116 | 683 | $2377 | — | — |

### Architecture notes
- PASS assets this fire: ['MCL', 'MYM']
- **NEW PASSes (not seen in prior 7 days):** ['XB-PB-EMA-Ladder-MCL', 'XB-PB-EMA-Ladder-MYM']

---

## 3. Queue Changes

### Current rolling queue (`forge_queue.md`)

**Recommended next candidates** (from rolling queue):
  - XB-BB-EMA-Ladder-MGC (Workhorse cross-asset, asset=MGC)
  - XB-BB-EMA-Ladder-MCL (Workhorse cross-asset / energy, asset=MCL)
  - XB-BB-EMA-Ladder-MYM (Workhorse cross-asset, asset=MYM)
  - XB-VWAP-EMA-Ladder-MES (Workhorse cross-asset / VWAP closeout test, asset=MES)
  - XB-VWAP-EMA-Ladder-MGC (Workhorse cross-asset / VWAP closeout test, asset=MGC)

### Aging analysis
- v2 TODO: snapshot queue daily and surface entries that have been recommended for >7 days without action

---

## 4. Evidence Absorption Status

### Counts

- distinct PASS candidates across prior 7 days + today: **2**
  - already in registry: **2** ✅
  - **awaiting review (not in registry):** **0**
- daily Forge reports on disk: 1

### Backlog status: 🟢 **GREEN — IN BALANCE**
- thresholds: GREEN ≤ 5 / YELLOW ≤ 15 / RED > 15

---

## 5. Automation Health

### Runtime
- total: 74.3s (limit 300s, threshold to fire 'runtime_overrun' tripwire)
- ✅ comfortably within limit

### stderr (`research/logs/forge_daily_loop_stderr.log`)

- empty ✅

### stdout (`research/logs/forge_daily_loop_stdout.log`)

- size: 0.8 KB; last modified: 13.3h ago

### Tripwires

- ✅ none

---

## 6. Recommended Next Action

### Operator action
- **REVIEW 2 PASS candidate(s) — see §2 for details**

### Safe Forge action
- **continue scheduled fires**

### Mode
- **🟢 CONTINUE — review PASSes when ready**

---
