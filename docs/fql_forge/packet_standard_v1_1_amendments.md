# Packet Standard V1.1 Amendments (Operator-Authorized)

> **Status:** Ratified by operator 2026-06-12 in #179 and #180 decisions.
> **Type:** Doctrine clarification amendments under operator authority.
> **Authority basis:** Direct operator instruction, not emergency integrity defect.
> **Retroactive application:** Per V1.1 enforcement clause — all affected candidates listed below, rules applied uniformly.

## V1.1 Amendment A — Probationary status interpretation

> **V1 Portfolio Classification Amendment:**
> Probationary strategies do NOT count as ACCEPTED strategies for formal PORTFOLIO_COMPLEMENT classification.
> However, probationary strategies DO count as ACTIVE EXPOSURE for family-review, correlation warning, candidate coexistence, and paper allocation caution.
> Therefore, a new candidate may remain a standalone PAPER_PACKET_CANDIDATE despite moderate correlation to a probationary strategy, but MUST carry an ACTIVE_EXPOSURE_WARNING until coexistence is reviewed.

### What this changes

Prior ambiguity: "PORTFOLIO_COMPLEMENT requires moderate correlation to an existing ACCEPTED strategy." Unclear whether probation counts as accepted.

Resolution:
- **ACCEPTED strategy** = can define formal PORTFOLIO_COMPLEMENT classification
- **PROBATION strategy** = does NOT block standalone classification, BUT requires ACTIVE_EXPOSURE_WARNING and coexistence review
- **Archived strategy** = used for family review only; cannot define PORTFOLIO_COMPLEMENT (no portfolio role)

### Affected candidates (retroactive application — V1.1 enforcement)

| Candidate | Pre-amendment | Post-amendment |
|---|---|---|
| WH-MNQ-stop_run_reversal | PORTFOLIO_COMPLEMENT vs XB-ORB-MNQ probation (corr 0.327) — interpretation A | **PAPER_PACKET_CANDIDATE with ACTIVE_EXPOSURE_WARNING** (probation doesn't block standalone) |
| WH-MNQ-range_compression_break | PORTFOLIO_COMPLEMENT (corr 0.495) — interpretation A | **PAPER_PACKET_CANDIDATE with ACTIVE_EXPOSURE_WARNING** (interpretation B per ratification) |
| FOMC-MNQ-Long-1h | Independent; not affected by this amendment | unchanged |

## V1.1 Amendment B — Max-event-share interpretation (loss-tail absorption)

> **Max-event-share concentration MUST be interpreted by sign.**
> If the max event by absolute PnL is a WINNING event, threshold failure is a concentration/lucky-win fragility warning.
> If the max event is a LOSING event, threshold failure is a loss-tail warning. If removing that loss IMPROVES PF and all other robustness checks survive, classify as LOSS_TAIL_ABSORPTION rather than concentration failure.
> Such candidates may receive PASS_WITH_LOSS_TAIL_WARN, NOT CLEAN_PASS.

### What this changes

Prior ambiguity: max-event-share check was symmetric. A strategy that absorbs a worst-case loss was equally penalized as one that depended on a lucky win.

Resolution:
- **Max event is a WIN** + exceeds threshold → CONCENTRATION_FRAGILITY (potential lucky-win carry; flag as concerning)
- **Max event is a LOSS** + exceeds threshold + removing it INCREASES PF → LOSS_TAIL_ABSORPTION (strategy is robust to worst-case loss; flag as warning but not fail)
- Such candidates receive label `PASS_WITH_LOSS_TAIL_WARN` (not CLEAN_PASS, not FAIL)

### Affected candidates (retroactive application)

| Candidate | Prior | Post-amendment |
|---|---|---|
| FOMC-MNQ-Long-1h | ROBUSTNESS PARTIAL (1 fail on max-event-share 16.9%) | **PASS_WITH_LOSS_TAIL_WARN** — max event is the 2022-01-26 LOSS of -$1152 (35.4% absolute), removing it improves PF 1.774 → 2.443 |

## V1.1 enforcement compliance check

Per V1.1 enforcement clause:
1. ✅ Every prior candidate affected listed (above tables)
2. ✅ New rules applied retroactively in a single audit pass (this document)
3. ✅ Not applied selectively (uniformly to all affected candidates)
4. ✅ Verdict changes stated explicitly (above tables)
5. ✅ Inventory table updated once (V1 inventory rescore doc reference)

## Inventory implications

After V1.1 amendments, the locked sprint state per operator:

| Lane | Candidate | Status |
|---|---|---|
| Daily workhorse | **WH-MNQ-stop_run_reversal** | **PAPER_PACKET_CANDIDATE — pending final robustness (primary daily foundation lead)** |
| Daily workhorse | WH-MNQ-range_compression_break | PAPER_PACKET_CANDIDATE — pending final robustness + ACTIVE_EXPOSURE_WARNING (secondary / possible complement after robustness) |
| Daily workhorse | XB-ORB-EMA-Ladder-MNQ | PROBATION (counts for ACTIVE_EXPOSURE, not for formal complement classification) |
| Event tail | FOMC-MNQ-Long-1h | REVIEW-GRADE PAPER_PACKET_CANDIDATE — PASS_WITH_LOSS_TAIL_WARN |

## Cross-reference

- [[packet_standard_v1]] — base V1 spec
- [[packet_standard_v1_change_control]] — V1.1 enforcement clause
- `docs/fql_forge/PACKET_STANDARD_V1_2026-06-11.md` (base spec amended to reference this)
- `docs/fql_forge/packet_standard_v1_inventory_rescore.md` (inventory rescore updated)
