# TRUTH_RESET — causality-first research doctrine (locked 2026-06-25)

> Triggered by the ORB `ema_slope` same-day-close lookahead reaching dossiers, sizing, and portfolio framing
> before the audit. The capital gate held; the **research gate fired too late**. This doctrine moves the truth
> check to the FRONT of the pipeline. Standing doctrine until explicitly revised by the operator.

## The failure pattern (now banned)
`idea → backtest → screen pass → analysis → narrative/dossier/sizing → (later) deep audit → VOID → rebuild`
This produced repeated false positives (ORB lookahead, XSMOM rollover artifact, several cost/data bugs). The
problem is NOT that bugs were found — it is that they were found AFTER confident language and downstream work.

## The required order of operations
`idea → CAUSALITY AUDIT (harness) → cost/data-lineage check → THEN backtest → THEN screen → THEN (labels)`
**No strategy is evaluated for edge until its harness is proven clean first.** The harness audits the *machine*,
not the strategy.

## Mandatory preflight — `research/causality_audit.py`
Every strategy/recipe MUST pass before any edge claim:
- **A. Future-perturbation invariance** (core): signals at bars ≤ T must be invariant to ANY change in bars > T
  (tested with ×3-up vs ×0.33-down future perturbations, including pre-session-close splits). Failure = lookahead.
- **B. Cost sensitivity**: net PnL must change under cost stress when turnover>0 (catches silent zero-cost/unwired costs).
- **C. Rollover-artifact scan**: continuous-future daily |move|>8% count (flags roll-stitch contamination).
- (Clears `_FEATURE_CACHE` around perturbations — cache key ignores close content, a known sharp-edge.)
`CAUSAL_CLEAN` on A is the gate; B/C are quality flags. Certification: the harness PASSES the fixed ORB and
CATCHES the contaminated ORB (run `python3 research/causality_audit.py`).

Also standing: the daily-aggregate regression test `research/test_no_lookahead_daily_filters.py`.

## Hard vocabulary rules
The following words are FORBIDDEN for any strategy that has not passed the causality harness (+ standard gates):
`proven`, `validated`, `primary engine`, `workhorse`, `ready`, `dossier-complete`, `deployment candidate`,
`research-candidate`.
Until a strategy passes, the ONLY permitted labels are:
`IDEA` · `SCREEN_PASS` · `UNAUDITED` · `POINT_IN_TIME_PENDING` · `DATA_BLOCKED` · `INVALIDATED` · `CLEAN_RESEARCH_CANDIDATE`
A strategy reaches `CLEAN_RESEARCH_CANDIDATE` only after: causality CAUSAL_CLEAN + costs wired + data-lineage clean
+ standard concentration/DSR gates. "Validated/primary/workhorse" requires that PLUS operator review. Language
drives decisions — the old language got confident too early.

## Label downgrades (effective 2026-06-25)
- **ORB (XB-ORB-EMA-Ladder, all assets):** `INVALIDATED` (lookahead; clean Sharpe ≤0.86, mostly ≤0).
- **Small-diversifier dossier:** VOID as written (rationale was "improve ORB").
- **MGC vol_low:** VOID (ORB refinement).
- **CV1/CV2/CV3/CV3-R:** VOID (measured against a non-edge).
- **TSMOM, vol-carry:** `POINT_IN_TIME_PENDING` — independent of ORB, must be re-audited STANDALONE as potential primaries.
- **All non-ORB probation books** (ZN-Afternoon-Reversion, Treasury-Rolldown, TV-NFP, etc.): `UNAUDITED` until harnessed.
- **There is currently NO validated primary workhorse.**

## TRUTH_RESET work queue (in order; normal new-WH discovery is PAUSED until cleared)
1. ✅ Build + certify the causality harness (`research/causality_audit.py`).
2. TSMOM standalone causality + standalone-edge audit.
3. Vol-carry standalone causality + standalone-edge audit.
4. Point-in-time audit of every non-ORB active/probation book.
5. Only then: resume new WH discovery — each new idea preflighted by the harness.

## Capital gate — unchanged, fail-closed
No promotion, sizing, wiring, registry, scheduler, portfolio mutation, or paper/live action. No narratives before
causality proof.
