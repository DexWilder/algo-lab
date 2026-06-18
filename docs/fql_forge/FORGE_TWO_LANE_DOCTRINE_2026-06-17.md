# Forge Two-Lane Doctrine — 2026-06-17

> Correction (operator 2026-06-17): the **"non-gold / non-MNQ" constraint applies ONLY to the WH2 diversification lane — it is NOT a global Forge restriction.** The paper-ready bench is still small, so Forge must keep improving the strongest sleeves we already have (MNQ, MGC/gold) while separately hunting a true diversifier. Report-only; no activation/registry/scheduler/portfolio/paper/live/prop mutation without explicit approval.

## Two parallel lanes

### Lane 1 — WH2 diversifier hunt
Prioritize **non-gold, non-MNQ** structural/flow/event mechanisms: auction-flow, roll-yield, inventory-surprise, settlement/calendar flow, positioning/proxy, cross-asset forced-flow. Generic gold/MNQ variants are excluded **from this lane only**, unless they can prove true portfolio distinctness.

### Lane 2 — Paper-bench / sleeve-improvement hunt
**MNQ and MGC/gold research is ALLOWED here.** Search for better workhorses, replacements, overlays, and packet-grade candidates on the sleeves we already run. Apply duplicate-family review + exposure controls before any promotion.

## Required classification for ANY new MNQ/MGC discovery (honest, evidence-based)
1. **Same-sleeve REPLACEMENT** — only if clearly better than the existing book on net PF, OOS, median, concentration, drawdown, prop fit, AND evidence integrity.
2. **Same-sleeve ADDITION** — only if signal overlap, bad-day overlap, regime exposure, and portfolio contribution show it is NOT just duplicate exposure.
3. **OVERLAY / ENHANCER** — useful as a filter, sizing switch, or timing layer; not a new independent strategy.
4. **TRUE DIVERSIFIER** — only if portfolio evidence proves distinct behavior, not merely strong topline metrics.

A strong topline metric alone does NOT earn "diversifier" or even "addition" — it must clear the overlap/exposure tests. (Same discipline that capped the P8 real-rate gate at gold-timing, and that killed gold conditioners OOS.)

## Re-homing existing finds under this doctrine
- **P8 real-rate long-only gold gate** (OOS-consistent, PF 1.209, corr-to-gold 0.57) → now a **Lane 2 category-3 OVERLAY/ENHANCER candidate** for the MGC sleeve (timing layer), NOT a WH2. Previously banked as "marginal gold-sleeve enhancer" — this doctrine gives it a proper home + evaluation path (does it improve the *combined gold sleeve's* net PF / DD / bad-day profile, with duplicate-exposure controls?).
- **MGC-prior_day_break** (additive to MGC-ORB, corr +0.244) → Lane 2 category-2 **same-sleeve ADDITION** candidate (already passed the not-duplicate test; gated on MGC soft-cap).
- **MNQ stop_run_reversal** (wired Phase 1C) and **XB-ORB-EMA-Ladder-MNQ** → the incumbent MNQ workhorse books Lane 2 improvements would be measured against.

## Lane status
- **Lane 1** continuing: structural feeds queued (`STAGING_MANIFEST.md` #1 auctions, #2 F2 roll, #3 EIA surprise); reachable cross-asset tests mostly KILL (price/ratio overlays look arbitraged) → frontier = the blocked structural feeds.
- **Lane 2** re-opened: evaluate the P8 gold overlay properly; hunt MNQ/MGC workhorse replacements/additions with duplicate-family + exposure controls. Gold guardrails still apply (don't double-count gold beta; soft-cap).

## Reachable-surface framing (corrected 2026-06-17 — do NOT over-claim "exhausted")
**Wrong:** "the reachable-data surface for daily WH2 is mapped/exhausted." **Right:** *"the currently-tested reachable daily macro/ratio OVERLAY surface has produced no WH2; structural forced-flow feeds are now the highest-EV frontier, but reachable discovery continues with tighter mechanism filters."* "Exhausted" quietly becomes "wait for files" — the anti-pattern. So:
1. **Lane 1 priority = structural feeds now** (auctions → rates F2/roll → EIA surprise). Simple price/ratio overlays demonstrably aren't producing edge.
2. **Lane 1 keeps a SMALL reachable-discovery thread alive** — NOT random/generic OHLCV screens, but any plausible **forced-flow / calendar / settlement / proxy** mechanism on reachable data (e.g. surfaced by Claw) gets tested.
3. **Lane 2 sleeve-improvement continues** — MGC-prior_day_break (cat-2 addition) review + MNQ/MGC replacement/addition/overlay candidates.

## Global evidence rule (locked 2026-06-17)
**Gap-clean any external/feed series BEFORE rolling means, rolling changes, z-scores, percentile ranks, or regime labels** (raw NaN holes poison rolling windows → silent false regimes). Sanity-check derived regime base rates (implausible firing/retention rate = plumbing bug, not a finding). See memory `clean-before-rolling`. This caught + retracted the P8 false-enhancer.

## No-repeat archive (additions)
- **P8 real-rate gold gate** — fully dead (not WH2 / not diversifier / not overlay; the 17f "enhancer" was a NaN artifact, retracted). Do not re-surface. The gold sleeve is better WITHOUT the real-rate gate.

## Boundaries
Both lanes report-only. No mutation, no promotion, no activation without explicit approval. "Keep hunting outside gold/MNQ for diversification, but do not stop improving the strongest sleeves we already have." And: structural feeds are highest-EV, but that must NOT become "stop hunting until files arrive."
